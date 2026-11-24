"""Módulo de segurança multi-tenant: Tokens HMAC-SHA256, prevenção de SSRF e Rate Limiting por Tenant."""

import base64
import hashlib
import hmac
import ipaddress
import json
import threading
import time
from collections import defaultdict, deque
from typing import Any, Deque, Dict, Optional
from urllib.parse import urlparse

from src.core.config import (
    ALLOW_MOCK_URLS,
    HARDTRACK_SECRET_KEY,
    RATE_LIMIT_RPM,
    TOKEN_TTL_SECONDS,
)


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(data: str) -> bytes:
    padding = "=" * ((4 - len(data) % 4) % 4)
    return base64.urlsafe_b64decode(data + padding)


def create_tenant_token(
    tenant_id: str,
    tipo: str,
    ttl_seconds: int = TOKEN_TTL_SECONDS,
    secret_key: Optional[str] = None,
) -> str:
    """Emite um token JWT-like (HS256) vinculado estritamente ao tenant_id."""
    key = (secret_key or HARDTRACK_SECRET_KEY).encode("utf-8")
    now = int(time.time())

    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "sub": tenant_id,
        "tipo": tipo,
        "iat": now,
        "exp": now + ttl_seconds,
        "iss": "hardtrack-saas",
    }

    header_b64 = _b64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    payload_b64 = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{header_b64}.{payload_b64}".encode("ascii")

    signature = hmac.new(key, signing_input, hashlib.sha256).digest()
    sig_b64 = _b64url_encode(signature)
    return f"{header_b64}.{payload_b64}.{sig_b64}"


def verify_tenant_token(
    token: str,
    secret_key: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Valida assinatura HMAC-SHA256 e expiração do token em tempo constante."""
    if not token or not isinstance(token, str):
        return None

    parts = token.strip().split(".")
    if len(parts) != 3:
        return None

    header_b64, payload_b64, sig_b64 = parts
    key = (secret_key or HARDTRACK_SECRET_KEY).encode("utf-8")

    try:
        signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
        expected_sig = _b64url_encode(hmac.new(key, signing_input, hashlib.sha256).digest())
        if not hmac.compare_digest(sig_b64, expected_sig):
            return None

        payload = json.loads(_b64url_decode(payload_b64).decode("utf-8"))
        if not isinstance(payload, dict) or "sub" not in payload:
            return None

        exp = payload.get("exp")
        if exp is None or int(time.time()) > int(exp):
            return None

        return payload
    except Exception:
        return None


_BLOCKED_HOSTNAMES = {
    "localhost",
    "localhost.localdomain",
    "ip6-localhost",
    "ip6-loopback",
    "metadata.google.internal",
    "metadata",
}


def validate_monitor_url(url: str, allow_mock: Optional[bool] = None) -> str:
    """Valida URL de monitoramento prevenindo SSRF e esquemas inseguros.

    Permite estritamente `http://` e `https://` para hosts públicos (e `mock://`/`test://`
    quando habilitado para testes determinísticos). Bloqueia:
    - Esquemas perigosos (`file://`, `ftp://`, `javascript:`, `gopher://`, `data:`)
    - Endereços de loopback, redes privadas RFC1918 e metadados cloud (`169.254.169.254`).
    """
    if not url or not isinstance(url, str):
        raise ValueError("URL é obrigatória.")

    cleaned = url.strip()
    parsed = urlparse(cleaned)
    scheme = (parsed.scheme or "").lower()

    mock_allowed = ALLOW_MOCK_URLS if allow_mock is None else allow_mock
    allowed_schemes = {"http", "https"} | ({"mock", "test"} if mock_allowed else set())

    if scheme not in allowed_schemes:
        raise ValueError(
            f"Esquema de URL não permitido: '{scheme or 'ausente'}'. "
            "Permitido apenas http:// ou https:// (proteção contra SSRF/injeção)."
        )

    hostname = (parsed.hostname or "").lower()
    if not hostname:
        raise ValueError("URL inválida: hostname ausente.")

    # Em modo mock/test, exige apenas hostname válido sem navegação de caminho suspeita
    if scheme in ("mock", "test"):
        return cleaned

    if hostname in _BLOCKED_HOSTNAMES or hostname.endswith(".local") or hostname.endswith(".internal"):
        raise ValueError(
            f"Host '{hostname}' bloqueado por política anti-SSRF (destino interno/local não permitido)."
        )

    # Bloqueio de IPs literais privados, loopback, link-local (ex: 169.254.169.254) ou reservados
    try:
        ip_obj = ipaddress.ip_address(hostname)
        if (
            ip_obj.is_private
            or ip_obj.is_loopback
            or ip_obj.is_link_local
            or ip_obj.is_multicast
            or ip_obj.is_reserved
            or ip_obj.is_unspecified
        ):
            raise ValueError(
                f"Endereço IP '{hostname}' bloqueado por política anti-SSRF (rede privada/loopback/metadata)."
            )
    except ValueError as exc:
        # Se foi nossa própria exceção anti-SSRF, relança; caso contrário é um domínio DNS normal
        if "bloqueado por política anti-SSRF" in str(exc):
            raise

    return cleaned


class TenantRateLimiter:
    """Rate limiter por tenant em janela deslizante (proteção contra Noisy Neighbor / HTTP 429)."""

    def __init__(self, max_requests_per_minute: int = RATE_LIMIT_RPM):
        self.max_requests = max_requests_per_minute
        self.window_seconds = 60.0
        self._hits: Dict[str, Deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def allow_request(self, tenant_id: str) -> bool:
        """Retorna True se o tenant está dentro do limite, False se excedeu (HTTP 429)."""
        if self.max_requests <= 0:
            return True
        now = time.monotonic()
        cutoff = now - self.window_seconds
        with self._lock:
            bucket = self._hits[tenant_id]
            while bucket and bucket[0] < cutoff:
                bucket.popleft()
            if len(bucket) >= self.max_requests:
                return False
            bucket.append(now)
            return True

    def reset(self, tenant_id: Optional[str] = None) -> None:
        """Reseta contadores (útil em testes automatizados)."""
        with self._lock:
            if tenant_id is None:
                self._hits.clear()
            else:
                self._hits.pop(tenant_id, None)


# Instância global compartilhada pelo Gateway da API
tenant_rate_limiter = TenantRateLimiter(max_requests_per_minute=RATE_LIMIT_RPM)

"""Testes unitários dos componentes core (tokens, anti-SSRF, parser de preços, afiliados e cotas)."""

import pytest

from src.core.models import TenantType
from src.core.security import (
    TenantRateLimiter,
    create_tenant_token,
    validate_monitor_url,
    verify_tenant_token,
)
from src.core.storage import TenantStorageManager
from src.worker.notifier import TelegramNotifier
from src.worker.scraper import parse_price_string


def test_token_roundtrip_and_tampering_detection():
    """Garante emissão, validação e detecção de adulteração de tokens HMAC-SHA256."""
    token = create_tenant_token("joao_b2c", "B2C_ENTUSIASTA", ttl_seconds=3600, secret_key="chave-teste")
    payload = verify_tenant_token(token, secret_key="chave-teste")
    assert payload is not None
    assert payload["sub"] == "joao_b2c"
    assert payload["tipo"] == "B2C_ENTUSIASTA"

    # Assinatura com outra chave deve falhar
    assert verify_tenant_token(token, secret_key="outra-chave") is None

    # Adulteração de 1 caractere na assinatura deve falhar
    tampered = token[:-1] + ("A" if token[-1] != "A" else "B")
    assert verify_tenant_token(tampered, secret_key="chave-teste") is None


def test_token_expiration():
    """Token expirado (TTL negativo) deve ser rejeitado."""
    expired = create_tenant_token("joao_b2c", "B2C_ENTUSIASTA", ttl_seconds=-10, secret_key="chave-teste")
    assert verify_tenant_token(expired, secret_key="chave-teste") is None


def test_validate_monitor_url_accepts_public_and_mock():
    """Aceita URLs públicas HTTP/HTTPS e mock:// em modo de testes."""
    assert validate_monitor_url("https://www.kabum.com.br/produto/123", allow_mock=False).startswith("https://")
    assert validate_monitor_url("http://terabyte.com.br/gpu", allow_mock=False).startswith("http://")
    assert validate_monitor_url("mock://kabum.com.br/rtx4060?price=2350", allow_mock=True).startswith("mock://")


@pytest.mark.parametrize(
    "bad_url",
    [
        "file:///etc/passwd",
        "ftp://servidor.com/arquivo",
        "javascript:alert(1)",
        "http://127.0.0.1:8000/health",
        "http://localhost:8000/tenants",
        "http://169.254.169.254/latest/meta-data/",
        "http://10.0.0.1/interno",
        "http://192.168.1.1/roteador",
        "https://metadata.google.internal/computeMetadata/v1/",
    ],
)
def test_validate_monitor_url_blocks_ssrf_and_bad_schemes(bad_url: str):
    """Bloqueia SSRF (loopback, RFC1918, cloud metadata) e esquemas não HTTP."""
    with pytest.raises(ValueError):
        validate_monitor_url(bad_url, allow_mock=True)


def test_affiliate_link_injection():
    """Garante injeção da tag comercial de afiliados preservando parâmetros originais."""
    notifier = TelegramNotifier(mock_mode=True)
    enriched = notifier.generate_affiliate_link("https://www.kabum.com.br/produto/999?promo=1")
    assert "tag=hardtrack-20" in enriched
    assert "utm_source=hardtrack_saas" in enriched
    assert "promo=1" in enriched


def test_plan_quotas_b2c_vs_b2b():
    """Valida diferenciação de cotas entre B2C Freemium (5) e B2B Pro (50)."""
    assert TenantStorageManager.get_quota_for_type(TenantType.B2C_ENTUSIASTA) == 5
    assert TenantStorageManager.get_quota_for_type(TenantType.B2B_OFICINA) == 50


def test_rate_limiter_isolates_buckets_per_tenant():
    """Rate limiter bloqueia apenas o tenant que excedeu o limite sem afetar o vizinho."""
    limiter = TenantRateLimiter(max_requests_per_minute=2)
    assert limiter.allow_request("tenant_a") is True
    assert limiter.allow_request("tenant_a") is True
    assert limiter.allow_request("tenant_a") is False  # 3ª req bloqueada
    # Vizinho permanece livre
    assert limiter.allow_request("tenant_b") is True


def test_parse_price_edge_cases():
    """Valida cenários de borda do parser de preços."""
    assert parse_price_string("R$ 12.499,90") == 12499.90
    assert parse_price_string("R$ 0,00") is None
    assert parse_price_string("Produto indisponível") is None

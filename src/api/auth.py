"""Dependências de Autenticação, Autorização por Tenant (AuthZ) e Rate Limiting da API."""

import hmac
from typing import Any, Dict, Optional
from fastapi import Header, HTTPException, status

from src.core import config as core_config
from src.core.security import tenant_rate_limiter, verify_tenant_token


def extract_token(
    authorization: Optional[str] = None,
    x_tenant_token: Optional[str] = None,
) -> Optional[str]:
    """Extrai o token Bearer do header Authorization ou do header alternativo X-Tenant-Token."""
    if authorization:
        parts = authorization.strip().split(" ", 1)
        if len(parts) == 2 and parts[0].lower() == "bearer":
            return parts[1].strip()
    if x_tenant_token:
        return x_tenant_token.strip()
    return None


def require_tenant_access(
    tenant_id: str,
    authorization: Optional[str] = Header(default=None),
    x_tenant_token: Optional[str] = Header(default=None, alias="X-Tenant-Token"),
    x_tenant_id: Optional[str] = Header(default=None, alias="X-Tenant-ID"),
) -> Dict[str, Any]:
    """Garante AuthN + AuthZ por Tenant + Anti-Header-Spoofing + Rate Limiting por Tenant.

    - Sem token ou token inválido/expirado -> 401 Unauthorized
    - Token pertence a outro tenant ou X-Tenant-ID forjado -> 403 Forbidden
    - Excesso de requisições do tenant (Noisy Neighbor) -> 429 Too Many Requests
    """
    token = extract_token(authorization=authorization, x_tenant_token=x_tenant_token)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de autenticação ausente. Informe 'Authorization: Bearer <token>'.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = verify_tenant_token(token, secret_key=core_config.HARDTRACK_SECRET_KEY)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de autenticação inválido ou expirado.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token_tenant = str(payload.get("sub", ""))

    # Bloqueio de Header Spoofing (mesmo se o cliente tentar injetar X-Tenant-ID de outro cliente)
    if x_tenant_id is not None and x_tenant_id.strip() != token_tenant:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                f"Acesso negado: header X-Tenant-ID ('{x_tenant_id}') diverge "
                f"da identidade autenticada do token ('{token_tenant}')."
            ),
        )

    # Bloqueio de acesso Cross-Tenant (IDOR)
    if token_tenant != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                f"Acesso cross-tenant bloqueado: token do tenant '{token_tenant}' "
                f"não está autorizado a acessar recursos do tenant '{tenant_id}'."
            ),
        )

    # Proteção contra Noisy Neighbor (Rate Limiting isolado por tenant)
    if not tenant_rate_limiter.allow_request(token_tenant):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                f"Limite de requisições excedido para o tenant '{token_tenant}'. "
                "Tente novamente em instantes."
            ),
        )

    return payload


def require_admin_key(
    x_admin_key: Optional[str] = Header(default=None, alias="X-Admin-Key"),
) -> bool:
    """Protege operações administrativas globais contra enumeração não autorizada de tenants."""
    if not x_admin_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credencial administrativa ausente (header X-Admin-Key obrigatório).",
        )
    if not hmac.compare_digest(x_admin_key.strip(), core_config.HARDTRACK_ADMIN_KEY):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Credencial administrativa inválida.",
        )
    return True

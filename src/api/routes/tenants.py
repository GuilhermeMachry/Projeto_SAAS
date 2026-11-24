"""Rotas para gerenciamento do ciclo de vida do Tenant, autenticação e atendimento à LGPD."""

import hmac
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, Header, HTTPException, status

from src.api.auth import extract_token, require_admin_key, require_tenant_access
from src.core import config as core_config
from src.core.models import (
    SiloInfoResponse,
    TenantAuthResponse,
    TenantCreate,
    TenantResponse,
    TokenRequest,
)
from src.core.security import create_tenant_token, verify_tenant_token
from src.core.storage import TenantStorageManager

router = APIRouter(prefix="/tenants", tags=["Tenants"])
auth_router = APIRouter(prefix="/auth", tags=["Autenticação"])
storage = TenantStorageManager()


@auth_router.post(
    "/token",
    response_model=TenantAuthResponse,
    status_code=status.HTTP_200_OK,
    summary="Autenticar tenant existente e emitir token Bearer HMAC-SHA256",
)
def issue_tenant_token(data: TokenRequest):
    """Autentica um tenant existente validando seu telegram_chat_id cadastrado."""
    try:
        tenant = storage.get_tenant(data.tenant_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    if not tenant or not hmac.compare_digest(tenant.telegram_chat_id, data.telegram_chat_id):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciais inválidas para o tenant informado.",
        )

    token = create_tenant_token(
        tenant_id=tenant.tenant_id,
        tipo=tenant.tipo.value,
        secret_key=core_config.HARDTRACK_SECRET_KEY,
    )
    return TenantAuthResponse(**tenant.model_dump(), access_token=token)


@router.post(
    "",
    response_model=TenantAuthResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Cadastrar novo tenant (ou atualizar perfil autenticado)",
)
def create_tenant(
    data: TenantCreate,
    authorization: Optional[str] = Header(default=None),
    x_tenant_token: Optional[str] = Header(default=None, alias="X-Tenant-Token"),
):
    """Cria um novo silo de dados exclusivo para o tenant especificado e emite seu token Bearer.

    Se o tenant já existir, exige credencial válida (chat_id correspondente ou token do próprio tenant)
    para evitar sequestro de conta (Tenant Hijacking).
    """
    try:
        existing = storage.get_tenant(data.tenant_id)
        if existing is not None:
            token = extract_token(authorization=authorization, x_tenant_token=x_tenant_token)
            payload = verify_tenant_token(token, secret_key=core_config.HARDTRACK_SECRET_KEY) if token else None
            owns_token = payload is not None and payload.get("sub") == existing.tenant_id
            matches_chat_id = hmac.compare_digest(existing.telegram_chat_id, data.telegram_chat_id)
            if not (owns_token or matches_chat_id):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Tenant '{data.tenant_id}' já existe. Autentique-se para atualizar seu perfil.",
                )

        tenant = storage.create_or_update_tenant(data)
        token = create_tenant_token(
            tenant_id=tenant.tenant_id,
            tipo=tenant.tipo.value,
            secret_key=core_config.HARDTRACK_SECRET_KEY,
        )
        return TenantAuthResponse(**tenant.model_dump(), access_token=token)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get(
    "",
    response_model=List[str],
    summary="Listar todos os IDs de tenants ativos (restrito a Admin)",
)
def list_tenants(_admin: bool = Depends(require_admin_key)):
    """Varre os silos do sistema e lista os identificadores de tenants cadastrados (requer X-Admin-Key)."""
    return storage.list_tenant_ids()


@router.get(
    "/{tenant_id}",
    response_model=TenantResponse,
    summary="Consultar dados do tenant autenticado",
)
def get_tenant(
    tenant_id: str,
    _auth: Dict[str, Any] = Depends(require_tenant_access),
):
    """Retorna os dados cadastrais do tenant consultando estritamente o seu silo."""
    try:
        tenant = storage.get_tenant(tenant_id)
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tenant '{tenant_id}' não encontrado.",
            )
        return tenant
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get(
    "/{tenant_id}/silo-info",
    response_model=SiloInfoResponse,
    summary="Consultar metadados de isolamento e cota do silo do tenant",
)
def get_tenant_silo_info(
    tenant_id: str,
    _auth: Dict[str, Any] = Depends(require_tenant_access),
):
    """Retorna informações operacionais do arquivo físico de silo do tenant (tamanho, chmod, cota)."""
    try:
        info = storage.get_silo_info(tenant_id)
        if not info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Silo do tenant '{tenant_id}' não encontrado.",
            )
        return info
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.delete(
    "/{tenant_id}",
    status_code=status.HTTP_200_OK,
    summary="Expurgo de Tenant (Conformidade com Art. 18 da LGPD)",
)
def delete_tenant(
    tenant_id: str,
    _auth: Dict[str, Any] = Depends(require_tenant_access),
):
    """Executa a eliminação física definitiva do arquivo de silo do tenant autenticado."""
    try:
        deleted = storage.delete_tenant(tenant_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tenant '{tenant_id}' não encontrado para expurgo.",
            )
        return {
            "status": "success",
            "message": f"Silo do tenant '{tenant_id}' excluído com sucesso em atendimento ao Art. 18 da LGPD.",
        }
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

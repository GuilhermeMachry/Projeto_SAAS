"""Rotas para gerenciamento do ciclo de vida do Tenant e atendimento à LGPD."""

from typing import List
from fastapi import APIRouter, HTTPException, status

from src.core.models import TenantCreate, TenantResponse
from src.core.storage import TenantStorageManager

router = APIRouter(prefix="/tenants", tags=["Tenants"])
storage = TenantStorageManager()


@router.post(
    "",
    response_model=TenantResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Cadastrar ou atualizar tenant",
)
def create_tenant(data: TenantCreate):
    """Cria um novo silo de dados exclusivo para o tenant especificado."""
    try:
        tenant = storage.create_or_update_tenant(data)
        return tenant
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get(
    "",
    response_model=List[str],
    summary="Listar todos os IDs de tenants ativos",
)
def list_tenants():
    """Varre os silos do sistema e lista os identificadores de tenants cadastrados."""
    return storage.list_tenant_ids()


@router.get(
    "/{tenant_id}",
    response_model=TenantResponse,
    summary="Consultar dados do tenant",
)
def get_tenant(tenant_id: str):
    """Retorna os dados cadastrais do tenant consultando estritamente o seu silo."""
    try:
        tenant = storage.get_tenant(tenant_id)
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tenant '{tenant_id}' não encontrado."
            )
        return tenant
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.delete(
    "/{tenant_id}",
    status_code=status.HTTP_200_OK,
    summary="Expurgo de Tenant (Conformidade com Art. 18 da LGPD)",
)
def delete_tenant(tenant_id: str):
    """Executa a eliminação física definitiva do arquivo de silo do tenant."""
    try:
        deleted = storage.delete_tenant(tenant_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tenant '{tenant_id}' não encontrado para expurgo."
            )
        return {
            "status": "success",
            "message": f"Silo do tenant '{tenant_id}' excluído com sucesso em atendimento ao Art. 18 da LGPD."
        }
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

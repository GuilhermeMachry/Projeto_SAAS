"""Rotas para cadastro de componentes, consulta de metas e histórico isolado por tenant."""

from typing import List
from fastapi import APIRouter, HTTPException, status

from src.core.models import (
    MonitorTargetCreate,
    MonitorTargetResponse,
    PriceRecord,
    AlertLog,
)
from src.core.storage import TenantStorageManager

router = APIRouter(prefix="/tenants/{tenant_id}", tags=["Monitoramento"])
storage = TenantStorageManager()


@router.post(
    "/targets",
    response_model=MonitorTargetResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Cadastrar componente para monitoramento no silo do tenant",
)
def add_monitor_target(tenant_id: str, data: MonitorTargetCreate):
    """Adiciona uma nova URL e meta de preço exclusivamente no arquivo do tenant."""
    try:
        target = storage.add_target(tenant_id, data)
        return target
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.get(
    "/targets",
    response_model=List[MonitorTargetResponse],
    summary="Listar componentes monitorados do tenant (Isolamento garantido)",
)
def list_monitor_targets(tenant_id: str):
    """Retorna os componentes monitorados pertencentes unicamente a este tenant."""
    try:
        # Verifica se o tenant existe
        if not storage.get_tenant(tenant_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tenant '{tenant_id}' não encontrado."
            )
        return storage.list_targets(tenant_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get(
    "/targets/{target_id}",
    response_model=MonitorTargetResponse,
    summary="Buscar componente específico monitorado pelo tenant",
)
def get_monitor_target(tenant_id: str, target_id: str):
    """Retorna dados de um componente específico do silo do tenant."""
    try:
        target = storage.get_target(tenant_id, target_id)
        if not target:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Componente '{target_id}' não encontrado no silo do tenant '{tenant_id}'."
            )
        return target
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.delete(
    "/targets/{target_id}",
    status_code=status.HTTP_200_OK,
    summary="Remover componente de monitoramento",
)
def delete_monitor_target(tenant_id: str, target_id: str):
    """Remove o componente de monitoramento do silo do tenant."""
    try:
        deleted = storage.delete_target(tenant_id, target_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Componente '{target_id}' não encontrado para remoção."
            )
        return {"status": "success", "message": f"Componente '{target_id}' removido com sucesso."}
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get(
    "/history",
    response_model=List[PriceRecord],
    summary="Consultar histórico de cotações capturadas do tenant",
)
def get_price_history(tenant_id: str, limit: int = 50):
    """Retorna o histórico cronológico gravado no silo do tenant."""
    try:
        if not storage.get_tenant(tenant_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tenant '{tenant_id}' não encontrado."
            )
        return storage.get_history(tenant_id, limit=limit)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get(
    "/alerts",
    response_model=List[AlertLog],
    summary="Consultar histórico de alertas disparados para o tenant",
)
def get_alert_history(tenant_id: str):
    """Retorna o histórico de notificações enviadas ao tenant."""
    try:
        if not storage.get_tenant(tenant_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tenant '{tenant_id}' não encontrado."
            )
        return storage.list_alerts(tenant_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

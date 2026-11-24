"""Rotas para cadastro de componentes, consulta de metas, varredura e histórico isolado por tenant."""

from typing import Any, Dict, List
from fastapi import APIRouter, Depends, HTTPException, status

from src.api.auth import require_tenant_access
from src.core.models import (
    AlertLog,
    MonitorTargetCreate,
    MonitorTargetResponse,
    MonitorTargetUpdate,
    PriceRecord,
    ScanResultResponse,
)
from src.core.storage import QuotaExceededError, TenantStorageManager
from src.worker.notifier import TelegramNotifier
from src.worker.runner import WorkerRunner
from src.worker.scraper import ScraperEngine

router = APIRouter(prefix="/tenants/{tenant_id}", tags=["Monitoramento"])
storage = TenantStorageManager()


@router.post(
    "/targets",
    response_model=MonitorTargetResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Cadastrar componente para monitoramento no silo do tenant",
)
def add_monitor_target(
    tenant_id: str,
    data: MonitorTargetCreate,
    _auth: Dict[str, Any] = Depends(require_tenant_access),
):
    """Adiciona uma nova URL e meta de preço exclusivamente no arquivo do tenant autenticado."""
    try:
        target = storage.add_target(tenant_id, data)
        return target
    except QuotaExceededError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.get(
    "/targets",
    response_model=List[MonitorTargetResponse],
    summary="Listar componentes monitorados do tenant (Isolamento e AuthZ garantidos)",
)
def list_monitor_targets(
    tenant_id: str,
    _auth: Dict[str, Any] = Depends(require_tenant_access),
):
    """Retorna os componentes monitorados pertencentes unicamente a este tenant."""
    try:
        if not storage.get_tenant(tenant_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tenant '{tenant_id}' não encontrado.",
            )
        return storage.list_targets(tenant_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get(
    "/targets/{target_id}",
    response_model=MonitorTargetResponse,
    summary="Buscar componente específico monitorado pelo tenant",
)
def get_monitor_target(
    tenant_id: str,
    target_id: str,
    _auth: Dict[str, Any] = Depends(require_tenant_access),
):
    """Retorna dados de um componente específico do silo do tenant."""
    try:
        target = storage.get_target(tenant_id, target_id)
        if not target:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Componente '{target_id}' não encontrado no silo do tenant '{tenant_id}'.",
            )
        return target
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.patch(
    "/targets/{target_id}",
    response_model=MonitorTargetResponse,
    summary="Atualizar meta de preço, nome ou URL de componente monitorado",
)
def update_monitor_target(
    tenant_id: str,
    target_id: str,
    data: MonitorTargetUpdate,
    _auth: Dict[str, Any] = Depends(require_tenant_access),
):
    """Atualiza parâmetros de um componente no silo isolado do tenant."""
    try:
        updated = storage.update_target(tenant_id, target_id, data)
        if not updated:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Componente '{target_id}' não encontrado para atualização.",
            )
        return updated
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.delete(
    "/targets/{target_id}",
    status_code=status.HTTP_200_OK,
    summary="Remover componente de monitoramento",
)
def delete_monitor_target(
    tenant_id: str,
    target_id: str,
    _auth: Dict[str, Any] = Depends(require_tenant_access),
):
    """Remove o componente de monitoramento do silo do tenant."""
    try:
        deleted = storage.delete_target(tenant_id, target_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Componente '{target_id}' não encontrado para remoção.",
            )
        return {"status": "success", "message": f"Componente '{target_id}' removido com sucesso."}
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post(
    "/scan",
    response_model=ScanResultResponse,
    status_code=status.HTTP_200_OK,
    summary="Disparar varredura imediata isolada para este tenant",
)
def trigger_tenant_scan(
    tenant_id: str,
    _auth: Dict[str, Any] = Depends(require_tenant_access),
):
    """Executa um ciclo isolado do motor de scraping exclusivamente no silo do tenant autenticado."""
    try:
        if not storage.get_tenant(tenant_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tenant '{tenant_id}' não encontrado.",
            )
        worker = WorkerRunner(
            storage=storage,
            scraper=ScraperEngine(),
            notifier=TelegramNotifier(mock_mode=True),
        )
        result = worker.run_cycle_for_tenant(tenant_id)
        return ScanResultResponse(**result)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get(
    "/history",
    response_model=List[PriceRecord],
    summary="Consultar histórico de cotações capturadas do tenant",
)
def get_price_history(
    tenant_id: str,
    limit: int = 50,
    _auth: Dict[str, Any] = Depends(require_tenant_access),
):
    """Retorna o histórico cronológico gravado no silo do tenant."""
    try:
        if not storage.get_tenant(tenant_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tenant '{tenant_id}' não encontrado.",
            )
        return storage.get_history(tenant_id, limit=limit)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get(
    "/alerts",
    response_model=List[AlertLog],
    summary="Consultar histórico de alertas disparados para o tenant",
)
def get_alert_history(
    tenant_id: str,
    limit: int = 50,
    _auth: Dict[str, Any] = Depends(require_tenant_access),
):
    """Retorna o histórico de notificações enviadas ao tenant."""
    try:
        if not storage.get_tenant(tenant_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tenant '{tenant_id}' não encontrado.",
            )
        return storage.list_alerts(tenant_id, limit=limit)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

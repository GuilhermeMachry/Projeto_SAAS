"""Configurações e fixtures para a suíte de testes com isolamento de diretório temporário."""

import shutil
import tempfile
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from src.core.security import tenant_rate_limiter
from src.core.storage import TenantStorageManager
from src.api.main import app
import src.api.routes.tenants as tenants_route
import src.api.routes.monitors as monitors_route


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    """Garante estado limpo do rate limiter entre cada teste."""
    original_max = tenant_rate_limiter.max_requests
    tenant_rate_limiter.reset()
    yield
    tenant_rate_limiter.max_requests = original_max
    tenant_rate_limiter.reset()


@pytest.fixture
def temp_storage_dir():
    """Cria um diretório temporário para silos durante os testes."""
    temp_dir = Path(tempfile.mkdtemp(prefix="test_silos_"))
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def storage(temp_storage_dir):
    """Instância do TenantStorageManager apontando para o diretório temporário."""
    return TenantStorageManager(storage_dir=temp_storage_dir)


@pytest.fixture
def client(temp_storage_dir):
    """Cliente de teste FastAPI com storage isolado configurado nos routers."""
    test_storage = TenantStorageManager(storage_dir=temp_storage_dir)
    tenants_route.storage = test_storage
    monitors_route.storage = test_storage
    with TestClient(app) as c:
        yield c


@pytest.fixture
def create_auth_tenant(client: TestClient):
    """Helper fixture que cria um tenant via API e retorna (dados, headers_auth)."""
    def _factory(
        tenant_id: str,
        nome: str = "Tenant Teste",
        tipo: str = "B2C_ENTUSIASTA",
        telegram_chat_id: str = "111222333",
    ):
        res = client.post(
            "/tenants",
            json={
                "tenant_id": tenant_id,
                "nome": nome,
                "tipo": tipo,
                "telegram_chat_id": telegram_chat_id,
            },
        )
        assert res.status_code == 201, f"Falha ao criar tenant {tenant_id}: {res.text}"
        data = res.json()
        headers = {"Authorization": f"Bearer {data['access_token']}"}
        return data, headers

    return _factory

"""Configurações e fixtures para a suíte de testes com isolamento de diretório temporário."""

import shutil
import tempfile
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from src.core.storage import TenantStorageManager
from src.api.main import app
import src.api.routes.tenants as tenants_route
import src.api.routes.monitors as monitors_route


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

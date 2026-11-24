"""Testes automatizados multi-vetor comprovando o isolamento estrito entre Tenants (Etapa 3.2)."""

import stat
import pytest
from fastapi.testclient import TestClient

from src.core.models import MonitorTargetCreate, TenantCreate, TenantType
from src.core.security import tenant_rate_limiter
from src.core.storage import TenantStorageManager
from src.worker.notifier import TelegramNotifier
from src.worker.runner import WorkerRunner
from src.worker.scraper import ScraperEngine


def test_tenant_creation_file_isolation_and_posix_permissions(storage: TenantStorageManager):
    """Vetor 1 (Disco): Silos físicos separados no disco com permissão restrita chmod 600."""
    storage.create_or_update_tenant(
        TenantCreate(tenant_id="tenant_alpha", nome="Alpha Ltda", tipo=TenantType.B2C_ENTUSIASTA, telegram_chat_id="111")
    )
    storage.create_or_update_tenant(
        TenantCreate(tenant_id="tenant_beta", nome="Beta S/A", tipo=TenantType.B2B_OFICINA, telegram_chat_id="222")
    )

    path_alpha = storage.get_silo_path("tenant_alpha")
    path_beta = storage.get_silo_path("tenant_beta")

    assert path_alpha.exists()
    assert path_beta.exists()
    assert path_alpha != path_beta
    assert stat.S_IMODE(path_alpha.stat().st_mode) == 0o600
    assert stat.S_IMODE(path_beta.stat().st_mode) == 0o600


def test_cross_tenant_isolation_read_storage(storage: TenantStorageManager):
    """Vetor 2 (Camada de Dados): Tenant A nunca enxerga registros do Tenant B no storage."""
    storage.create_or_update_tenant(
        TenantCreate(tenant_id="tenant_a", nome="Tenant A", tipo=TenantType.B2C_ENTUSIASTA, telegram_chat_id="111")
    )
    storage.create_or_update_tenant(
        TenantCreate(tenant_id="tenant_b", nome="Tenant B", tipo=TenantType.B2B_OFICINA, telegram_chat_id="222")
    )

    storage.add_target(
        "tenant_a",
        MonitorTargetCreate(nome_componente="GeForce RTX 4090", url="https://loja.com/rtx4090", preco_alvo=10000.0),
    )
    storage.add_target(
        "tenant_b",
        MonitorTargetCreate(nome_componente="Core i9 14900K", url="https://loja.com/i9", preco_alvo=3500.0),
    )

    nomes_em_a = [t.nome_componente for t in storage.list_targets("tenant_a")]
    nomes_em_b = [t.nome_componente for t in storage.list_targets("tenant_b")]

    assert nomes_em_a == ["GeForce RTX 4090"]
    assert nomes_em_b == ["Core i9 14900K"]
    assert "Core i9 14900K" not in nomes_em_a
    assert "GeForce RTX 4090" not in nomes_em_b


def test_cross_tenant_api_idor_blocked(client: TestClient, create_auth_tenant):
    """Vetor 3 (API IDOR): Token válido do Tenant A é bloqueado (403) ao tentar acessar Tenant B."""
    _, headers_a = create_auth_tenant("tenant_a", "João B2C", "B2C_ENTUSIASTA", "1001")
    _, headers_b = create_auth_tenant("tenant_b", "Oficina B2B", "B2B_OFICINA", "2002")

    res_b = client.post(
        "/tenants/tenant_b/targets",
        headers=headers_b,
        json={"nome_componente": "Lote Ryzen 7", "url": "mock://loja.com/r7?price=2500", "preco_alvo": 2600},
    )
    assert res_b.status_code == 201
    target_b_id = res_b.json()["id"]

    # Tenant A tenta ler, escrever, atualizar e excluir recursos do Tenant B -> 403 em todos!
    assert client.get("/tenants/tenant_b", headers=headers_a).status_code == 403
    assert client.get("/tenants/tenant_b/targets", headers=headers_a).status_code == 403
    assert client.get(f"/tenants/tenant_b/targets/{target_b_id}", headers=headers_a).status_code == 403
    assert client.get("/tenants/tenant_b/history", headers=headers_a).status_code == 403
    assert client.get("/tenants/tenant_b/alerts", headers=headers_a).status_code == 403
    assert client.get("/tenants/tenant_b/silo-info", headers=headers_a).status_code == 403
    assert client.post("/tenants/tenant_b/scan", headers=headers_a).status_code == 403
    assert (
        client.post(
            "/tenants/tenant_b/targets",
            headers=headers_a,
            json={"nome_componente": "Invasao", "url": "https://loja.com/x", "preco_alvo": 100},
        ).status_code
        == 403
    )
    assert client.delete(f"/tenants/tenant_b/targets/{target_b_id}", headers=headers_a).status_code == 403
    assert client.delete("/tenants/tenant_b", headers=headers_a).status_code == 403

    # Vetor 4: Tenant A tenta consultar o target_id de B usando sua própria rota -> 404 (zero vazamento)
    assert client.get(f"/tenants/tenant_a/targets/{target_b_id}", headers=headers_a).status_code == 404


def test_header_spoofing_x_tenant_id_blocked(client: TestClient, create_auth_tenant):
    """Vetor 5 (Header Spoofing): Enviar X-Tenant-ID de outro cliente com token válido retorna 403."""
    _, headers_a = create_auth_tenant("tenant_a", "João B2C", "B2C_ENTUSIASTA", "1001")
    create_auth_tenant("tenant_b", "Oficina B2B", "B2B_OFICINA", "2002")

    spoofed = {**headers_a, "X-Tenant-ID": "tenant_b"}
    res = client.get("/tenants/tenant_a/targets", headers=spoofed)
    assert res.status_code == 403
    assert "X-Tenant-ID" in res.json()["detail"]


def test_path_traversal_prevention(storage: TenantStorageManager):
    """Vetor 6 (Path Traversal): Múltiplas injeções de caminho são rejeitadas."""
    malicious_inputs = [
        "../../etc/passwd",
        "../tenant_a",
        "/root/admin",
        "tenant\\windows\\hack",
        "tenant;rm -rf /",
        "tenant%2f..%2fsecret",
        "tenant\x00null",
        " ",
    ]
    for bad_id in malicious_inputs:
        with pytest.raises(ValueError):
            storage.sanitize_tenant_id(bad_id)


def test_worker_cross_tenant_notification_isolation(storage: TenantStorageManager):
    """Vetor 7 (Worker / Notificações): Alertas e histórico vão estritamente ao silo e chat_id do dono."""
    storage.create_or_update_tenant(
        TenantCreate(tenant_id="joao_b2c", nome="João", tipo=TenantType.B2C_ENTUSIASTA, telegram_chat_id="11111")
    )
    storage.create_or_update_tenant(
        TenantCreate(tenant_id="oficina_b2b", nome="Oficina", tipo=TenantType.B2B_OFICINA, telegram_chat_id="99999")
    )

    # Apenas João atinge a meta; Oficina fica acima da meta
    storage.add_target(
        "joao_b2c",
        MonitorTargetCreate(nome_componente="RTX 4060", url="mock://loja.com/rtx?price=1800", preco_alvo=2000),
    )
    storage.add_target(
        "oficina_b2b",
        MonitorTargetCreate(nome_componente="SSD 2TB", url="mock://loja.com/ssd?price=1200", preco_alvo=900),
    )

    sent_calls = []

    class SpyNotifier(TelegramNotifier):
        def send_price_alert(self, tenant_id, chat_id, component_name, current_price, target_price, original_url):
            sent_calls.append((tenant_id, chat_id, component_name))
            return True

    worker = WorkerRunner(storage=storage, scraper=ScraperEngine(), notifier=SpyNotifier(mock_mode=True))
    worker.run_cycle()

    # Apenas 1 alerta disparado e exclusivamente para o chat_id de joao_b2c
    assert sent_calls == [("joao_b2c", "11111", "RTX 4060")]
    assert len(storage.list_alerts("joao_b2c")) == 1
    assert len(storage.list_alerts("oficina_b2b")) == 0
    assert [h.nome_componente for h in storage.get_history("joao_b2c")] == ["RTX 4060"]
    assert [h.nome_componente for h in storage.get_history("oficina_b2b")] == ["SSD 2TB"]


def test_lgpd_atomic_delete_isolation(storage: TenantStorageManager):
    """Vetor 8 (Expurgo LGPD Art. 18): Deletar Tenant A apaga apenas o silo A e mantém Tenant B íntegro."""
    storage.create_or_update_tenant(
        TenantCreate(tenant_id="tenant_del", nome="Excluir", tipo=TenantType.B2C_ENTUSIASTA, telegram_chat_id="111")
    )
    storage.create_or_update_tenant(
        TenantCreate(tenant_id="tenant_keep", nome="Manter", tipo=TenantType.B2B_OFICINA, telegram_chat_id="222")
    )
    storage.add_target(
        "tenant_keep",
        MonitorTargetCreate(nome_componente="SSD 2TB NVMe", url="https://loja.com/ssd", preco_alvo=700.0),
    )

    assert storage.delete_tenant("tenant_del") is True
    assert not storage.get_silo_path("tenant_del").exists()
    assert storage.get_silo_path("tenant_keep").exists()
    assert [t.nome_componente for t in storage.list_targets("tenant_keep")] == ["SSD 2TB NVMe"]


def test_noisy_neighbor_rate_limit_isolation(client: TestClient, create_auth_tenant):
    """Vetor 9 (Noisy Neighbor): Flood do Tenant A gera HTTP 429 para A sem degradar Tenant B (HTTP 200)."""
    _, headers_a = create_auth_tenant("noisy_a", "Vizinho Barulhento", "B2C_ENTUSIASTA", "1111")
    _, headers_b = create_auth_tenant("calm_b", "Vizinho Comportado", "B2B_OFICINA", "2222")

    # Configura teto baixo por minuto para demonstrar isolamento de cota de requisições
    tenant_rate_limiter.max_requests = 3
    tenant_rate_limiter.reset()

    codes_a = [client.get("/tenants/noisy_a/targets", headers=headers_a).status_code for _ in range(5)]
    assert codes_a == [200, 200, 200, 429, 429]

    # Tenant B continua recebendo 200 OK normalmente!
    codes_b = [client.get("/tenants/calm_b/targets", headers=headers_b).status_code for _ in range(3)]
    assert codes_b == [200, 200, 200]

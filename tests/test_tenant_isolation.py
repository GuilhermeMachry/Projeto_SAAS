"""Testes automatizados comprovando matematicamente o isolamento de dados entre Tenants."""

import pytest
from src.core.models import TenantCreate, TenantType, MonitorTargetCreate
from src.core.storage import TenantStorageManager


def test_tenant_creation_and_file_isolation(storage: TenantStorageManager):
    """Garante que a criação de tenants gera silos físicos separados no disco."""
    t1 = storage.create_or_update_tenant(
        TenantCreate(tenant_id="tenant_alpha", nome="Alpha Ltda", tipo=TenantType.B2C_ENTUSIASTA, telegram_chat_id="111")
    )
    t2 = storage.create_or_update_tenant(
        TenantCreate(tenant_id="tenant_beta", nome="Beta S/A", tipo=TenantType.B2B_OFICINA, telegram_chat_id="222")
    )

    path_alpha = storage.get_silo_path("tenant_alpha")
    path_beta = storage.get_silo_path("tenant_beta")

    assert path_alpha.exists()
    assert path_beta.exists()
    assert path_alpha != path_beta
    assert path_alpha.name == "tenant_tenant_alpha.json"
    assert path_beta.name == "tenant_tenant_beta.json"


def test_cross_tenant_isolation_read(storage: TenantStorageManager):
    """Comprova que Tenant A nunca tem acesso aos componentes cadastrados pelo Tenant B."""
    storage.create_or_update_tenant(
        TenantCreate(tenant_id="tenant_a", nome="Tenant A", tipo=TenantType.B2C_ENTUSIASTA, telegram_chat_id="111")
    )
    storage.create_or_update_tenant(
        TenantCreate(tenant_id="tenant_b", nome="Tenant B", tipo=TenantType.B2B_OFICINA, telegram_chat_id="222")
    )

    storage.add_target(
        "tenant_a",
        MonitorTargetCreate(nome_componente="GeForce RTX 4090", url="http://loja.com/rtx4090", preco_alvo=10000.0),
    )
    storage.add_target(
        "tenant_b",
        MonitorTargetCreate(nome_componente="Core i9 14900K", url="http://loja.com/i9", preco_alvo=3500.0),
    )

    targets_a = storage.list_targets("tenant_a")
    targets_b = storage.list_targets("tenant_b")

    assert len(targets_a) == 1
    assert len(targets_b) == 1

    assert targets_a[0].nome_componente == "GeForce RTX 4090"
    assert targets_b[0].nome_componente == "Core i9 14900K"

    # Verificação cruzada negativa rigorosa
    nomes_em_a = [t.nome_componente for t in targets_a]
    nomes_em_b = [t.nome_componente for t in targets_b]

    assert "Core i9 14900K" not in nomes_em_a, "Violação de isolamento: Tenant A viu dados de B!"
    assert "GeForce RTX 4090" not in nomes_em_b, "Violação de isolamento: Tenant B viu dados de A!"


def test_path_traversal_prevention(storage: TenantStorageManager):
    """Garante que injeções de caminhos de diretório são bloqueadas com exceção."""
    malicious_inputs = [
        "../../etc/passwd",
        "../tenant_a",
        "/root/admin",
        "tenant\\windows\\hack",
        "tenant;rm -rf /",
    ]
    for bad_id in malicious_inputs:
        with pytest.raises(ValueError, match="Path Traversal bloqueado"):
            storage.sanitize_tenant_id(bad_id)


def test_lgpd_atomic_delete(storage: TenantStorageManager):
    """Comprova que o expurgo do Tenant A (LGPD Art. 18) apaga seu silo e não afeta o Tenant B."""
    storage.create_or_update_tenant(
        TenantCreate(tenant_id="tenant_del", nome="Excluir", tipo=TenantType.B2C_ENTUSIASTA, telegram_chat_id="111")
    )
    storage.create_or_update_tenant(
        TenantCreate(tenant_id="tenant_keep", nome="Manter", tipo=TenantType.B2B_OFICINA, telegram_chat_id="222")
    )

    storage.add_target(
        "tenant_keep",
        MonitorTargetCreate(nome_componente="SSD 2TB NVMe", url="http://loja.com/ssd", preco_alvo=700.0),
    )

    silo_del = storage.get_silo_path("tenant_del")
    silo_keep = storage.get_silo_path("tenant_keep")

    assert silo_del.exists()
    assert silo_keep.exists()

    # Executar expurgo LGPD de A
    deleted = storage.delete_tenant("tenant_del")
    assert deleted is True
    assert not silo_del.exists(), "Falha: O arquivo do tenant excluído ainda existe em disco!"

    # O Tenant B deve continuar 100% íntegro
    assert silo_keep.exists(), "Falha: O arquivo do tenant mantido foi corrompido ou apagado!"
    assert len(storage.list_targets("tenant_keep")) == 1
    assert storage.list_targets("tenant_keep")[0].nome_componente == "SSD 2TB NVMe"

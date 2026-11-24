"""Testes de Contrato entre Serviços: Serviço 01 (API REST) <-> Silo JSON <-> Serviço 02 (Worker).

Valida o contrato estrutural assíncrono estabelecido no ADR 005 e ADR 006:
- O que a API grava no silo ('profile', 'targets') deve ser consumível sem erro pelo Worker;
- O que o Worker grava no silo ('history', 'alerts', 'ultimo_preco', 'ultima_checagem')
  deve ser validado e serializado corretamente pelos contratos Pydantic da API.
"""

import json
from fastapi.testclient import TestClient

from src.core.storage import TenantStorageManager
from src.worker.notifier import TelegramNotifier
from src.worker.runner import WorkerRunner
from src.worker.scraper import ScraperEngine


def test_contract_api_writes_worker_consumes_and_api_reads_back(
    client: TestClient,
    temp_storage_dir,
    create_auth_tenant,
):
    """Prova o contrato ponta a ponta API -> Silo JSON -> Worker -> Silo JSON -> API."""
    # 1. Serviço 01 (API) grava perfil e componente no silo
    _, headers = create_auth_tenant(
        tenant_id="contrato_b2b",
        nome="Oficina Contrato",
        tipo="B2B_OFICINA",
        telegram_chat_id="778899",
    )
    post_res = client.post(
        "/tenants/contrato_b2b/targets",
        headers=headers,
        json={
            "nome_componente": "RTX 4070 Super 12GB",
            "url": "mock://kabum.com.br/rtx4070s?price=3650.00",
            "preco_alvo": 3800.00,
        },
    )
    assert post_res.status_code == 201
    target_id = post_res.json()["id"]

    # Valida contrato físico do JSON gerado pela API
    silo_file = temp_storage_dir / "tenant_contrato_b2b.json"
    raw_before = json.loads(silo_file.read_text(encoding="utf-8"))
    assert "profile" in raw_before
    assert "targets" in raw_before
    target_doc = next(iter(raw_before["targets"].values()))
    required_target_keys = {"id", "tenant_id", "nome_componente", "url", "preco_alvo", "ultimo_preco", "ultima_checagem", "criado_em"}
    assert required_target_keys.issubset(target_doc.keys())

    # 2. Serviço 02 (Worker) lê o mesmo diretório de silos independentemente da API
    worker_storage = TenantStorageManager(storage_dir=temp_storage_dir)
    worker = WorkerRunner(
        storage=worker_storage,
        scraper=ScraperEngine(),
        notifier=TelegramNotifier(mock_mode=True),
    )
    stats = worker.run_cycle()
    assert stats["tenants_processados"] == 1
    assert stats["cotacoes_sucesso"] == 1
    assert stats["alertas_disparados"] == 1

    # Valida contrato físico gravado pelo Worker ('history' e 'alerts')
    raw_after = json.loads(silo_file.read_text(encoding="utf-8"))
    assert "history" in raw_after
    assert "alerts" in raw_after
    hist_doc = next(iter(raw_after["history"].values()))
    assert {"id", "target_id", "nome_componente", "url", "preco_coletado", "preco_alvo", "alerta_disparado", "timestamp"}.issubset(
        hist_doc.keys()
    )

    # 3. Serviço 01 (API) lê de volta os dados gravados pelo Worker validando todos os schemas de resposta
    t_res = client.get(f"/tenants/contrato_b2b/targets/{target_id}", headers=headers)
    assert t_res.status_code == 200
    assert t_res.json()["ultimo_preco"] == 3650.00
    assert t_res.json()["ultima_checagem"] is not None

    h_res = client.get("/tenants/contrato_b2b/history", headers=headers)
    assert h_res.status_code == 200
    assert h_res.json()[0]["preco_coletado"] == 3650.00
    assert h_res.json()[0]["alerta_disparado"] is True

    a_res = client.get("/tenants/contrato_b2b/alerts", headers=headers)
    assert a_res.status_code == 200
    assert a_res.json()[0]["canal"] == "Telegram"
    assert a_res.json()[0]["status"] == "ENVIADO"

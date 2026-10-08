"""Testes de integração dos endpoints da API REST (FastAPI)."""

from fastapi.testclient import TestClient


def test_api_healthcheck(client: TestClient):
    """Verifica saúde do endpoint /health."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "hardtrack-api"


def test_create_and_get_tenant(client: TestClient):
    """Cadastra um tenant via API e consulta seus dados."""
    payload = {
        "tenant_id": "gamer_sp",
        "nome": "Gamer São Paulo",
        "tipo": "B2C_ENTUSIASTA",
        "telegram_chat_id": "99988877",
    }
    post_res = client.post("/tenants", json=payload)
    assert post_res.status_code == 201
    created = post_res.json()
    assert created["tenant_id"] == "gamer_sp"
    assert created["tipo"] == "B2C_ENTUSIASTA"

    # Consultar
    get_res = client.get("/tenants/gamer_sp")
    assert get_res.status_code == 200
    assert get_res.json()["nome"] == "Gamer São Paulo"


def test_add_and_list_targets_by_tenant(client: TestClient):
    """Adiciona componente de hardware via API e lista os itens do tenant."""
    # Criar tenant primeiro
    client.post(
        "/tenants",
        json={"tenant_id": "oficina_sul", "nome": "Oficina Sul", "tipo": "B2B_OFICINA", "telegram_chat_id": "1234"},
    )

    # Cadastrar target
    target_payload = {
        "nome_componente": "Placa Mãe B650 AM5",
        "url": "http://loja.com/b650",
        "preco_alvo": 1150.00,
    }
    add_res = client.post("/tenants/oficina_sul/targets", json=target_payload)
    assert add_res.status_code == 201
    target_data = add_res.json()
    assert target_data["nome_componente"] == "Placa Mãe B650 AM5"
    assert target_data["preco_alvo"] == 1150.00

    # Listar
    list_res = client.get("/tenants/oficina_sul/targets")
    assert list_res.status_code == 200
    items = list_res.json()
    assert len(items) == 1
    assert items[0]["id"] == target_data["id"]


def test_cross_tenant_api_isolation(client: TestClient):
    """Garante que a chamada de API de um tenant nunca lista componentes de outro."""
    client.post(
        "/tenants",
        json={"tenant_id": "tenant_1", "nome": "Tenant 1", "tipo": "B2C_ENTUSIASTA", "telegram_chat_id": "1001"},
    )
    client.post(
        "/tenants",
        json={"tenant_id": "tenant_2", "nome": "Tenant 2", "tipo": "B2C_ENTUSIASTA", "telegram_chat_id": "1002"},
    )

    client.post("/tenants/tenant_1/targets", json={"nome_componente": "Item A", "url": "http://a.com", "preco_alvo": 100})
    client.post("/tenants/tenant_2/targets", json={"nome_componente": "Item B", "url": "http://b.com", "preco_alvo": 200})

    res_t1 = client.get("/tenants/tenant_1/targets").json()
    res_t2 = client.get("/tenants/tenant_2/targets").json()

    assert len(res_t1) == 1
    assert len(res_t2) == 1
    assert res_t1[0]["nome_componente"] == "Item A"
    assert res_t2[0]["nome_componente"] == "Item B"


def test_delete_tenant_lgpd_endpoint(client: TestClient):
    """Testa a exclusão atômica de tenant via endpoint DELETE /tenants/{id}."""
    client.post(
        "/tenants",
        json={"tenant_id": "t_delete", "nome": "Para Excluir", "tipo": "B2C_ENTUSIASTA", "telegram_chat_id": "1234"},
    )
    del_res = client.delete("/tenants/t_delete")
    assert del_res.status_code == 200
    assert "LGPD" in del_res.json()["message"]

    # Tentativa de busca subsequente deve dar 404
    get_res = client.get("/tenants/t_delete")
    assert get_res.status_code == 404

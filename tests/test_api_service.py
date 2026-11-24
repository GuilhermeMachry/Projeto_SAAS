"""Testes de integração dos endpoints da API REST (FastAPI) com AuthZ HMAC-SHA256."""

from fastapi.testclient import TestClient


def test_api_healthcheck_and_native_ui(client: TestClient):
    """Verifica saúde do endpoint /health e disponibilidade da interface web nativa /app."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "hardtrack-api"
    assert data["authz"] == "hmac-sha256-bearer"

    ui_res = client.get("/app")
    assert ui_res.status_code == 200
    assert "HardTrack Solutions" in ui_res.text


def test_create_authenticate_and_get_tenant(client: TestClient, create_auth_tenant):
    """Cadastra tenant, valida emissão de token via /auth/token e consulta perfil."""
    created, headers = create_auth_tenant(
        tenant_id="gamer_sp",
        nome="Gamer São Paulo",
        tipo="B2C_ENTUSIASTA",
        telegram_chat_id="99988877",
    )
    assert created["tenant_id"] == "gamer_sp"
    assert created["tipo"] == "B2C_ENTUSIASTA"
    assert created["access_token"]

    # Consultar perfil autenticado
    get_res = client.get("/tenants/gamer_sp", headers=headers)
    assert get_res.status_code == 200
    assert get_res.json()["nome"] == "Gamer São Paulo"

    # Re-autenticar via POST /auth/token
    token_res = client.post(
        "/auth/token",
        json={"tenant_id": "gamer_sp", "telegram_chat_id": "99988877"},
    )
    assert token_res.status_code == 200
    assert token_res.json()["access_token"]


def test_crud_targets_patch_and_scan_flow(client: TestClient, create_auth_tenant):
    """Testa ciclo completo: criar target, listar, editar meta (PATCH), rodar scan e remover."""
    _, headers = create_auth_tenant(
        tenant_id="oficina_sul",
        nome="Oficina Sul",
        tipo="B2B_OFICINA",
        telegram_chat_id="123456",
    )

    # Cadastrar target
    add_res = client.post(
        "/tenants/oficina_sul/targets",
        headers=headers,
        json={
            "nome_componente": "Placa Mãe B650 AM5",
            "url": "mock://loja.com/b650?price=1100.00",
            "preco_alvo": 1000.00,
        },
    )
    assert add_res.status_code == 201
    target_id = add_res.json()["id"]

    # Atualizar meta (PATCH) para disparar alerta na varredura
    patch_res = client.patch(
        f"/tenants/oficina_sul/targets/{target_id}",
        headers=headers,
        json={"preco_alvo": 1150.00},
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["preco_alvo"] == 1150.00

    # Disparar varredura isolada (POST /scan)
    scan_res = client.post("/tenants/oficina_sul/scan", headers=headers)
    assert scan_res.status_code == 200
    scan_data = scan_res.json()
    assert scan_data["componentes_checados"] == 1
    assert scan_data["cotacoes_sucesso"] == 1
    assert scan_data["alertas_disparados"] == 1

    # Consultar silo-info, history e alerts
    silo_res = client.get("/tenants/oficina_sul/silo-info", headers=headers)
    assert silo_res.status_code == 200
    assert silo_res.json()["targets_quota"] == 50
    assert silo_res.json()["alerts_count"] == 1

    hist_res = client.get("/tenants/oficina_sul/history", headers=headers)
    assert hist_res.status_code == 200
    assert len(hist_res.json()) == 1

    alerts_res = client.get("/tenants/oficina_sul/alerts", headers=headers)
    assert alerts_res.status_code == 200
    assert len(alerts_res.json()) == 1

    # Remover target
    del_res = client.delete(f"/tenants/oficina_sul/targets/{target_id}", headers=headers)
    assert del_res.status_code == 200
    assert client.get("/tenants/oficina_sul/targets", headers=headers).json() == []


def test_b2c_plan_quota_enforced(client: TestClient, create_auth_tenant):
    """Garante que tenant B2C Freemium não excede a cota de 5 URLs simultâneas."""
    _, headers = create_auth_tenant("b2c_quota", "Usuário Freemium", "B2C_ENTUSIASTA", "334455")
    for i in range(5):
        res = client.post(
            "/tenants/b2c_quota/targets",
            headers=headers,
            json={
                "nome_componente": f"Peça {i + 1}",
                "url": f"mock://loja.com/item{i}?price=500.00",
                "preco_alvo": 450.0,
            },
        )
        assert res.status_code == 201

    # 6ª URL deve ser barrada com 403 Forbidden (cota do plano)
    sixth = client.post(
        "/tenants/b2c_quota/targets",
        headers=headers,
        json={
            "nome_componente": "Peça Extra 6",
            "url": "mock://loja.com/item6?price=500.00",
            "preco_alvo": 450.0,
        },
    )
    assert sixth.status_code == 403
    assert "Cota do plano atingida" in sixth.json()["detail"]


def test_delete_tenant_lgpd_endpoint(client: TestClient, create_auth_tenant):
    """Testa a exclusão atômica de tenant autenticado via endpoint DELETE /tenants/{id}."""
    _, headers = create_auth_tenant("t_delete", "Para Excluir", "B2C_ENTUSIASTA", "1234")
    del_res = client.delete("/tenants/t_delete", headers=headers)
    assert del_res.status_code == 200
    assert "LGPD" in del_res.json()["message"]

    # Tentativa de busca subsequente com o mesmo token deve retornar 404 (silo inexistente)
    get_res = client.get("/tenants/t_delete", headers=headers)
    assert get_res.status_code == 404

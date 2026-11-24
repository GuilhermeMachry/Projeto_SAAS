"""Testes de verificação de segurança (Etapa 3.5): AuthZ, Anti-Hijacking, Anti-SSRF, CORS e Headers."""

import pytest
from fastapi.testclient import TestClient

from src.core import config as core_config
from src.core.security import create_tenant_token


def test_unauthenticated_access_returns_401(client: TestClient, create_auth_tenant):
    """Achado 1 corrigido: Nenhuma rota de tenant pode ser acessada sem token Bearer."""
    create_auth_tenant("vitima_b2b", "Empresa Vítima", "B2B_OFICINA", "555555")

    assert client.get("/tenants/vitima_b2b").status_code == 401
    assert client.get("/tenants/vitima_b2b/targets").status_code == 401
    assert client.get("/tenants/vitima_b2b/history").status_code == 401
    assert client.get("/tenants/vitima_b2b/alerts").status_code == 401
    assert client.delete("/tenants/vitima_b2b").status_code == 401


def test_invalid_and_expired_tokens_return_401(client: TestClient, create_auth_tenant):
    """Tokens forjados ou expirados são rejeitados com HTTP 401."""
    create_auth_tenant("t_sec", "Sec User", "B2C_ENTUSIASTA", "8888")

    # Token malformado
    assert client.get("/tenants/t_sec/targets", headers={"Authorization": "Bearer token.falso.123"}).status_code == 401

    # Token expirado
    expired = create_tenant_token("t_sec", "B2C_ENTUSIASTA", ttl_seconds=-5)
    assert client.get("/tenants/t_sec/targets", headers={"Authorization": f"Bearer {expired}"}).status_code == 401


def test_tenant_hijacking_via_post_tenants_blocked(client: TestClient, create_auth_tenant):
    """Impede que um atacante sobrescreva um tenant existente alterando seu telegram_chat_id."""
    create_auth_tenant("loja_real", "Loja Real", "B2B_OFICINA", "777777")

    hijack = client.post(
        "/tenants",
        json={
            "tenant_id": "loja_real",
            "nome": "Hacker",
            "tipo": "B2B_OFICINA",
            "telegram_chat_id": "000000",  # chat_id diferente sem token
        },
    )
    assert hijack.status_code == 409


def test_admin_tenant_enumeration_protected(client: TestClient, create_auth_tenant):
    """Listagem global GET /tenants bloqueia enumeração sem X-Admin-Key válida."""
    create_auth_tenant("t_enum", "Enum Teste", "B2C_ENTUSIASTA", "1212")

    assert client.get("/tenants").status_code == 401
    assert client.get("/tenants", headers={"X-Admin-Key": "chave-errada"}).status_code == 403

    ok_res = client.get("/tenants", headers={"X-Admin-Key": core_config.HARDTRACK_ADMIN_KEY})
    assert ok_res.status_code == 200
    assert "t_enum" in ok_res.json()


@pytest.mark.parametrize(
    "ssrf_url",
    [
        "http://169.254.169.254/latest/meta-data/",
        "http://127.0.0.1:8000/health",
        "http://localhost:8000/docs",
        "file:///etc/passwd",
        "http://10.0.0.5/internal",
        "javascript:alert(1)",
    ],
)
def test_ssrf_urls_rejected_by_api(client: TestClient, create_auth_tenant, ssrf_url: str):
    """Achado 2 corrigido: API rejeita URLs internas/privadas e esquemas perigosos com 422."""
    _, headers = create_auth_tenant("ssrf_tester", "Tester", "B2C_ENTUSIASTA", "321321")
    res = client.post(
        "/tenants/ssrf_tester/targets",
        headers=headers,
        json={"nome_componente": "Ataque SSRF", "url": ssrf_url, "preco_alvo": 100.0},
    )
    assert res.status_code == 422


def test_security_headers_and_cors_hardening(client: TestClient):
    """Achado 3 corrigido: Headers HTTP de segurança presentes e CORS não aceita origem maliciosa."""
    res = client.get("/health", headers={"Origin": "https://site-malicioso.evil"})
    assert res.status_code == 200
    assert res.headers.get("X-Content-Type-Options") == "nosniff"
    assert res.headers.get("X-Frame-Options") == "DENY"
    assert res.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
    # Origem maliciosa não deve receber Allow-Origin nem Allow-Credentials=true
    assert res.headers.get("access-control-allow-origin") != "https://site-malicioso.evil"
    assert res.headers.get("access-control-allow-credentials") != "true"

# Qualidade, Pirâmide de Testes e Pipeline CI (Etapa 3.1 & 3.2)

**Disciplina:** Arquitetura de Software SAAS (8512) · EC7 · SETREM 2026-2  
**Projeto:** HardTrack Solutions — Plataforma SaaS Multi-Tenant de Hardware  
**Responsável:** Guilherme Machry  

---

## 1. Visão Geral da Suíte de Testes (44 Testes Automatizados)

A suíte automatizada em [`tests/`](../tests/) cobre integralmente todas as camadas da pirâmide de testes cobradas na Etapa 3, incluindo **testes de contrato entre serviços** e **isolamento multi-vetor**:

| Camada / Tipo | Arquivo | Qtd. | O que valida |
|---|---|---:|---|
| **Unitários (Core & Domínio)** | [`tests/test_unit_core.py`](../tests/test_unit_core.py) | 16 | Assinatura/adulteração/expiração HMAC-SHA256, validador anti-SSRF (9 vetores), parser de preços BRL/USD, links de afiliados, cotas B2C/B2B e rate limiter por tenant. |
| **Resiliência do Worker** | [`tests/test_worker_resilience.py`](../tests/test_worker_resilience.py) | 3 | Parsing de moeda, degradação graciosa em falhas HTTP/timeout (0% crashes) e ciclo completo com disparo de alerta e histórico. |
| **Integração da API REST** | [`tests/test_api_service.py`](../tests/test_api_service.py) | 5 | Healthcheck, interface web `/app`, onboarding + `/auth/token`, CRUD + `PATCH` + `POST /scan`, cota B2C (5 URLs → `403`) e expurgo LGPD (`DELETE`). |
| **Contrato entre Serviços** *(Degrau Alto)* | [`tests/test_service_contract.py`](../tests/test_service_contract.py) | 1 | Contrato estrutural ponta a ponta **API REST → Silo JSON → Worker → Silo JSON → API REST**, garantindo compatibilidade de schema nas tabelas `profile`, `targets`, `history` e `alerts`. |
| **Isolamento Multi-Vetor de Tenant** *(Etapa 3.2)* | [`tests/test_tenant_isolation.py`](../tests/test_tenant_isolation.py) | 8 | 9 vetores de vazamento cobertos: silos físicos + `chmod 600`, leitura cruzada no storage, IDOR na API (`403` em todas as rotas), busca de `target_id` alheio (`404`), Header Spoofing `X-Tenant-ID` (`403`), Path Traversal (8 payloads), isolamento de notificações no Worker, expurgo LGPD atômico e Noisy Neighbor (`429` vs `200`). |
| **Segurança & Hardening** *(Etapa 3.5)* | [`tests/test_security_authz.py`](../tests/test_security_authz.py) | 11 | Rotas sem token (`401`), tokens adulterados/expirados (`401`), Tenant Hijacking (`409`), proteção de enumeração `GET /tenants` (`401/403`), bloqueio SSRF na API (6 payloads → `422`), CORS e headers de segurança. |

---

## 2. Pipeline Automatizado no GitHub Actions

O workflow [`.github/workflows/ci.yml`](../.github/workflows/ci.yml) é disparado a cada `push` e `pull_request` na branch `main`, executando 6 estágios encadeados:
1. **Testes Unitários e de Resiliência** (`test_unit_core.py`, `test_worker_resilience.py`);
2. **Testes de Integração e Contrato API ↔ Worker** (`test_api_service.py`, `test_service_contract.py`);
3. **Testes Multi-Vetor de Isolamento e Segurança** (`test_tenant_isolation.py`, `test_security_authz.py`);
4. **Auditoria Estática de Segurança** (`python scripts/security_audit.py` — secrets, CORS, cobertura AuthZ e pinning de dependências);
5. **Demonstração Automatizada de Isolamento** (`python scripts/demo_isolamento.py`);
6. **Smoke Test ao Vivo da API** (sobe Uvicorn, valida `GET /health` → `200` e confirma que `GET /tenants/joao_b2c/targets` sem token retorna `401`).

---

## 3. Como Demonstrar que o Pipeline Falha Quando um Teste Quebra

Para atender ao critério de aceite da Etapa 3 (*"O pipeline falha quando um teste quebra — e você demonstra isso"*), execute o script automatizado [`scripts/demo_pipeline_fail.sh`](../scripts/demo_pipeline_fail.sh):

```bash
./scripts/demo_pipeline_fail.sh
```

O script:
1. Injeta temporariamente um teste simulando uma regressão de isolamento (acesso cross-tenant retornando `200` em vez de `403`);
2. Executa o `pytest` e comprova retorno de **exit code `1`** (que faz o GitHub Actions marcar o job como **FALHA / VERMELHO** e bloquear o merge);
3. Remove o teste temporário e reexecuta a suíte completa comprovando **exit code `0`** (**44 passed / VERDE**).

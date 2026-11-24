# Verificação de Segurança e Correção de Achados (Etapa 3.5)

**Disciplina:** Arquitetura de Software SAAS (8512) · EC7 · SETREM 2026-2  
**Projeto:** HardTrack Solutions — Plataforma SaaS Multi-Tenant de Hardware  
**Entregável:** Etapa 3.5 — Checklist de Segurança + Achados Reais Corrigidos e Demonstrados  
**Responsável:** Guilherme Machry  

---

## 1. Checklist de Segurança Aplicado

| Categoria | Item Auditado | Status | Evidência / Mecanismo Técnico |
|---|---|---|---|
| **AuthZ por Tenant** | Autenticação obrigatória em rotas de tenant (`/tenants/{id}/*`) | ✅ **Corrigido & Testado** | Tokens stateless **HMAC-SHA256** (`Authorization: Bearer`) validados por `require_tenant_access` em [`src/api/auth.py`](../src/api/auth.py). Sem token → **HTTP 401**. |
| **AuthZ por Tenant** | Prevenção de IDOR / Acesso Cross-Tenant | ✅ **Corrigido & Testado** | Verifica `token.sub == path.tenant_id`. Token de `joao_b2c` tentando ler/alterar/deletar `techparts_b2b` → **HTTP 403 Forbidden** ([`test_tenant_isolation.py`](../tests/test_tenant_isolation.py)). |
| **AuthZ por Tenant** | Proteção contra Header Spoofing (`X-Tenant-ID`) | ✅ **Corrigido & Testado** | Se header `X-Tenant-ID` divergir de `token.sub`, bloqueia imediatamente com **HTTP 403 Forbidden**. |
| **AuthZ por Tenant** | Proteção contra Tenant Hijacking no Onboarding (`POST /tenants`) | ✅ **Corrigido & Testado** | Tentar recriar/sobrescrever um `tenant_id` já existente sem token válido ou `telegram_chat_id` correspondente → **HTTP 409 Conflict**. |
| **AuthZ por Tenant** | Proteção contra Enumeração Global de Tenants (`GET /tenants`) | ✅ **Corrigido & Testado** | Exige header administrativo `X-Admin-Key` validado em tempo constante (`hmac.compare_digest`). Sem chave → **HTTP 401**; chave inválida → **HTTP 403**. |
| **Isolamento / Noisy Neighbor** | Rate Limiting isolado por tenant | ✅ **Implementado & Testado** | `TenantRateLimiter` (janela deslizante em [`src/core/security.py`](../src/core/security.py)) retorna **HTTP 429** apenas para o tenant abusivo sem degradar vizinhos (**HTTP 200**). |
| **Validação de Entrada** | Prevenção de Path Traversal no nome do Silo | ✅ **Implementado & Testado** | Regex estrita `^[a-zA-Z0-9_-]+$` em `TenantStorageManager.sanitize_tenant_id`. Rejeita `../`, `\\`, `;`, `%2f`, null byte. |
| **Validação de Entrada** | Prevenção de SSRF nas URLs de scraping | ✅ **Corrigido & Testado** | `validate_monitor_url` em [`src/core/security.py`](../src/core/security.py) + `@field_validator` em `MonitorTargetCreate`: bloqueia `file://`, `ftp://`, `javascript:`, `localhost`, RFC1918 (`10.x`, `192.168.x`) e cloud metadata (`169.254.169.254`) → **HTTP 422**. |
| **CORS & Headers HTTP** | Restrição de CORS e Cabeçalhos de Segurança | ✅ **Corrigido & Testado** | Removido `allow_origins=["*"]` + `allow_credentials=True`; lista controlada por `CORS_ALLOWED_ORIGINS` + middleware de headers `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy`. |
| **Secrets** | Nenhum segredo hardcoded no código ou Git | ✅ **Auditado via CI** | `TELEGRAM_BOT_TOKEN`, `HARDTRACK_SECRET_KEY` e `HARDTRACK_ADMIN_KEY` lidos via `os.getenv`; `.env` no `.gitignore`; modelo [`.env.example`](../.env.example) criado; validado a cada push por [`scripts/security_audit.py`](../scripts/security_audit.py). |
| **Dependências** | Versionamento fixo (*pinning*) e revisão de CVEs | ✅ **Auditado** | Todas as 28 dependências em [`requirements.txt`](../requirements.txt) possuem versão exata (`==`), sem bibliotecas abandonadas; auditoria automática no CI. |
| **Host / Containers** | Execução sob usuário não-root e `chmod 600` nos silos | ✅ **Implementado** | `user: "1000:1000"` em [`docker-compose.yml`](../docker-compose.yml) e `os.chmod(path, 0o600)` automático na criação de cada arquivo `tenant_<id>.json`. |

---

## 2. Achados Reais de Segurança Encontrados, Corrigidos e Demonstrados

Durante a revisão de segurança da entrega da Etapa 2 para a Etapa 3, **três vulnerabilidades reais** presentes no código-fonte foram identificadas, corrigidas no código e cobertas por testes automatizados de regressão:

### Achado #1 (Crítico) — Ausência de Autenticação e Autorização por Tenant (IDOR / Broken Access Control)
- **Onde estava:** [`src/api/routes/monitors.py`](../src/api/routes/monitors.py) e [`src/api/routes/tenants.py`](../src/api/routes/tenants.py) (versão Etapa 2).
- **Descrição do risco:** Embora os dados estivessem isolados fisicamente em arquivos `tenant_<id>.json` na camada de storage, a camada de API não exigia credencial alguma. Qualquer pessoa que soubesse ou adivinhasse o `tenant_id` (ex.: `techparts_b2b`, inclusive exposto em `GET /tenants` público) podia ler metas concorrentes, injetar URLs ou disparar `DELETE /tenants/techparts_b2b` (expurgo LGPD destrutivo de terceiros).
- **Correção implementada:**
  1. Emissão de tokens assinados **HMAC-SHA256** (`create_tenant_token` / `verify_tenant_token`) no onboarding (`POST /tenants`) e em `POST /auth/token`.
  2. Dependência obrigatória `Depends(require_tenant_access)` em todas as rotas de tenant, validando identidade do token (`401`), correspondência estrita `token.sub == tenant_id` (`403`), bloqueio de `X-Tenant-ID` forjado (`403`) e proteção contra sobrescrita de tenant existente (`409`).
  3. Proteção de `GET /tenants` via `X-Admin-Key`.
- **Demonstração automatizada e interativa:**
  - Suíte [`tests/test_security_authz.py`](../tests/test_security_authz.py) e [`tests/test_tenant_isolation.py`](../tests/test_tenant_isolation.py) (`test_cross_tenant_api_idor_blocked`, `test_header_spoofing_x_tenant_id_blocked`, `test_tenant_hijacking_via_post_tenants_blocked`).
  - Laboratório interativo na interface web (`/app` → aba **Visão Dupla & Segurança** → botões *Invasão Cross-Tenant* e *Header Spoofing*).

### Achado #2 (Alto) — SSRF (Server-Side Request Forgery) no Cadastro de URLs de Scraping
- **Onde estava:** `MonitorTargetCreate.url` em [`src/core/models.py`](../src/core/models.py) (aceitava qualquer `str` sem validação de protocolo ou host, contrariando a promessa do [`docs/lgpd.md`](lgpd.md)).
- **Descrição do risco:** Um cliente mal-intencionado podia cadastrar URLs apontando para serviços internos (`http://127.0.0.1:8000/...`), rede interna (`http://10.0.0.1/...`), metadados de nuvem (`http://169.254.169.254/latest/meta-data/`) ou arquivos locais (`file:///etc/passwd`), forçando o Worker Scraper a realizar requisições internas.
- **Correção implementada:** Validador `validate_monitor_url` em [`src/core/security.py`](../src/core/security.py) acoplado via `@field_validator("url")` em `MonitorTargetCreate` e `MonitorTargetUpdate`, rejeitando com **HTTP 422** qualquer esquema fora de `http/https` (e `mock/test` apenas quando `ALLOW_MOCK_URLS=true`) e bloqueando IPs privados/loopback/link-local via módulo `ipaddress`.
- **Demonstração automatizada:** `test_ssrf_urls_rejected_by_api` (6 vetores parametrizados em [`tests/test_security_authz.py`](../tests/test_security_authz.py)) + botão *Ataque SSRF* na interface web.

### Achado #3 (Médio) — Configuração Permissiva de CORS (`allow_origins=["*"]` com `allow_credentials=True`)
- **Onde estava:** [`src/api/main.py`](../src/api/main.py) linhas 19–25 (versão Etapa 2).
- **Descrição do risco:** Combinar wildcard `*` com `allow_credentials=True` é uma má configuração clássica que amplia a superfície para requisições cross-origin indesejadas a partir de sites de terceiros, além da ausência de headers de hardening HTTP.
- **Correção implementada:** Substituição por lista explícita `CORS_ALLOWED_ORIGINS` (via variável de ambiente) com `allow_credentials=False` e adição de middleware de headers (`X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: strict-origin-when-cross-origin`).
- **Demonstração automatizada:** `test_security_headers_and_cors_hardening` em [`tests/test_security_authz.py`](../tests/test_security_authz.py) e verificação estática em [`scripts/security_audit.py`](../scripts/security_audit.py).

---

## 3. Auditoria de Dependências (`requirements.txt`)

- Todas as 28 bibliotecas em [`requirements.txt`](../requirements.txt) estão com **versões fixadas (`==`)** para builds reprodutíveis no CI e no Docker (`fastapi==0.143.0`, `pydantic==2.14.0`, `uvicorn==0.54.0`, `requests==2.34.2`, `urllib3==2.8.0`, `beautifulsoup4==4.15.0`, `tinydb==4.9.0`, `pytest==9.1.1`).
- Autenticação HMAC-SHA256, validação anti-SSRF (`ipaddress`/`urllib.parse`) e rate limiting foram implementados com a **biblioteca padrão do Python**, reduzindo a superfície de ataque de terceiros (0 novas dependências externas adicionadas na Etapa 3).
- Execução da auditoria automatizada (`python scripts/security_audit.py`): **4/4 verificações aprovadas (0 pendências)**, integrada ao workflow [`.github/workflows/ci.yml`](../.github/workflows/ci.yml).

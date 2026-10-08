# HardTrack Solutions — Rastreador e Monitor de Preços de Hardware
> **Plataforma SaaS Multi-Tenant de Monitoramento Autônomo e Alertas de Preços em Tempo Real**

[![CI Pipeline](https://github.com/GuilhermeMachry/Projeto_SAAS/actions/workflows/ci.yml/badge.svg)](https://github.com/GuilhermeMachry/Projeto_SAAS/actions/workflows/ci.yml)
[![Python Version](https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.14-blue.svg)](https://www.python.org/)
[![Multi-Tenancy](https://img.shields.io/badge/tenancy-Silo%20JSON%20(TinyDB)-green.svg)](docs/adr/001-tenancy-silo-json.md)
[![License](https://img.shields.io/badge/license-MIT-purple.svg)](LICENSE)

* **Disciplina:** Arquitetura de Software SAAS (8512) · EC7 · SETREM  
* **Docente:** Prof. Jonas Pacheco  
* **Aluno / Unidade de PI:** Guilherme Machry  
* **Cliente Fictício:** HardTrack Solutions  
* **Repositório Oficial:** [https://github.com/GuilhermeMachry/Projeto_SAAS](https://github.com/GuilhermeMachry/Projeto_SAAS)

---

## 📌 Status das Entregas do Projeto Integrador

| Etapa | Foco da Entrega | Prazo | Peso | Status |
| :---: | :--- | :---: | :---: | :---: |
| **Etapa 1** | **Proposta de Arquitetura:** C4 Níveis 1, 2 e Esboço 3 + ADRs (1 a 4) + Atributos de Qualidade + LGPD | 26/09/2026 | 20% | ✅ **Concluído** |
| **Etapa 2** | **Núcleo Multi-Tenant:** Repositório estruturado + CI verde + 2 Serviços (API + Worker) + Isolamento ao vivo + Mapa DDD + ADRs (5 e 6) | 22/10/2026 | 25% | ✅ **Pronto para Defesa** |
| **Etapa 3** | **Qualidade e Testes:** Suíte no pipeline + Teste de vazamento + Relatório k6 + SLO/SLA | 12/11/2026 | 25% | ⏳ Previsto |
| **Etapa 4** | **Produto Integrado:** Demo completa + Defesa de Custo Unitário com memória de cálculo | 03/12/2026 | 30% | ⏳ Previsto |

---

## 📂 Estrutura de Documentação do Projeto (`docs/`)

Em estrito atendimento ao **Guia do Projeto Integrador**, todos os artefatos de arquitetura estão versionados na pasta `docs/`:

```text
docs/
├── visao.md                          # 1.1 Visão do Produto, Personas de Tenant e Monetização
├── atributos.md                      # 1.4 Atributos de Qualidade (Cenários SEI mensuráveis)
├── lgpd.md                           # 1.5 Mapeamento LGPD e Medidas Técnicas por Camada
├── c4/                               # 1.2 Modelagem de Arquitetura C4
│   ├── README.md                     # Visão geral dos Níveis C4 e Limites de Tenancy
│   ├── diagrama_nivel_1_contexto.html# C4 Nível 1 interativo (Contexto do Sistema)
│   ├── diagrama_nivel_2_containers.html# C4 Nível 2 interativo (Containers Executáveis)
│   └── esboco_nivel_3_componentes.md # C4 Nível 3 (Componentes Críticos e Limites de Tenant)
├── adr/                              # 1.3 e 2.5 Architecture Decision Records
│   ├── README.md                     # Índice formal dos ADRs
│   ├── 001-tenancy-silo-json.md      # ADR 001: Silo por Arquivo JSON (Pool vs Schema vs Silo)
│   ├── 002-stack-python-tinydb.md    # ADR 002: Stack Backend e Persistência NoSQL Embutida
│   ├── 003-notificacoes-telegram.md  # ADR 003: Notificações Push via Telegram Bot API
│   ├── 004-ambiente-local-worker.md  # ADR 004: Arquitetura de Execução Local e Agendador
│   ├── 005-decomposicao-servicos.md  # ADR 005 (Etapa 2): Decomposição em 2 Serviços (API e Worker)
│   └── 006-comunicacao-resiliencia.md# ADR 006 (Etapa 2): Comunicação Inter-serviços e Resiliência
└── ddd/                              # 2.4 Mapa de Contextos (Domain-Driven Design)
    └── mapa_contextos.md             # Bounded Contexts, Context Map e Linguagem Ubíqua
```

---

## 🛠️ Arquitetura dos 2 Serviços em Execução (Etapa 2)

O núcleo da aplicação é composto por **2 serviços desacoplados** que operam de forma autônoma:

```
                  ┌──────────────────────────────────────────────┐
                  │                 CLIENTES                     │
                  │   (Tenant A - B2C)     (Tenant B - B2B)      │
                  └──────────────┬───────────────────┬───────────┘
                                 │                   │
                        HTTP REST│                   │Push Alertas
                                 ▼                   ▼
                  ┌────────────────────────┐       ┌────────────────────────┐
                  │  SERVIÇO 01: API REST  │       │  TELEGRAM BOT GATEWAY  │
                  │     (FastAPI Gateway)  │       │  (Notificações Push)   │
                  └──────────────┬─────────┘       └───────────▲────────────┘
                                 │ Leitura / Escrita           │ Dispara Alerta
                                 ▼                             │
                         ┌────────────────────────────────────────┐
                         │   CAMADA DE SILOS FÍSICOS (TinyDB)     │
                         │  • storage/tenants/tenant_joao.json    │
                         │  • storage/tenants/tenant_oficina.json │
                         └────────────────────────────────────────┘
                                 ▲
                                 │ Varredura periódica & Gravação de Histórico
                  ┌──────────────┴─────────┐
                  │   SERVIÇO 02: WORKER   │──────► E-commerces (Kabum/Terabyte)
                  │ (Scraper BeautifulSoup)│        Requisições HTTP com Retry Exponencial
                  └────────────────────────┘
```

1. **Serviço 01 — API REST Gateway (`src/api/`):**
   * Implementado em **FastAPI**;
   * Responsável por onboarding de tenants, cadastro de metas de preço e consultas;
   * Endpoint de expurgo atômico LGPD (`DELETE /tenants/{id}`);
   * Sanitização rigorosa de `tenant_id` impedindo ataques de *Path Traversal*.
2. **Serviço 02 — Worker Autônomo de Scraping (`src/worker/`):**
   * Motor de varredura periódica assíncrona;
   * Scraping resiliente com **BeautifulSoup4** (timeout estrito de 5s e até 3 retries exponenciais);
   * Comparação do valor coletado contra o preço-alvo do tenant;
   * Despacho de alertas com links parametrizados de afiliados (`affiliate_tag`).

---

## 🚀 Como Rodar o Projeto no Ambiente Local

### Pré-requisitos
* Python 3.10+ (ou Docker / Docker Compose)
* Git instalado

### 1. Clonar e Instalar Dependências

```bash
git clone https://github.com/GuilhermeMachry/Projeto_SAAS.git
cd Projeto_SAAS

# Criar e ativar ambiente virtual
python3 -m venv .venv
source .venv/bin/activate

# Instalar dependências
pip install -r requirements.txt
```

---

## 🎯 Demonstração ao Vivo do Isolamento (Checklist da Etapa 2)

Para a **Defesa Técnica ao Vivo** diante do docente, execute o script interativo que comprova os 6 requisitos essenciais de Tenancy e LGPD:

```bash
python demo_isolamento.py
```

### O que o script valida e imprime na tela:
1. **Criação de 2 Tenants Heterogêneos:** Cria `tenant_joao_b2c` (B2C) e `tenant_techparts_b2b` (B2B);
2. **Persistência em Silos Físicos Separados:** Mostra os arquivos `tenant_joao_b2c.json` e `tenant_techparts_b2b.json` criados em disco;
3. **Prova Matemática de Isolamento de Leitura:** Consulta com a credencial de A retorna apenas o componente de A (zero dados de B); consulta com a credencial de B retorna apenas o componente de B (zero dados de A);
4. **Ciclo do Worker Isolado:** Executa o scraping e grava o histórico exclusivamente dentro do silo correspondente de cada tenant;
5. **Teste de Segurança:** Tenta injetar `../../etc/passwd` e comprova o bloqueio imediato contra Path Traversal;
6. **Expurgo LGPD (Art. 18):** Exclui o Tenant A e comprova que seu arquivo foi deletado, enquanto o Tenant B permanece 100% íntegro.

---

## 🧪 Execução da Suíte de Testes Automatizada

Os testes validam a integridade dos silos, endpoints da API e a resiliência do Worker:

```bash
pytest -v
```

Resultado esperado: **12 testes passando (100% verde)**:
```text
tests/test_api_service.py::test_api_healthcheck PASSED
tests/test_api_service.py::test_create_and_get_tenant PASSED
tests/test_api_service.py::test_add_and_list_targets_by_tenant PASSED
tests/test_api_service.py::test_cross_tenant_api_isolation PASSED
tests/test_api_service.py::test_delete_tenant_lgpd_endpoint PASSED
tests/test_tenant_isolation.py::test_tenant_creation_and_file_isolation PASSED
tests/test_tenant_isolation.py::test_cross_tenant_isolation_read PASSED
tests/test_tenant_isolation.py::test_path_traversal_prevention PASSED
tests/test_tenant_isolation.py::test_lgpd_atomic_delete PASSED
tests/test_worker_resilience.py::test_parse_price_formats PASSED
tests/test_worker_resilience.py::test_scraper_resilience_on_failure PASSED
tests/test_worker_resilience.py::test_worker_cycle_triggers_alert_and_records_history PASSED
```

---

## 🖥️ Executando os 2 Serviços

### Opção A: Execução Local Direta (2 Terminais)

* **Terminal 1 — API REST Gateway:**
  ```bash
  python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload
  ```
  * Swagger UI interativo: `http://localhost:8000/docs`
  * Healthcheck: `http://localhost:8000/health`

* **Terminal 2 — Background Worker:**
  ```bash
  python -m src.worker.runner --interval 60
  # Ou para uma execução única sob demanda:
  python -m src.worker.runner --once
  ```

---

### Opção B: Execução via Docker Compose (Comando Único)

```bash
docker compose up --build
```
Ambos os containers (`hardtrack_api` e `hardtrack_worker`) sobem em conjunto compartilhando o volume dos silos de dados.

---

## 📋 Checklist de Aceite da Etapa 2 (Auto-Conferência)

- [x] **Demo do isolamento entre 2 tenants, ao vivo, na defesa técnica do dia** (`demo_isolamento.py`)
- [x] **Comunicação entre os 2 serviços justificada em ADR** (`docs/adr/006-comunicacao-resiliencia.md`)
- [x] **Pipeline base verde no repositório** (`ci/ci.yml` / GitHub Actions)
- [x] **Mapa de contextos coerente com o C4 da Etapa 1** (`docs/ddd/mapa_contextos.md`)
- [x] **Degrau Alto Alcançado:**
  - Resiliência básica demonstrada (timeout + retry exponencial + 0% crashes)
  - Isolamento testado rigorosamente na camada de dados e de API
  - Linguagem ubíqua evidente no código
  - Alternativas descartadas justificadas com números nos ADRs

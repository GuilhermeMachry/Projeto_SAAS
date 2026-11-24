# HardTrack Solutions
### *Plataforma SaaS Multi-Tenant de Inteligência de Preços e Alertas de Hardware em Tempo Real*

[![Multi-Tenancy](https://img.shields.io/badge/Tenancy-Silo%20por%20Arquivo%20JSON-blue.svg)](docs/adr/001-tenancy-silo-json.md)
[![Arquitetura](https://img.shields.io/badge/Arquitetura-Modelo%20C4%20%2B%20DDD-teal.svg)](docs/c4/README.md)
[![LGPD](https://img.shields.io/badge/Conformidade-LGPD%20Art.%2018%20(Expurgo%20At%C3%B4mico)-green.svg)](docs/lgpd.md)
[![Defesa Técnica](https://img.shields.io/badge/Etapa%203-Qualidade%2C%20k6%20%26%20Seguran%C3%A7a-brightgreen.svg)](docs/qualidade-e-testes.md)
[![SLO](https://img.shields.io/badge/SLO-p95%20%3C%20150ms%20%7C%20Erro%20%3C%201%25-informational.svg)](docs/slo.md)
[![Licença](https://img.shields.io/badge/Licen%C3%A7a-MIT-purple.svg)](LICENSE)

---

## 🎯 Sobre o Produto

O **HardTrack Solutions** é uma plataforma SaaS (*Software as a Service*) concebida para automatizar o monitoramento de componentes de informática de alta performance (placas de vídeo, processadores, memórias RAM e unidades de armazenamento).

### O Problema que Resolvemos
O mercado de hardware no Brasil é marcado por **volatilidade contínua de preços**, oscilações bruscas de estoque e promoções relâmpago descentralizadas em múltiplos e-commerces (Kabum, Terabyte, Pichau, Amazon). Consumidores individuais e pequenas montadoras perdem horas realizando checagens manuais diárias e frequentemente perdem lotes promocionais por questão de minutos.

### A Nossa Proposta de Valor
A plataforma opera como uma sentinela inteligente e autônoma:
1. **Varredura Contínua:** Coleta periodicamente os valores praticados pelos e-commerces cadastrados;
2. **Avaliação Automatizada:** Confronta a cotação em tempo real com a meta de preço estipulada pelo cliente;
3. **Alertas Instantâneos Push:** Dispara notificações em menos de 1 segundo via **Telegram**, contendo o link da oferta já parametrizado com a tag de afiliados da plataforma para compra imediata.

---

## 👥 Personas e Modelos de Uso

A arquitetura multi-tenant foi desenhada para atender a dois perfis centrais de clientes com demandas heterogêneas:

| Persona | Perfil do Cliente | Volume Monitorado | Principal Necessidade |
| :--- | :--- | :---: | :--- |
| **Tenant A** | **Consumidor Final / Gamer (B2C)** | 1 a 5 URLs simultâneas | Alertas diretos no smartphone sem instalação de apps pesados, foco em desconto direto para montagem pessoal. |
| **Tenant B** | **Oficina / Montadora Local (B2B)** | 20 a 50 URLs simultâneas | Cotação em lote para reposição de estoque, acompanhamento de margens de revenda e histórico cronológico de flutuação de mercado. |

---

## 💡 Modelo de Negócio e Sustentabilidade

A plataforma estrutura sua sustentabilidade financeira em três pilares complementares:
* **Marketing de Afiliados:** Receita gerada por comissão sobre conversões a partir dos links de alerta enriquecidos com tags comerciais;
* **Planos por Assinatura (Freemium & B2B Pro):** Modalidade gratuita com limite de links e periodicidade padrão; modalidade Pro com prioridade de fila e cotas ilimitadas;
* **Inteligência de Mercado:** Agregação anonimizada de séries históricas para geração de relatórios de tendências sazonais de preço.

---

## 🏛️ Destaques da Engenharia de Software

O desenvolvimento segue rigorosas práticas de engenharia de software e padrões de arquitetura SaaS:

* **Isolamento Físico de Tenancy (Silo por Arquivo):**  
  Cada cliente opera sobre um silo de dados independente (`storage/tenants/tenant_<id>.json`), garantindo segregação total, zero risco de vazamento cruzado e eliminação do overhead de servidores de banco relacionais.
* **Decomposição em 2 Serviços Independentes:**  
  * **Serviço 01 (API REST Gateway):** Interface interativa em FastAPI para onboarding, gestão de metas e histórico.
  * **Serviço 02 (Worker Autônomo):** Processo em background com motor BeautifulSoup4 resiliente (timeout de 5s, retries com Exponential Backoff e 0% crashes).
* **Privacidade e LGPD por Design:**  
  Coleta estritamente minimizada (Telegram Chat ID e URLs de hardware) sob a base legal de Execução de Contrato (Art. 7º, V) e mecanismo de **expurgo atômico** em atendimento ao Artigo 18 da LGPD.

---

## 📚 Documentação do Projeto

Toda a documentação técnica exigida pelo Guia do Projeto Integrador está organizada na pasta [`docs/`](docs/):

| Documento | Descrição do Conteúdo |
| :--- | :--- |
| 📖 **[Visão do Produto](docs/visao.md)** | Problema de mercado, proposta de valor, personas detalhadas e monetização. |
| 📐 **[Modelagem C4](docs/c4/README.md)** | Diagramas interativos de [Contexto (Nível 1)](docs/c4/diagrama_nivel_1_contexto.html), [Containers (Nível 2)](docs/c4/diagrama_nivel_2_containers.html) e [Componentes Críticos (Nível 3)](docs/c4/esboco_nivel_3_componentes.md). |
| 📝 **[Decisões Arquiteturais (ADRs)](docs/adr/README.md)** | Registros formais de decisões (ADR 001 a 006) comparando opções, números e custos em R$. |
| 🎯 **[Atributos de Qualidade](docs/atributos.md)** | Cenários mensuráveis padrão SEI/Len Bass (Desempenho, Confiabilidade e Auditabilidade). |
| 🛡️ **[Mapeamento LGPD](docs/lgpd.md)** | Inventário de dados pessoais, minimização, medidas de segurança em 4 camadas e expurgo. |
| 🗺️ **[Mapa de Contextos DDD](docs/ddd/mapa_contextos.md)** | Bounded Contexts, mapa de relações Upstream/Downstream e glossário de Linguagem Ubíqua. |
| 📊 **[SLO / SLA do Produto](docs/slo.md)** | Metas mensuráveis (`p95 < 150 ms`, erro `< 1%`), premissa de pico (`20 VUs`) e limiares k6 (Entregável 3.4 + Ficha Enc. 16). |
| 🚀 **[Relatório de Carga (k6)](docs/carga-enc14.md)** | Resultado real do k6 no pico (`p95 = 61,51 ms`, `0%` erro) vs. SLO + análise de gargalo sob estresse (`p95 = 204,83 ms`). |
| 🧪 **[Qualidade, Testes & CI](docs/qualidade-e-testes.md)** | Suíte de 44 testes (unidade, integração, contrato API↔Worker, 9 vetores de isolamento) e demo de falha no CI. |
| 🔐 **[Verificação de Segurança](docs/seguranca.md)** | Checklist completo (AuthZ HMAC-SHA256, SSRF, CORS, secrets, dependências) e 3 achados reais corrigidos. |
| 📋 **[Ficha SLO Preenchida (Enc. 16)](docs/ficha-slo-enc16-preenchida.md)** | Transcrição das 6 respostas da atividade do Encontro 16 (também disponível em [`ficha-slo-enc16-1911-preenchida.docx`](ficha-slo-enc16-1911-preenchida.docx)). |
| 🤖 **[Declaração de Uso de IA](docs/uso-de-ia.md)** | Registro de transparência das ferramentas de IA utilizadas nas Etapas 2 e 3, escopo e julgamento crítico. |

---

## 📂 Estrutura Enxuta do Repositório

O projeto segue estritamente a convenção de repositórios SaaS, centralizando toda a documentação das etapas na pasta `docs/` e mantendo a raiz limpa e organizada:

```text
├── .github/          # Automações de CI (GitHub Actions)
├── docker/           # Definições de contêineres Docker (API e Worker)
├── docs/             # Toda a documentação e entregáveis das Etapas (C4, ADRs, DDD, LGPD)
├── scripts/          # Utilitários e script de demonstração ao vivo
├── src/              # Código-fonte da aplicação (API REST e Worker de Scraping)
├── storage/          # Armazenamento físico dos Silos por Tenant
├── tests/            # Suíte de testes automatizados (Pytest)
├── docker-compose.yml# Orquestração unificada dos serviços
├── pytest.ini        # Configurações de execução de testes
├── README.md         # Fachada de apresentação do produto e projeto
└── requirements.txt  # Dependências Python fixadas
```

---

## ⚡ Demonstração Rápida, Interface Nativa e Execução

### 1. Como Abrir a Interface Web Interativa Nativa (Perfis B2C + B2B + Lab de Segurança)
Roda 100% nativamente em Python/FastAPI (sem Node/npm), já com os dois perfis do SaaS (**Tenant A — João B2C Gamer** e **Tenant B — Oficina TechParts B2B**) e laboratório interativo de segurança:

```bash
# Inicia a API + Interface Web Nativa e abre automaticamente no navegador
.venv/bin/python run_app.py
# Acesse: http://127.0.0.1:8000/app
```

### 2. Como Rodar a Suíte de Testes (Etapa 3 — 44 Testes) e Auditoria de Segurança
```bash
# Suíte completa (unitários, integração, contrato API↔Worker, isolamento multi-vetor e segurança)
.venv/bin/pytest -v

# Auditoria automatizada de segurança (secrets, CORS, cobertura AuthZ, dependências)
.venv/bin/python scripts/security_audit.py

# Demonstração controlada de que o pipeline quebra quando um teste falha (Etapa 3.1)
./scripts/demo_pipeline_fail.sh
```

### 3. Como Rodar o Teste de Carga k6 (Etapa 3.3)
```bash
# Com a API rodando na porta 8000:
docker run --rm --network host -v "$(pwd)/tests/load:/scripts:ro" grafana/k6 run /scripts/carga.js
```

### 4. Como Rodar a Demonstração de Isolamento e os 2 Serviços
* **Demo de Isolamento CLI:** `.venv/bin/python scripts/demo_isolamento.py`
* **Opção Direta:** Inicie a API (`.venv/bin/python -m uvicorn src.api.main:app --port 8000`) e o Worker (`.venv/bin/python -m src.worker.runner --interval 60`) em terminais separados.
* **Opção Docker:** Suba ambos com um comando único via `docker compose up --build`.

---

## 👨‍💻 Informações Acadêmicas

* **Instituição:** SETREM — Sociedade Educacional Três de Maio  
* **Curso:** Engenharia de Computação (EC7)  
* **Disciplina:** Arquitetura de Software SAAS (8512) · 2026-2  
* **Professor:** Jonas Pacheco (`@jonasrpacheco86`)  
* **Aluno:** Guilherme Machry (`@GuilhermeMachry`)

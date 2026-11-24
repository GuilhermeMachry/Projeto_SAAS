# Declaração de Uso de Inteligência Artificial (Etapa 2)

**Disciplina:** Arquitetura de Software SAAS (8512) · EC7 · SETREM  
**Docente:** Prof. Jonas Pacheco  
**Aluno:** Guilherme Machry  
**Entrega:** Etapa 2 — Núcleo Multi-Tenant  
**Data:** Outubro / 2026  

---

Em conformidade com as diretrizes do Guia do Projeto Integrador (seção 3 — *Declaração de uso de IA a partir da Etapa 2*), este documento detalha por artefato relevante as ferramentas utilizadas, a finalidade, a metodologia de uso e o processo crítico de aceitação, rejeição ou correção:

| Artefato / Componente | Ferramenta de IA | Para quê foi usada | Como foi usada e o que foi aceito, rejeitado ou corrigido |
| :--- | :--- | :--- | :--- |
| **ADR 005 (Decomposição de Serviços)** | Google DeepMind / Antigravity | Estruturação de argumentos de decomposição síncrona vs. assíncrona. | • **Aceito:** A recomendação de manter o gateway REST separado do loop de scraping para evitar congelamento de I/O.<br>• **Rejeitado:** Sugestão inicial de usar microsserviços com Service Mesh (rejeitada por complexidade excessiva e alto custo de memória para o ambiente local do projeto). |
| **ADR 006 (Comunicação e Resiliência)** | Google DeepMind / Antigravity | Mapeamento de estratégias de resiliência e retentativas em web scraping. | • **Aceito:** Política de Exponential Backoff (1s, 2s, 4s) com timeout estrito de 5s.<br>• **Rejeitado:** Sugestão de utilizar RabbitMQ/Kafka como broker externo (rejeitada para manter R$ 0,00 de custo e evitar daemons adicionais no notebook). |
| **Mapa de Contextos (DDD)** | Google DeepMind / Antigravity | Revisão de terminologia estratégica (Bounded Contexts e Context Map). | • **Aceito:** A separação entre o Core Domain (Monitoramento de Preços) e Supporting Domains (Gestão de Tenants e Notificações).<br>• **Corrigido:** Ajustada a Linguagem Ubíqua para refletir rigorosamente o vocabulário do hardware brasileiro (ex: *Componente Monitorado*, *Preço-Alvo*, *Alerta de Oportunidade*). |
| **Script de Demonstração (`demo_isolamento.py`)** | Google DeepMind / Antigravity | Apoio na estruturação do roteiro automatizado da defesa técnica. | • **Aceito:** O fluxo em 6 etapas cobrindo onboarding, isolamento de leitura, execução do worker, teste de Path Traversal e expurgo LGPD.<br>• **Corrigido:** Inclusão de formatação em cores ANSI e asserções matemáticas estritas garantindo que Tenant A não receba dados de Tenant B. |
| **Suíte de Testes Automatizada (`tests/`)** | Google DeepMind / Antigravity | Geração de casos de teste de borda para o parser de preços e isolamento. | • **Aceito:** Fixtures temporárias com `tmp_path` e testes de injeção de diretório.<br>• **Corrigido:** Ajustadas as regras de regex do parser de preços para tratar corretamente o separador de milhar brasileiro (ex: `R$ 2.450`). |

---

## Etapa 3 — Qualidade, Carga (k6), Segurança e Interface Nativa (Novembro / 2026)

| Artefato / Componente | Ferramenta de IA | Para quê foi usada | Como foi usada e o que foi aceito, rejeitado ou corrigido |
| :--- | :--- | :--- | :--- |
| **Hardening de Segurança (`src/core/security.py`, `src/api/auth.py`, `docs/seguranca.md`)** | Google DeepMind / Antigravity | Auditoria do código da Etapa 2 para localizar vulnerabilidades reais (ausência de AuthZ, SSRF e CORS aberto) e implementar correções. | • **Aceito:** Autenticação stateless HMAC-SHA256 com stdlib Python (zero novas dependências), validador anti-SSRF via `ipaddress` e rate limiter por tenant.<br>• **Rejeitado:** Sugestão de adotar um servidor OAuth2/Keycloak externo (rejeitada por custo de RAM e complexidade incompatível com o escopo de 50 tenants). |
| **SLO e Testes de Carga k6 (`docs/slo.md`, `tests/load/carga.js`, `docs/carga-enc14.md`)** | Google DeepMind / Antigravity | Estruturação dos scripts k6 com thresholds coerentes ao modelo da Ficha do Encontro 16 e cenário de estresse para descoberta de gargalo. | • **Aceito:** Cenário de pico multi-tenant (20 VUs = 15 B2C + 5 B2B) e teste de estresse focado em contenção de lock de um único silo B2B.<br>• **Corrigido:** Todos os números de latência e taxa de erro do relatório foram obtidos a partir da execução real do `grafana/k6` contra a API local (nenhum dado simulado). |
| **Suíte Ampliada & Contrato (`tests/test_service_contract.py`, `tests/test_security_authz.py`)** | Google DeepMind / Antigravity | Elaboração dos testes de contrato API ↔ Silo ↔ Worker e cobertura multi-vetor de vazamento (9 vetores). | • **Aceito:** Testes de header spoofing (`X-Tenant-ID`), Noisy Neighbor (`429` vs `200`) e auditoria automática de segurança no CI.<br>• **Corrigido:** Isolamento do estado global do rate limiter via fixture `autouse` no `conftest.py` para evitar interferência entre testes. |
| **Interface Web Nativa (`src/web/`, `run_app.py`)** | Google DeepMind / Antigravity | Criação de interface interativa zero-build servida diretamente pelo FastAPI para visualização dos perfis B2C e B2B e laboratório de segurança ao vivo. | • **Aceito:** SPA em HTML/CSS/JS puro servido pelo FastAPI (sem dependência de Node/npm) com autenticação real via `/auth/token`, gráficos SVG e botões de ataque real (IDOR/SSRF/Path Traversal). |

# Architecture Decision Records (ADRs)

Este diretório contém os Registros de Decisões Arquiteturais (**ADRs — Architecture Decision Records**) do projeto **HardTrack Solutions**, documentando as escolhas técnicas fundamentais, as alternativas descartadas e as consequências positivas e negativas mensuráveis.

---

## Formato Padronizado de Cada Decisão (Encontro 02 / 05)

Cada ADR segue estritamente a estrutura requerida pela disciplina:
1. **Contexto:** Os fatos e os números reais do cenário que forçam a decisão (mínimo de 3 métricas numéricas).
2. **Decisão:** Uma frase afirmativa no presente: *"Adotaremos..."*.
3. **Alternativas Descartadas:** As duas alternativas que perderam — e a justificativa técnica objetiva de por que foram descartadas para este contexto.
4. **Consequências:** Análise explícita das consequências positivas e negativas, com impacto operacional e valores de custo em R$ obrigatórios.

---

## Índice de Decisões Arquiteturais

| ADR | Título | Etapa | Status | Resumo da Decisão |
| :--- | :--- | :---: | :---: | :--- |
| **[ADR 001](001-tenancy-silo-json.md)** | Estratégia de Multi-Tenancy baseada em Silo por Arquivo JSON | Etapa 1 | Aprovado | Adoção de silos físicos de dados por tenant (`tenant_<id>.json`) com TinyDB, garantindo isolamento estrito e expurgo instantâneo para LGPD. |
| **[ADR 002](002-stack-python-tinydb.md)** | Stack Backend e Persistência NoSQL Embutida | Etapa 1 | Aprovado | Seleção de Python 3, FastAPI, BeautifulSoup4 e TinyDB para desenvolvimento ágil, sem RDBMS tradicional e consumo < 85 MB RAM. |
| **[ADR 003](003-notificacoes-telegram.md)** | Canal de Notificações Push via Telegram Bot API | Etapa 1 | Aprovado | Utilização da Telegram Bot API para alertas em tempo real com custo R$ 0,00 e entrega < 800 ms com links de afiliados. |
| **[ADR 004](004-ambiente-local-worker.md)** | Arquitetura de Execução Local e Agendamento do Worker | Etapa 1 | Aprovado | Estruturação do Worker via loop assíncrono em Python com timer configurável e flag determinística `--once` para testes e CI. |
| **[ADR 005](005-decomposicao-servicos.md)** | Decomposição Arquitetural em Dois Serviços (API e Worker) | Etapa 2 | Aprovado | Divisão do núcleo em 2 serviços independentes: API REST Gateway (FastAPI) e Background Scraper Worker. |
| **[ADR 006](006-comunicacao-resiliencia.md)** | Estratégia de Comunicação Inter-serviços e Política de Resiliência | Etapa 2 | Aprovado | Comunicação desacoplada orientada a estado em Silos com travas atômicas e resiliência via timeout de 5s e Exponential Backoff (3 retries). |

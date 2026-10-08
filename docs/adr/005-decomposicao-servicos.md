# ADR 005: Decomposição Arquitetural em Dois Serviços Independentes (API e Worker)

**Status:** Aprovado  
**Data:** 2026-10-01 (Etapa 2 — Núcleo Multi-Tenant)  
**Decisores:** Guilherme Machry  
**Componente Afetado:** Topologia de Serviços e Decomposição de Containers  

---

## 1. Contexto

Para o cumprimento da **Etapa 2 (Núcleo Multi-Tenant)**, é obrigatória a existência e execução de **2+ serviços rodando no ambiente**.

No modelo de negócio do **HardTrack Solutions**:
- A **API REST** lida com operações interativas de baixa latência (tempo de resposta alvo < **100 ms** para cadastro de tenants, adição de links e consulta de status);
- O **Processo de Scraping**, por sua vez, realiza I/O de rede intensivo em sites externos de terceiros (cada ciclo de 10 URLs pode levar entre **5 e 15 segundos** devido à latência de download do HTML e mitigação de rate limiting).

Se essas duas responsabilidades rodassem acopladas no mesmo processo de requisição HTTP, a chamada da API ficaria travada até o término do scraping, degradando a experiência do cliente e estourando limites de timeout HTTP (504 Gateway Timeout).

---

## 2. Decisão

**Adotaremos a decomposição do sistema em dois serviços autônomos e desacoplados: o Serviço 01 (API REST Gateway com FastAPI) e o Serviço 02 (Worker de Monitoramento e Scraping com ciclo autônomo).**

---

## 3. Alternativas Descartadas

* **Alternativa Descartada 1: Monolito Síncrono de Processo Único**  
  *Por que perdeu:* Acoplar o scraping síncrono na rota `POST /tenants/{id}/targets` faria com que o usuário esperasse até 15 segundos pelo retorno do cadastro. Além disso, se o site do e-commerce ficasse lento, todo o servidor web travaria para os demais tenants.
* **Alternativa Descartada 2: Arquitetura de Microsserviços Granulares (5+ Serviços com Service Mesh)**  
  *Por que perdeu:* Dividir a solução em microsserviço de Tenant, microsserviço de Scraper, microsserviço de Notificação, microsserviço de Billing e API Gateway exigiria orquestração complexa com Kubernetes/Istio, aumentando o consumo de memória para mais de **1.5 GB** de RAM e violando o princípio da simplicidade operacional para a escala inicial de 50 tenants.

---

## 4. Consequências

### Positivas:
* **Desacoplamento e Disponibilidade:** A API permanece 100% responsiva (< 50 ms) independentemente de falhas, lentidões ou indisponibilidade temporária de e-commerces externos no Worker.
* **Escalabilidade Independente:** Em cenários futuros de pico de cadastros ou de varredura, o Worker pode ser escalado horizontalmente sem necessidade de replicar a API.
* **Custo Zero (R$ 0,00):** Ambos os serviços rodam como processos nativos leves em Python ou em contêineres Docker independentes no mesmo host Linux.
* **Atendimento aos Requisitos da Etapa 2:** Cumpre integralmente o requisito de 2+ serviços rodando com responsabilidades bem delimitadas.

### Negativas:
* **Gestão de Ciclo de Vida de Múltiplos Processos:** Requer a inicialização de dois comandos (`python -m src.api.main` e `python -m src.worker.runner`) ou orquestração via `docker-compose`.

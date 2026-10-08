# ADR 006: Estratégia de Comunicação Inter-Serviços e Política de Resiliência

**Status:** Aprovado  
**Data:** 2026-10-01 (Etapa 2 — Núcleo Multi-Tenant)  
**Decisores:** Guilherme Machry  
**Componente Afetado:** Comunicação Inter-serviços, Tolerância a Falhas e Resiliência  

---

## 1. Contexto

A decomposição em dois serviços (definida no ADR 005) exige a especificação do mecanismo de comunicação e sincronização entre a **API REST** e o **Worker de Scraping**.

Cenário operacional:
- A API cadastra e atualiza componentes monitorados no silo do tenant;
- O Worker lê periodicamente esses parâmetros para efetuar as cotações;
- E-commerces externos possuem uma taxa de falha intrínseca de **3% a 7%** (timeouts, oscilações de DNS, bloqueios anti-DDoS e respostas HTTP 503/504);
- Soluções baseadas em brokers de mensageria dedicados gerenciados (ex: Amazon SQS, RabbitMQ Cloud) adicionariam um custo de **R$ 80,00 a R$ 200,00/mês**.

---

## 2. Decisão

**Adotaremos a comunicação assíncrona orientada a estado via Silos de Dados (`storage/tenants/tenant_<id>.json`) com travas atômicas de arquivo, combinada a uma política de resiliência no Worker baseada em timeout estrito de 5s por requisição, retentativas com Exponential Backoff (até 3 tentativas) e degradação graciosa com 0% de interrupção no ciclo de varredura.**

---

## 3. Alternativas Descartadas

* **Alternativa Descartada 1: Comunicação Síncrona HTTP Ponto-a-Ponto (Worker chamando API REST para cada produto)**  
  *Por que perdeu:* Criaria acoplamento temporal estreito entre os dois serviços. Se a API estivesse reiniciando ou sob carga momentânea, o Worker falharia em cadeia. Além disso, geraria centenas de requisições HTTP internas redundantes desnecessárias em loop local.
* **Alternativa Descartada 2: Fila Distribuída Externa Dedicada (RabbitMQ ou Apache Kafka)**  
  *Por que perdeu:* Adicionaria complexidade excessiva de orquestração, consumo extra de pelo menos **300 MB de memória RAM** e necessidade de gerenciamento de tópicos e partições para uma volumetria de 50 tenants, infringindo o princípio da navalha de Occam na engenharia de software para este escopo.

---

## 4. Consequências

### Positivas:
* **Desacoplamento Temporal Completo:** A API grava a intenção no silo e responde imediatamente ao cliente; o Worker consome o estado no momento oportuno do seu ciclo.
* **Resiliência Comprovada:** O algoritmo de retry exponencial (1s, 2s, 4s) resolve falhas transitórias de rede sem travar a varredura das outras URLs.
* **Tolerância a Falhas:** Falhas permanentes em um site (ex: página removida 404) são logadas como erro estruturado, e o Worker prossegue normalmente para o próximo item (0% crashes).
* **Custo Zero (R$ 0,00):** Não há custo com brokers pagos ou tráfego de rede interno entre contêineres.

### Negativas:
* **Latência Eventual:** Há um atraso (de segundos a minutos, dependendo do intervalo do agendador) entre o momento em que o usuário cadastra uma URL na API e a primeira execução da coleta pelo Worker.

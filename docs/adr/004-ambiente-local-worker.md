# ADR 004: Arquitetura de Execução Local e Agendamento do Worker

**Status:** Aprovado  
**Data:** 2026-09-24  
**Decisores:** Guilherme Machry  
**Componente Afetado:** Agendamento de Tarefas e Infraestrutura de Execução  

---

## 1. Contexto

A entrega da disciplina exige uma demonstração interativa e executável em ambiente acadêmico local (notebook com sistema operacional Linux), sem orçamento para instâncias de nuvem pagas (custo limite de **R$ 0,00**).

O agendador de tarefas precisa ser capaz de:
- Executar ciclos periódicos de verificação a cada intervalo pré-definido (ex: a cada **60 segundos** em modo demonstração e a cada **15 a 60 minutos** em produção);
- Fornecer um modo determinístico de execução única (`--once`) para rodar em testes automatizados e pipelines de CI/CD que duram menos de **10 segundos**;
- Evitar o consumo de recursos computacionais pesados (como brokers em cluster) que sobrecarreguem o notebook.

---

## 2. Decisão

**Adotaremos a estruturação do Worker de monitoramento via loop autônomo em Python com temporizador configurável e suporte a execução sob demanda (`--once`), executado em processo desacoplado da API.**

---

## 3. Alternativas Descartadas

* **Alternativa Descartada 1: Celery com Broker Redis / RabbitMQ**  
  *Por que perdeu:* O Celery introduz alta complexidade de orquestração e exige a inicialização e manutenção de daemons adicionais de broker (Redis/RabbitMQ), consumindo mais de **150 MB a 250 MB** de RAM e complicando a montagem de pipelines rápidos de CI/CD, o que é desnecessário para a volumetria de 50 tenants.
* **Alternativa Descartada 2: Agendador via Crontab do Sistema Operacional Linux**  
  *Por que perdeu:* O Crontab do SO é dependente da configuração de privilégios e caminhos absolutos do host Linux, não possui portabilidade entre diferentes ambientes de desenvolvimento, dificulta o mock de testes automatizados e não roda de forma nativa e isolada em contêineres Docker leves sem configurações complexas de permissão.

---

## 4. Consequências

### Positivas:
* **Execução em Comando Único:** O Worker pode ser iniciado com um simples comando (`python -m src.worker.runner`), operando de forma imediata e transparente.
* **Custo Zero (R$ 0,00):** Nenhuma infraestrutura externa de mensageria ou orquestração paga é requerida.
* **Compatibilidade Total com CI/CD:** O parâmetro `--once` permite que o pipeline do GitHub Actions execute uma rodada completa de teste em menos de **3 segundos**.
* **Baixíssimo Overhead:** Consumo de CPU inferior a **1%** em repouso e uso de RAM em torno de **30 MB**.

### Negativas:
* **Escala Horizontal Limitada:** Em um cenário com dezenas de milhares de tenants, um loop único em processo único precisaria ser refatorado para workers distribuídos com particionamento de silos.

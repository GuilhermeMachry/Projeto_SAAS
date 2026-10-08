# Atributos de Qualidade e Cenários de Arquitetura

Os atributos de qualidade do sistema foram formalizados segundo o modelo do **SEI (Software Engineering Institute / Len Bass)**, sendo caracterizados por seis dimensões essenciais: **Fonte**, **Estímulo**, **Artefato**, **Ambiente**, **Resposta** e **Medida de Resposta Mensurável**.

---

## Tabela de Cenários Estimulatórios (Padrão SEI)

| Atributo de Qualidade | Estrutura do Cenário Estimulatório (SEI) | Resposta e Medida Mensurável |
| :--- | :--- | :--- |
| **Desempenho (Performance)**<br>*Foco: Latência de Coleta e Parsing* | • **Fonte:** Agendador interno de tarefas / Disparo Periódico<br>• **Estímulo:** Início do ciclo de varredura de preços<br>• **Artefato:** Worker Scraper (BeautifulSoup4 + Engine HTTP)<br>• **Ambiente:** Operação regular local (notebook Linux) | • **Resposta:** Executar requisições HTTP, parsing da árvore DOM do HTML e avaliação de preço-alvo.<br>• **Medida Mensurável:** Coleta, parsing e avaliação de lote de **10 URLs distintas** concluídas em **menos de 15 segundos** (média ≤ 1.5s por URL). |
| **Confiabilidade (Reliability)**<br>*Foco: Tolerância a Falhas e Resiliência* | • **Fonte:** E-commerce externo indisponível, timeout de rede ou alteração no layout da página (seletor DOM quebrado)<br>• **Estímulo:** Erro de conexão (HTTP 5xx / Timeout / ConnReset) ou seletor CSS nulo<br>• **Artefato:** Módulo de Scraping / Parser / Loop do Worker<br>• **Ambiente:** Execução contínua em segundo plano | • **Resposta:** Tratamento gracioso de exceções (*graceful degradation*), política de retry exponencial (até 3 tentativas) e registro de log estruturado sem interrupção do serviço.<br>• **Medida Mensurável:** **0% de interrupção (crashes)** no loop do Worker e **100% dos erros registrados** em log com contexto e timestamp. |
| **Auditabilidade & Integridade**<br>*Foco: Rastreabilidade Cronológica* | • **Fonte:** Finalização do ciclo de checagem com sucesso<br>• **Estímulo:** Obtenção de leitura de preço válida de uma URL<br>• **Artefato:** Silo de Dados do Tenant (`tenant_<id>.json` via TinyDB)<br>• **Ambiente:** Operação normal | • **Resposta:** Gravação atômica do histórico de verificação no silo exclusivo do respectivo tenant.<br>• **Medida Mensurável:** **100% das checagens gravadas** contendo: Timestamp ISO-8601, URL alvo, preço capturado, preço meta e flag indicativa de disparo de alerta. |
| **Segurança & Confidencialidade**<br>*Foco: Isolamento Estrito de Tenancy* | • **Fonte:** Requisição de API ou ciclo de processamento do Worker<br>• **Estímulo:** Operação de leitura, escrita ou deleção contendo credencial de um determinado Tenant<br>• **Artefato:** TenantStorageManager / Silos de Dados<br>• **Ambiente:** Ambiente multi-tenant concorrente | • **Resposta:** Confinamento físico do acesso ao arquivo silo correspondente (`storage/tenants/tenant_<tenant_id>.json`).<br>• **Medida Mensurável:** **0% de vazamento cruzado** (zero registros de Tenant A visíveis ou modificáveis por Tenant B) e **100% de sanitização** contra ataques de Path Traversal. |

---

## Trade-offs e Justificativas Numéricas

1. **Desempenho vs. Bloqueio por Rate Limiting:**
   - Para evitar banimento de IP e captchas nos e-commerces monitorados, adota-se um pequeno delay intencional (500ms a 1s) entre requisições sequenciais, mantendo a latência total de 10 URLs abaixo de 15s sem acionar defesas anti-bot.
2. **Confiabilidade vs. Latência:**
   - O uso de retry exponencial com timeout estrito de 5s por requisição garante que e-commerces lentos não travem o ciclo dos demais tenants.

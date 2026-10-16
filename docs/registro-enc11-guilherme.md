# Folha de registro — Encontro de 15/10

**Arquitetura de Software SAAS · o CampoConta rodando**

**Nome:** Guilherme Machry da Silva &nbsp;&nbsp;&nbsp; **Unidade de PI:** HardTRack

**O que é:** o seu registro dos seis experimentos (frente) e o primeiro desenho dos serviços do seu produto (verso). **O que não é:** prova. Os comandos estão em experimentos.md, no repositório.

- [ ] Frente: a resposta de abertura e as seis previsões, cada uma escrita ANTES de rodar.
- [ ] Verso: as caixas do seu produto e as quatro respostas.
- [ ] Verso fotografado antes de entregar a folha ao professor.

Não entra aqui: comando copiado, saída do terminal colada.

---

**Abertura (2 min, sem consulta).** O que é um microsserviço? E o que muda nele quando o produto é multi-tenant?

> Um microsserviço é uma meio que em um aplicativo grande seja dividido em componentes menores que conversam por uma API.
>
> Quando é um contexto multi-tentat o microsserviço muda drasticamente. Onde o serviço passa a utilizar um Token JWT, que é basicamente uma identidade do cliente.

---

**Os seis experimentos.** Previsão antes do sinal; "O que saiu", depois de rodar; "O nome disso", com o professor, no fim de cada experimento.

| Experimento | Minha previsão | O que saiu | O nome disso |
| :--- | :--- | :--- | :--- |
| **1 — Seguir uma requisição** | Atravessa 3 serviços, na ordem:<br>1º gateway -> 2º producao -> 3º cobranca (via relay/outbox). | • Sem token (GET /cotas): `{"erro":"token ausente ou invalido"}`<br>• Com $A (GET /cotas): 2 cotas da Alvorada (A-017: 1200/10000 kg; A-023: 0/6000 kg).<br>• POST /entregas?associado=A-023&kg=400: entrega_id=3, evento_id=1, entregue_kg=400.<br>• Logs em ordem: [gateway] POST /entregas -> producao; [producao] entrega 3 gravada + evento 1 na outbox; [cobranca] evento 1 -> taxa R$ 20.00 gerada; [producao/relay] evento 1 entregue.<br>• GET /taxas: 2 taxas (R$ 60 e R$ 20), total: 80. | API Gateway, Propagação de Contexto (x-tenant-id) e Transactional Outbox / Eventos |
| **2 — A Buricá tenta ver o dado da Alvorada** | Não. Mesmo desligando o filtro WHERE no código, o banco bloqueia o acesso aos dados de outro tenant via Row-Level Security (RLS). | • GET /entregas/1 com $B: `{"erro":"entrega nao encontrada"}`.<br>• Com header x-tenant-id: alvorada: ignorou o header externo e retornou apenas a entrega 2 (Buricá).<br>• Com POST /chaves/filtro-app/off: continuou retornando só a entrega 2 (protegido pelo banco).<br>• Com DISABLE ROW LEVEL SECURITY: vazaram todas as entregas (id 1 e 3 da Alvorada + id 2 da Buricá).<br>• Restaurado com ENABLE ROW LEVEL SECURITY e filtro-app/on. | Isolamento Multi-tenant, Defesa em Profundidade e Row-Level Security (RLS) |
| **3 — O relatório da diretoria** | Não resolve, porque cada microsserviço possui seu próprio banco de dados isolado (entrega fica no producao-db e taxa no cobranca-db). | • SELECT ... FROM entrega e JOIN taxa t no producao-db: `ERROR: relation "taxa" does not exist`.<br>• GET /relatorio com $A: o gateway consultou producao e cobranca via HTTP e agregou o JSON com producao (2 cotas) e cobranca (total: 80, 2 taxas) em total_ms: 3 ms. | Database per Service (Banco por Serviço) e API Composition (Agregação no Gateway) |
| **4 — A cobrança sai do ar** | Sim, o balanceiro consegue registrar a entrega normalmente porque producao grava a entrega e o evento na outbox localmente de forma assíncrona. | • Com stop cobranca, os 5 POST /entregas?associado=A-017&kg=100 funcionaram (entregas 4 a 8, eventos 2 a 6, entregue_kg de 1300 a 1700).<br>• GET /fila: `{"pendentes":5}` (log mostrou retry com backoff em 500 ms e 1000 ms).<br>• GET /taxas: `{"erro":"servico indisponivel","total_ms":1198}`.<br>• GET /relatorio: cotas da produção + `"cobranca":"INDISPONIVEL (relatorio parcial)"` (total_ms: 2002).<br>• Após start cobranca e 15s: /fila zerou (`{"pendentes":0}`) e /taxas listou as 5 novas taxas de R$ 5 (total: 105). | Desacoplamento Temporal, Outbox Pattern + Retry com Backoff e Degradação Graciosa |
| **5 — O mesmo evento chega duas vezes** | Sem conferência de repetição, aparecem 2 taxas de R$ 50,00 cada para a entrega de 1000 kg. Com a conferência ligada, aparece apenas 1 taxa. | • Com relay-duplica/on e idempotencia/off: POST de 1000 kg (entrega 9, evento 7) gerou 2 taxas duplicadas de R$ 50 em /taxas (total: 145).<br>• Com idempotencia/on: POST de 2000 kg (entrega 10, evento 8) gerou apenas 1 taxa de R$ 100 (total: 245).<br>• Log cobranca: [cobranca] evento 8 -> taxa de R$ 100.00 gerada / [cobranca] evento 8 JA PROCESSADO - ignorado. | Entrega Pelo Menos Uma Vez (At-least-once Delivery) e Consumidor Idempotente (Idempotência) |
| **6 — O vizinho barulhento** | Sem limite por tenant, a Buricá espera cerca de 6 segundos (~6000 ms) na fila atrás da Alvorada. Com o limite ligado, responde em ~5 ms. | • Com limite-tenant/off e inundar.js: ALVORADA teve `{ "200": 60 }` e BURICA esperou 6068 ms (menor/mediana/maior: 6068 ms).<br>• Com limite-tenant/on e inundar.js: ALVORADA teve `{ "200": 3, "429": 57 }` e BURICA respondeu rápido (3 medidas: menor 4 ms \| mediana 5 ms \| maior 40 ms). | Vizinho Barulhento (Noisy Neighbor) e Rate Limiting / Bulkhead por Tenant (HTTP 429) |

---

**No fim do encontro (2 min).** Releia a sua resposta de abertura e reescreva:

> 

---

## Verso — agora o seu produto

É o produto que a sua equipe propôs no começo do semestre e vai defender em 29/10, na Etapa 2, com dois serviços no ar. O CampoConta não é o seu projeto: use o formato do desenho, não a divisão dele.

**1. As caixas.** Desenhe a porta de entrada, os dois serviços e onde cada um guarda dado. Ponha uma seta para cada conversa entre eles.

> *(Espaço para o desenho das caixas)*

**2. Quatro respostas, uma linha cada.** "Ainda não sei" vale, desde que escrito: vira a sua primeira pendência até 29/10.

a) Qual é o segundo serviço, e o que ele recebe do primeiro?
> 

b) Onde o tenant é descoberto, e como chega ao segundo serviço?
> 

c) Se alguém esquecer o filtro no código, o que segura o vazamento?
> 

d) Se o segundo serviço cair, o que o usuário ainda consegue fazer?
> 

**Em casa, até sábado, 17/10, 23h59:** passe este verso para o arquivo `docs/servicos-rascunho.md` no repositório do seu projeto: salve a foto do desenho na pasta `docs/`, cite o nome dela no arquivo e digite as quatro respostas. Faça o commit e o push. Um arquivo por projeto: se o projeto é de dupla, cada um faz o commit com as respostas combinadas. É o rascunho do ADR de comunicação que a Etapa 2 pede.

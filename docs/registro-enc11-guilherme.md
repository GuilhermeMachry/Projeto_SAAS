# Registro do encontro de 15/10

**Nome:** Guilherme Machry da Silva  
**Unidade de PI:** HardTRack

**O que é:** a folha de registro do encontro, em arquivo. Substitui a folha impressa.
**Onde vai:** copie este arquivo para o repositório do **seu PI**, como `docs/registro-enc11-<seu-primeiro-nome>.md`. Um arquivo por aluno.

## Checklist de entrega

- [x] **Commit 1, `previsoes`:** partes 1 e 2 preenchidas, com push, até 20h05 e **antes** de rodar qualquer comando dos experimentos 2 a 6.
- [x] **Commit 2, `observacoes`:** parte 3 preenchida, com push, até 20h55.
- [x] **Leitura, 20h55 às 21h15:** `o-que-e-microsservico.md`, nesta mesma pasta (aparece no repositório às 20h50: rode `git pull` no clone do CampoConta).
- [x] **Commit 3, `reescrita`:** parte 4 preenchida, com push, logo depois do fechamento (21h15).
- [ ] **Até sábado, 17/10, 23h59:** `docs/servicos-rascunho.md` da sua unidade de PI (ver `experimentos.md`, "Ao terminar").

**Dúvida durante o encontro:** levante a mão; o professor circula.

**Por que a ordem dos commits importa:** no presencial, ninguém rodava antes do sinal do professor. Aqui quem faz esse papel é o `git log`. **Previsão errada vale. Previsão enviada depois de rodar não vale.** Hoje a sua presença também é conferida pelo commit `previsoes`.

**Por que isso interessa ao seu projeto:** na Etapa 2 (29/10) o seu produto precisa ter dois serviços no ar e um tenant sem enxergar o dado do outro. Cada previsão abaixo é uma decisão que você vai ter de tomar nele.

## Parte 1 — Antes de tudo (2 min, sem consulta)

O que é um microsserviço? E o que muda nele quando o produto é multi-tenant?

> Um microsserviço é um meio em que um aplicativo grande seja dividido em componentes menores que conversam por uma API.
> Quando é um contexto multi-tenant o microsserviço muda drasticamente. Onde o serviço passa a utilizar um Token JWT, que é basicamente uma identidade do cliente.

## Parte 2 — As seis previsões

Leia a pergunta marcada **Previsão no registro** em cada experimento de `experimentos.md` e responda aqui em uma linha, com número quando a pergunta pede número. A linha 1 você escreve na abertura, antes de o professor rodar o experimento 1 no projetor.

| Exp. | Previsão |
|---|---|
| 1 | Atravessa 3 serviços, na ordem: `gateway` -> `producao` -> `cobranca` (via relay/outbox). |
| 2 | Não. Mesmo sem o `WHERE` no código, a regra de Row-Level Security (RLS) do banco impede que a Buricá veja entregas da Alvorada. |
| 3 | Não resolve, pois `entrega` e `taxa` estão em bancos de dados separados (`producao-db` e `cobranca-db`). |
| 4 | Sim. O serviço `producao` grava a entrega e o evento na `outbox` localmente; a cobrança processará quando voltar. |
| 5 | Com idempotência desligada, aparecem 2 taxas de R$ 50,00 cada. Com idempotência ligada, aparece apenas 1 taxa. |
| 6 | Sem limite por tenant, a Buricá espera cerca de 6 segundos (~6000 ms). Com o limite ativo, espera ~5 ms. |

Agora, **no terminal aberto na pasta do repositório do seu PI** (não no do CampoConta), troque `<seu-primeiro-nome>` e rode:

```
git add docs/registro-enc11-<seu-primeiro-nome>.md
git commit -m "previsoes"
git push
```

Push recusado porque um colega enviou antes? `git pull --rebase` e `git push` de novo. Confira no GitHub que o commit apareceu. Só depois rode os experimentos 2 a 6.

## Parte 3 — O que aconteceu

Para cada experimento: o que a saída mostrou (o número, a mensagem, a linha do log) e se a sua previsão acertou. A coluna "O nome disso" você preenche no fechamento, ou antes, se souber o nome.

| Exp. | O que a saída mostrou | Acertei? | O nome disso |
|---|---|---|---|
| 1 | Sem token: `{"erro":"token ausente ou invalido"}`. Com `$A`: 2 cotas da Alvorada. `POST /entregas?associado=A-023&kg=400`: gerou `entrega_id: 3`, `evento_id: 1`, `entregue_kg: 400`. Log em ordem: `[gateway] POST /entregas -> producao`, `[producao] entrega 3 gravada + evento 1 na outbox`, `[cobranca] evento 1 -> taxa de R$ 20.00 gerada`, `[producao/relay] evento 1 entregue a cobranca`. `GET /taxas`: 2 taxas, `total: 80`. | Sim | API Gateway, Propagação de Contexto (`x-tenant-id`) e Transactional Outbox |
| 2 | `GET /entregas/1` com `$B`: `{"erro":"entrega nao encontrada"}`. Com `-H "x-tenant-id: alvorada"`: ignorou header externo e trouxe só entrega 2 (Buricá). Com `filtro-app/off`: continuou trazendo só entrega 2. Após `DISABLE ROW LEVEL SECURITY`: vazaram todas as entregas (1 e 3 da Alvorada + 2 da Buricá). Restaurado com `ENABLE ROW LEVEL SECURITY` e `filtro-app/on`. | Sim | Isolamento Multi-tenant, Defesa em Profundidade e Row-Level Security (RLS) |
| 3 | `JOIN` no `producao-db`: `ERROR: relation "taxa" does not exist`. `GET /relatorio`: gateway buscou `producao` (2 cotas) e `cobranca` (`total: 80`, 2 taxas) e juntou no JSON (`total_ms: 3`). | Sim | Database per Service (Banco por Serviço) e API Composition (Agregação no Gateway) |
| 4 | Com `cobranca` parada (`stop`), os 5 `POST /entregas` funcionaram (`entrega_id` 4 a 8, `evento_id` 2 a 6). `GET /fila`: `{"pendentes":5}` e log de retry com backoff (500 ms, 1000 ms). `GET /taxas`: `{"erro":"servico indisponivel","total_ms":1198}`. `GET /relatorio`: `"cobranca":"INDISPONIVEL (relatorio parcial)"` (`total_ms: 2002`). Ao religar (`start`), após 15s: `{"pendentes":0}` e 5 novas taxas de R$ 5 (`total: 105`). | Sim | Desacoplamento Temporal, Outbox + Retry com Backoff e Degradação Graciosa |
| 5 | Com `relay-duplica/on` e `idempotencia/off`, o `POST` de 1000 kg (`entrega_id: 9`, `evento_id: 7`) gerou 2 taxas repetidas de R$ 50 (`total: 145`). Com `idempotencia/on`, o `POST` de 2000 kg (`entrega_id: 10`, `evento_id: 8`) gerou só 1 taxa de R$ 100 (`total: 245`) e no log: `[cobranca] evento 8 (tenant=burica) JA PROCESSADO - ignorado`. | Sim | Entrega Pelo Menos Uma Vez (*At-least-once*) e Consumidor Idempotente (Idempotência) |
| 6 | Com `limite-tenant/off` e `inundar.js`: Alvorada teve `{ '200': 60 }` e Buricá esperou `6068 ms` (menor/mediana/maior: 6068 ms). Com `limite-tenant/on`: Alvorada teve `{ '200': 3, '429': 57 }` e Buricá respondeu rápido (3 medidas: menor `4 ms`, mediana `5 ms`, maior `40 ms`). | Sim | Vizinho Barulhento (*Noisy Neighbor*) e Rate Limiting / Bulkhead por Tenant (HTTP 429) |

**O sistema não subiu na sua máquina?** Use a tabela "Se der errado" do `README.md` da raiz do repositório por no máximo 10 minutos. Não resolveu: pare de consertar. Faça as previsões e o commit `previsoes` normalmente, e só então abra `saidas-reais.md` e preencha esta parte a partir dele. Nesse caso, escreva "Preenchido pelas saídas reais" na linha logo acima da tabela.

Agora, **no terminal aberto na pasta do repositório do seu PI** (não no do CampoConta), troque `<seu-primeiro-nome>` e rode:

```
git add docs/registro-enc11-<seu-primeiro-nome>.md
git commit -m "observacoes"
git push
```

Push recusado porque um colega enviou antes? `git pull --rebase` e `git push` de novo. Confira no GitHub que o commit apareceu.

## Parte 4 — Reescrita (no fechamento)

Releia a sua resposta da parte 1 e reescreva-a aqui, sem apagar a original. Termine com uma linha: o que mudou.

> Um microsserviço é um serviço organizado em torno de um assunto do negócio, dono exclusivo dos seus próprios dados (banco próprio, sem `JOIN` direto com tabelas de outros serviços), com implantação independente, projetado para falhar e que conversa com outros serviços apenas pela rede (de forma síncrona via HTTP ou assíncrona via fila/eventos com Outbox e idempotência).
> Em um produto multi-tenant, o contexto do tenant nasce na porta de entrada (Gateway) a partir do token do cliente, viaja em todas as chamadas síncronas (`x-tenant-id`) e dentro do payload de cada evento assíncrono (`tenant_id`), é conferido em profundidade em cada banco de dados (filtro no código + trava com Row-Level Security) e exige controle de cota/rate limiting por tenant para evitar o efeito de vizinho barulhento (*noisy neighbor*).
> **O que mudou:** na abertura pensei apenas em "dividir em componentes menores conversando por API e usando token JWT"; agora ficou claro que a fronteira real está nos dados isolados por serviço, na comunicação assíncrona resiliente (Outbox/idempotência) e na propagação e defesa do `tenant_id` (RLS e rate limit) ponta a ponta.

Agora, **no terminal aberto na pasta do repositório do seu PI** (não no do CampoConta), troque `<seu-primeiro-nome>` e rode:

```
git add docs/registro-enc11-<seu-primeiro-nome>.md
git commit -m "reescrita"
git push
```

Push recusado porque um colega enviou antes? `git pull --rebase` e `git push` de novo. Confira no GitHub que o commit apareceu.

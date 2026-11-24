# Relatório de Teste de Carga com k6 (Etapa 3.3)

**Disciplina:** Arquitetura de Software SAAS (8512) · EC7 · SETREM 2026-2  
**Produto:** HardTrack Solutions — Plataforma SaaS Multi-Tenant de Hardware  
**Entregável:** Etapa 3.3 — Relatório de Carga (k6) confrontado com o SLO ([`docs/slo.md`](slo.md))  
**Data da Execução:** 24/11/2026 · **Ferramenta:** Grafana k6 `v2.4.0` (container `grafana/k6`)  
**Autor:** Guilherme Machry  

---

## 1. Ambiente e Comando de Execução

- **Serviço avaliado:** Serviço 01 — API REST Gateway (`src.api.main:app`, FastAPI + Uvicorn 1 worker, AuthZ HMAC-SHA256 ativo, Silos TinyDB em disco local com trava `RLock + fcntl.flock`).
- **Host:** Notebook Linux local (mesmo ambiente especificado no [ADR 004](adr/004-ambiente-local-worker.md)).
- **Script do cenário de pico:** [`tests/load/carga.js`](../tests/load/carga.js) (com exatamente os mesmos `thresholds` de [`docs/slo.md`](slo.md)).
- **Script de estresse / gargalo:** [`tests/load/estresse_gargalo.js`](../tests/load/estresse_gargalo.js).

```bash
# 1. Subir a API Gateway localmente
.venv/bin/python -m uvicorn src.api.main:app --host 127.0.0.1 --port 8000 --log-level warning

# 2. Executar o cenário de pico oficial (20 VUs = 15 B2C + 5 B2B)
docker run --rm --network host \
  -v "$(pwd)/tests/load:/scripts:ro" \
  -e BASE_URL=http://127.0.0.1:8000 \
  grafana/k6 run /scripts/carga.js
```

---

## 2. Cenário 1 — Pico Declarado Multi-Tenant (`tests/load/carga.js`)

### Perfil de Carga
- **Estágios:** `5s` rampa 0 → 20 VUs · `25s` sustentação em **20 VUs** · `5s` rampa 20 → 0 VUs (total `35s`).
- **Composição Multi-Tenant:** **20 tenants reais isolados** criados no `setup()` (**15 B2C Freemium + 5 B2B Pro**, coerente com a premissa de 40% da base de 50 tenants do ADR 001 no pico de Black Friday / drop de GPU).
- **Fluxo por iteração:** `POST /tenants/{id}/targets` (fluxo crítico) → `GET /tenants/{id}/targets` (consulta do painel) → `DELETE /tenants/{id}/targets/{target_id}` (limpeza respeitando cota B2C de 5 URLs) + `sleep(0.3s)`. Ao final, o `teardown()` executa o expurgo LGPD (`DELETE /tenants/{id}`) de todos os 20 silos de teste.

### Confronto Número contra Número: SLO Declarado vs. Resultado Medido (k6)

| Métrica (SLI) | SLO Declarado ([`docs/slo.md`](slo.md)) | Resultado Medido (k6) | Margem / Diferença | Veredito |
|---|---:|---:|---:|:---:|
| **Latência p95 geral (`http_req_duration`)** | `< 150,00 ms` | **`61,51 ms`** | `-88,49 ms` (59% abaixo do teto) | ✅ **PASSOU** |
| **Latência p95 de `POST /tenants/{id}/targets`** | `< 150,00 ms` | **`66,56 ms`** | `-83,44 ms` (56% abaixo do teto) | ✅ **PASSOU** |
| **Taxa de erro (`http_req_failed`)** | `< 1,00%` (`< 0.01`) | **`0,00%`** (`0 / 4.942`) | `-1,00 p.p.` (zero erros) | ✅ **PASSOU** |
| **Latência média / mediana / máxima** | *(referência)* | `23,13 ms` / `14,37 ms` / `97,30 ms` | Máximo abaixo de 100 ms | ✅ **SAUDÁVEL** |
| **Vazão sustentada (throughput)** | *(referência)* | **`139,83 req/s`** (`4.942 reqs`) | `4.902 / 4.902` checks (100%) | ✅ **ESTÁVEL** |

### Evidência Bruta da Saída Real do k6 (Cenário de Pico)

```text
  █ THRESHOLDS 

    http_req_duration
    ✓ 'p(95)<150' p(95)=61.51ms

      {endpoint:post_target}
      ✓ 'p(95)<150' p(95)=66.56ms

    http_req_failed
    ✓ 'rate<0.01' rate=0.00%

  █ TOTAL RESULTS 

    checks_total.......: 4902    138.699109/s
    checks_succeeded...: 100.00% 4902 out of 4902
    checks_failed......: 0.00%   0 out of 4902

    ✓ POST /targets retorna 201
    ✓ GET /targets retorna 200
    ✓ DELETE /targets/{id} retorna 200

    HTTP
    http_req_duration..............: avg=23.13ms  min=2.21ms  med=14.37ms  max=97.3ms   p(90)=54.02ms  p(95)=61.51ms 
      { endpoint:post_target }.....: avg=27.3ms   min=4.64ms  med=17.58ms  max=97.21ms  p(90)=59.9ms   p(95)=66.56ms 
    http_req_failed................: 0.00%  0 out of 4942
    http_reqs......................: 4942   139.830884/s
    iterations.....................: 1634   46.233036/s
    vus_max........................: 20     min=20         max=20
```

**Conclusão do Cenário de Pico:** Quando a carga de pico é distribuída entre múltiplos tenants (cada um em seu próprio arquivo silo), a arquitetura de **Silo por Arquivo JSON (ADR 001)** evita contenção cruzada entre clientes e atende com ampla folga todos os SLOs declarados (**p95 de 66,56 ms** no fluxo crítico e **0,00% de falha**).

---

## 3. Cenário 2 — Estresse e Identificação de Gargalo Real (`tests/load/estresse_gargalo.js`)

Para atingir o degrau de excelência arquitetural (*identificar um gargalo real com hipótese mensurável de correção*), executamos um segundo ensaio concentrando **40 VUs simultâneos escrevendo intensivamente no MESMO silo B2B** (`tenant_stress_single_b2b.json`, `sleep(0.05s)`, com rate limiting desabilitado via `RATE_LIMIT_RPM=0` para isolar o comportamento da camada de persistência):

### Resultado Medido no Estresse (Contenção de Silo Único)

| Métrica | Cenário 1 (20 VUs · 20 Silos) | Cenário 2 (40 VUs · 1 Silo B2B) | Variação | Status vs. SLO (`< 150 ms`) |
|---|---:|---:|---:|:---:|
| **Latência p95 (`http_req_duration`)** | `61,51 ms` | **`204,83 ms`** | **+233% (3,3x mais lento)** | ❌ **VIOLOU O SLO** |
| **Latência Média (`avg`)** | `23,13 ms` | **`159,77 ms`** | **+591% (6,9x mais lento)** | ❌ Degradado |
| **Latência Mediana (`med`)** | `14,37 ms` | **`192,39 ms`** | **+1.239%** | ❌ Fila na trava |
| **Taxa de Erro (`http_req_failed`)** | `0,00%` | **`0,00%`** (`0 / 4.136`) | Zero corrupção de JSON | ✅ Integridade preservada |
| **Throughput** | `139,83 req/s` | `179,25 req/s` (`4.136 reqs`) | Saturado no lock do arquivo | — |

```text
  █ THRESHOLDS 

    http_req_duration
    ✗ 'p(95)<150' p(95)=204.83ms

    http_req_failed
    ✓ 'rate<0.01' rate=0.00%

    http_req_duration..............: avg=159.77ms min=3.88ms  med=192.39ms max=236.04ms p(90)=202.38ms p(95)=204.83ms
    http_req_failed................: 0.00%  0 out of 4136
    http_reqs......................: 4136   179.251432/s
    time="2026-11-24T23:45:29Z" level=error msg="thresholds on metrics 'http_req_duration' have been crossed"
```

### Diagnóstico do Gargalo Identificado
1. **Causa Raiz:** No modelo de Silo JSON com TinyDB (`src/core/storage.py`), a trava exclusiva por tenant (`RLock` + `fcntl.flock`) garantiu **0% de erros e 0% de corrupção de arquivo**, porém serializou todas as 40 threads concorrentes de escrita do mesmo tenant B2B. Como cada operação de `insert`/`remove` no TinyDB realiza leitura integral, desserialização JSON e **reescrita completa do arquivo em disco com `indent=2`** (*full-file rewrite*), o tempo de espera na fila do lock saltou a mediana para `192,39 ms` e o `p95` para **`204,83 ms`**.
2. **Observação de Defesa em Profundidade:** Em operação padrão com `RATE_LIMIT_RPM=1200` habilitado, o `TenantRateLimiter` impede que um único tenant *Noisy Neighbor* atinja esse nível de saturação contínua (limitando-o com `HTTP 429` e mantendo os outros silos em ~`60 ms`).

### Hipóteses Concretas de Correção (para Evolução na Etapa 4 / Escala B2B)
1. **Hipótese 1 — Otimização de I/O no Silo (Custo R$ 0,00, ganho estimado de 40%–60% no p95):**
   - Remover `indent=2` nas gravações do TinyDB (reduzindo tamanho do payload e custo de serialização);
   - Separar a tabela `history` (alta frequência de append) para um arquivo **append-only NDJSON** (`tenant_<id>.history.ndjson`), evitando reescrever o JSON completo a cada leitura;
   - Trocar a trava exclusiva simples por **Read-Write Lock** para permitir leituras paralelas (`GET /targets`, `GET /history`) sem aguardar outras leituras.
2. **Hipótese 2 — Motor Embarcado com WAL/MVCC para Tenants B2B Enterprise (Escala > 100 escritas/s por tenant):**
   - Substituir o TinyDB em silos de altíssima concorrência por um armazenamento key-value embarcado com suporte a escrita concorrente/WAL (ex.: **LMDB** ou **DuckDB/RocksDB** por arquivo-silo), preservando o isolamento físico por tenant sem introduzir servidor RDBMS.

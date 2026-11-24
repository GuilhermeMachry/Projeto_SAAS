# SLO — HardTrack Solutions

**Disciplina:** Arquitetura de Software SAAS (8512) · EC7 · SETREM 2026-2  
**Entregável:** Etapa 3.4 — SLO/SLA de Produto (vínculo com a Ficha do Encontro 16, 19/11/2026)  
**Responsável:** Guilherme Machry  

---

## Tabela de SLOs do Produto

| Métrica | Fórmula | Meta | Justificativa de negócio |
|---|---|---|---|
| **Latência de `POST /tenants/{tenant_id}/targets`** | p95 das respostas | **< 150 ms** | Fluxo crítico de cadastro de oferta de hardware durante promoções relâmpago (ex.: Black Friday ou drop de GPU). Oficinas B2B cadastram dezenas de links em sequência e consumidores B2C correm contra o esgotamento de estoque; respostas acima de 150 ms degradam o fluxo interativo (coerente com o ADR 005, alvo base de 100 ms + margem de 50 ms para I/O em disco sob pico). |
| **Erro de `POST /tenants/{tenant_id}/targets`** | requisições com falha (HTTP ≥ 400, incluindo 429, ou timeout) / total | **< 1%** | Cada falha no cadastro representa um componente não monitorado, perda direta da janela promocional para o gamer B2C e perda de margem de revenda em lote para a oficina B2B. |
| **Latência de `GET /tenants/{tenant_id}/targets`** | p95 das respostas | **< 150 ms** | Tela principal do dashboard (B2C e B2B) onde o cliente acompanha cotações atuais vs. preço-alvo em tempo real. |
| **Latência do ciclo de coleta do Worker** *(vínculo `docs/atributos.md` — Etapa 1)* | tempo total de coleta, parsing DOM e avaliação de 10 URLs | **< 15 s** (≤ 1,5 s/URL) | Garante varredura periódica contínua sem acionar rate limiting anti-bot dos e-commerces (delay intencional de 500 ms–1 s) e entrega do alerta Telegram em < 800 ms após detecção. |

---

## Pico

- **Quando:** Sexta-feira de **Black Friday / Promoção Relâmpago (20h–22h)** ou noite de lançamento/drop de nova geração de placas de vídeo (GPUs).
- **Volume simultâneo:** **20 usuários simultâneos (VUs)** autenticados operando ao mesmo tempo.
- **Premissa:** Base inicial projetada no [ADR 001](adr/001-tenancy-silo-json.md) de **50 tenants ativos** (40 B2C + 10 B2B), assumindo taxa de concorrência simultânea de **40%** no minuto de pico (**15 consumidores B2C + 5 oficinas B2B** cadastrando metas e consultando o painel simultaneamente em seus respectivos silos físicos).

---

## Limiar no k6

Os limiares abaixo são aplicados literalmente no script [`tests/load/carga.js`](../tests/load/carga.js) — qualquer violação reprova a execução do k6:

```javascript
thresholds: {
  http_req_duration: ['p(95)<150'],
  'http_req_duration{endpoint:post_target}': ['p(95)<150'],
  http_req_failed: ['rate<0.01'],
}
```

---

## SLA Externo Sugerido (Compromisso Comercial)

Para manter margem operacional de segurança (*error budget*) entre a meta interna de engenharia (SLO) e o compromisso contratual com o cliente (SLA):

| Plano | SLA de Disponibilidade Mensal | SLA de Erro de API | Tempo Máximo de Alerta após Detecção |
|---|---|---|---|
| **B2C Freemium** | 99,0% (melhor esforço) | < 2% | Até 5 s via Telegram Push |
| **B2B Pro (Oficinas)** | 99,5% (≤ 3h36m/mês de indisponibilidade) | < 1,5% | Até 2 s via Telegram Push |

---

## Nota de Evolução em Relação à Ficha (Encontro 16)

- Os números de **latência (`p95 < 150 ms`)**, **erro (`< 1%`)** e **pico (`20 VUs`)** foram definidos a partir do cenário de desempenho já documentado no [ADR 005](adr/005-decomposicao-servicos.md) (`< 100 ms` em operação nominal) e em [`docs/atributos.md`](atributos.md) (`< 15 s` para 10 URLs no Worker), validados empiricamente no relatório de carga [`docs/carga-enc14.md`](carga-enc14.md).
- A foto da ficha física (frente e verso com a conferência da unidade revisora) deve ser anexada em `docs/slo-ficha-1911.jpg` conforme o checklist do Encontro 16.

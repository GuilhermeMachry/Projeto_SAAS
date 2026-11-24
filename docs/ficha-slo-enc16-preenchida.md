# Ficha Preenchida: o SLO do seu produto, no papel (Encontro 16 — 19/11/2026)

**Disciplina:** Arquitetura de Software SAAS (8512) · EC7 · SETREM 2026-2  
**Unidade de PI:** HardTrack Solutions (Guilherme Machry)  
**Arquivo original:** [`ficha-slo-enc16-1911.docx`](../ficha-slo-enc16-1911.docx)  
**Versão DOCX preenchida pronta para impressão:** [`ficha-slo-enc16-1911-preenchida.docx`](../ficha-slo-enc16-1911-preenchida.docx)  

---

## Parte 1 — Escrever (Respostas da Unidade HardTrack Solutions)

| # | Pergunta | Resposta da unidade (HardTrack Solutions) |
|---|---|---|
| **1** | **Fluxo crítico.** Qual operação, se ficar lenta ou falhar, faz o cliente reclamar primeiro? Diga a rota ou a tela. Health check e página estática não valem. | **`POST /tenants/{tenant_id}/targets`** (cadastro de componente de hardware e preço-alvo para monitoramento) e leitura do painel **`GET /tenants/{tenant_id}/targets`**. Em promoções relâmpago de GPUs/CPUs, se o cadastro travar ou falhar, o cliente perde o lote promocional. |
| **2** | **SLI de latência.** "p95 do tempo de resposta de ..." | **p95 do tempo de resposta de `POST /tenants/{tenant_id}/targets`** (e de `GET /tenants/{tenant_id}/targets`). |
| **3** | **SLO de latência.** p95 < quantos ms? Por que esse número para esse produto? | **`p95 < 150 ms`** *(meta calibrada a partir do ADR 005 — alvo nominal < 100 ms — + margem de 50 ms para I/O em disco e trava por silo sob pico)*. Oficinas B2B cadastram dezenas de peças em sequência e gamers B2C precisam registrar alertas imediatamente durante lives/Black Friday antes que o estoque acabe. |
| **4** | **SLO de erro.** Requisições com falha / total < quantos %? Por quê? | **`Falhas / total < 1%`** (incluindo HTTP ≥ 400, 429 e timeouts). Cada requisição com erro no cadastro significa um componente fora do radar do Worker, gerando perda direta de oportunidade de compra (B2C) ou de margem de revenda em lote (B2B). |
| **5** | **Pico.** Quando é o dia de pico? Quantos usuários ao mesmo tempo? Escreva a premissa. | **Sexta-feira de Black Friday / Promoção Relâmpago (20h–22h)** ou lançamento de nova geração de GPUs. **20 usuários ao mesmo tempo.** *Premissa:* base projetada no ADR 001 de 50 tenants ativos (40 B2C + 10 B2B), assumindo 40% de uso simultâneo no pico (15 consumidores B2C + 5 oficinas B2B operando ao mesmo tempo). |
| **6** | **Limiar.** Os números 3 e 4, escritos como thresholds do k6. Em thresholds, 1% se escreve 0.01. | `http_req_duration: ['p(95)<150']` e `http_req_failed: ['rate<0.01']` |

---

## Checklist da Atividade (Encontro 16)

- [x] Referência cruzada com [`docs/atributos.md`](atributos.md) e [`docs/adr/005-decomposicao-servicos.md`](adr/005-decomposicao-servicos.md)
- [x] Parte 1 preenchida em [`ficha-slo-enc16-1911-preenchida.docx`](../ficha-slo-enc16-1911-preenchida.docx) e transcrita acima
- [x] Transcrição oficial no modelo obrigatório em [`docs/slo.md`](slo.md)
- [x] Script k6 com os mesmos limiares em [`tests/load/carga.js`](../tests/load/carga.js)
- [x] Relatório de carga real confrontando número contra número em [`docs/carga-enc14.md`](carga-enc14.md)
- [ ] *(Ação física do aluno)* Anexar a foto da ficha em papel (frente e verso com a conferência da outra unidade) em `docs/slo-ficha-1911.jpg` antes do commit final.

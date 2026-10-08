# Visão do Produto e Contexto de Negócio

**Produto:** Rastreador e Monitor de Preços de Hardware (SaaS Multi-Tenant)  
**Cliente Fictício:** HardTrack Solutions  
**Ambiente de Operação:** Local Notebook Linux  
**Disciplina:** Arquitetura de Software SAAS (8512) · EC7 · SETREM  
**Autor:** Guilherme Machry  

---

## 1. Contextualização do Problema

O mercado de componentes e periféricos de informática (GPUs, CPUs, memórias RAM, placas-mãe e unidades de armazenamento SSD/NVMe) é caracterizado por:
- **Altíssima volatilidade de preços**, impulsionada por variações cambiais, lançamentos de novas gerações e ciclos de oferta e demanda.
- **Oscilações constantes de estoque** e promoções relâmpago distribuídas de forma descentralizada em múltiplos e-commerces (Kabum, Terabyte, Pichau, Amazon, etc.).

Tanto consumidores individuais quanto pequenas montadoras enfrentam o problema da **checagem manual diária e fragmentada**. Esse processo é:
1. Extremamente ineficiente e desgastante em tempo operacional;
2. Propenso a erros humanos de checagem;
3. Suscetível à perda de oportunidades de compra no menor valor histórico devido ao esgotamento rápido de lotes promocionais.

---

## 2. Proposta de Valor do Produto

A **HardTrack Solutions** propõe uma plataforma SaaS (*Software as a Service*) multi-tenant de monitoramento automatizado e contínuo de preços de hardware.

O sistema atua como um agente autônomo e inteligente que:
- Monitora periodicamente URLs cadastradas pelos clientes;
- Extrai os valores de oferta e disponibilidade em tempo real via web scraping resiliente;
- Compara o valor detectado com a meta de preço pré-definida pelo cliente;
- Dispara alertas instantâneos via **Telegram Push Notification** assim que um componente atinge ou supera favoravelmente o valor-alvo definido pelo tenant.

Dessa forma, o usuário economiza tempo e garante a aquisição de componentes no melhor preço sem necessidade de intervenção humana recorrente.

---

## 3. Mapeamento de Personas de Tenant

Para garantir que a arquitetura atenda a perfis heterogêneos de usuários com diferentes volumetrias de requisição e requisitos operacionais, o sistema especifica duas personas centrais de tenant:

### Tenant A — Entusiasta / Consumidor Final (B2C)
* **Perfil:** Indivíduo focado na montagem ou upgrade de seu setup pessoal de computador/jogos/trabalho.
* **Volume:** Monitora entre 1 e 5 links simultâneos.
* **Necessidades:**
  - Facilidade e agilidade de cadastro via interface simples;
  - Alertas instantâneos diretamente no smartphone (Telegram), dispensando a instalação de aplicativos dedicados pesados;
  - Foco em economia direta e aproveitamento de cupons e quedas de preço.

### Tenant B — Oficina / Pequeno Montador B2B
* **Perfil:** Pequena assistência técnica ou montadora de PCs customizados para revenda local.
* **Volume:** Cadastra dezenas de componentes de alta rotação (20 a 50 URLs simultâneas) para reposição de estoque.
* **Necessidades:**
  - Acompanhamento contínuo da margem de lucro na revenda;
  - Tomada de decisão estratégica para compras em lote;
  - Frequência elevada de checagem automatizada;
  - Histórico cronológico detalhado de flutuação de preços para auditoria e inteligência de compras.

---

## 4. Modelo de Negócio e Estratégias de Monetização

A sustentabilidade financeira e monetização da plataforma estruturam-se em três pilares complementares:

1. **Marketing de Afiliados (Fonte Principal de Receita):**
   - Os alertas de oportunidade enviados aos usuários contêm links parametrizados com tags de afiliados dos principais e-commerces parceiros (Kabum, Amazon, etc.).
   - A cada conversão ou compra realizada através do link de alerta, a plataforma aufere comissão sobre o valor total do pedido (geralmente entre 1% e 5%).

2. **Modelo Freemium por Assinatura:**
   - **Plano Gratuito (Freemium):** Limitado a até 3 URLs por tenant com intervalos de checagem mais espaçados (ex: a cada 6 horas).
   - **Plano Pro / B2B:** Suporte a URLs ilimitadas, prioridade na fila de varredura (checagem a cada 15 a 30 minutos), múltiplos canais de notificação e relatórios exportáveis.

3. **Relatórios de Tendências de Mercado:**
   - Consolidação analítica e anonimizada dos dados históricos de preços coletados em toda a plataforma.
   - Venda de relatórios de inteligência competitiva e previsibilidade de safra de preços para montadoras locais e distribuidores de informática.

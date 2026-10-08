# ADR 003: Canal de Comunicação e Notificações Push via Telegram Bot API

**Status:** Aprovado  
**Data:** 2026-09-24  
**Decisores:** Guilherme Machry  
**Componente Afetado:** Módulo de Notificações e Engajamento  

---

## 1. Contexto

A proposta de valor do **HardTrack Solutions** depende criticamente da velocidade e eficácia de entrega dos alertas de oportunidade no momento exato em que um componente atinge o preço desejado. Promoções relâmpago duram frequentemente menos de **15 a 30 minutos** antes do esgotamento do estoque.

Analisando a volumetria estimada de **500 alertas potenciais por mês**:
- Gateways de SMS cobram em média **R$ 0,12 por mensagem enviada**, totalizando um custo mensal de ~**R$ 60,00 a R$ 150,00**;
- A API oficial do WhatsApp Business impõe cobrança por conversa iniciada pelo negócio (~**R$ 0,32 por disparo**), inviabilizando o modelo financeiro gratuito de validação;
- A entrega deve ocorrer com latência inferior a **2 segundos** diretamente no smartphone do usuário.

---

## 2. Decisão

**Adotaremos a Telegram Bot API como canal oficial de entrega de notificações push em tempo real via chamadas diretas HTTPS POST.**

---

## 3. Alternativas Descartadas

* **Alternativa Descartada 1: Gateway de SMS (ex: Twilio / Zenvia)**  
  *Por que perdeu:* Custo proibitivo (R$ 0,12/envio) para um modelo que visa oferecer plano Freemium. Além disso, o SMS impõe limite severo de 160 caracteres, dificultando a inclusão de especificações completas de hardware e links de afiliados com rastreamento longo.
* **Alternativa Descartada 2: Notificações via E-mail Transacional (SMTP / SendGrid)**  
  *Por que perdeu:* Baixíssima taxa de abertura imediata (média de 15% a 25% com atraso de leitura de horas). E-mails frequentemente caem em abas de "Promoções" ou "Spam", fazendo com que o usuário perca o timing de compra rápida da promoção.

---

## 4. Consequências

### Positivas:
* **Custo Zero Absoluto (R$ 0,00):** A Telegram Bot API é 100% gratuita, sem tarifas por volume de mensagens enviadas.
* **Economia Operacional:** Economia direta de pelo menos **R$ 150,00/mês** em comparação a gateways pagos de SMS ou WhatsApp.
* **Entrega Instantânea:** Latência de entrega inferior a **800 ms** diretamente na tela de bloqueio do smartphone ou aplicativo desktop.
* **Formatação Rica e Afiliados:** Permite formatação em Markdown/HTML, botões de ação e links parametrizados com tags de monetização de afiliados.

### Negativas:
* **Dependência do App Telegram:** O usuário precisa possuir uma conta no Telegram e iniciar uma conversa com o bot para obter seu `chat_id`.
* **Risco de Dependência de Plataforma (Vendor Lock-in):** Mitigado pelo isolamento da interface de despacho (`NotifierInterface`), permitindo plugar futuros adaptadores (ex: Discord Webhook ou E-mail).

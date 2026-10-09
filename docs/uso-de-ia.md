# Declaração de Uso de Inteligência Artificial (Etapa 2)

**Disciplina:** Arquitetura de Software SAAS (8512) · EC7 · SETREM  
**Docente:** Prof. Jonas Pacheco  
**Aluno:** Guilherme Machry  
**Entrega:** Etapa 2 — Núcleo Multi-Tenant  
**Data:** Outubro / 2026  

---

Em conformidade com as diretrizes do Guia do Projeto Integrador (seção 3 — *Declaração de uso de IA a partir da Etapa 2*), este documento detalha por artefato relevante as ferramentas utilizadas, a finalidade, a metodologia de uso e o processo crítico de aceitação, rejeição ou correção:

| Artefato / Componente | Ferramenta de IA | Para quê foi usada | Como foi usada e o que foi aceito, rejeitado ou corrigido |
| :--- | :--- | :--- | :--- |
| **ADR 005 (Decomposição de Serviços)** | Google DeepMind / Antigravity | Estruturação de argumentos de decomposição síncrona vs. assíncrona. | • **Aceito:** A recomendação de manter o gateway REST separado do loop de scraping para evitar congelamento de I/O.<br>• **Rejeitado:** Sugestão inicial de usar microsserviços com Service Mesh (rejeitada por complexidade excessiva e alto custo de memória para o ambiente local do projeto). |
| **ADR 006 (Comunicação e Resiliência)** | Google DeepMind / Antigravity | Mapeamento de estratégias de resiliência e retentativas em web scraping. | • **Aceito:** Política de Exponential Backoff (1s, 2s, 4s) com timeout estrito de 5s.<br>• **Rejeitado:** Sugestão de utilizar RabbitMQ/Kafka como broker externo (rejeitada para manter R$ 0,00 de custo e evitar daemons adicionais no notebook). |
| **Mapa de Contextos (DDD)** | Google DeepMind / Antigravity | Revisão de terminologia estratégica (Bounded Contexts e Context Map). | • **Aceito:** A separação entre o Core Domain (Monitoramento de Preços) e Supporting Domains (Gestão de Tenants e Notificações).<br>• **Corrigido:** Ajustada a Linguagem Ubíqua para refletir rigorosamente o vocabulário do hardware brasileiro (ex: *Componente Monitorado*, *Preço-Alvo*, *Alerta de Oportunidade*). |
| **Script de Demonstração (`demo_isolamento.py`)** | Google DeepMind / Antigravity | Apoio na estruturação do roteiro automatizado da defesa técnica. | • **Aceito:** O fluxo em 6 etapas cobrindo onboarding, isolamento de leitura, execução do worker, teste de Path Traversal e expurgo LGPD.<br>• **Corrigido:** Inclusão de formatação em cores ANSI e asserções matemáticas estritas garantindo que Tenant A não receba dados de Tenant B. |
| **Suíte de Testes Automatizada (`tests/`)** | Google DeepMind / Antigravity | Geração de casos de teste de borda para o parser de preços e isolamento. | • **Aceito:** Fixtures temporárias com `tmp_path` e testes de injeção de diretório.<br>• **Corrigido:** Ajustadas as regras de regex do parser de preços para tratar corretamente o separador de milhar brasileiro (ex: `R$ 2.450`). |

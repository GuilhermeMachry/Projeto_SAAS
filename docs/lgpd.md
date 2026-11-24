# Mapeamento LGPD Preliminar e Segurança por Camada

**Enquadramento Legal:** Lei Geral de Proteção de Dados (Lei nº 13.709/2018 - LGPD)  
**Sistema:** HardTrack Solutions — Rastreador e Monitor de Preços de Hardware  
**Responsável Técnico:** Guilherme Machry  

---

## 1. Inventário de Dados Pessoais Coletados por Tenant

Em estrita consonância com o **Princípio da Minimização dos Dados** (Art. 6º, III da LGPD), a plataforma coleta exclusivamente as informações mínimas indispensáveis para o cumprimento do serviço de monitoramento e envio de notificações:

| Categoria do Dado | Dado Específico | Classificação LGPD | Finalidade do Tratamento |
| :--- | :--- | :--- | :--- |
| **Identificador de Comunicação** | Telegram Chat ID (numérico) | Dado Pessoal | Roteamento e entrega instantânea de notificações push quando o preço-alvo for atingido. |
| **Parâmetros de Serviço** | URLs de produtos e componentes | Dado Operacional | Identificação do link do e-commerce para scraping automatizado. |
| **Parâmetros de Regra de Negócio** | Preço-alvo (R$) e margem de desconto | Dado Operacional | Limiar matemático que ativa o gatilho de notificação. |
| **Registros de Auditoria e Logs** | Timestamp ISO-8601, status de envio e preços históricos | Dado de Log / Rastreabilidade | Auditoria de cumprimento do serviço e histórico consultável pelo próprio usuário. |

> **Nota:** A plataforma **não coleta dados pessoais sensíveis** (Art. 5º, II da LGPD), tais como dados biométricos, dados de saúde, crenças religiosas ou opiniões políticas. Também não são armazenados dados de cartão de crédito ou senhas no modelo local.

---

## 2. Enquadramento na Base Legal (Art. 7º, V - LGPD)

O tratamento das informações dos usuários encontra respaldo legal formal na hipótese do **Artigo 7º, Inciso V da LGPD**:

> *"quando necessário para a execução de contrato ou de procedimentos preliminares relacionados a contrato do qual seja parte o titular, a pedido do titular dos dados"*

### Justificativa:
O titular do dado (seja Consumidor B2C ou Montador B2B) cadastra voluntariamente seu Telegram Chat ID e os links que deseja acompanhar com a finalidade exclusiva de receber os alertas contratados. O tratamento cessa imediatamente mediante solicitação de cancelamento.

---

## 3. Esboço de Medidas Técnicas de Segurança por Camada

A estratégia de segurança adota o princípio de **Defesa em Profundidade** (*Defense-in-Depth*), estabelecendo salvaguardas técnicas em quatro camadas:

| Camada da Arquitetura | Ameaças e Riscos Mapeados | Medida Técnica de Segurança Implementada |
| :--- | :--- | :--- |
| **Armazenamento (Storage)** | • Acesso não autorizado aos dados de terceiros<br>• Retenção indevida após cancelamento<br>• Vazamento cruzado entre tenants | • **Segregação Física Total:** Cada tenant possui seu próprio arquivo silo (`storage/tenants/tenant_<tenant_id>.json`).<br>• **Permissões de SO:** Controle rigoroso de permissões (`chmod 600`) no Linux, permitindo leitura e escrita exclusivamente pelo usuário de serviço.<br>• **Exclusão Atômica (Art. 18 LGPD):** O cancelamento do tenant aciona a exclusão física imediata do arquivo JSON via chamada de sistema. |
| **Aplicação (Backend / API)** | • Vazamento de dados em memória<br>• IDOR (*Insecure Direct Object Reference*)<br>• SSRF (*Server-Side Request Forgery*) | • **Validação e Isolamento por Contexto:** O `tenant_id` é sanitizado com regex (`^[a-zA-Z0-9_-]+$`) para impedir *Path Traversal* (`../`).<br>• **Validação de URLs:** Sanitização e whitelist de protocolos (estritamente `http://` e `https://`). |
| **Rede e Comunicação** | • Interceptação de tráfego (*Man-in-the-Middle*)<br>• Exposição de dados de navegação | • **Criptografia em Trânsito:** Todas as comunicações externas (requisições de scraping e chamadas à API do Telegram) utilizam estritamente **TLS 1.3 / HTTPS** com validação de certificados digitais. |
| **Processo e Sistema Operacional (Host)** | • Elevação de privilégios<br>• Comprometimento do ambiente Linux | • **Princípio do Menor Privilégio:** Os serviços (API e Worker) rodam sob usuário não-root no sistema operacional, sem permissões administrativas de sudo. |

---

## 4. Procedimento para Atendimento aos Direitos do Titular (Art. 18)

Para atender ao direito de eliminação e revogação do consentimento:
1. O usuário autenticado solicita a exclusão através do endpoint `DELETE /tenants/{tenant_id}` (com Bearer token válido do próprio tenant);
2. A API valida a autorização (`require_tenant_access`), impedindo que terceiros excluam dados de outro titular, e chama `TenantStorageManager.delete_tenant(tenant_id)`;
3. O arquivo `tenant_<tenant_id>.json` é removido imediatamente do disco sob trava exclusiva;
4. Nenhum resíduo de histórico, chat ID ou URLs permanece armazenado no sistema.

---

## 5. Status de Implementação das Medidas Técnicas LGPD (Revisão Etapa 3)

| Medida Técnica LGPD | Camada | Status Atual | Prazo / Evidência |
| :--- | :--- | :---: | :--- |
| Segregação física em silo por tenant (`tenant_<id>.json`) | Armazenamento | ✅ **Implementado** | Validado em `tests/test_tenant_isolation.py` |
| Permissões restritas POSIX (`chmod 0o600`) nos silos | Armazenamento | ✅ **Implementado** | Aplicado em `src/core/storage.py` e testado via `stat.S_IMODE` |
| Expurgo atômico definitivo (Art. 18 — `DELETE /tenants/{id}`) | Armazenamento / API | ✅ **Implementado** | Validado em `test_lgpd_atomic_delete_isolation` e na UI (`/app`) |
| AuthZ estrito por tenant (HMAC-SHA256) bloqueando IDOR | Aplicação / API | ✅ **Implementado** | Aplicado em `src/api/auth.py` (Etapa 3.5) |
| Sanitização anti-Path Traversal + validação anti-SSRF | Aplicação / API | ✅ **Implementado** | Aplicado em `src/core/security.py` e `src/core/models.py` |
| Execução com usuário não-root nos containers (`1000:1000`) | Host / Docker | ✅ **Implementado** | Configurado em `docker-compose.yml` |
| Portabilidade automatizada dos dados do titular (Art. 18, V — exportação CSV/JSON completa) | API / Interface | ✅ **Implementado (Parcial B2B CSV)** / 🗓️ **Completo em 03/12/2026** | Exportação CSV ativa no painel B2B; endpoint unificado `GET /tenants/{id}/export` planejado para Etapa 4 (03/12/2026) |
| Criptografia em repouso (*encryption-at-rest* com chave por tenant / AES-GCM) | Armazenamento | 🗓️ **Planejado** | Planejado para evolução pós-MVP / produção em nuvem (Q1/2027), após definição de KMS na Etapa 4 |
| Política automatizada de retenção e expurgo de histórico > 90 dias | Worker / Storage | 🗓️ **Planejado** | Job de compactação/expurgo cronológico planejado para Etapa 4 (03/12/2026) |

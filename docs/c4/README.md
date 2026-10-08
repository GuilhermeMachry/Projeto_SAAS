# Diagramas de Arquitetura C4

Esta pasta contém a modelagem da arquitetura de software da plataforma **HardTrack Solutions** segundo o **Modelo C4** (Contexto, Containers, Componentes e Código), criado por Simon Brown.

---

## 1. Nível 1 — Diagrama de Contexto do Sistema

Representa a visão macro do sistema, seus usuários e suas integrações com sistemas externos.

* **Arquivo Interativo:** [diagrama_nivel_1_contexto.html](file:///home/guilhermemachry/Documents/Projeto_SAAS/docs/c4/diagrama_nivel_1_contexto.html)
* **Elementos Centrais:**
  - **Sistema HardTrack Solutions (SaaS Multi-Tenant):** Núcleo central que orquestra a coleta de preços e alerta os usuários.
  - **Usuários / Personas:** Consumidor Final (B2C) e Pequena Montadora/Oficina (B2B).
  - **Sistemas Externos:**
    - *E-commerces de Hardware:* Plataformas externas (Kabum, Pichau, Terabyte, Amazon) de onde os preços são extraídos via scraping HTTPS.
    - *Telegram Bot API:* Serviço de mensageria externo utilizado para despachar notificações push com links de afiliados.

```mermaid
flowchart TD
    subgraph Usuarios ["Usuários do Sistema"]
        UserA["Tenant A (Consumidor B2C)<br>1 a 5 URLs"]
        UserB["Tenant B (Montador B2B)<br>20 a 50 URLs"]
    end

    subgraph HardTrack ["Fronteira do Sistema: HardTrack Solutions (SaaS)"]
        Core["Rastreador & Monitor de Preços<br>(Núcleo Multi-Tenant)"]
    end

    subgraph Externos ["Sistemas Externos"]
        Stores["Lojas de Hardware / E-commerces<br>(Kabum, Terabyte, Pichau)"]
        Telegram["Telegram Bot API<br>(Canal de Notificações Push)"]
    end

    UserA -->|"Configura URLs e Alertas (HTTPS)"| Core
    UserB -->|"Configura Lotes de URLs (HTTPS)"| Core
    Core -->|"Coleta Preços e Disponibilidade (HTTPS/TLS)"| Stores
    Core -->|"Dispara Alertas de Preço Atingido (HTTPS/TLS)"| Telegram
    Telegram -.->|"Notificação Push no Smartphone/Desktop"| UserA
    Telegram -.->|"Notificação Push no Smartphone/Desktop"| UserB
```

---

## 2. Nível 2 — Diagrama de Containers

Mapeia as unidades de software executáveis que compõem o sistema e como se comunicam.

* **Arquivo Interativo:** [diagrama_nivel_2_containers.html](file:///home/guilhermemachry/Documents/Projeto_SAAS/docs/c4/diagrama_nivel_2_containers.html)
* **Containers Executáveis:**
  1. **Interface / App (SPA / Frontend):** Interface do usuário para cadastro de componentes e visualização de preços.
  2. **API Backend (Python / FastAPI):** Gateway REST responsável pelas regras de negócio, autenticação e gestão de ciclo de vida do tenant.
  3. **Camada de Persistência (Silos JSON / TinyDB):** Segregação física dos dados em arquivos independentes (`storage/tenants/tenant_<id>.json`), garantindo isolamento estrito de tenancy.
  4. **Worker de Monitoramento & Scraping (Python):** Processo em background autônomo com motor BeautifulSoup4 que itera periodicamente sobre os silos, extrai os preços e dispara notificações via Telegram.

```mermaid
flowchart TB
    Client["Navegador Web / Cliente HTTP"]

    subgraph Boundaries ["Fronteira da Aplicação HardTrack"]
        API["Container 01: API REST Gateway<br>[Python / FastAPI]<br>Gerencia Tenants, Metas e Histórico"]
        Worker["Container 02: Worker de Scraping<br>[Python / Worker Autônomo]<br>Varredura periódica e comparação de preço"]
        
        subgraph StorageLayer ["Camada de Persistência (Silos de Dados)"]
            SiloA[("tenant_01.json<br>[TinyDB / JSON]<br>Dados do Tenant A")]
            SiloB[("tenant_02.json<br>[TinyDB / JSON]<br>Dados do Tenant B")]
            SiloN[("tenant_N.json<br>[TinyDB / JSON]<br>Dados do Tenant N")]
        end
    end

    ExternalWeb["E-commerces de Hardware<br>(Websites Externos)"]
    TelegramAPI["Telegram Bot API<br>(Push Gateway)"]

    Client -->|"Requisições REST / JSON"| API
    API -->|"Grava / Consulta com tenant_id"| SiloA
    API -->|"Grava / Consulta com tenant_id"| SiloB
    API -->|"Grava / Consulta com tenant_id"| SiloN

    Worker -->|"Lê metas e grava histórico"| SiloA
    Worker -->|"Lê metas e grava histórico"| SiloB
    Worker -->|"Lê metas e grava histórico"| SiloN
    
    Worker -->|"Scraping HTTP GET (TLS)"| ExternalWeb
    Worker -->|"Push Notification (HTTPS POST)"| TelegramAPI
```

---

## 3. Nível 3 — Esboço de Componentes Críticos

Para o detalhamento interno dos componentes de software que formam a API e o Worker, bem como os mecanismos de isolamento de tenant, consulte:
👉 **[esboco_nivel_3_componentes.md](file:///home/guilhermemachry/Documents/Projeto_SAAS/docs/c4/esboco_nivel_3_componentes.md)**

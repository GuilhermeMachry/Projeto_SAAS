# ADR 001: Estratégia de Multi-Tenancy baseada em Silo por Arquivo JSON

**Status:** Aprovado  
**Data:** 2026-09-24  
**Decisores:** Guilherme Machry  
**Componente Afetado:** Camada de Persistência e Modelo de Tenancy  

---

## 1. Contexto

A plataforma **HardTrack Solutions** foi projetada para operar inicialmente com uma base estimada de **50 tenants ativos** (sendo 80% do perfil B2C com 1 a 5 URLs cadastradas e 20% do perfil B2B com até 50 URLs cadastradas), gerando uma volumetria diária de aproximadamente **500 ciclos de verificação**. 

O projeto possui restrições explícitas de ambiente:
1. Execução demonstrável em notebook Linux local sem orçamento de nuvem (custo limite de infraestrutura de **R$ 0,00/mês**);
2. Proibição explícita do uso de SGBDs relacionais tradicionais (MySQL e SQLite descartados pelo docente);
3. Rigor absoluto de isolamento para evitar vazamento cruzado de estratégias de compras entre concorrentes B2B e garantir atendimento imediato ao Artigo 18 da LGPD (direito de eliminação dos dados).

---

## 2. Decisão

**Adotaremos a estratégia de Silo de Dados baseada em arquivos JSON independentes por tenant (`storage/tenants/tenant_<id>.json`), onde cada arquivo representa o banco isolado de um cliente gerenciado pelo motor NoSQL embutido TinyDB.**

---

## 3. Alternativas Descartadas

* **Alternativa Descartada 1: Modelo Pool (Banco Compartilhado com Coluna `tenant_id`)**  
  *Por que perdeu:* Em um banco compartilhado sem constraints relacionais nativas (NoSQL), o isolamento depende 100% de cláusulas lógicas de filtro no código da aplicação. Um bug em query ou injeção de parâmetro poderia expor dados confidenciais de cotação entre tenants. Além disso, o expurgo de dados de um tenant exigiria operações de `DELETE` varrendo tabelas inteiras, com risco de inconsistência.
* **Alternativa Descartada 2: Modelo Schema / Database Dedicado em SGBD Tradicional**  
  *Por que perdeu:* Criar um banco de dados ou schema isolado por tenant em instâncias PostgreSQL/MySQL violaria a restrição acadêmica contra RDBMS e exigiria serviços/daemons pesados rodando em background consumindo de 500 MB a 1 GB de memória RAM no notebook, inviabilizando a portabilidade e gerando custo financeiro desnecessário caso fosse levado para cloud (~R$ 150,00 a R$ 250,00/mês por instância gerenciada mínima).

---

## 4. Consequências

### Positivas:
* **Isolamento Físico Absoluto:** Risco zero de vazamento cruzado no nível de dados; um tenant fisicamente não compartilha arquivo com outro.
* **Conformidade Instantânea com LGPD (Art. 18):** O direito ao esquecimento e eliminação é atendido de forma atômica por meio da exclusão direta do arquivo `tenant_<id>.json` no sistema de arquivos.
* **Custo Zero (R$ 0,00):** Elimina a necessidade de contratar bancos gerenciados ou manter serviços adicionais ativos na máquina host.
* **Leveza Operacional:** Cada arquivo de silo ocupa inicialmente menos de **50 KB** em disco.

### Negativas:
* **Consultas Analíticas Transversais Complexas:** Para gerar relatórios consolidados de tendências globais de mercado, é necessário que um script leia e agregue dados de múltiplos arquivos silos de forma assíncrona.
* **Limite de Concorrência por Tenant:** O TinyDB utiliza travas de escrita no arquivo; se o mesmo tenant realizar dezenas de escritas simultâneas no mesmo arquivo, pode haver concorrência (mitigado pelo fato de cada tenant ter seu próprio arquivo).

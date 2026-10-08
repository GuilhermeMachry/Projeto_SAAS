# ADR 002: Stack Backend e Persistência NoSQL Embutida

**Status:** Aprovado  
**Data:** 2026-09-24  
**Decisores:** Guilherme Machry  
**Componente Afetado:** Stack Tecnológica, Motor de Coleta e Persistência  

---

## 1. Contexto

O desenvolvimento do sistema de rastreamento exige uma linguagem com excelente ecossistema para parsing de HTML/DOM, facilidade para orquestrar requisições assíncronas e consumo mínimo de memória RAM (alvo de menos de **100 MB** de uso total no host). 

Além disso, a solução necessita operar com custo de licença e hosting de **R$ 0,00** e respeitar o veto a bancos de dados relacionais padrão (MySQL/SQLite). Com uma média de **10 requisições por ciclo** e tempo de resposta esperado abaixo de **1,5 segundos por URL**, a stack deve garantir agilidade no desenvolvimento e execução estável.

---

## 2. Decisão

**Adotaremos a stack backend baseada em Python 3, utilizando FastAPI para a API REST, BeautifulSoup4 e Requests para o motor de scraping, e TinyDB como gerenciador NoSQL embutido orientado a documentos JSON.**

---

## 3. Alternativas Descartadas

* **Alternativa Descartada 1: Node.js (Express) com Cheerio e Lowdb**  
  *Por que perdeu:* Embora o ecossistema Node.js seja rápido para I/O, o tratamento e manipulação analítica de dados em Python é mais expressivo e possui bibliotecas de parsing (BeautifulSoup4) que lidam com maior tolerância a HTML malformado de e-commerces brasileiros, além de exigir configuração adicional de gerenciadores de versão no ambiente Linux.
* **Alternativa Descartada 2: Go (Golang) com SQLite Embutido**  
  *Por que perdeu:* O uso de SQLite foi expressamente vedado nas diretrizes da disciplina para a modelagem do SaaS. Além disso, o tempo de desenvolvimento de rotinas de scraping e manipulação dinâmica de seletores CSS em Go é significativamente mais custoso em esforço humano sem agregar ganhos perceptíveis para a volumetria de 50 tenants.

---

## 4. Consequências

### Positivas:
* **Custo Zero (R$ 0,00):** Todas as bibliotecas são de código aberto sob licenças permissivas (MIT/BSD/PSF).
* **Consumo de Memória Reduzido:** A aplicação completa (API + Worker) roda utilizando menos de **85 MB de memória RAM** combinada no ambiente local.
* **Alta Tolerância do Parser:** `BeautifulSoup4` oferece seletores robustos capazes de contornar tags e aninhamentos malformados frequentemente encontrados em páginas de e-commerce.
* **Silos Nativos em JSON:** O TinyDB manipula nativamente os arquivos de silo no formato JSON, tornando os dados legíveis diretamente por humanos para auditoria e inspeção rápida.

### Negativas:
* **Tipagem Dinâmica em Runtime:** Requer o uso de Pydantic e type hints estritos para evitar erros de validação em tempo de execução.
* **Concorrência de Arquivo Único:** Requer cuidado para não efetuar escritas simultâneas descontroladas no mesmo arquivo de silo (mitigado pelo isolamento por tenant).

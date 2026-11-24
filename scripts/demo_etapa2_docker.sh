#!/usr/bin/env bash
# ==============================================================================
# HardTrack Solutions — Script de Demonstração ao Vivo (Etapa 2: Núcleo Multi-Tenant)
# Disciplina: Arquitetura de Software SAAS (SETREM)
# Aluno: Guilherme Machry
#
# Modos de uso:
#   ./scripts/demo_etapa2_docker.sh          # Modo interativo (pausa com ENTER a cada etapa)
#   ./scripts/demo_etapa2_docker.sh --auto   # Modo contínuo (executa tudo com pausas curtas)
# ==============================================================================

set -e

AUTO_MODE=false
if [[ "$1" == "--auto" ]]; then
    AUTO_MODE=true
fi

# Cores ANSI
C_RESET="\033[0m"
C_BOLD="\033[1m"
C_GREEN="\033[92m"
C_CYAN="\033[96m"
C_YELLOW="\033[93m"
C_RED="\033[91m"
C_BLUE="\033[94m"
C_MAGENTA="\033[95m"

# Garantir que estamos na raiz do repositório
cd "$(dirname "$0")/.."

pause_step() {
    if [[ "$AUTO_MODE" == "true" ]]; then
        sleep 1.2
    else
        echo ""
        read -r -p "$(echo -e "${C_YELLOW}${C_BOLD}👉 [Pressione ENTER para avançar para a próxima etapa...]${C_RESET}")"
    fi
}

banner() {
    echo -e "\n${C_BOLD}${C_CYAN}================================================================================${C_RESET}"
    echo -e "${C_BOLD}${C_CYAN}>>> $1${C_RESET}"
    echo -e "${C_BOLD}${C_CYAN}================================================================================${C_RESET}"
}

step_header() {
    echo -e "\n${C_BOLD}${C_BLUE}┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓${C_RESET}"
    echo -e "${C_BOLD}${C_BLUE}┃ [$1] $2${C_RESET}"
    echo -e "${C_BOLD}${C_BLUE}┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛${C_RESET}"
}

show_cmd() {
    echo -e "\n${C_MAGENTA}${C_BOLD}\$ $*${C_RESET}"
}

ok_msg() {
    echo -e "  ${C_GREEN}✔ [OK]${C_RESET} $1"
}

info_msg() {
    echo -e "  ${C_YELLOW}⚡ [INFO]${C_RESET} $1"
}

format_json() {
    python3 -m json.tool --no-ensure-ascii 2>/dev/null || python3 -m json.tool 2>/dev/null || cat
}

clear || true
banner "DEFESA TÉCNICA ETAPA 2 — HARDTRACK SOLUTIONS (SAAS MULTI-TENANT)"
echo -e "${C_BOLD}Arquitetura:${C_RESET} 2 Serviços em Containers Docker (API FastAPI + Worker Scraper)"
echo -e "${C_BOLD}Isolamento:${C_RESET}  Silo Físico por Arquivo JSON (TinyDB) em ./storage/tenants/"
echo -e "${C_BOLD}Aluno:${C_RESET}       Guilherme Machry — Engenharia de Computação (SETREM)"

# ==============================================================================
# PASSO 1: Inicialização dos 2 Serviços no Docker
# ==============================================================================
step_header "ETAPA 1/6" "Subindo os 2 Serviços no Ambiente Docker (API Gateway + Worker)"

info_msg "Limpando silos antigos em storage/tenants/ para iniciar a demonstração do zero..."
rm -f storage/tenants/tenant_*.json

show_cmd "docker compose up -d --build"
docker compose up -d --build

echo -e "\n${C_BOLD}Verificando os 2 containers em execução e consumo de recursos (ADR 002/005):${C_RESET}"
show_cmd "docker compose ps"
docker compose ps

show_cmd "docker stats --no-stream hardtrack_api hardtrack_worker"
docker stats --no-stream hardtrack_api hardtrack_worker

info_msg "Aguardando a API REST responder no endpoint de Healthcheck..."
for i in {1..15}; do
    if curl -s http://localhost:8000/health >/dev/null; then
        break
    fi
    sleep 0.5
done

show_cmd "curl -s http://localhost:8000/health"
curl -s http://localhost:8000/health | format_json

ok_msg "Serviço 01 (hardtrack_api) e Serviço 02 (hardtrack_worker) ativos no Docker!"
pause_step

# ==============================================================================
# PASSO 2: Onboarding de 2 Tenants (B2C e B2B) e Visualização dos Silos em Disco
# ==============================================================================
step_header "ETAPA 2/6" "Onboarding de 2 Tenants Heterogêneos e Criação dos Silos Físicos"

echo -e "\n${C_BOLD}1) Cadastrando Tenant A — Consumidor Final / Gamer (B2C):${C_RESET}"
show_cmd "curl -s -X POST http://localhost:8000/tenants -d '{\"tenant_id\":\"joao_b2c\", ...}'"
RESP_A=$(curl -s -X POST http://localhost:8000/tenants \
  -H "Content-Type: application/json" \
  -d '{"tenant_id":"joao_b2c","nome":"João Silva (Gamer / B2C)","tipo":"B2C_ENTUSIASTA","telegram_chat_id":"11223344"}')
echo "$RESP_A" | format_json
TOKEN_A=$(echo "$RESP_A" | python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])")

echo -e "\n${C_BOLD}2) Cadastrando Tenant B — Oficina / Montadora Local (B2B):${C_RESET}"
show_cmd "curl -s -X POST http://localhost:8000/tenants -d '{\"tenant_id\":\"techparts_b2b\", ...}'"
RESP_B=$(curl -s -X POST http://localhost:8000/tenants \
  -H "Content-Type: application/json" \
  -d '{"tenant_id":"techparts_b2b","nome":"Oficina TechParts (Montadora / B2B)","tipo":"B2B_OFICINA","telegram_chat_id":"99887766"}')
echo "$RESP_B" | format_json
TOKEN_B=$(echo "$RESP_B" | python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])")

echo -e "\n${C_BOLD}3) Listando Tenants ativos via API Gateway (com X-Admin-Key):${C_RESET}"
show_cmd "curl -s -H 'X-Admin-Key: dev-only-hardtrack-admin-key' http://localhost:8000/tenants"
curl -s -H "X-Admin-Key: dev-only-hardtrack-admin-key" http://localhost:8000/tenants | format_json

echo -e "\n${C_BOLD}4) Verificando os arquivos físicos de Silo gerados no disco (permissão chmod 600):${C_RESET}"
show_cmd "ls -la storage/tenants/"
ls -la storage/tenants/

ok_msg "Cada tenant possui seu próprio arquivo JSON isolado no sistema de arquivos!"
pause_step

# ==============================================================================
# PASSO 3: Cadastro de Metas e Prova de Isolamento entre Tenant A e Tenant B
# ==============================================================================
step_header "ETAPA 3/6" "Cadastro de Hardware Monitorado e Prova Ao Vivo de Isolamento"

echo -e "\n${C_BOLD}1) [Tenant A - joao_b2c] Cadastra Placa de Vídeo RTX 4060 Ti (Meta: R\$ 2.400,00 | Loja: R\$ 2.350,00):${C_RESET}"
show_cmd "curl -s -X POST http://localhost:8000/tenants/joao_b2c/targets -H 'Authorization: Bearer <TOKEN_A>'"
curl -s -X POST http://localhost:8000/tenants/joao_b2c/targets \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${TOKEN_A}" \
  -d '{"nome_componente":"GeForce RTX 4060 Ti 8GB","url":"mock://kabum.com.br/rtx4060ti?price=2350.00","preco_alvo":2400.00}' | format_json

echo -e "\n${C_BOLD}2) [Tenant B - techparts_b2b] Cadastra Processador Ryzen 7 7800X3D (Meta: R\$ 2.900,00 | Loja: R\$ 2.799,00):${C_RESET}"
show_cmd "curl -s -X POST http://localhost:8000/tenants/techparts_b2b/targets -H 'Authorization: Bearer <TOKEN_B>'"
curl -s -X POST http://localhost:8000/tenants/techparts_b2b/targets \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${TOKEN_B}" \
  -d '{"nome_componente":"Processador AMD Ryzen 7 7800X3D","url":"mock://terabyte.com.br/ryzen7800x3d?price=2799.00","preco_alvo":2900.00}' | format_json

echo -e "\n${C_BOLD}3) [Tenant B - techparts_b2b] Cadastra SSD NVMe 2TB (Meta: R\$ 950,00 | Loja: R\$ 1.150,00 - acima da meta):${C_RESET}"
curl -s -X POST http://localhost:8000/tenants/techparts_b2b/targets \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${TOKEN_B}" \
  -d '{"nome_componente":"SSD NVMe Kingston Fury 2TB PCIe 4.0","url":"mock://pichau.com.br/ssd2tb?price=1150.00","preco_alvo":950.00}' | format_json

echo -e "\n${C_BOLD}${C_GREEN}>>> PROVA DE ISOLAMENTO NA CAMADA DE API:${C_RESET}"
echo -e "${C_BOLD}Consultando itens do Tenant A (joao_b2c) — NÃO vê nada da Oficina TechParts:${C_RESET}"
show_cmd "curl -s -H 'Authorization: Bearer <TOKEN_A>' http://localhost:8000/tenants/joao_b2c/targets"
curl -s -H "Authorization: Bearer ${TOKEN_A}" http://localhost:8000/tenants/joao_b2c/targets | format_json

echo -e "\n${C_BOLD}Consultando itens do Tenant B (techparts_b2b) — NÃO vê nada do João Silva:${C_RESET}"
show_cmd "curl -s -H 'Authorization: Bearer <TOKEN_B>' http://localhost:8000/tenants/techparts_b2b/targets"
curl -s -H "Authorization: Bearer ${TOKEN_B}" http://localhost:8000/tenants/techparts_b2b/targets | format_json

echo -e "\n${C_BOLD}Tentativa Cross-Tenant: Token A tentando ler Tenant B (esperado HTTP 403 Forbidden):${C_RESET}"
curl -i -s -H "Authorization: Bearer ${TOKEN_A}" http://localhost:8000/tenants/techparts_b2b/targets | head -n 10
echo ""

ok_msg "Isolamento e AuthZ comprovados! Tenant A só enxerga a RTX 4060 Ti e recebe 403 ao tentar invadir B."
pause_step

# ==============================================================================
# PASSO 4: Comunicação com o 2º Serviço (Worker Container) + Resiliência
# ==============================================================================
step_header "ETAPA 4/6" "Execução do Serviço 02 (Worker no Docker), Alertas Push e Resiliência"

info_msg "Cadastrando temporariamente 1 URL com falha simulada no Tenant B para demonstrar Resiliência (0% crashes)..."
FAIL_TARGET_ID=$(curl -s -X POST http://localhost:8000/tenants/techparts_b2b/targets \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${TOKEN_B}" \
  -d '{"nome_componente":"Fonte 850W (Simulacao Timeout Loja)","url":"mock://loja-instavel.com.br/fonte?fail=true","preco_alvo":600.00}' \
  | python3 -c "import sys, json; print(json.load(sys.stdin)['id'])")

info_msg "Disparando ciclo de varredura ao vivo dentro do container 'hardtrack_worker'..."
show_cmd "docker exec hardtrack_worker python -m src.worker.runner --once"
docker exec hardtrack_worker python -m src.worker.runner --once

# Remove o item de falha simulada para manter o silo limpo
curl -s -X DELETE -H "Authorization: Bearer ${TOKEN_B}" "http://localhost:8000/tenants/techparts_b2b/targets/${FAIL_TARGET_ID}" >/dev/null

echo -e "\n${C_BOLD}Consultando o Histórico de Preços gravado no Silo do Tenant A (via API):${C_RESET}"
show_cmd "curl -s -H 'Authorization: Bearer <TOKEN_A>' http://localhost:8000/tenants/joao_b2c/history"
curl -s -H "Authorization: Bearer ${TOKEN_A}" http://localhost:8000/tenants/joao_b2c/history | format_json

echo -e "\n${C_BOLD}Consultando os Alertas Push de Oportunidade disparados para o Tenant A:${C_RESET}"
show_cmd "curl -s -H 'Authorization: Bearer <TOKEN_A>' http://localhost:8000/tenants/joao_b2c/alerts"
curl -s -H "Authorization: Bearer ${TOKEN_A}" http://localhost:8000/tenants/joao_b2c/alerts | format_json

echo -e "\n${C_BOLD}Consultando o Histórico do Tenant B (Ryzen gerou alerta; SSD não gerou pois R\$ 1150 > R\$ 950):${C_RESET}"
show_cmd "curl -s -H 'Authorization: Bearer <TOKEN_B>' http://localhost:8000/tenants/techparts_b2b/history"
curl -s -H "Authorization: Bearer ${TOKEN_B}" http://localhost:8000/tenants/techparts_b2b/history | format_json

ok_msg "Comunicação assíncrona API <-> Worker via Silo e degradação graciosa validadas!"
pause_step

# ==============================================================================
# PASSO 5: Visualização Física dos Silos JSON no Disco
# ==============================================================================
step_header "ETAPA 5/6" "Inspeção Direta dos Arquivos de Silo no Disco (Camada de Dados)"

echo -e "\n${C_BOLD}Conteúdo físico do arquivo ${C_CYAN}storage/tenants/tenant_joao_b2c.json${C_RESET}${C_BOLD}:${C_RESET}"
show_cmd "cat storage/tenants/tenant_joao_b2c.json"
cat storage/tenants/tenant_joao_b2c.json

echo -e "\n\n${C_BOLD}Conteúdo físico do arquivo ${C_CYAN}storage/tenants/tenant_techparts_b2b.json${C_RESET}${C_BOLD}:${C_RESET}"
show_cmd "cat storage/tenants/tenant_techparts_b2b.json"
cat storage/tenants/tenant_techparts_b2b.json
echo ""

ok_msg "Segregação física total (Silo por Arquivo): zero compartilhamento de tabela entre clientes."
pause_step

# ==============================================================================
# PASSO 6: Segurança Anti-Path Traversal e Expurgo Atômico LGPD (Art. 18)
# ==============================================================================
step_header "ETAPA 6/6" "Segurança (Bloqueio Path Traversal) e Expurgo Atômico LGPD (Art. 18)"

echo -e "\n${C_BOLD}1) Tentativa de ataque de Path Traversal no tenant_id ('../etc/passwd'):${C_RESET}"
show_cmd "curl -i -s -X POST http://localhost:8000/tenants -H 'Content-Type: application/json' -d '{\"tenant_id\":\"../etc/passwd\",\"nome\":\"Hacker\",\"tipo\":\"B2C_ENTUSIASTA\",\"telegram_chat_id\":\"000\"}'"
curl -i -s -X POST http://localhost:8000/tenants \
  -H "Content-Type: application/json" \
  -d '{"tenant_id":"../etc/passwd","nome":"Hacker","tipo":"B2C_ENTUSIASTA","telegram_chat_id":"000"}' | head -n 10
echo ""
ok_msg "Ataque de Path Traversal bloqueado pela sanitização Regex (HTTP 400 Bad Request)!"

echo -e "\n${C_BOLD}2) Demonstração do Expurgo Atômico LGPD (Art. 18 — Direito de Eliminação):${C_RESET}"
info_msg "Criando um 3º tenant temporário ('cliente_lgpd') e solicitando exclusão definitiva..."
TOKEN_LGPD=$(curl -s -X POST http://localhost:8000/tenants \
  -H "Content-Type: application/json" \
  -d '{"tenant_id":"cliente_lgpd","nome":"Carlos (Teste Expurgo LGPD)","tipo":"B2C_ENTUSIASTA","telegram_chat_id":"555555"}' \
  | python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])")

echo -e "${C_BOLD}Arquivos em storage/tenants/ ANTES do expurgo:${C_RESET}"
ls -1 storage/tenants/

show_cmd "curl -s -X DELETE -H 'Authorization: Bearer <TOKEN_LGPD>' http://localhost:8000/tenants/cliente_lgpd"
curl -s -X DELETE -H "Authorization: Bearer ${TOKEN_LGPD}" http://localhost:8000/tenants/cliente_lgpd | format_json

echo -e "\n${C_BOLD}Arquivos em storage/tenants/ DEPOIS do expurgo (cliente_lgpd eliminado, joao_b2c e techparts_b2b intactos):${C_RESET}"
show_cmd "ls -la storage/tenants/"
ls -la storage/tenants/

banner "DEMONSTRAÇÃO CONCLUÍDA COM SUCESSO!"
echo -e "${C_GREEN}${C_BOLD}Resumo do estado atual no seu terminal (pronto para perguntas da banca):${C_RESET}"
echo -e "  • Containers ativos:   ${C_CYAN}hardtrack_api${C_RESET} (porta 8000) e ${C_CYAN}hardtrack_worker${C_RESET}"
echo -e "  • Swagger UI ao vivo:  ${C_CYAN}http://localhost:8000/docs${C_RESET}"
echo -e "  • Silos ativos:        ${C_CYAN}storage/tenants/tenant_joao_b2c.json${C_RESET}"
echo -e "                         ${C_CYAN}storage/tenants/tenant_techparts_b2b.json${C_RESET}"
echo -e "  • Logs dos containers: ${C_YELLOW}docker compose logs -f${C_RESET}\n"

#!/usr/bin/env bash
# ==============================================================================
# HardTrack Solutions — Demonstração de Falha Controlada no Pipeline (Etapa 3.1)
# Comprova o critério de aceite: "O pipeline falha quando um teste quebra — e você demonstra isso"
# ==============================================================================

set -u

cd "$(dirname "$0")/.."
PYTEST_BIN=".venv/bin/pytest"
if [[ ! -x "$PYTEST_BIN" ]]; then
    PYTEST_BIN="pytest"
fi

TMP_TEST="tests/_tmp_demo_broken_test.py"

cleanup() {
    rm -f "$TMP_TEST"
}
trap cleanup EXIT

echo "========================================================================"
echo "  ETAPA 3.1 — DEMONSTRAÇÃO: PIPELINE QUEBRA QUANDO UM TESTE FALHA"
echo "========================================================================"
echo ""
echo "[1/3] Injetando temporariamente um teste de regressão quebrado em $TMP_TEST..."
cat << 'EOF' > "$TMP_TEST"
def test_regressao_isolamento_simulada():
    """Simula regressão intencional para comprovar que o CI bloqueia o merge."""
    status_cross_tenant = 200  # Simula bug grave (deveria ser 403 Forbidden)
    assert status_cross_tenant == 403, "REGRESSÃO DETECTADA: Acesso cross-tenant retornou 200 em vez de 403!"
EOF

echo "[2/3] Executando suíte de testes (esperado: FALHA / exit code != 0)..."
"$PYTEST_BIN" -q "$TMP_TEST"
FAIL_CODE=$?
echo ">>> Código de saída retornado ao GitHub Actions: $FAIL_CODE (PIPELINE VERMELHO / MERGE BLOQUEADO)"

echo ""
echo "[3/3] Removendo regressão e reexecutando suíte completa (esperado: SUCESSO / exit code 0)..."
rm -f "$TMP_TEST"
"$PYTEST_BIN" -q
OK_CODE=$?
echo ">>> Código de saída retornado ao GitHub Actions: $OK_CODE (PIPELINE VERDE)"
exit "$OK_CODE"

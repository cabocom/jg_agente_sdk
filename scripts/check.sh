#!/usr/bin/env bash
set -e

# Directorio base de jg_agente_sdk
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

# Determinar ejecutable de entorno virtual
if [ -f "$PROJECT_ROOT/.venv/bin/ruff" ]; then
    VENV_BIN="$PROJECT_ROOT/.venv/bin"
fi

if [ -n "$VENV_BIN" ]; then
    RUFF="$VENV_BIN/ruff"
    PYTEST="$VENV_BIN/pytest"
else
    RUFF="ruff"
    PYTEST="pytest"
fi

echo "========================================"
echo "🔍 Verificando jg_agente_sdk..."
echo "========================================"

echo ""
echo "1️⃣  [Ruff] Linter y formato de código..."
"$RUFF" check jg_sdk tests
"$RUFF" format --check jg_sdk tests

echo ""
echo "2️⃣  [Pytest] Ejecución de suite de tests unitarios..."
"$PYTEST" -v tests

echo ""
echo "========================================"
echo "✅ ¡Todas las comprobaciones de jg_agente_sdk pasaron con éxito!"
echo "========================================"

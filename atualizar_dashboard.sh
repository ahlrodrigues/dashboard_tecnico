#!/usr/bin/env bash
set -euo pipefail

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$BASE_DIR"

LOG_FILE="$BASE_DIR/atualizar_dashboard.log"
PYTHON_BIN="$BASE_DIR/.venv/bin/python"

{
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] Iniciando atualização do dashboard"
  if [[ ! -x "$PYTHON_BIN" ]]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Ambiente virtual nao encontrado em $PYTHON_BIN"
    exit 1
  fi
  "$PYTHON_BIN" "$BASE_DIR/main.py"
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] Atualização concluída"
} >> "$LOG_FILE" 2>&1

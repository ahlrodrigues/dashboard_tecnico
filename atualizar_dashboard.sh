#!/usr/bin/env bash
set -euo pipefail

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$BASE_DIR"

LOG_FILE="$BASE_DIR/atualizar_dashboard.log"

{
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] Iniciando atualização do dashboard"
  "$BASE_DIR/.venv/bin/python" "$BASE_DIR/main.py"
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] Atualização concluída"
} >> "$LOG_FILE" 2>&1

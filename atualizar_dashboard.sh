#!/usr/bin/env bash
set -euo pipefail

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$BASE_DIR"

LOG_FILE="$BASE_DIR/atualizar_dashboard.log"
PYTHON_BIN="$BASE_DIR/.venv/bin/python"
REFRESH_TARGET="${1:-all}"
REBUILD_HTML_FLAG="${DASHBOARD_REBUILD_HTML_ON_REFRESH:-0}"

{
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] Iniciando atualização do dashboard (target=${REFRESH_TARGET})"
  if [[ ! -x "$PYTHON_BIN" ]]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Ambiente virtual nao encontrado em $PYTHON_BIN"
    exit 1
  fi
  CMD=("$PYTHON_BIN" "$BASE_DIR/main.py" --refresh-target "$REFRESH_TARGET")
  if [[ "$REBUILD_HTML_FLAG" == "1" ]]; then
    CMD+=(--rebuild-html)
  fi
  "${CMD[@]}"
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] Atualização concluída"
} >> "$LOG_FILE" 2>&1

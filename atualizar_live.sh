#!/usr/bin/env bash
set -euo pipefail

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$BASE_DIR"

BRANCH="${1:-feature/dashboard-live-api}"
PYTHON_BIN="$BASE_DIR/.venv/bin/python"
LOG_FILE="$BASE_DIR/atualizar_live.log"

{
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] Iniciando deploy da branch $BRANCH"

  if [[ ! -d "$BASE_DIR/.git" ]]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Este diretório nao e um repositorio git."
    exit 1
  fi

  if [[ ! -x "$PYTHON_BIN" ]]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Ambiente virtual nao encontrado em $PYTHON_BIN"
    exit 1
  fi

  git fetch origin
  git checkout "$BRANCH"
  git restore dashboard_os_sgp.html
  git pull --ff-only origin "$BRANCH"
  "$PYTHON_BIN" main.py --rebuild-html

  VERSION_LABEL="$("$PYTHON_BIN" -c 'from version import VERSION; print(VERSION)' 2>/dev/null || echo "desconhecida")"
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] Deploy concluido na versao ${VERSION_LABEL} em $(git rev-parse --short HEAD)"
} | tee -a "$LOG_FILE"

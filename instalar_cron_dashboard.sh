#!/usr/bin/env bash
set -euo pipefail

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="$BASE_DIR/config.json"
SCRIPT_FILE="$BASE_DIR/atualizar_dashboard.sh"

if [[ ! -f "$CONFIG_FILE" ]]; then
  echo "config.json nao encontrado em $BASE_DIR" >&2
  exit 1
fi

if [[ ! -x "$SCRIPT_FILE" ]]; then
  chmod +x "$SCRIPT_FILE"
fi

INTERVALO_SEGUNDOS="$("$BASE_DIR/.venv/bin/python" - <<'PY'
import json
from pathlib import Path

cfg = json.loads(Path("config.json").read_text(encoding="utf-8"))
refresh = int(cfg.get("dashboard", {}).get("atualizacao_segundos", 300))
print(max(refresh, 60))
PY
)"

INTERVALO_MINUTOS=$(( INTERVALO_SEGUNDOS / 60 ))
if (( INTERVALO_MINUTOS < 1 )); then
  INTERVALO_MINUTOS=1
fi

if (( 60 % INTERVALO_MINUTOS != 0 )); then
  echo "O cron usa resolucao em minutos. Ajuste 'atualizacao_segundos' para um multiplo de 60 que divida 60." >&2
  exit 1
fi

CRON_TAG="# dashboard_tecnico_auto_update"
CRON_CMD="*/${INTERVALO_MINUTOS} * * * * \"$SCRIPT_FILE\" $CRON_TAG"

TMP_CRON="$(mktemp)"
trap 'rm -f "$TMP_CRON"' EXIT

crontab -l 2>/dev/null | grep -v "$CRON_TAG" > "$TMP_CRON" || true
echo "$CRON_CMD" >> "$TMP_CRON"
crontab "$TMP_CRON"

echo "Cron instalado com sucesso para executar a cada ${INTERVALO_MINUTOS} minuto(s)."

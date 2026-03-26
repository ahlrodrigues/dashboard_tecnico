#!/usr/bin/env bash
set -euo pipefail

BASE_DIR="/var/www/html/dashboard_tecnico-main"
cd "$BASE_DIR"

HOST="${DASHBOARD_SERVER_HOST:-0.0.0.0}"
PORT="${DASHBOARD_SERVER_PORT:-8765}"
CHECK_HOST="${DASHBOARD_SERVER_CHECK_HOST:-127.0.0.1}"
PYTHON_BIN="$BASE_DIR/.venv/bin/python"
SERVER_SCRIPT="$BASE_DIR/dashboard_server.py"
LOG_FILE="$BASE_DIR/dashboard_server.log"

if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] Python do ambiente virtual não encontrado em $PYTHON_BIN" >&2
  exit 1
fi

if [[ ! -f "$SERVER_SCRIPT" ]]; then
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] Arquivo do servidor não encontrado em $SERVER_SCRIPT" >&2
  exit 1
fi

porta_ativa="$("$PYTHON_BIN" - <<PY
import socket
sock = socket.socket()
sock.settimeout(1.5)
try:
    sock.connect(("${CHECK_HOST}", int("${PORT}")))
except OSError:
    print("0")
else:
    print("1")
finally:
    sock.close()
PY
)"

if [[ "$porta_ativa" == "1" ]]; then
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] Servidor do dashboard já está ativo em ${CHECK_HOST}:${PORT}" >> "$LOG_FILE"
  exit 0
fi

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Iniciando servidor do dashboard em ${HOST}:${PORT}" >> "$LOG_FILE"
nohup "$PYTHON_BIN" "$SERVER_SCRIPT" --host "$HOST" --port "$PORT" >> "$LOG_FILE" 2>&1 &

sleep 2

porta_ativa="$("$PYTHON_BIN" - <<PY
import socket
sock = socket.socket()
sock.settimeout(1.5)
try:
    sock.connect(("${CHECK_HOST}", int("${PORT}")))
except OSError:
    print("0")
else:
    print("1")
finally:
    sock.close()
PY
)"

if [[ "$porta_ativa" != "1" ]]; then
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] Falha ao iniciar servidor do dashboard em ${CHECK_HOST}:${PORT}" >> "$LOG_FILE"
  exit 1
fi

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Servidor do dashboard iniciado com sucesso" >> "$LOG_FILE"

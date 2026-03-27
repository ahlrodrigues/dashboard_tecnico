#!/usr/bin/env bash
set -euo pipefail

SERVICE_NAME="${DASHBOARD_SERVICE_NAME:-dashboard-tecnico.service}"
SERVICE_PATH="/etc/systemd/system/${SERVICE_NAME}"
BASE_DIR="${DASHBOARD_BASE_DIR:-/var/www/html/dashboard_tecnico-main}"
PYTHON_BIN="${DASHBOARD_PYTHON_BIN:-${BASE_DIR}/.venv/bin/python}"
SERVER_SCRIPT="${DASHBOARD_SERVER_SCRIPT:-${BASE_DIR}/dashboard_server.py}"
HOST="${DASHBOARD_SERVER_HOST:-0.0.0.0}"
PORT="${DASHBOARD_SERVER_PORT:-8765}"
LOG_FILE="${DASHBOARD_LOG_FILE:-${BASE_DIR}/dashboard_server.log}"
SERVICE_USER="${DASHBOARD_SERVICE_USER:-root}"
SERVICE_DESCRIPTION="${DASHBOARD_SERVICE_DESCRIPTION:-Dashboard Tecnico Server}"

if [[ "${EUID}" -ne 0 ]]; then
  echo "Execute este script como root." >&2
  exit 1
fi

if [[ ! -x "${PYTHON_BIN}" ]]; then
  echo "Python não encontrado ou sem permissão de execução: ${PYTHON_BIN}" >&2
  exit 1
fi

if [[ ! -f "${SERVER_SCRIPT}" ]]; then
  echo "Arquivo do servidor não encontrado: ${SERVER_SCRIPT}" >&2
  exit 1
fi

cat > "${SERVICE_PATH}" <<EOF
[Unit]
Description=${SERVICE_DESCRIPTION}
After=network.target

[Service]
Type=simple
User=${SERVICE_USER}
WorkingDirectory=${BASE_DIR}
ExecStart=${PYTHON_BIN} ${SERVER_SCRIPT} --host ${HOST} --port ${PORT}
Restart=always
RestartSec=5
StandardOutput=append:${LOG_FILE}
StandardError=append:${LOG_FILE}

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable "${SERVICE_NAME}"
systemctl restart "${SERVICE_NAME}"

echo "Service instalado em: ${SERVICE_PATH}"
echo "Status atual:"
systemctl --no-pager --full status "${SERVICE_NAME}" || true

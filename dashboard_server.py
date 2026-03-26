from __future__ import annotations

import argparse
import json
import subprocess
import threading
import time
import traceback
from functools import partial
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

class DashboardRequestHandler(SimpleHTTPRequestHandler):
    refresh_lock = threading.Lock()
    base_dir = Path(__file__).resolve().parent
    refresh_state: dict[str, object] = {
        "running": False,
        "started_at": None,
        "finished_at": None,
        "ok": None,
        "message": "Nenhuma atualização em execução.",
    }

    def __init__(self, *args, directory: str | None = None, **kwargs):
        super().__init__(*args, directory=directory or str(self.base_dir), **kwargs)

    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Accept")
        super().end_headers()

    def do_OPTIONS(self) -> None:
        self.send_response(HTTPStatus.NO_CONTENT)
        self.end_headers()

    def do_GET(self) -> None:
        if self.path.rstrip("/") == "/api/refresh-status":
            self._responder_json(HTTPStatus.OK, self.refresh_state.copy())
            return
        if self.path.rstrip("/") == "/api/dashboard-data":
            self._responder_dashboard_data()
            return
        if self.path in {"/", "/index.html"}:
            self.path = "/dashboard_os_sgp.html"
        super().do_GET()

    def do_POST(self) -> None:
        if self.path.rstrip("/") != "/api/refresh":
            self.send_error(HTTPStatus.NOT_FOUND, "Endpoint não encontrado")
            return

        if not self.refresh_lock.acquire(blocking=False):
            self._responder_json(
                HTTPStatus.ACCEPTED,
                {
                    "ok": True,
                    "started": False,
                    "message": "Atualização já está em andamento.",
                    "status_url": "/api/refresh-status",
                },
            )
            return

        self.refresh_state.update(
            {
                "running": True,
                "started_at": time.time(),
                "finished_at": None,
                "ok": None,
                "message": "Executando rotina automática de atualização...",
            }
        )

        worker = threading.Thread(target=self._executar_refresh_em_background, daemon=True)
        worker.start()
        self._responder_json(
            HTTPStatus.ACCEPTED,
            {
                "ok": True,
                "started": True,
                "message": "Atualização iniciada em segundo plano.",
                "status_url": "/api/refresh-status",
            },
        )

    def log_message(self, format: str, *args) -> None:
        super().log_message(format, *args)

    def _responder_json(self, status: HTTPStatus, payload: dict[str, object]) -> None:
        corpo = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(corpo)))
        self.end_headers()
        self.wfile.write(corpo)

    def _responder_dashboard_data(self) -> None:
        payload_path = self.base_dir / "dashboard_data.json"
        if not payload_path.exists():
            self._responder_json(
                HTTPStatus.NOT_FOUND,
                {
                    "ok": False,
                    "message": f"Arquivo de dados não encontrado: {payload_path.name}",
                },
            )
            return

        try:
            payload = json.loads(payload_path.read_text(encoding="utf-8"))
        except Exception as exc:  # pragma: no cover - proteção de runtime
            self._responder_json(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                {
                    "ok": False,
                    "message": f"Falha ao carregar os dados do dashboard: {exc}",
                },
            )
            return

        self._responder_json(HTTPStatus.OK, payload)

    def _executar_refresh_em_background(self) -> None:
        try:
            script_path = self.base_dir / "atualizar_dashboard.sh"
            if not script_path.exists():
                raise FileNotFoundError(f"Script de atualização não encontrado: {script_path}")

            processo = subprocess.run(
                [str(script_path)],
                cwd=self.base_dir,
                capture_output=True,
                text=True,
                timeout=600,
                check=False,
            )
            if processo.returncode != 0:
                detalhes = (processo.stderr or processo.stdout or "").strip()
                raise RuntimeError(detalhes or f"Script terminou com código {processo.returncode}")

            self.refresh_state.update(
                {
                    "running": False,
                    "finished_at": time.time(),
                    "ok": True,
                    "message": "Dados e HTML atualizados com o mesmo fluxo da rotina automática.",
                }
            )
        except Exception as exc:  # pragma: no cover - proteção de runtime
            traceback.print_exc()
            self.refresh_state.update(
                {
                    "running": False,
                    "finished_at": time.time(),
                    "ok": False,
                    "message": f"Falha ao atualizar arquivos: {exc}",
                }
            )
        finally:
            self.refresh_lock.release()


def main() -> None:
    parser = argparse.ArgumentParser(description="Servidor local do dashboard técnico")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()

    base_dir = Path(__file__).resolve().parent
    handler = partial(DashboardRequestHandler, directory=str(base_dir))
    server = ThreadingHTTPServer((args.host, args.port), handler)

    print(f"Servidor disponível em http://{args.host}:{args.port}")
    print("Use Ctrl+C para encerrar.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()

"""Local transport for the desktop interface; no third-party dependencies."""

import hmac
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import secrets
import threading

from desktop_service import DesktopService

ASSETS = Path(__file__).resolve().parent / "ui"


def create_server(service, choose_folder, on_shutdown=None):
    """Build a loopback-only server. Dependencies are injectable for temp-dir tests."""
    token = secrets.token_urlsafe(32)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass

        def reply(self, status, body, content_type="application/json; charset=utf-8"):
            if isinstance(body, dict):
                body = json.dumps(body, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("X-Frame-Options", "DENY")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'")
            self.end_headers()
            self.wfile.write(body)

        def authorized(self, api=False):
            expected = f"127.0.0.1:{self.server.server_port}"
            if self.headers.get("Host") != expected:
                self.reply(403, {"error": "Endereço local inválido."})
                return False
            origin = self.headers.get("Origin")
            if origin and origin != "http://" + expected:
                self.reply(403, {"error": "Origem não autorizada."})
                return False
            if api and not hmac.compare_digest(self.headers.get("X-Central-Token", ""), token):
                self.reply(403, {"error": "Sessão inválida. Reabra a aplicação."})
                return False
            return True

        def do_GET(self):
            if not self.authorized(self.path.startswith("/api/")):
                return
            if self.path == "/api/state":
                return self.call(service.snapshot)
            assets = {"/": ("index.html", "text/html; charset=utf-8"),
                      "/app.css": ("app.css", "text/css; charset=utf-8"),
                      "/app.js": ("app.js", "text/javascript; charset=utf-8")}
            if self.path not in assets:
                return self.reply(404, {"error": "Página não encontrada."})
            name, mime = assets[self.path]
            try:
                data = (ASSETS / name).read_bytes()
                if name == "index.html":
                    data = data.replace(b"__CENTRAL_TOKEN__", token.encode("ascii"))
                self.reply(200, data, mime)
            except OSError:
                self.reply(500, {"error": "Não foi possível carregar a interface. Reabra a aplicação pela pasta do projeto."})

        def call(self, callback):
            with self.server.work_lock:
                if self.server.closing:
                    return self.reply(409, {"error": "A aplicação está encerrando."})
                self.server.active_work += 1
            try:
                self.reply(200, callback())
            except (ValueError, OSError, RuntimeError) as exc:
                self.reply(400, {"error": str(exc)})
            except Exception:
                self.reply(500, {"error": "Não foi possível concluir a operação. Atualize a revisão para conferir os arquivos."})
            finally:
                with self.server.work_lock:
                    self.server.active_work -= 1

        def do_POST(self):
            if not self.authorized(api=True):
                return
            try:
                if self.headers.get("Content-Type", "").split(";")[0] != "application/json":
                    raise ValueError()
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= 8192:
                    raise ValueError()
                data = json.loads(self.rfile.read(length))
                if not isinstance(data, dict):
                    raise ValueError()
            except (ValueError, UnicodeDecodeError):
                return self.reply(400, {"error": "Solicitação inválida."})
            if self.path == "/api/choose-folder":
                if data.get("kind") not in ("source", "central") or set(data) != {"kind"}:
                    return self.reply(400, {"error": "Escolha origem ou pasta central."})

                def pick():
                    snapshot = service.snapshot()
                    selected = snapshot.get(data["kind"]) or {}
                    path = choose_folder(data["kind"], selected.get("path"))
                    return service.select_folder(data["kind"], path) if path else service.snapshot()

                return self.call(pick)
            if self.path == "/api/refresh" and not data:
                return self.call(service.refresh)
            if self.path == "/api/move" and set(data) == {"preview_id"} and isinstance(data["preview_id"], str):
                return self.call(lambda: service.execute(data["preview_id"]))
            if self.path == "/api/retry" and not data:
                return self.call(service.retry_failed)
            if self.path == "/api/shutdown" and not data:
                with self.server.work_lock:
                    if self.server.active_work:
                        return self.reply(409, {"error": "Aguarde a operação terminar antes de encerrar."})
                    self.server.closing = True
                self.reply(200, {"closed": True})
                if on_shutdown:
                    on_shutdown()
                elif hasattr(self.server, "shutdown_request_from_ui"):
                    self.server.shutdown_request_from_ui()
                return
            self.reply(400, {"error": "Ação inválida."})

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server.daemon_threads = True
    server.work_lock = threading.Lock()
    server.active_work = 0
    server.closing = False
    # A hung client cannot hold a connection forever before sending its request.
    original_get_request = server.get_request

    def get_request():
        connection, address = original_get_request()
        connection.settimeout(10)
        return connection, address

    server.get_request = get_request
    return server



def main():
    from app_window import main as open_application
    open_application()


if __name__ == "__main__":
    main()

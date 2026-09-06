"""Windows application host; the approved interface runs inside WebView2."""

import os
from pathlib import Path
import sys
import threading

from desktop import create_server
from desktop_service import DesktopService
from native_folders import NativePicker, show_startup_error


def application_config():
    """Keep installed settings outside the executable and its bundled resources."""
    if not getattr(sys, "frozen", False):
        return Path(__file__).resolve().with_name("config.json")
    root = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")) / "Central"
    root.mkdir(parents=True, exist_ok=True)
    return root / "config.json"


def allow_close(server):
    """Serialize window closure with admission of new file operations."""
    with server.work_lock:
        if server.active_work:
            return False
        server.closing = True
        return True


def run(config_file=None, *, webview_module=None, on_loaded=None, hidden=False):
    if webview_module is None:
        import webview as webview_module

    picker = NativePicker()
    service = DesktopService(config_file if config_file is not None else application_config())
    server = create_server(service, picker.choose)
    thread = threading.Thread(target=server.serve_forever, name="Central-local-service", daemon=True)
    thread.start()
    try:
        webview_module.settings["OPEN_EXTERNAL_LINKS_IN_BROWSER"] = False
        window = webview_module.create_window(
            "Central", f"http://127.0.0.1:{server.server_port}/",
            width=1180, height=820, min_size=(940, 620),
            background_color="#f5f5f3", text_select=True, hidden=hidden,
        )

        def closing():
            if allow_close(server):
                return True
            show_startup_error("Aguarde a operação terminar ou conclua a escolha de pasta antes de fechar a Central.")
            return False

        window.events.closing += closing
        server.shutdown_request_from_ui = window.destroy
        if on_loaded is not None:
            window.events.loaded += lambda: on_loaded(window, server)
        # Require the modern renderer; silently falling back changes the approved UI.
        webview_module.start(gui="edgechromium", debug=False, private_mode=True)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def main():
    if len(sys.argv) == 3 and sys.argv[1] == "--smoke-test":
        from app_smoke import smoke_test
        smoke_test(Path(sys.argv[2]))
    else:
        run()


if __name__ == "__main__":
    main()

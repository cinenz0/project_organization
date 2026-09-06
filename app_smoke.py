"""Opt-in executable health check, using only disposable documents."""

import json
from pathlib import Path
import tempfile
import threading
import time


def smoke_test(report_path):
    import webview
    from app_window import run

    report = {"ok": False, "checks": []}

    def check(condition, label):
        if not condition:
            raise AssertionError(label)
        report["checks"].append(label)

    def timeout():
        report["error"] = "The application did not finish its smoke test within 45 seconds."
        if webview.windows:
            webview.windows[0].destroy()

    timer = threading.Timer(45, timeout)
    timer.daemon = True
    with tempfile.TemporaryDirectory(prefix="central-app-smoke-") as temporary:
        root = Path(temporary)
        source, central = root / "Entrada de teste", root / "Central de teste"
        source.mkdir()
        central.mkdir()
        payload = b"Disposable Central desktop test."
        (source / "teste.pdf").write_bytes(payload)
        config = root / "config.json"
        config.write_text(json.dumps({"source path": str(source), "central path": str(central)}), encoding="utf-8")

        def loaded(window, server):
            try:
                deadline = time.monotonic() + 15
                while time.monotonic() < deadline:
                    if window.evaluate_js("!document.getElementById('move').disabled"):
                        break
                    time.sleep(0.1)
                check(window.evaluate_js("document.getElementById('source-name').textContent") == source.name, "Packaged UI loaded the temporary source")
                check(window.evaluate_js("document.querySelectorAll('#planned-rows tr').length") == 1, "Preview rendered one disposable file")
                check(window.evaluate_js("!document.getElementById('move').disabled"), "Move action is available")
                window.evaluate_js("document.getElementById('move').click()")
                deadline = time.monotonic() + 15
                while time.monotonic() < deadline:
                    if window.evaluate_js("!document.getElementById('result').hidden && !document.getElementById('shutdown').disabled"):
                        break
                    time.sleep(0.1)
                check(not source.joinpath("teste.pdf").exists(), "The reviewed temporary original was moved")
                check(central.joinpath("PDF", "teste.pdf").read_bytes() == payload, "The central copy contains the complete file")
                check("1 arquivo movido" in window.evaluate_js("document.getElementById('result-title').textContent"), "The UI displays the real result")
                report["port"] = server.server_port
                report["ok"] = True
                window.evaluate_js("document.getElementById('shutdown').click()")
            except Exception as exc:
                report["error"] = str(exc)
                window.destroy()

        timer.start()
        try:
            run(config, on_loaded=loaded, hidden=True)
            check(not any(t.name == "Central-local-service" and t.is_alive() for t in threading.enumerate()), "Window shutdown stopped the local service")
        except Exception as exc:
            report["ok"] = False
            report["error"] = str(exc)
        finally:
            timer.cancel()
    if "error" in report:
        report["ok"] = False
    Path(report_path).write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    raise SystemExit(0 if report["ok"] else 1)

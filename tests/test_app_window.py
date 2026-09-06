"""Windows host tests using temporary folders and a fake WebView implementation."""
import os
from pathlib import Path
import tempfile
import unittest
import json
from types import SimpleNamespace
from unittest.mock import patch

import app_window


class Event:
    def __init__(self):
        self.handlers = []

    def __iadd__(self, handler):
        self.handlers.append(handler)
        return self

    def fire(self):
        return [handler() for handler in self.handlers]


class FakeWindow:
    def __init__(self):
        self.events = SimpleNamespace(closing=Event(), loaded=Event())
        self.destroyed = 0

    def destroy(self):
        self.destroyed += 1


class FakeWebview:
    def __init__(self, *, start_error=None):
        self.settings = {}
        self.start_error = start_error
        self.window = FakeWindow()
        self.created = None
        self.started = None

    def create_window(self, *args, **kwargs):
        self.created = (args, kwargs)
        return self.window

    def start(self, **kwargs):
        self.started = kwargs
        if self.start_error:
            raise self.start_error
        self.window.events.loaded.fire()


class FakeServer:
    def __init__(self, port=43711):
        self.server_port = port
        self.active_work = 0
        self.closing = False
        self.work_lock = __import__("threading").Lock()
        self.serve_calls = 0
        self.shutdown_calls = 0
        self.close_calls = 0

    def serve_forever(self):
        self.serve_calls += 1

    def shutdown(self):
        self.shutdown_calls += 1

    def server_close(self):
        self.close_calls += 1


class AppWindowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "source"
        self.central = self.root / "central"
        self.source.mkdir()
        self.central.mkdir()
        self.config = self.root / "config.json"
        self.config.write_text(json.dumps({"source path": str(self.source), "central path": str(self.central)}), encoding="utf-8")

    def test_application_config_uses_project_config_when_running_from_source(self):
        expected = Path(app_window.__file__).resolve().with_name("config.json")
        with patch.object(app_window.sys, "frozen", False, create=True):
            self.assertEqual(app_window.application_config(), expected)

    def test_frozen_config_is_outside_bundle_and_preserves_existing_file(self):
        local_data = self.root / "LocalAppData"
        config = local_data / "Central" / "config.json"
        config.parent.mkdir(parents=True)
        config.write_text("keep this configuration", encoding="utf-8")
        with patch.dict(os.environ, {"LOCALAPPDATA": str(local_data)}, clear=False):
            with patch.object(app_window.sys, "frozen", True, create=True):
                self.assertEqual(app_window.application_config(), config)
        self.assertEqual(config.read_text(encoding="utf-8"), "keep this configuration")

    def test_allow_close_waits_for_active_work(self):
        server = FakeServer()
        server.active_work = 1
        self.assertFalse(app_window.allow_close(server))
        self.assertFalse(server.closing)
        server.active_work = 0
        self.assertTrue(app_window.allow_close(server))
        self.assertTrue(server.closing)

    def test_run_uses_edge_webview_and_shutdown_callback_destroys_window(self):
        webview = FakeWebview()
        server = FakeServer()
        startup_errors = []
        with patch("app_window.create_server", return_value=server), \
             patch("app_window.show_startup_error", side_effect=startup_errors.append):
            app_window.run(self.config, webview_module=webview, hidden=True)

        self.assertFalse(webview.settings["OPEN_EXTERNAL_LINKS_IN_BROWSER"])
        self.assertEqual(webview.started, {"gui": "edgechromium", "debug": False, "private_mode": True})
        self.assertEqual(webview.created[0], ("Central", "http://127.0.0.1:43711/"))
        self.assertTrue(webview.created[1]["hidden"])
        self.assertEqual(startup_errors, [])
        server.shutdown_request_from_ui()
        self.assertEqual(webview.window.destroyed, 1)
        self.assertEqual(server.shutdown_calls, 1)
        self.assertEqual(server.close_calls, 1)

    def test_window_close_rejects_active_work_and_allows_idle_close(self):
        webview = FakeWebview()
        server = FakeServer()
        messages = []

        def start_and_try_close(**_kwargs):
            server.active_work = 1
            self.assertEqual(webview.window.events.closing.fire(), [False])
            self.assertFalse(server.closing)
            server.active_work = 0
            self.assertEqual(webview.window.events.closing.fire(), [True])
            self.assertTrue(server.closing)

        webview.start = start_and_try_close
        with patch("app_window.create_server", return_value=server), \
             patch("app_window.show_startup_error", side_effect=messages.append):
            app_window.run(self.config, webview_module=webview)
        self.assertEqual(len(messages), 1)
        self.assertIn("Aguarde a operação", messages[0])

    def test_gui_initialization_failure_still_stops_server_and_closes_socket(self):
        server = FakeServer()
        webview = FakeWebview(start_error=RuntimeError("WebView2 unavailable"))
        with patch("app_window.create_server", return_value=server):
            with self.assertRaisesRegex(RuntimeError, "WebView2 unavailable"):
                app_window.run(self.config, webview_module=webview)
        self.assertEqual(server.shutdown_calls, 1)
        self.assertEqual(server.close_calls, 1)


if __name__ == "__main__":
    unittest.main()

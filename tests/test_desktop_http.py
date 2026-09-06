"""Transport boundaries tested with temporary assets and no personal files."""
import http.client
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from desktop import create_server


class FakeService:
    def __init__(self):
        self.calls = []

    def snapshot(self):
        return {"source": None, "central": None}

    def select_folder(self, kind, path):
        self.calls.append((kind, path))
        return self.snapshot()

    def refresh(self):
        self.calls.append("refresh")
        return self.snapshot()

    def execute(self, revision):
        self.calls.append(("execute", revision))
        return {"result": {"moved": 1}}

    def retry_failed(self):
        self.calls.append("retry")
        return self.snapshot()


class LocalTransportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.assets = Path(self.temp.name)
        (self.assets / "index.html").write_text('__CENTRAL_TOKEN__', encoding="utf-8")
        self.asset_patch = patch("desktop.ASSETS", self.assets)
        self.asset_patch.start()
        self.service = FakeService()
        self.picks = []
        self.server = create_server(self.service, self.pick)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        status, self.token, _ = self.request("GET", "/")
        self.assertEqual(status, 200)

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.asset_patch.stop()
        self.temp.cleanup()

    def pick(self, kind, initial):
        self.picks.append(kind)
        return None

    def request(self, method, path, data=None, headers=None):
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=5)
        body = json.dumps(data) if data is not None else None
        connection.request(method, path, body=body, headers=headers or {})
        response = connection.getresponse()
        result = response.status, response.read().decode(), dict(response.getheaders())
        connection.close()
        return result

    def authenticated(self, **extras):
        return {"X-Central-Token": self.token, "Content-Type": "application/json", **extras}

    def test_moves_require_session_token(self):
        for headers in ({}, {"X-Central-Token": "wrong"}):
            self.assertEqual(self.request("POST", "/api/move", {"preview_id": "one"}, headers)[0], 403)
        self.assertEqual(self.service.calls, [])

    def test_cross_origin_and_invalid_host_are_denied(self):
        self.assertEqual(self.request("POST", "/api/move", {"preview_id": "one"}, self.authenticated(Origin="https://example.com"))[0], 403)
        self.assertEqual(self.request("GET", "/", headers={"Host": "example.com"})[0], 403)
        self.assertEqual(self.service.calls, [])

    def test_only_review_identifier_is_accepted_for_execution(self):
        status, _, _ = self.request("POST", "/api/move", {"preview_id": "one"}, self.authenticated())
        self.assertEqual(status, 200)
        self.assertEqual(self.service.calls, [("execute", "one")])
        self.assertEqual(self.request("POST", "/api/move", {"preview_id": "one", "path": "arbitrary"}, self.authenticated())[0], 400)

    def test_picker_cancel_keeps_selection_and_paths_cannot_be_submitted(self):
        self.assertEqual(self.request("POST", "/api/choose-folder", {"kind": "central"}, self.authenticated())[0], 200)
        self.assertEqual(self.picks, ["central"])
        self.assertEqual(self.service.calls, [])
        self.assertEqual(self.request("POST", "/api/choose-folder", {"kind": "central", "path": "untrusted"}, self.authenticated())[0], 400)
        self.assertEqual(self.picks, ["central"])

    def test_static_assets_do_not_expose_arbitrary_files(self):
        for path in ("/config.json", "/../config.json", "/api/state"):
            self.assertIn(self.request("GET", path)[0], (403, 404))
        _, _, headers = self.request("GET", "/")
        self.assertEqual(headers["X-Frame-Options"], "DENY")
        self.assertEqual(headers["Cache-Control"], "no-store")

    def test_invalid_request_cannot_trigger_work(self):
        for body in ([], None, {"preview_id": 8}):
            self.assertEqual(self.request("POST", "/api/move", body, self.authenticated())[0], 400)
        self.assertEqual(self.service.calls, [])


if __name__ == "__main__":
    unittest.main()

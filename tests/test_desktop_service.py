import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import desktop_service
from desktop_service import DesktopService


class DesktopServiceTests(unittest.TestCase):
    def test_both_unavailable_saved_folders_can_be_replaced(self):
        blocked = self.root / "not-a-folder"
        blocked.write_text("preserve", encoding="utf-8")
        self.config.write_text(json.dumps({"source path": str(self.root / "missing-source"),
                                          "central path": str(blocked / "central")}), encoding="utf-8")
        service = self.service()
        self.assertIsNotNone(service.snapshot()["error"])
        service.select_folder("source", self.source)
        recovered = service.select_folder("central", self.central)
        self.assertIsNone(recovered["error"])
        self.assertEqual(blocked.read_text(), "preserve")

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "incoming"
        self.source.mkdir()
        self.default_source = self.root / "default-source"
        self.default_source.mkdir()
        self.default_patch = patch("default_paths.DEFAULT_PATH", self.default_source)
        self.default_patch.start()
        self.addCleanup(self.default_patch.stop)
        self.central = self.root / "central"
        self.config = self.root / "config.json"

    def service(self):
        return DesktopService(self.config)

    def configure(self, service):
        service.select_folder("central", self.central)
        return service.select_folder("source", self.source)

    def test_preview_does_not_write_and_central_selection_persists_only_central(self):
        original = self.source / "report.pdf"
        original.write_bytes(b"report")
        service = self.service()
        snapshot = service.select_folder("central", self.central)
        self.assertEqual(json.loads(self.config.read_text()), {"central path": str(self.central)})
        self.assertFalse(self.central.exists())
        snapshot = service.select_folder("source", self.source)
        self.assertEqual(snapshot["summary"]["planned"], 1)
        self.assertFalse(self.central.exists())
        self.assertEqual(original.read_bytes(), b"report")
        self.assertNotIn("source path", json.loads(self.config.read_text()))

    def test_legacy_central_is_used_without_rewriting_configuration(self):
        self.config.write_text(json.dumps({"destination path": str(self.central)}), encoding="utf-8")
        before = self.config.read_bytes()
        snapshot = self.service().select_folder("source", self.source)
        self.assertEqual(snapshot["central"]["path"], str(self.central / "Documents"))
        self.assertEqual(self.config.read_bytes(), before)

    def test_same_folder_is_rejected_and_cancel_is_a_noop(self):
        service = self.service()
        service.select_folder("source", self.source)
        with self.assertRaises(ValueError):
            service.select_folder("central", self.source)
        before = service.snapshot()
        self.assertEqual(service.select_folder("source", None), before)

    def test_execute_moves_only_reviewed_data_and_handles_collision(self):
        (self.source / "report.pdf").write_bytes(b"new")
        folder = self.central / "PDF"
        folder.mkdir(parents=True)
        (folder / "report.pdf").write_bytes(b"old")
        snapshot = self.configure(self.service())
        result = self.service()  # Make accidental service state reuse impossible in this test.
        del result
        # Recreate once, because the preview token belongs to the configured instance.
        service = self.service()
        snapshot = self.configure(service)
        completed = service.execute(snapshot["preview_id"])
        self.assertEqual(completed["result"]["summary"]["moved"], 1)
        self.assertEqual((folder / "report.pdf").read_bytes(), b"old")
        self.assertEqual((folder / "1_report.pdf").read_bytes(), b"new")
        self.assertFalse((self.source / "report.pdf").exists())

    def test_new_or_changed_reviewed_files_require_a_new_preview(self):
        original = self.source / "report.pdf"
        original.write_bytes(b"old")
        service = self.service()
        snapshot = self.configure(service)
        (self.source / "new.pdf").write_bytes(b"unreviewed")
        original.write_bytes(b"changed content")
        refused = service.execute(snapshot["preview_id"])
        self.assertIn("mudaram", refused["error"])
        self.assertTrue(original.exists())
        self.assertTrue((self.source / "new.pdf").exists())
        self.assertFalse(self.central.exists())
        self.assertIsNotNone(refused["preview_id"])

    def test_new_unreviewed_file_is_not_moved_and_changed_destination_is_refused(self):
        original = self.source / "report.pdf"
        original.write_bytes(b"reviewed")
        service = self.service()
        snapshot = self.configure(service)
        (self.source / "later.pdf").write_bytes(b"later")
        completed = service.execute(snapshot["preview_id"])
        self.assertEqual(completed["result"]["summary"]["moved"], 1)
        self.assertTrue((self.source / "later.pdf").exists())

        snapshot = service.refresh()
        destination = Path(next(op for op in snapshot["operations"] if op["name"] == "later.pdf")["destination"])
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(b"competing")
        refused = service.execute(snapshot["preview_id"])
        self.assertIn("destinos mudaram", refused["error"])
        self.assertTrue((self.source / "later.pdf").exists())

    def test_each_file_is_rechecked_while_an_earlier_move_runs(self):
        first = self.source / "a.pdf"
        second = self.source / "b.pdf"
        first.write_bytes(b"first")
        second.write_bytes(b"second")
        service = self.service()
        snapshot = self.configure(service)
        real_move = desktop_service.move_planned_file
        calls = 0

        def move_then_change_second(*args):
            nonlocal calls
            calls += 1
            result = real_move(*args)
            if calls == 1:
                second.write_bytes(b"changed while first was copying")
            return result

        with patch("desktop_service.move_planned_file", side_effect=move_then_change_second):
            completed = service.execute(snapshot["preview_id"])
        operations = completed["result"]["operations"]
        self.assertEqual(operations[0]["status"], "moved")
        self.assertEqual(operations[1]["status"], "failed")
        self.assertTrue(second.exists())
        self.assertEqual(second.read_bytes(), b"changed while first was copying")

    def test_deleted_reviewed_file_and_reused_token_do_not_rerun(self):
        original = self.source / "report.pdf"
        original.write_bytes(b"data")
        service = self.service()
        snapshot = self.configure(service)
        original.unlink()
        refused = service.execute(snapshot["preview_id"])
        self.assertIn("mudaram", refused["error"])
        original.write_bytes(b"data")
        fresh = service.refresh()
        completed = service.execute(fresh["preview_id"])
        repeated = service.execute(fresh["preview_id"])
        self.assertEqual(completed["result"]["summary"]["moved"], 1)
        self.assertIn("expirou", repeated["error"])
        self.assertIsNone(repeated["result"])

    def test_cancel_preserves_result_but_refresh_or_selection_clears_it(self):
        (self.source / "report.pdf").write_bytes(b"data")
        service = self.service()
        snapshot = self.configure(service)
        finished = service.execute(snapshot["preview_id"])
        self.assertIsNotNone(finished["result"])
        self.assertIsNotNone(service.select_folder("source", None)["result"])
        self.assertIsNone(service.refresh()["result"])

        (self.source / "again.pdf").write_bytes(b"data")
        review = service.refresh()
        service.execute(review["preview_id"])
        alternate = self.root / "alternate"
        self.assertIsNone(service.select_folder("central", alternate)["result"])

    def test_copy_failure_retries_only_failed_reviewed_file(self):
        original = self.source / "report.pdf"
        original.write_bytes(b"data")
        service = self.service()
        snapshot = self.configure(service)
        with patch("desktop_service.move_planned_file", side_effect=OSError("disk full")):
            failed = service.execute(snapshot["preview_id"])
        operation = failed["result"]["operations"][0]
        self.assertEqual(operation["status"], "failed")
        self.assertTrue(operation["retryable"])
        (self.source / "unrelated.pdf").write_bytes(b"keep")
        retried = service.retry_failed()
        self.assertEqual(retried["result"]["summary"]["moved"], 1)
        self.assertTrue((self.source / "unrelated.pdf").exists())

    def test_unlink_failure_is_not_retried_as_a_copy(self):
        original = self.source / "report.pdf"
        original.write_bytes(b"data")
        service = self.service()
        snapshot = self.configure(service)
        with patch("desktop_service.move_planned_file", side_effect=__import__("desktop_service").CopyCompletedSourceRetainedError("locked")):
            result = service.execute(snapshot["preview_id"])
        operation = result["result"]["operations"][0]
        self.assertEqual(operation["status"], "copied_source_retained")
        self.assertFalse(operation["retryable"])
        self.assertEqual(result["result"]["summary"]["copied"], 1)
        self.assertEqual(result["result"]["summary"]["errors"], 1)
        after = service.retry_failed()
        self.assertIn("seguras", after["error"])


if __name__ == "__main__":
    unittest.main()

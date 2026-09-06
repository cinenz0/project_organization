"""Preservation guarantees under failed operations and concurrent collisions."""

from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from organize_by_suffix import organize_by_sufix


class OrganizerErrorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.source = self.root / "incoming"
        self.source.mkdir()
        self.central = self.root / "central"

    def test_copy_failure_removes_partial_preserves_source_and_continues(self):
        original = self.source / "report.pdf"
        original.write_bytes(b"original")
        (self.source / "photo.jpg").write_bytes(b"photo")
        actual_copy = shutil.copyfileobj

        def fail_pdf(incoming, outgoing, *args, **kwargs):
            if Path(incoming.name).suffix == ".pdf":
                outgoing.write(b"partial")
                raise OSError("Disk full")
            return actual_copy(incoming, outgoing, *args, **kwargs)

        with patch("organize_by_suffix.shutil.copyfileobj", fail_pdf):
            report = organize_by_sufix(self.source, self.central)
        self.assertEqual(report["errors"], 1)
        self.assertEqual(report["moved"], 1)
        self.assertEqual(original.read_bytes(), b"original")
        self.assertFalse((self.central / "PDF" / "report.pdf").exists())
        self.assertEqual((self.central / "Images" / "photo.jpg").read_bytes(), b"photo")

    def test_metadata_copy_failure_preserves_source(self):
        original = self.source / "report.pdf"
        original.write_bytes(b"original")
        with patch("organize_by_suffix.shutil.copystat", side_effect=OSError("Metadata denied")):
            report = organize_by_sufix(self.source, self.central)
        self.assertEqual(report["errors"], 1)
        self.assertEqual(original.read_bytes(), b"original")
        self.assertFalse((self.central / "PDF" / "report.pdf").exists())

    def test_exclusive_open_handles_collision_after_availability_check(self):
        original = self.source / "report.pdf"
        original.write_bytes(b"original")
        contested = self.central / "PDF" / "report.pdf"
        actual_open = Path.open
        raced = False

        def racing_open(path, mode="r", *args, **kwargs):
            nonlocal raced
            if path == contested and mode == "xb" and not raced:
                raced = True
                with actual_open(path, "wb") as other:
                    other.write(b"concurrent file")
            return actual_open(path, mode, *args, **kwargs)

        with patch.object(Path, "open", racing_open):
            report = organize_by_sufix(self.source, self.central)
        self.assertTrue(raced)
        self.assertEqual(report["moved"], 1)
        self.assertEqual(contested.read_bytes(), b"concurrent file")
        self.assertEqual((contested.parent / "1_report.pdf").read_bytes(), b"original")

    def test_category_traversal_rejected_before_any_files_are_moved(self):
        original = self.source / "report.pdf"
        original.write_bytes(b"original")
        for category in ("../outside", "..", "nested/category", "nested\\category", "D:outside", ""):
            with self.subTest(category=category):
                with patch("organize_by_suffix.data_dict", [{"Folder": category, "Suffixes": [".pdf"]}]):
                    with self.assertRaisesRegex(ValueError, "single folder name"):
                        organize_by_sufix(self.source, self.central)
                self.assertFalse(self.central.exists())
                self.assertEqual(original.read_bytes(), b"original")

    def test_category_resolving_outside_central_is_rejected(self):
        original = self.source / "report.pdf"
        original.write_bytes(b"original")
        folder = self.central / "PDF"
        actual_resolve = Path.resolve

        def redirect_folder(path, *args, **kwargs):
            if path == folder:
                return self.root / "outside"
            return actual_resolve(path, *args, **kwargs)

        with patch.object(Path, "resolve", redirect_folder):
            report = organize_by_sufix(self.source, self.central)
        self.assertEqual(report["errors"], 1)
        self.assertFalse(self.central.exists())
        self.assertTrue(original.exists())

    def test_source_symbolic_link_is_skipped(self):
        original = self.source / "report.pdf"
        original.write_bytes(b"original")
        actual_is_symlink = Path.is_symlink

        def simulate_link(path):
            return path == original or actual_is_symlink(path)

        with patch.object(Path, "is_symlink", simulate_link):
            report = organize_by_sufix(self.source, self.central)
        self.assertEqual(report["skipped"], 1)
        self.assertEqual(original.read_bytes(), b"original")
        self.assertFalse(self.central.exists())

    def test_dry_run_reserves_names_planned_in_same_batch(self):
        folder = self.central / "PDF"
        folder.mkdir(parents=True)
        (folder / "report.pdf").write_bytes(b"existing")
        (self.source / "report.pdf").write_bytes(b"report")
        (self.source / "1_report.pdf").write_bytes(b"numbered")
        report = organize_by_sufix(self.source, self.central, dry_run=True)
        self.assertEqual(report["planned"], 2)
        destinations = {Path(operation["destination"]).name for operation in report["operations"]}
        self.assertEqual(destinations, {"1_report.pdf", "2_report.pdf"})
        self.assertEqual(len(list(folder.iterdir())), 1)
        self.assertEqual(len(list(self.source.iterdir())), 2)

    def test_dry_run_reports_category_obstacle_without_writing(self):
        self.central.mkdir()
        obstacle = self.central / "PDF"
        obstacle.write_bytes(b"obstacle")
        original = self.source / "report.pdf"
        original.write_bytes(b"original")
        report = organize_by_sufix(self.source, self.central, dry_run=True)
        self.assertEqual(report["errors"], 1)
        self.assertEqual(report["planned"], 0)
        self.assertEqual(obstacle.read_bytes(), b"obstacle")
        self.assertEqual(original.read_bytes(), b"original")

    def test_already_organized_category_is_unchanged(self):
        folder = self.central / "PDF"
        folder.mkdir(parents=True)
        original = folder / "report.pdf"
        original.write_bytes(b"original")
        for dry_run in (True, False):
            with self.subTest(dry_run=dry_run):
                report = organize_by_sufix(folder, self.central, dry_run=dry_run)
                self.assertEqual(report["skipped"], 1)
                self.assertEqual(report["moved"], 0)
                self.assertEqual(report["planned"], 0)
                self.assertEqual(list(folder.iterdir()), [original])
                self.assertEqual(original.read_bytes(), b"original")


if __name__ == "__main__":
    unittest.main()

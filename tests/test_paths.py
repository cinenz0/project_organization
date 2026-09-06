import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import default_paths
from paths import parse_args, validate_central
import main


class PathTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.config = self.root / "config.json"
        self.source = self.root / "incoming"
        self.source.mkdir()
        self.central = self.root / "library"

    def parse(self, args):
        return parse_args(args, config_file=self.config)

    def assert_invalid(self, args, message=None):
        output = io.StringIO()
        with contextlib.redirect_stderr(output), self.assertRaises(SystemExit) as caught:
            self.parse(args)
        self.assertEqual(caught.exception.code, 2)
        if message:
            self.assertIn(message, output.getvalue())

    def write_config(self, data):
        self.config.write_text(json.dumps(data), encoding="utf-8")

    def test_missing_config_read_does_not_write(self):
        source, central = default_paths.paths(self.config)
        self.assertEqual(source, Path.home() / "Desktop")
        self.assertIsNone(central)
        self.assertFalse(self.config.exists())

    def test_first_configuration_persists_direct_central_only(self):
        options = self.parse(["--set-central", str(self.central)])
        self.assertTrue(options.configure_only)
        self.assertIsNone(options.source)
        self.assertEqual(options.destination, self.central)
        self.assertEqual(json.loads(self.config.read_text()), {"central path": str(self.central)})
        self.assertFalse(self.central.exists())
        self.assertEqual(self.parse(["-s", str(self.source)]).destination, self.central)

    def test_missing_central_has_actionable_error(self):
        self.assert_invalid(["-s", str(self.source)], "--set-central PATH")
        self.assertFalse(self.config.exists())

    def test_legacy_effective_destination_preserved_without_writing(self):
        self.write_config({"source path": str(self.source), "destination path": str(self.central)})
        before = self.config.read_bytes()
        options = self.parse(["--dry-run"])
        self.assertEqual(options.destination, self.central / "Documents")
        self.assertEqual(self.config.read_bytes(), before)

    def test_new_central_overrides_legacy(self):
        self.write_config({"source path": str(self.source), "destination path": str(self.root),
                           "central path": str(self.central)})
        self.assertEqual(self.parse(["--dry-run"]).destination, self.central)

    def test_invalid_json_is_not_overwritten_even_when_setting_central(self):
        self.config.write_text("{broken", encoding="utf-8")
        self.assert_invalid(["--set-central", str(self.central)], "Invalid JSON")
        self.assertEqual(self.config.read_text(), "{broken")

    def test_invalid_config_types(self):
        for data in ([], {"source path": None}, {"central path": 1}, {"destination path": ""}):
            with self.subTest(data=data):
                self.write_config(data)
                self.assert_invalid(["--set-central", str(self.central)], "Configuration")

    def test_incomplete_arguments(self):
        for flag in ("-s", "--source", "-d", "--destination", "--set-central"):
            with self.subTest(flag=flag):
                self.assert_invalid([flag], "expected one argument")

    def test_source_must_be_existing_directory(self):
        file_path = self.root / "file.txt"
        file_path.write_text("keep me", encoding="utf-8")
        for source in (file_path, self.root / "missing"):
            with self.subTest(source=source):
                self.assert_invalid(["-s", str(source), "-d", str(self.central), "-sd"],
                                    "Source must be an existing directory")
                self.assertFalse(self.config.exists())

    def test_central_cannot_equal_source(self):
        self.assert_invalid(["-s", str(self.source), "-d", str(self.source), "-sd"],
                            "must be different directories")
        self.assertFalse(self.config.exists())

    def test_central_rejects_file_and_file_ancestor(self):
        file_path = self.root / "file.txt"
        file_path.write_text("keep me", encoding="utf-8")
        for central in (file_path, file_path / "nested"):
            with self.subTest(central=central):
                self.assert_invalid(["--set-central", str(central)], "directory")
        self.assertFalse(self.config.exists())

    def test_central_rejects_unavailable_root(self):
        with patch.object(Path, "exists", return_value=False):
            with patch.object(Path, "is_symlink", return_value=False):
                with self.assertRaisesRegex(ValueError, "no available directory ancestor"):
                    validate_central(self.central)

    def test_destination_override_is_not_saved(self):
        self.write_config({"central path": str(self.central)})
        before = self.config.read_bytes()
        alternate = self.root / "alternate"
        options = self.parse(["-s", str(self.source), "-d", str(alternate)])
        self.assertEqual(options.destination, alternate)
        self.assertEqual(self.config.read_bytes(), before)

    def test_set_default_persists_valid_paths(self):
        options = self.parse(["-s", str(self.source), "-d", str(self.central), "-sd"])
        self.assertFalse(options.configure_only)
        self.assertEqual(default_paths.paths(self.config), (self.source, self.central))

    def test_dry_run_never_saves_or_creates_directories(self):
        options = self.parse(["-s", str(self.source), "-d", str(self.central), "--dry-run"])
        self.assertTrue(options.dry_run)
        self.assertFalse(self.config.exists())
        self.assertFalse(self.central.exists())
        for arguments in (["--set-central", str(self.central)],
                          ["-s", str(self.source), "-d", str(self.central), "-sd"]):
            self.assert_invalid(arguments + ["--dry-run"], "cannot be combined")
            self.assertFalse(self.config.exists())

    def test_help_does_not_read_or_create_config(self):
        with patch("paths.paths", side_effect=AssertionError("Config read")):
            with contextlib.redirect_stdout(io.StringIO()), self.assertRaises(SystemExit) as caught:
                self.parse(["--help"])
        self.assertEqual(caught.exception.code, 0)
        self.assertFalse(self.config.exists())

    def test_interactive_first_run_saves_central_after_validation(self):
        with patch("builtins.input", side_effect=[str(self.source), str(self.central)]):
            options = self.parse([])
        self.assertEqual(options.destination, self.central)
        self.assertEqual(default_paths.paths(self.config)[1], self.central)

    def test_interactive_reuses_saved_central(self):
        self.write_config({"source path": str(self.source), "central path": str(self.central)})
        with patch("builtins.input", return_value="") as ask:
            options = self.parse([])
        self.assertEqual(ask.call_count, 1)
        self.assertEqual(options.destination, self.central)

    def test_config_file_is_independent_of_working_directory(self):
        self.assertEqual(default_paths.CONFIG_FILE,
                         Path(default_paths.__file__).resolve().with_name("config.json"))

    def test_main_configuration_does_not_invoke_organizer(self):
        output = io.StringIO()
        with patch("main.organize_by_sufix") as organize, contextlib.redirect_stdout(output):
            code = main.main(["--set-central", str(self.central)], config_file=self.config)
        self.assertEqual(code, 0)
        organize.assert_not_called()
        self.assertIn(str(self.central), output.getvalue())

    def test_main_reports_summary_and_failure_exit(self):
        result = {"moved": 0, "planned": 0, "skipped": 0, "errors": 1,
                  "operations": [{"source": "example.pdf", "destination": None,
                                  "status": "error", "error": "Access denied"}]}
        output = io.StringIO()
        with patch("main.organize_by_sufix", return_value=result) as organize:
            with contextlib.redirect_stdout(output):
                code = main.main(["-s", str(self.source), "-d", str(self.central), "--dry-run"],
                                 config_file=self.config)
        self.assertEqual(code, 1)
        organize.assert_called_once_with(original_directory=self.source, dst_directory=self.central, dry_run=True)
        self.assertIn("Access denied", output.getvalue())
        self.assertIn("1 errors", output.getvalue())


if __name__ == "__main__":
    unittest.main()

"""Exercise the public CLI flow without touching the real configuration."""

import contextlib
import io
import tempfile
import unittest
from pathlib import Path

from main import main


class CentralFolderIntegrationTests(unittest.TestCase):
    def test_configure_preview_and_organize_two_sources(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            config = root / 'settings.json'
            central = root / 'documents'
            source_a = root / 'a'
            source_b = root / 'b'
            for source, content in [(source_a, b'first'), (source_b, b'second')]:
                source.mkdir()
                (source / 'report.PDF').write_bytes(content)
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(main(['--set-central', str(central)], config_file=config), 0)
                self.assertFalse(central.exists())
                saved = config.read_bytes()
                self.assertEqual(main(['-s', str(source_a), '--dry-run'], config_file=config), 0)
                self.assertFalse(central.exists())
                self.assertEqual((source_a / 'report.PDF').read_bytes(), b'first')
                self.assertEqual(config.read_bytes(), saved)
                for source in (source_a, source_b):
                    self.assertEqual(main(['-s', str(source)], config_file=config), 0)
            self.assertEqual((central / 'PDF' / 'report.PDF').read_bytes(), b'first')
            self.assertEqual((central / 'PDF' / '1_report.PDF').read_bytes(), b'second')
            self.assertEqual(config.read_bytes(), saved)
            self.assertFalse((source_a / 'Documents').exists())
            self.assertFalse((source_b / 'Documents').exists())
            self.assertTrue(output.getvalue().strip())

    def test_operational_failure_returns_nonzero_and_preserves_source(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / 'source'
            source.mkdir()
            original = source / 'report.pdf'
            original.write_bytes(b'original')
            central = root / 'central'
            central.mkdir()
            (central / 'PDF').write_bytes(b'obstacle')
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                status = main(['-s', str(source), '-d', str(central)], config_file=root / 'absent.json')
            self.assertNotEqual(status, 0)
            self.assertEqual(original.read_bytes(), b'original')
            self.assertFalse((root / 'absent.json').exists())


if __name__ == '__main__':
    unittest.main()

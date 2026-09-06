"""Behavioral regression tests using disposable documents only."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from organize_by_suffix import organize_by_sufix


class OrganizerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / 'incoming'
        self.source.mkdir()
        self.central = self.root / 'central'

    def test_multiple_sources_share_direct_category_root(self):
        other = self.root / 'other'
        other.mkdir()
        (self.source / 'first.pdf').write_bytes(b'first')
        (other / 'second.pdf').write_bytes(b'second')
        for source in (self.source, other):
            report = organize_by_sufix(source, self.central)
            self.assertEqual(report['moved'], 1)
            self.assertEqual(report['errors'], 0)
            self.assertEqual(list(source.iterdir()), [])
        self.assertEqual((self.central / 'PDF' / 'first.pdf').read_bytes(), b'first')
        self.assertEqual((self.central / 'PDF' / 'second.pdf').read_bytes(), b'second')
        self.assertFalse((self.central / 'Documents').exists())

    def test_collisions_preserve_every_existing_file(self):
        folder = self.central / 'PDF'
        folder.mkdir(parents=True)
        (folder / 'report.pdf').write_bytes(b'old')
        (folder / '1_report.pdf').write_bytes(b'also old')
        (self.source / 'report.pdf').write_bytes(b'new')
        report = organize_by_sufix(self.source, self.central)
        self.assertEqual(report['moved'], 1)
        self.assertEqual((folder / 'report.pdf').read_bytes(), b'old')
        self.assertEqual((folder / '1_report.pdf').read_bytes(), b'also old')
        self.assertEqual((folder / '2_report.pdf').read_bytes(), b'new')

    def test_dry_run_has_no_filesystem_writes(self):
        (self.source / 'report.pdf').write_bytes(b'original')
        report = organize_by_sufix(self.source, self.central, dry_run=True)
        self.assertEqual(report['planned'], 1)
        self.assertEqual(report['moved'], 0)
        self.assertFalse(self.central.exists())
        self.assertEqual((self.source / 'report.pdf').read_bytes(), b'original')
        self.assertEqual(Path(report['operations'][0]['destination']), self.central / 'PDF' / 'report.pdf')

    def test_dry_run_accounts_for_existing_collisions(self):
        folder = self.central / 'PDF'
        folder.mkdir(parents=True)
        (folder / 'report.pdf').write_bytes(b'old')
        (self.source / 'report.pdf').write_bytes(b'new')
        report = organize_by_sufix(self.source, self.central, dry_run=True)
        self.assertEqual(Path(report['operations'][0]['destination']), folder / '1_report.pdf')
        self.assertEqual(list(folder.iterdir()), [folder / 'report.pdf'])

    def test_extensions_are_case_insensitive_and_legacy_formats_work(self):
        for filename in ('photo.JPG', 'book.xls', 'movie.wmv'):
            (self.source / filename).write_bytes(b'data')
        report = organize_by_sufix(self.source, self.central)
        self.assertEqual(report['moved'], 3)
        for category, filename in [('Images', 'photo.JPG'), ('Excel', 'book.xls'), ('Video', 'movie.wmv')]:
            self.assertTrue((self.central / category / filename).is_file())

    def test_unknown_files_and_nested_content_are_preserved(self):
        (self.source / 'unknown.xyz').write_bytes(b'unknown')
        nested = self.source / 'nested'
        nested.mkdir()
        (nested / 'nested.pdf').write_bytes(b'nested')
        report = organize_by_sufix(self.source, self.central)
        self.assertEqual(report['moved'], 0)
        self.assertGreaterEqual(report['skipped'], 1)
        self.assertTrue((nested / 'nested.pdf').exists())
        self.assertTrue((self.source / 'unknown.xyz').exists())
        self.assertFalse(self.central.exists())

    def test_category_path_obstacle_does_not_block_other_categories(self):
        self.central.mkdir()
        (self.central / 'PDF').write_bytes(b'obstacle')
        (self.source / 'report.pdf').write_bytes(b'original')
        (self.source / 'photo.jpg').write_bytes(b'photo')
        report = organize_by_sufix(self.source, self.central)
        self.assertEqual(report['errors'], 1)
        self.assertEqual(report['moved'], 1)
        self.assertEqual((self.source / 'report.pdf').read_bytes(), b'original')
        self.assertEqual((self.central / 'PDF').read_bytes(), b'obstacle')
        self.assertTrue((self.central / 'Images' / 'photo.jpg').exists())

    def test_failed_source_deletion_preserves_both_copies(self):
        source_file = self.source / 'report.pdf'
        source_file.write_bytes(b'original')
        original_unlink = Path.unlink

        def guarded_unlink(path, *args, **kwargs):
            if path == source_file:
                raise PermissionError('source is locked')
            return original_unlink(path, *args, **kwargs)

        with patch.object(Path, 'unlink', guarded_unlink):
            report = organize_by_sufix(self.source, self.central)
        self.assertEqual(report['errors'], 1)
        self.assertEqual(source_file.read_bytes(), b'original')
        self.assertEqual((self.central / 'PDF' / 'report.pdf').read_bytes(), b'original')

    def test_same_source_and_central_is_rejected_without_movement(self):
        (self.source / 'report.pdf').write_bytes(b'original')
        with self.assertRaises(ValueError):
            organize_by_sufix(self.source, self.source)
        self.assertEqual((self.source / 'report.pdf').read_bytes(), b'original')


if __name__ == '__main__':
    unittest.main()

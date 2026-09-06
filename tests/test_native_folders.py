import ctypes as ct
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from native_folders import NativePicker, WindowsFolderDialog, _method


class NativePickerTests(unittest.TestCase):
    def test_cancel_returns_no_selection_and_releases_lock(self):
        picker=NativePicker()
        with patch('native_folders.WindowsFolderDialog') as dialog:
            dialog.return_value.__enter__.return_value.show.return_value=None
            self.assertIsNone(picker.choose('source'))
            self.assertIsNone(picker.choose('source'))
            self.assertEqual(dialog.call_count,2)

    def test_failed_dialog_does_not_lock_future_selection(self):
        picker=NativePicker()
        with patch('native_folders.WindowsFolderDialog',side_effect=OSError('unavailable')):
            with self.assertRaises(OSError):
                picker.choose('central')
        self.assertTrue(picker.lock.acquire(blocking=False))
        picker.lock.release()

    @unittest.skipUnless(sys.platform=='win32','Windows COM integration')
    def test_real_windows_dialog_initializes_in_folder_mode_without_tk(self):
        with tempfile.TemporaryDirectory() as path:
            with WindowsFolderDialog('Central test',Path(path)) as dialog:
                flags=ct.c_uint32()
                hr=_method(dialog.pointer,10,ct.POINTER(ct.c_uint32))(dialog.pointer,ct.byref(flags))
                self.assertGreaterEqual(hr,0)
                self.assertEqual(flags.value & (0x20|0x40|0x800),0x20|0x40|0x800)


if __name__=='__main__':
    unittest.main()

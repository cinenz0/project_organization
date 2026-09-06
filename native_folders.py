"""Windows Common Item Dialog, using ctypes instead of a GUI dependency.

Interface and flags: https://learn.microsoft.com/windows/win32/shell/common-file-dialog
IFileDialog inherits IModalWindow; the COM vtable positions are defined by the
Windows SDK (shobjidl_core.h). All COM objects live and are released in one STA.
"""

import ctypes as ct
from pathlib import Path
import sys
import threading
import uuid


class GUID(ct.Structure):
    _fields_ = [("data1", ct.c_uint32), ("data2", ct.c_uint16),
                ("data3", ct.c_uint16), ("data4", ct.c_ubyte * 8)]

    @classmethod
    def parse(cls, text):
        return cls.from_buffer_copy(uuid.UUID(text).bytes_le)


def _check(hr):
    if hr < 0:
        raise OSError(f"Não foi possível abrir a janela de pastas do Windows (0x{hr & 0xffffffff:08X}).")
    return hr


def _method(pointer, slot, *argtypes, result=ct.c_long):
    table = ct.cast(pointer, ct.POINTER(ct.POINTER(ct.c_void_p))).contents
    return ct.WINFUNCTYPE(result, ct.c_void_p, *argtypes)(table[slot])


class WindowsFolderDialog:
    def __init__(self, title, initial=None):
        self.title = title
        self.initial = initial
        self.pointer = ct.c_void_p()
        self.initialized = False

    def __enter__(self):
        if sys.platform != "win32":
            raise RuntimeError("A interface desktop usa o seletor de pastas do Windows. A CLI continua disponível nesta plataforma.")
        self.ole = ct.WinDLL("ole32")
        self.ole.CoInitializeEx.argtypes = [ct.c_void_p, ct.c_ulong]
        self.ole.CoInitializeEx.restype = ct.c_long
        self.ole.CoUninitialize.argtypes = []
        self.ole.CoUninitialize.restype = None
        self.ole.CoTaskMemFree.argtypes = [ct.c_void_p]
        self.ole.CoTaskMemFree.restype = None
        self.ole.CoCreateInstance.argtypes = [ct.POINTER(GUID), ct.c_void_p, ct.c_ulong, ct.POINTER(GUID), ct.POINTER(ct.c_void_p)]
        self.ole.CoCreateInstance.restype = ct.c_long
        _check(self.ole.CoInitializeEx(None, 0x2 | 0x4))
        self.initialized = True
        try:
            clsid = GUID.parse("DC1C5A9C-E88A-4DDE-A5A1-60F82A20AEF7")
            iid = GUID.parse("42F85136-DB7E-439C-85F1-E4075D135FC8")
            _check(self.ole.CoCreateInstance(ct.byref(clsid), None, 1, ct.byref(iid), ct.byref(self.pointer)))
            flags = ct.c_uint32()
            _check(_method(self.pointer, 10, ct.POINTER(ct.c_uint32))(self.pointer, ct.byref(flags)))
            # Pick filesystem directories, require a valid path, keep CWD and
            # the user's recent-file history untouched.
            flags.value |= 0x20 | 0x40 | 0x800 | 0x8 | 0x02000000
            _check(_method(self.pointer, 9, ct.c_uint32)(self.pointer, flags.value))
            _check(_method(self.pointer, 17, ct.c_wchar_p)(self.pointer, self.title))
            _check(_method(self.pointer, 18, ct.c_wchar_p)(self.pointer, "Usar esta pasta"))
            self._set_initial()
            return self
        except Exception:
            self.__exit__(None, None, None)
            raise

    def _set_initial(self):
        if not self.initial or not Path(self.initial).is_dir():
            return
        shell = ct.WinDLL("shell32")
        shell.SHCreateItemFromParsingName.argtypes = [ct.c_wchar_p, ct.c_void_p, ct.POINTER(GUID), ct.POINTER(ct.c_void_p)]
        shell.SHCreateItemFromParsingName.restype = ct.c_long
        iid = GUID.parse("43826D1E-E718-42EE-BC55-A1E261C37BFE")
        item = ct.c_void_p()
        hr = shell.SHCreateItemFromParsingName(str(Path(self.initial).resolve()), None, ct.byref(iid), ct.byref(item))
        if hr >= 0 and item:
            try:
                _check(_method(self.pointer, 12, ct.c_void_p)(self.pointer, item))
            finally:
                _method(item, 2, result=ct.c_ulong)(item)

    def show(self):
        user = ct.WinDLL("user32")
        user.GetForegroundWindow.argtypes = []
        user.GetForegroundWindow.restype = ct.c_void_p
        hr = _method(self.pointer, 3, ct.c_void_p)(self.pointer, user.GetForegroundWindow())
        if hr & 0xffffffff == 0x800704C7:  # HRESULT_FROM_WIN32(ERROR_CANCELLED)
            return None
        _check(hr)
        item, text = ct.c_void_p(), ct.c_void_p()
        _check(_method(self.pointer, 20, ct.POINTER(ct.c_void_p))(self.pointer, ct.byref(item)))
        try:
            _check(_method(item, 5, ct.c_uint32, ct.POINTER(ct.c_void_p))(item, 0x80058000, ct.byref(text)))
            return ct.wstring_at(text)
        finally:
            if text:
                self.ole.CoTaskMemFree(text)
            _method(item, 2, result=ct.c_ulong)(item)

    def __exit__(self, *_args):
        if self.pointer:
            _method(self.pointer, 2, result=ct.c_ulong)(self.pointer)
            self.pointer = ct.c_void_p()
        if self.initialized:
            self.ole.CoUninitialize()
            self.initialized = False


class NativePicker:
    def __init__(self):
        self.lock = threading.Lock()

    def choose(self, kind, initial=None):
        if not self.lock.acquire(blocking=False):
            raise RuntimeError("Já há uma janela de pastas aberta. Conclua ou cancele essa seleção.")
        try:
            title = "Escolher pasta para organizar" if kind == "source" else "Escolher pasta central"
            with WindowsFolderDialog(title, initial) as dialog:
                return dialog.show()
        finally:
            self.lock.release()


def show_startup_error(message):
    if sys.platform == "win32":
        user = ct.WinDLL("user32")
        user.MessageBoxW.argtypes = [ct.c_void_p, ct.c_wchar_p, ct.c_wchar_p, ct.c_uint]
        user.MessageBoxW(None, str(message), "Central", 0x10)

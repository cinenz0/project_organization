# Build from the isolated environment with: python -m PyInstaller Central.spec
from pathlib import Path

project = Path(SPECPATH)
a = Analysis(
    [str(project / 'Abrir Central.pyw')],
    pathex=[str(project)],
    binaries=[],
    datas=[(str(project / 'ui'), 'ui')],
    hiddenimports=[],
    hookspath=[],
    runtime_hooks=[],
    excludes=['tkinter', 'PyQt5', 'PyQt6', 'PySide2', 'PySide6'],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, [], exclude_binaries=True, name='Central',
    debug=False, bootloader_ignore_signals=False, strip=False,
    upx=False, console=False, disable_windowed_traceback=False,
)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='Central')

"""Double-click to start Central without a terminal window."""
try:
    import importlib.util
    from pathlib import Path
    import subprocess
    import sys

    environment_python = Path(__file__).resolve().parent / '.venv' / 'Scripts' / 'pythonw.exe'
    if not getattr(sys, 'frozen', False) and importlib.util.find_spec('webview') is None and environment_python.is_file():
        subprocess.Popen([str(environment_python), str(Path(__file__).resolve()), *sys.argv[1:]])
    else:
        from app_window import main
        main()
except Exception as exc:
    from native_folders import show_startup_error
    show_startup_error("Não foi possível iniciar a aplicação.\n\n" + str(exc))

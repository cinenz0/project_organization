"""Persistent defaults; reading configuration never creates or changes files."""

import json
import os
from pathlib import Path
import tempfile

SRC_KEY = "source path"
DST_KEY = "destination path"  # Legacy: parent of Documents.
CENTRAL_KEY = "central path"
DEFAULT_PATH = Path.home() / "Desktop"
CONFIG_FILE = Path(__file__).resolve().with_name("config.json")


def read_config(config_file=None):
    config_path = Path(config_file) if config_file is not None else CONFIG_FILE
    try:
        with config_path.open(encoding="utf-8") as stream:
            data = json.load(stream)
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in configuration {config_path}: {exc.msg}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"Configuration {config_path} must be a JSON object")
    for key in (SRC_KEY, DST_KEY, CENTRAL_KEY):
        if key in data and (not isinstance(data[key], str) or not data[key].strip()):
            raise ValueError(f"Configuration '{key}' must be a non-empty path string")
    return data


def paths(config_file=None):
    data = read_config(config_file)
    source = Path(data.get(SRC_KEY, DEFAULT_PATH)).expanduser()
    if CENTRAL_KEY in data:
        central = Path(data[CENTRAL_KEY]).expanduser()
    elif DST_KEY in data:
        central = Path(data[DST_KEY]).expanduser() / "Documents"
    else:
        central = None
    return source, central


def save_paths(source=None, central=None, config_file=None):
    """Save explicit validated defaults atomically, preserving unrelated settings."""
    config_path = Path(config_file) if config_file is not None else CONFIG_FILE
    data = read_config(config_path)
    if source is not None:
        data[SRC_KEY] = str(source)
    if central is not None:
        data[CENTRAL_KEY] = str(central)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=config_path.parent,
                                         prefix=".organizer-", suffix=".json", delete=False) as stream:
            temporary = Path(stream.name)
            json.dump(data, stream, indent=4)
            stream.write("\n")
        os.replace(temporary, config_path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)

"""Validate command-line paths and resolve the persistent central library."""

import argparse
from dataclasses import dataclass
from pathlib import Path
import sys

from default_paths import paths, save_paths


@dataclass(frozen=True)
class Options:
    source: Path | None
    destination: Path
    dry_run: bool = False
    configure_only: bool = False


def validate_source(value):
    source = Path(value).expanduser().resolve()
    if not source.is_dir():
        raise ValueError(f"Source must be an existing directory: {source}")
    return source


def validate_central(value):
    raw = Path(value).expanduser()
    if not str(value).strip():
        raise ValueError("Central directory cannot be empty")
    # Validate unresolved ancestors too, so a broken symlink is not mistaken for a new folder.
    ancestor = raw.absolute()
    while not ancestor.exists():
        if ancestor.is_symlink():
            raise ValueError(f"Central path has a broken symbolic link: {ancestor}")
        if ancestor.parent == ancestor:
            raise ValueError(f"Central path has no available directory ancestor: {raw}")
        ancestor = ancestor.parent
    if not ancestor.is_dir():
        raise ValueError(f"Central path must be a directory or have a directory ancestor: {raw}")
    return raw.resolve()


def _parser():
    parser = argparse.ArgumentParser(description="Organize files into one central library.")
    parser.add_argument("-s", "--source", help="Existing directory to organize")
    parser.add_argument("-d", "--destination", help="Central library for this run (direct category root)")
    parser.add_argument("--set-central", metavar="PATH", help="Save a central library without organizing files")
    parser.add_argument("-sd", "--set-default", action="store_true", help="Save selected source and central library, then organize")
    parser.add_argument("--dry-run", action="store_true", help="Preview operations without writing files or configuration")
    return parser


def parse_args(argv=None, config_file=None):
    arguments = list(sys.argv[1:] if argv is None else argv)
    parser = _parser()
    args = parser.parse_args(arguments)
    if args.dry_run and (args.set_central is not None or args.set_default):
        parser.error("--dry-run cannot be combined with --set-central or --set-default")
    if args.set_central is not None and (args.source is not None or args.destination is not None or args.set_default):
        parser.error("--set-central configures only; use it separately from source, destination, or set-default")
    try:
        default_source, default_central = paths(config_file)
        if args.set_central is not None:
            central = validate_central(args.set_central)
            save_paths(central=central, config_file=config_file)
            return Options(None, central, configure_only=True)

        source_value = args.source if args.source is not None else default_source
        central_value = args.destination if args.destination is not None else default_central
        save_interactive_central = False
        if not arguments:
            source_value = input(f"Source directory [{default_source}]: ").strip() or default_source
            if central_value is None:
                central_value = input("Central library directory (saved for future runs): ").strip()
                save_interactive_central = True
        if central_value is None or not str(central_value).strip():
            raise ValueError("No central library configured. Run --set-central PATH or provide --destination PATH.")
        if not str(source_value).strip():
            raise ValueError("Source directory cannot be empty")
        source = validate_source(source_value)
        central = validate_central(central_value)
        if source == central:
            raise ValueError("Source and central library must be different directories")
        if args.set_default:
            save_paths(source=source, central=central, config_file=config_file)
        elif save_interactive_central:
            save_paths(central=central, config_file=config_file)
        return Options(source, central, dry_run=args.dry_run)
    except (OSError, ValueError, EOFError) as exc:
        parser.error(str(exc))

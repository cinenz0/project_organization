"""Plan and move files into a direct central category root without overwriting."""

import os
from pathlib import Path
import shutil

from data_dict import data_dict
from paths import validate_central, validate_source


class CopyCompletedSourceRetainedError(OSError):
    """The destination is complete, but the source could not be removed."""


def _category_map():
    categories = {}
    for entry in data_dict:
        folder = entry["Folder"]
        if (not isinstance(folder, str) or not folder.strip()
                or folder in (".", "..")
                or any(character in folder for character in '/\\:')):
            raise ValueError(f"Category must be a single folder name: {folder!r}")
        suffixes = entry["Suffixes"]
        if not isinstance(suffixes, (list, tuple)):
            raise ValueError(f"Category suffixes must be a list: {folder}")
        for suffix in suffixes:
            if not isinstance(suffix, str) or not suffix.startswith(".") or len(suffix) < 2:
                raise ValueError(f"Invalid extension in category {folder}: {suffix!r}")
            key = suffix.casefold()
            if key in categories and categories[key] != folder:
                raise ValueError(f"Extension belongs to multiple categories: {suffix}")
            categories[key] = folder
    return categories


def _category_folder(central, category):
    folder = central / category
    # resolve() also detects Windows junctions pointing outside the central root.
    if folder.is_symlink() or folder.resolve().parent != central:
        raise ValueError(f"Category points outside the central library or is a symbolic link: {folder}")
    if folder.exists() and not folder.is_dir():
        raise ValueError(f"Category path is not a directory: {folder}")
    return folder


def _available_destination(folder, filename, reserved):
    candidate = folder / filename
    index = 0
    while candidate in reserved or candidate.exists() or candidate.is_symlink():
        index += 1
        candidate = folder / f"{index}_{filename}"
    return candidate


def _create_destination(folder, filename, reserved):
    while True:
        destination = _available_destination(folder, filename, reserved)
        try:
            return destination, destination.open("xb")
        except FileExistsError:
            # Another process claimed this name after the availability check.
            reserved.add(destination)


def _copy_and_remove(source, destination, output):
    created_stat = None
    try:
        with output:
            created_stat = os.fstat(output.fileno())
            with source.open("rb") as incoming:
                shutil.copyfileobj(incoming, output)
            output.flush()
            os.fsync(output.fileno())
        shutil.copystat(source, destination, follow_symlinks=False)
    except OSError as copy_error:
        try:
            current_stat = destination.lstat()
            if created_stat is not None and (current_stat.st_dev, current_stat.st_ino) == (created_stat.st_dev, created_stat.st_ino):
                destination.unlink()
        except FileNotFoundError:
            pass
        except OSError as cleanup_error:
            raise OSError(f"{copy_error}; could not remove partial destination: {cleanup_error}") from copy_error
        raise
    # Keep the completed destination if deleting the source fails.  Callers need
    # to distinguish this state from a failed copy: retrying it would duplicate
    # user data.
    try:
        source.unlink()
    except OSError as exc:
        raise CopyCompletedSourceRetainedError(str(exc)) from exc


def move_planned_file(source, destination, central, category):
    """Move one reviewed file to its exact reviewed destination.

    This intentionally never chooses a replacement name.  The exclusive create
    keeps a late competing writer from being overwritten, while the service can
    report that the reviewed plan is no longer executable.
    """
    source = Path(source)
    destination = Path(destination)
    if source.is_symlink() or not source.is_file():
        raise OSError("Reviewed source is no longer a regular file")
    central = validate_central(central)
    folder = _category_folder(central, category)
    if destination.parent != folder:
        raise ValueError("Reviewed destination is outside its category folder")
    folder.mkdir(parents=True, exist_ok=True)
    _category_folder(central, category)
    try:
        output = destination.open("xb")
    except FileExistsError as exc:
        raise OSError("Reviewed destination is no longer available") from exc
    _copy_and_remove(source, destination, output)


def organize_by_sufix(original_directory, dst_directory, dry_run=False):
    """Return operation details and counts; dry-run performs no filesystem writes."""
    source_directory = validate_source(original_directory)
    central = validate_central(dst_directory)
    if source_directory == central:
        raise ValueError("Source and central library must be different directories")
    categories = _category_map()
    report = {"moved": 0, "planned": 0, "skipped": 0, "errors": 0, "operations": []}
    reserved = set()
    entries = sorted(source_directory.iterdir(), key=lambda entry: (entry.name.casefold(), entry.name))
    for source in entries:
        operation = {"source": str(source), "destination": None, "status": "skipped"}
        try:
            if source.is_symlink() or not source.is_file():
                report["skipped"] += 1
                report["operations"].append(operation)
                continue
            category = categories.get(source.suffix.casefold())
            if category is None:
                report["skipped"] += 1
                report["operations"].append(operation)
                continue
            folder = _category_folder(central, category)
            if source.resolve() == (folder / source.name).resolve():
                report["skipped"] += 1
                report["operations"].append(operation)
                continue
            destination = _available_destination(folder, source.name, reserved)
            operation["destination"] = str(destination)
            if dry_run:
                reserved.add(destination)
                operation["status"] = "planned"
                report["planned"] += 1
            else:
                folder.mkdir(parents=True, exist_ok=True)
                _category_folder(central, category)
                destination, output = _create_destination(folder, source.name, reserved)
                operation["destination"] = str(destination)
                _copy_and_remove(source, destination, output)
                reserved.add(destination)
                operation["status"] = "moved"
                report["moved"] += 1
        except (OSError, ValueError) as exc:
            operation["status"] = "error"
            operation["error"] = str(exc)
            report["errors"] += 1
        report["operations"].append(operation)
    return report

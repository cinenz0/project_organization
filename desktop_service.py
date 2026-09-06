"""Stateful, dependency-free service used by the local desktop interface.

The CLI remains the public command-line entry point.  This module adds the
review/execute boundary needed by a graphical client: a preview records the
identity of every file and its exact destination, and execution refuses to
move anything that was not reviewed.
"""

from copy import deepcopy
import os
from pathlib import Path
import threading
import uuid

from default_paths import paths, save_paths
from organize_by_suffix import (
    CopyCompletedSourceRetainedError,
    _category_map,
    organize_by_sufix,
    move_planned_file,
)
from paths import validate_central, validate_source


def _identity(path):
    """A sufficiently strong local-file identity for a reviewed operation."""
    stat = Path(path).stat(follow_symlinks=False)
    return {
        "size": stat.st_size,
        "mtime_ns": stat.st_mtime_ns,
        "inode": getattr(stat, "st_ino", 0),
        "device": getattr(stat, "st_dev", 0),
    }


def _existing_identity(path):
    path = Path(path)
    if not path.exists() and not path.is_symlink():
        return None
    return _identity(path)


def _known_absent(path):
    """Only a verified absence makes retrying a failed copy safe."""
    try:
        return _existing_identity(path) is None
    except OSError:
        return False


class DesktopService:
    """Keep selection, reviewed preview and last execution result in one lock."""

    def __init__(self, config_file=None):
        self.config_file = config_file
        self._lock = threading.RLock()
        self._source = None
        self._central = None
        self._preview_id = None
        self._preview = []
        self._result = None
        self._error = None
        try:
            source, central = paths(config_file)
            self._source = Path(source) if source is not None else None
            self._central = Path(central) if central is not None else None
        except (OSError, ValueError) as exc:
            # A malformed config must stay visible.  In particular, do not use
            # the default source as a quiet substitute for an invalid config.
            self._error = f"Não foi possível ler a configuração: {exc}"
        self.refresh()

    @staticmethod
    def _folder(value):
        return None if value is None else {"name": Path(value).name or str(value), "path": str(value)}

    def _available_error(self):
        if self._error and self._error.startswith("Não foi possível ler a configuração"):
            return self._error
        if self._source is None:
            return "Selecione a pasta de origem."
        try:
            validate_source(self._source)
        except (OSError, ValueError) as exc:
            return f"A pasta de origem não está disponível: {exc}"
        if self._central is None:
            return "Selecione a biblioteca central."
        try:
            validate_central(self._central)
        except (OSError, ValueError) as exc:
            return f"A biblioteca central não está disponível: {exc}"
        if validate_source(self._source) == validate_central(self._central):
            return "A origem e a biblioteca central devem ser pastas diferentes."
        return None

    def _summary(self, operations):
        return {
            "planned": sum(operation["status"] == "planned" for operation in operations),
            "skipped": sum(operation["status"] == "skipped" for operation in operations),
            "errors": sum(operation["status"] == "failed" for operation in operations),
        }

    def _result_summary(self, operations):
        return {
            "moved": sum(operation["status"] == "moved" for operation in operations),
            "skipped": sum(operation["status"] == "skipped" for operation in operations),
            "errors": sum(operation["status"] in {"failed", "copied_source_retained"} for operation in operations),
            "copied": sum(operation["status"] == "copied_source_retained" for operation in operations),
        }

    def _snapshot(self):
        return {
            "source": self._folder(self._source),
            "central": self._folder(self._central),
            "preview_id": self._preview_id,
            "operations": deepcopy(self._preview),
            "summary": self._summary(self._preview),
            "result": deepcopy(self._result),
            "error": self._error,
        }

    def snapshot(self):
        with self._lock:
            return self._snapshot()

    def refresh(self):
        """Create a new review token.  It does not create folders or move files."""
        with self._lock:
            error = self._available_error()
            self._preview_id = None
            self._preview = []
            # Refresh means the user is back in review mode.  A result cannot
            # safely be retried after a newly selected/reviewed destination.
            self._result = None
            if error:
                self._error = error
                return self._snapshot()
            try:
                report = organize_by_sufix(self._source, self._central, dry_run=True)
                categories = _category_map()
                preview = []
                for item in report["operations"]:
                    source = Path(item["source"])
                    category = categories.get(source.suffix.casefold()) if source.is_file() and not source.is_symlink() else None
                    operation = {
                        "source": str(source),
                        "destination": item["destination"],
                        "name": source.name,
                        "category": category,
                        "size": None,
                        "status": "failed" if item["status"] == "error" else item["status"],
                        "reason": None,
                        "error": item.get("error"),
                    }
                    if operation["status"] == "planned":
                        operation["size"] = _identity(source)["size"]
                        operation["fingerprint"] = _identity(source)
                        operation["destination_fingerprint"] = _existing_identity(item["destination"])
                    elif item["status"] == "skipped":
                        if source.is_symlink():
                            operation["reason"] = "Link simbólico não é organizado."
                        elif not source.is_file():
                            operation["reason"] = "Subpasta não é organizada."
                        elif category is None:
                            operation["reason"] = "Extensão não suportada."
                        else:
                            operation["reason"] = "Arquivo já está na pasta de destino."
                    preview.append(operation)
                self._preview = preview
                self._preview_id = uuid.uuid4().hex
                self._error = None
            except (OSError, ValueError) as exc:
                self._error = f"Não foi possível gerar a prévia: {exc}"
            return self._snapshot()

    def select_folder(self, kind, path):
        with self._lock:
            if kind not in {"source", "central"}:
                raise ValueError("Tipo de pasta inválido")
            if path is None:
                return self._snapshot()
            if kind == "source":
                selected = validate_source(path)
                if self._central is not None and selected == self._central.expanduser().resolve():
                    raise ValueError("A origem e a biblioteca central devem ser pastas diferentes")
                self._source = selected
            else:
                selected = validate_central(path)
                if self._source is not None and selected == self._source.expanduser().resolve():
                    raise ValueError("A origem e a biblioteca central devem ser pastas diferentes")
                # Only an explicit central selection writes configuration.
                save_paths(central=selected, config_file=self.config_file)
                self._central = selected
            self._error = None
            return self.refresh()

    def _review_is_current(self, operations):
        for operation in operations:
            if operation["status"] != "planned":
                continue
            try:
                if _identity(operation["source"]) != operation["fingerprint"]:
                    return False
                if _existing_identity(operation["destination"]) != operation["destination_fingerprint"]:
                    return False
            except OSError:
                return False
        return True

    def execute(self, preview_id):
        with self._lock:
            if not preview_id or preview_id != self._preview_id:
                message = "Esta prévia já foi usada ou expirou. Revise a nova prévia antes de executar."
                self.refresh()
                self._error = message
                return self._snapshot()
            operations = deepcopy(self._preview)
            if not self._review_is_current(operations):
                message = "Os arquivos ou destinos mudaram desde a prévia. Revise a nova prévia antes de executar."
                self.refresh()
                self._error = message
                return self._snapshot()

            # Invalidate before the first write so repeated/concurrent requests
            # cannot run the same reviewed plan twice.
            self._preview_id = None
            for operation in operations:
                if operation["status"] != "planned":
                    continue
                try:
                    # Recheck immediately before each write.  The preflight
                    # catches ordinary stale reviews; this closes the gap while
                    # earlier files in the same reviewed batch are copied.
                    if _identity(operation["source"]) != operation["fingerprint"]:
                        raise OSError("O arquivo de origem mudou após a revisão")
                    if _existing_identity(operation["destination"]) != operation["destination_fingerprint"]:
                        raise OSError("O destino mudou após a revisão")
                    move_planned_file(operation["source"], operation["destination"], self._central, operation["category"])
                    operation["status"] = "moved"
                    operation["copy_completed"] = True
                except CopyCompletedSourceRetainedError as exc:
                    operation.update(status="copied_source_retained", error=str(exc),
                                     retryable=False, copy_completed=True)
                except (OSError, ValueError) as exc:
                    # A retry is safe only when this call did not complete a copy
                    # and no uncertain destination was retained.
                    clean = _known_absent(operation["destination"])
                    operation.update(status="failed", error=str(exc), retryable=clean,
                                     copy_completed=False)
            self._result = {"operations": operations, "summary": self._result_summary(operations)}
            self._preview = []
            self._error = None
            return self._snapshot()

    def retry_failed(self):
        with self._lock:
            if not self._result:
                self._error = "Não há falhas anteriores para tentar novamente."
                return self._snapshot()
            operations = deepcopy(self._result["operations"])
            retryable = [operation for operation in operations if operation.get("retryable") and operation["status"] == "failed"]
            if not retryable:
                self._error = "Não há falhas seguras para tentar novamente."
                return self._snapshot()
            for operation in retryable:
                try:
                    if _identity(operation["source"]) != operation["fingerprint"]:
                        raise OSError("O arquivo de origem mudou desde a execução anterior")
                    if _existing_identity(operation["destination"]) is not None:
                        raise OSError("O destino da falha não está disponível para uma tentativa segura")
                    move_planned_file(operation["source"], operation["destination"], self._central, operation["category"])
                    operation.update(status="moved", error=None, retryable=False, copy_completed=True)
                except CopyCompletedSourceRetainedError as exc:
                    operation.update(status="copied_source_retained", error=str(exc), retryable=False, copy_completed=True)
                except (OSError, ValueError) as exc:
                    operation.update(status="failed", error=str(exc), retryable=False,
                                     copy_completed=False)
            self._result = {"operations": operations, "summary": self._result_summary(operations)}
            self._error = None
            return self._snapshot()

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

from .contracts import FileSnapshot, SourceRecord


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file_handle:
        while True:
            chunk = file_handle.read(1024 * 1024)
            if len(chunk) == 0:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _fingerprint(path: str, mtime_ns: int, content_hash: str) -> str:
    payload = f"{path}|{mtime_ns}|{content_hash}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


@dataclass(frozen=True)
class ScanResult:
    snapshots: list[FileSnapshot]
    errors: list[str]


class IncrementalScanner:
    def scan_source(self, source: SourceRecord) -> ScanResult:
        source_root = Path(source.path)
        if source_root.exists() is False:
            return ScanResult(snapshots=[], errors=["source path not found"])
        if source_root.is_dir() is False:
            return ScanResult(snapshots=[], errors=["source path is not a directory"])

        snapshots: list[FileSnapshot] = []
        errors: list[str] = []
        for file_path in source_root.rglob("*"):
            if file_path.is_file() is False:
                continue
            if _is_ignored_path(source_root, file_path):
                continue
            try:
                stat_result = file_path.stat()
                content_hash = _hash_file(file_path)
                absolute_path = str(file_path.resolve())
                snapshots.append(
                    FileSnapshot(
                        source_id=source.id,
                        source_path=source.path,
                        file_path=absolute_path,
                        mtime_ns=stat_result.st_mtime_ns,
                        content_hash=content_hash,
                        fingerprint=_fingerprint(
                            absolute_path, stat_result.st_mtime_ns, content_hash
                        ),
                    )
                )
            except OSError as exc:
                errors.append(f"{file_path}: {exc}")

        return ScanResult(snapshots=snapshots, errors=errors)


def _is_ignored_path(source_root: Path, file_path: Path) -> bool:
    try:
        relative = file_path.relative_to(source_root)
    except ValueError:
        return False
    return any(part.startswith(".") for part in relative.parts)

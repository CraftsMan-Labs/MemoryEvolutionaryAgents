from __future__ import annotations

from .contracts import (
    SourceCreateRequest,
    SourcePatchRequest,
    SourceRecord,
)
from .database import Database
from .repositories import SourceRepository


class SourceRegistryService:
    def __init__(self, database: Database) -> None:
        self._repository = SourceRepository(database)

    def create_source(self, request: SourceCreateRequest) -> SourceRecord:
        return self._repository.create(request.path)

    def patch_source(self, source_id: int, request: SourcePatchRequest) -> SourceRecord:
        return self._repository.patch(source_id, request.path, request.state)

    def list_sources(self) -> list[SourceRecord]:
        return self._repository.list_all()

    def list_active_sources(self) -> list[SourceRecord]:
        return self._repository.list_active()

    def set_scan_status(
        self,
        source_id: int,
        error: str | None,
        scanned_files: int,
        scan_errors: int,
    ) -> None:
        self._repository.set_scan_status(source_id, error, scanned_files, scan_errors)

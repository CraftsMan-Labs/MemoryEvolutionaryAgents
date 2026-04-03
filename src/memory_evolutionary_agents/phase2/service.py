from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any

from ..contracts import FileRunRecord
from ..run_tracking import RunTrackingService
from .adapters import ObsidianAdapter, QdrantAdapter
from ..phase3.contracts import OntologyEvolutionRequest, OntologyEvolutionResult
from ..phase3.service import OntologyEvolutionService
from ..phase5.contracts import TelemetryEventRequest
from ..phase5.service import TelemetryService
from ..phase6.contracts import FileStage, StageTransitionRequest
from ..phase6.service import FileProgressService
from .contracts import (
    CanonicalMemoryPersistRequest,
    IngestWorkflowInput,
    MemoryChunkPersistRequest,
    ObsidianWriteRequest,
    QdrantPoint,
    QdrantUpsertRequest,
    StageStatus,
    StructuredMemoryResult,
    WorkflowExecutionResult,
    WorkflowStageEventRequest,
)
from .extraction_service import WorkflowExtractionService
from .errors import WorkflowExecutionError
from .persistence import Phase2Repository
from .workflow_runner import SimpleAgentsWorkflowRunner


class Phase2IngestionService:
    def __init__(
        self,
        run_tracking: RunTrackingService,
        repository: Phase2Repository,
        workflow_runner: SimpleAgentsWorkflowRunner,
        extraction_service: WorkflowExtractionService,
        qdrant_adapter: QdrantAdapter,
        obsidian_adapter: ObsidianAdapter,
        ontology_service: OntologyEvolutionService | None = None,
        phase6_progress: FileProgressService | None = None,
        telemetry_service: TelemetryService | None = None,
    ) -> None:
        self._run_tracking = run_tracking
        self._repository = repository
        self._workflow_runner = workflow_runner
        self._extraction_service = extraction_service
        self._qdrant_adapter = qdrant_adapter
        self._obsidian_adapter = obsidian_adapter
        self._ontology_service = ontology_service
        self._phase6_progress = phase6_progress
        self._telemetry_service = telemetry_service

    def execute_for_run(self, run_id: int) -> None:
        file_runs = self._run_tracking.list_file_runs_for_run(run_id)
        for file_run in file_runs:
            if file_run.status != "queued":
                continue
            self._execute_single_file(run_id, file_run)

    def execute_file_run(self, file_run_id: int) -> None:
        file_run = self._run_tracking.get_file_run(file_run_id)
        if file_run.status not in {"queued", "running", "failed"}:
            return
        self._execute_single_file(file_run.run_id, file_run)

    def _execute_single_file(self, run_id: int, file_run: FileRunRecord) -> None:
        correlation_id = f"run-{run_id}-file-{file_run.id}"
        started_at = datetime.now(tz=timezone.utc)
        self._record_telemetry_event(
            TelemetryEventRequest(
                event_type="ingest_run",
                run_id=run_id,
                request_id=None,
                correlation_id=correlation_id,
                stage="workflow_started",
                status="success",
                provider=self._workflow_provider(),
                model_name=self._workflow_model(),
                input_tokens=0,
                output_tokens=0,
                error_classification=None,
                metadata={"file_path": file_run.file_path},
                recorded_at=started_at,
            ),
            span_name="ingest.workflow_started",
        )
        self._repository.record_stage_event(
            WorkflowStageEventRequest(
                run_id=run_id,
                file_run_id=file_run.id,
                source_id=file_run.source_id,
                file_path=file_run.file_path,
                stage="workflow_started",
                status=StageStatus.SUCCESS,
                error_code=None,
                error_message=None,
                recorded_at=started_at,
            )
        )
        if self._phase6_progress is not None:
            self._phase6_progress.transition(
                StageTransitionRequest(
                    run_id=run_id,
                    file_run_id=file_run.id,
                    source_id=file_run.source_id,
                    file_path=file_run.file_path,
                    to_stage=FileStage.WORKFLOW_STARTED,
                    status="running",
                    error_code=None,
                    error_message=None,
                    occurred_at=started_at,
                )
            )

        try:
            file_content = self._read_file(file_run.file_path)
            workflow_input = IngestWorkflowInput(
                run_id=run_id,
                file_run_id=file_run.id,
                source_id=file_run.source_id,
                source_path=file_run.source_path,
                file_path=file_run.file_path,
                file_content=file_content,
                correlation_id=correlation_id,
            )
            result = self._workflow_runner.run_workflow(workflow_input)
            usage = _extract_usage(raw_output=result.raw_output)
            extraction = self._extraction_service.extract(result)
            self._persist_memory_record(workflow_input, extraction)
            self._record_telemetry_event(
                TelemetryEventRequest(
                    event_type="ingest_node",
                    run_id=run_id,
                    request_id=None,
                    correlation_id=correlation_id,
                    stage="workflow_completed",
                    status="success",
                    provider=self._workflow_provider(),
                    model_name=self._workflow_model(),
                    input_tokens=usage.input_tokens,
                    output_tokens=usage.output_tokens,
                    error_classification=None,
                    metadata={"file_path": file_run.file_path},
                    recorded_at=datetime.now(tz=timezone.utc),
                ),
                span_name="ingest.workflow_completed",
            )
            self._repository.record_stage_event(
                WorkflowStageEventRequest(
                    run_id=run_id,
                    file_run_id=file_run.id,
                    source_id=file_run.source_id,
                    file_path=file_run.file_path,
                    stage="workflow_completed",
                    status=StageStatus.SUCCESS,
                    error_code=None,
                    error_message=None,
                    recorded_at=datetime.now(tz=timezone.utc),
                )
            )
            completed_at = datetime.now(tz=timezone.utc)
            if self._phase6_progress is not None:
                self._phase6_progress.transition(
                    StageTransitionRequest(
                        run_id=run_id,
                        file_run_id=file_run.id,
                        source_id=file_run.source_id,
                        file_path=file_run.file_path,
                        to_stage=FileStage.WORKFLOW_COMPLETED,
                        status="success",
                        error_code=None,
                        error_message=None,
                        occurred_at=completed_at,
                    )
                )
                self._phase6_progress.transition(
                    StageTransitionRequest(
                        run_id=run_id,
                        file_run_id=file_run.id,
                        source_id=file_run.source_id,
                        file_path=file_run.file_path,
                        to_stage=FileStage.COMPLETED,
                        status="success",
                        error_code=None,
                        error_message=None,
                        occurred_at=completed_at,
                    )
                )
        except (OSError, WorkflowExecutionError, RuntimeError, ValueError) as exc:
            self._record_telemetry_event(
                TelemetryEventRequest(
                    event_type="ingest_node",
                    run_id=run_id,
                    request_id=None,
                    correlation_id=correlation_id,
                    stage="workflow_failed",
                    status="failed",
                    provider=self._workflow_provider(),
                    model_name=self._workflow_model(),
                    input_tokens=0,
                    output_tokens=0,
                    error_classification=(
                        self._telemetry_service.classify_failure(exc)
                        if self._telemetry_service is not None
                        else "runtime"
                    ),
                    metadata={"file_path": file_run.file_path, "error": str(exc)},
                    recorded_at=datetime.now(tz=timezone.utc),
                ),
                span_name="ingest.workflow_failed",
            )
            self._repository.record_stage_event(
                WorkflowStageEventRequest(
                    run_id=run_id,
                    file_run_id=file_run.id,
                    source_id=file_run.source_id,
                    file_path=file_run.file_path,
                    stage="workflow_failed",
                    status=StageStatus.FAILED,
                    error_code="workflow_execution_failed",
                    error_message=str(exc),
                    recorded_at=datetime.now(tz=timezone.utc),
                )
            )
            if self._phase6_progress is not None:
                failed_at = datetime.now(tz=timezone.utc)
                self._phase6_progress.transition(
                    StageTransitionRequest(
                        run_id=run_id,
                        file_run_id=file_run.id,
                        source_id=file_run.source_id,
                        file_path=file_run.file_path,
                        to_stage=FileStage.FAILED,
                        status="failed",
                        error_code="workflow_execution_failed",
                        error_message=str(exc),
                        occurred_at=failed_at,
                    )
                )
                self._phase6_progress.queue_retry(
                    file_run_id=file_run.id,
                    error_code="workflow_execution_failed",
                    error_message=str(exc),
                )

    def _record_telemetry_event(
        self,
        event: TelemetryEventRequest,
        span_name: str,
    ) -> None:
        if self._telemetry_service is None:
            return
        self._telemetry_service.record_event(
            request=event,
            span_name=span_name,
            span_kind="node",
            allow_missing_pricing=True,
        )

    def _workflow_provider(self) -> str:
        provider = getattr(self._workflow_runner, "provider", "workflow")
        if isinstance(provider, str) and len(provider.strip()) > 0:
            return provider
        return "workflow"

    def _workflow_model(self) -> str:
        model = getattr(self._workflow_runner, "model", "default")
        if isinstance(model, str) and len(model.strip()) > 0:
            return model
        return "default"

    def _read_file(self, file_path: str) -> str:
        with open(file_path, "r", encoding="utf-8") as file_handle:
            return file_handle.read()

    def _persist_memory_record(
        self, request: IngestWorkflowInput, extraction: StructuredMemoryResult
    ) -> None:
        content_hash = hashlib.sha256(request.file_content.encode("utf-8")).hexdigest()
        ontology_result = self._evolve_ontology(request, extraction, content_hash)
        qdrant_point_ids = self._upsert_qdrant_points(
            request, extraction, ontology_result
        )
        obsidian_note_path = self._write_obsidian_summary(request, extraction)
        persist_result = self._repository.persist_memory(
            CanonicalMemoryPersistRequest(
                source_id=request.source_id,
                source_path=request.source_path,
                file_path=request.file_path,
                content_hash=content_hash,
                project=extraction.project,
                problem=extraction.problem,
                solution=extraction.solution,
                event_date=extraction.date,
                extraction_confidence=extraction.confidence,
                tags=extraction.tags,
                entities=extraction.entities,
                obsidian_note_path=obsidian_note_path,
                qdrant_point_ids=qdrant_point_ids,
                ontology_terms=ontology_result.ontology_terms,
                taxonomy_tags=ontology_result.taxonomy_tags,
                relation_edges=[
                    {
                        "source": edge.source,
                        "predicate": edge.predicate,
                        "target": edge.target,
                        "status": edge.status.value,
                    }
                    for edge in ontology_result.relation_edges
                ],
            )
        )
        for index, chunk in enumerate(extraction.chunks):
            vector_size = 0
            if index < len(extraction.embeddings):
                vector_size = len(extraction.embeddings[index].vector)
            self._repository.persist_chunk(
                MemoryChunkPersistRequest(
                    memory_id=persist_result.memory_id,
                    chunk_id=chunk.chunk_id,
                    chunk_index=chunk.chunk_index,
                    chunk_text=chunk.text,
                    start_offset=chunk.start_offset,
                    end_offset=chunk.end_offset,
                    vector_size=vector_size,
                )
            )

    def _upsert_qdrant_points(
        self,
        request: IngestWorkflowInput,
        extraction: StructuredMemoryResult,
        ontology_result: OntologyEvolutionResult,
    ) -> list[str]:
        chunk_by_id = {chunk.chunk_id: chunk for chunk in extraction.chunks}
        points: list[QdrantPoint] = []
        for embedding in extraction.embeddings:
            chunk = chunk_by_id.get(embedding.chunk_id)
            points.append(
                QdrantPoint(
                    point_id=embedding.chunk_id,
                    vector=embedding.vector,
                    payload={
                        "chunk_id": embedding.chunk_id,
                        "text": chunk.text if chunk is not None else "",
                        "source_id": request.source_id,
                        "source_path": request.source_path,
                        "file_path": request.file_path,
                        "project": extraction.project,
                        "event_date": extraction.date,
                        "tags": extraction.tags,
                        "entities": extraction.entities,
                        "obsidian_note_path": extraction.obsidian_note_path,
                        "ontology_terms": ontology_result.ontology_terms,
                        "taxonomy_tags": ontology_result.taxonomy_tags,
                        "relation_edges": [
                            {
                                "source": edge.source,
                                "predicate": edge.predicate,
                                "target": edge.target,
                                "status": edge.status.value,
                            }
                            for edge in ontology_result.relation_edges
                        ],
                    },
                )
            )
        if len(points) == 0:
            return extraction.qdrant_point_ids
        upsert_response = self._qdrant_adapter.upsert(
            QdrantUpsertRequest(points=points)
        )
        return upsert_response.stored_point_ids

    def _write_obsidian_summary(
        self, request: IngestWorkflowInput, extraction: StructuredMemoryResult
    ) -> str | None:
        if (
            extraction.project is None
            and extraction.problem is None
            and extraction.solution is None
        ):
            return extraction.obsidian_note_path
        title = extraction.project or "Memory Summary"
        body = f"Problem: {extraction.problem or 'n/a'}\nSolution: {extraction.solution or 'n/a'}"
        write_response = self._obsidian_adapter.write_summary(
            ObsidianWriteRequest(
                source_path=request.source_path,
                file_path=request.file_path,
                title=title,
                body=body,
            )
        )
        return write_response.note_path

    def _evolve_ontology(
        self,
        request: IngestWorkflowInput,
        extraction: StructuredMemoryResult,
        content_hash: str,
    ) -> OntologyEvolutionResult:
        if self._ontology_service is None:
            return OntologyEvolutionResult(
                ontology_terms=extraction.entities,
                taxonomy_tags=extraction.tags,
                relation_edges=[],
                proposal_ids=[],
            )
        return self._ontology_service.evolve(
            OntologyEvolutionRequest(
                source_id=request.source_id,
                source_path=request.source_path,
                file_path=request.file_path,
                content_hash=content_hash,
                project=extraction.project,
                tags=extraction.tags,
                entities=extraction.entities,
                actor="worker",
            )
        )


class _UsageSummary:
    def __init__(self, input_tokens: int, output_tokens: int) -> None:
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens


def _extract_usage(raw_output: dict[str, object]) -> _UsageSummary:
    usage = raw_output.get("usage")
    if isinstance(usage, dict):
        return _extract_usage_from_dict(usage)
    for value in raw_output.values():
        if isinstance(value, dict) and "usage" in value:
            nested_usage = value.get("usage")
            if isinstance(nested_usage, dict):
                return _extract_usage_from_dict(nested_usage)
    return _UsageSummary(input_tokens=0, output_tokens=0)


def _extract_usage_from_dict(usage: dict[str, Any]) -> _UsageSummary:
    input_tokens = _to_non_negative_int(
        usage.get("input_tokens", usage.get("prompt_tokens", 0))
    )
    output_tokens = _to_non_negative_int(
        usage.get("output_tokens", usage.get("completion_tokens", 0))
    )
    return _UsageSummary(input_tokens=input_tokens, output_tokens=output_tokens)


def _to_non_negative_int(value: object) -> int:
    if isinstance(value, bool):
        return 0
    if isinstance(value, int):
        return max(0, value)
    if isinstance(value, float):
        return max(0, int(value))
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return 0

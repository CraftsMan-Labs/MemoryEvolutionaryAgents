from __future__ import annotations

import asyncio
from datetime import datetime

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse

from .container import AppContainer, build_container
from .contracts import (
    ConnectorTestRequest,
    ConnectorTestResponse,
    OnboardingConfigureRequest,
    OnboardingConfigureResponse,
    OnboardingStatusResponse,
    SourceCreateRequest,
    SourcePatchRequest,
    SourceRecord,
)
from .phase3.contracts import (
    ProposalDecisionRequest,
    ProposalDetailResponse,
    ProposalListResponse,
    ProposalMergeRequest,
    ProposalStatus,
    ProposalType,
    SchemaProposalRecord,
)
from .phase3.errors import InvalidProposalTransitionError, ProposalNotFoundError
from .phase4.contracts import ChatQueryRequest, ChatQueryResponse
from .phase4.errors import Phase4ValidationError
from .phase5.contracts import (
    ConnectorHealthResponse,
    FreshnessStatusResponse,
    JobHealthResponse,
    UsageMetricsResponse,
)
from .phase5.errors import MissingPricingError
from .phase6.contracts import (
    FileStage,
    FileRetryRequest,
    FileTimelineResponse,
    RetryScheduleResult,
    RunFilesQuery,
    RunFilesResponse,
)
from .phase6.errors import FileRunNotFoundError, RetryNotAllowedError


def create_app() -> FastAPI:
    container = build_container()
    app = FastAPI(title="Memory Evolutionary Agents API", version="0.1.0")

    def get_container() -> AppContainer:
        return container

    @app.middleware("http")
    async def onboarding_gate(request: Request, call_next):
        exempt_paths = {
            "/status/health",
            "/onboarding/status",
            "/onboarding/configure",
            "/onboarding/test-connector",
            "/docs",
            "/openapi.json",
            "/redoc",
        }
        if request.url.path in exempt_paths:
            return await call_next(request)
        if container.onboarding.is_completed() is False:
            payload = {
                "detail": "onboarding is required before accessing this route",
                "next": "complete /onboarding/configure",
            }
            return JSONResponse(status_code=423, content=payload)
        return await call_next(request)

    @app.get("/status/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/onboarding/status", response_model=OnboardingStatusResponse)
    def onboarding_status(
        dep_container: AppContainer = Depends(get_container),
    ) -> OnboardingStatusResponse:
        return dep_container.onboarding.get_status()

    @app.post("/onboarding/test-connector", response_model=ConnectorTestResponse)
    def onboarding_test_connector(
        request: ConnectorTestRequest,
        dep_container: AppContainer = Depends(get_container),
    ) -> ConnectorTestResponse:
        return dep_container.onboarding.test_connector(request)

    @app.post("/onboarding/configure", response_model=OnboardingConfigureResponse)
    def onboarding_configure(
        request: OnboardingConfigureRequest,
        dep_container: AppContainer = Depends(get_container),
    ) -> OnboardingConfigureResponse:
        try:
            return dep_container.onboarding.configure(request)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.get("/sources", response_model=list[SourceRecord])
    def list_sources(
        dep_container: AppContainer = Depends(get_container),
    ) -> list[SourceRecord]:
        return dep_container.source_registry.list_sources()

    @app.post("/sources", response_model=SourceRecord)
    def create_source(
        request: SourceCreateRequest,
        dep_container: AppContainer = Depends(get_container),
    ) -> SourceRecord:
        try:
            return dep_container.source_registry.create_source(request)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.patch("/sources/{source_id}", response_model=SourceRecord)
    def patch_source(
        source_id: int,
        request: SourcePatchRequest,
        dep_container: AppContainer = Depends(get_container),
    ) -> SourceRecord:
        try:
            return dep_container.source_registry.patch_source(source_id, request)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.get("/status/jobs", response_model=JobHealthResponse)
    def list_jobs(
        dep_container: AppContainer = Depends(get_container),
    ) -> JobHealthResponse:
        if dep_container.phase5_status is None:
            runs = dep_container.run_tracking.list_runs(limit=50)
            latest = runs[0] if len(runs) > 0 else None
            running_runs = len([run for run in runs if run.status == "running"])
            failed_runs = len([run for run in runs if run.status == "failed"])
            return JobHealthResponse(
                total_runs=len(runs),
                running_runs=running_runs,
                failed_runs=failed_runs,
                latest_run_id=None if latest is None else latest.id,
                latest_run_status=None if latest is None else latest.status,
            )
        return dep_container.phase5_status.job_health()

    @app.get("/status/connectors", response_model=ConnectorHealthResponse)
    def connector_health(
        dep_container: AppContainer = Depends(get_container),
    ) -> ConnectorHealthResponse:
        if dep_container.phase5_status is None:
            raise HTTPException(
                status_code=404, detail="phase5 status service is disabled"
            )
        return dep_container.phase5_status.connector_health()

    @app.get("/status/freshness", response_model=FreshnessStatusResponse)
    def freshness_status(
        dep_container: AppContainer = Depends(get_container),
    ) -> FreshnessStatusResponse:
        if dep_container.phase5_status is None:
            raise HTTPException(
                status_code=404, detail="phase5 status service is disabled"
            )
        return dep_container.phase5_status.freshness()

    @app.get("/metrics/usage", response_model=UsageMetricsResponse)
    def usage_metrics(
        days: int = 7,
        dep_container: AppContainer = Depends(get_container),
    ) -> UsageMetricsResponse:
        if dep_container.phase5_status is None:
            raise HTTPException(
                status_code=404, detail="phase5 status service is disabled"
            )
        if days < 1 or days > 90:
            raise HTTPException(status_code=400, detail="days must be between 1 and 90")
        return dep_container.phase5_status.usage_metrics(range_days=days)

    @app.post("/jobs/scan")
    def trigger_scan(
        dep_container: AppContainer = Depends(get_container),
    ) -> dict[str, object]:
        try:
            cycle = dep_container.scheduler.run_cycle()
            if dep_container.phase2_ingestion is not None:
                dep_container.phase2_ingestion.execute_for_run(cycle.run.id)
            return {
                "run": cycle.run.model_dump(),
                "discovered_count": cycle.discovered_count,
                "queued_count": cycle.queued_count,
                "failed_count": cycle.failed_count,
            }
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.get("/runs/{run_id}/files", response_model=RunFilesResponse)
    def list_run_files(
        run_id: int,
        source_id: int | None = None,
        stage: FileStage | None = None,
        status: str | None = None,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
        limit: int = 200,
        dep_container: AppContainer = Depends(get_container),
    ) -> RunFilesResponse:
        try:
            query = RunFilesQuery(
                source_id=source_id,
                stage=stage,
                status=status,
                from_date=from_date,
                to_date=to_date,
                limit=limit,
            )
            return dep_container.phase6_progress.list_run_files(
                run_id=run_id, query=query
            )
        except Exception as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.get("/files/{file_id}/timeline", response_model=FileTimelineResponse)
    def file_timeline(
        file_id: int,
        dep_container: AppContainer = Depends(get_container),
    ) -> FileTimelineResponse:
        try:
            return dep_container.phase6_progress.timeline(file_run_id=file_id)
        except FileRunNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.post("/files/{file_id}/retry", response_model=RetryScheduleResult)
    def retry_file(
        file_id: int,
        request: FileRetryRequest,
        dep_container: AppContainer = Depends(get_container),
    ) -> RetryScheduleResult:
        try:
            return dep_container.phase6_progress.manual_retry(file_id, request)
        except FileRunNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except RetryNotAllowedError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.get("/status/dead-letter", response_model=list[RetryScheduleResult])
    def dead_letter(
        limit: int = 100,
        dep_container: AppContainer = Depends(get_container),
    ) -> list[RetryScheduleResult]:
        items = dep_container.phase6_progress.dead_letter_items(limit)
        return [
            RetryScheduleResult(
                file_run_id=item.file_run_id,
                attempt_count=item.attempt_count,
                next_attempt_at=item.next_attempt_at,
                status=item.status,
            )
            for item in items
        ]

    @app.get("/runs/{run_id}/stream")
    async def run_progress_stream(
        run_id: int,
        dep_container: AppContainer = Depends(get_container),
    ) -> StreamingResponse:
        queue = dep_container.phase6_progress.subscribe(run_id)

        async def _generator():
            try:
                while True:
                    try:
                        payload = await asyncio.wait_for(queue.get(), timeout=10)
                        yield f"event: progress\ndata: {payload}\n\n"
                    except asyncio.TimeoutError:
                        yield "event: heartbeat\ndata: {}\n\n"
            finally:
                dep_container.phase6_progress.unsubscribe(run_id, queue)

        return StreamingResponse(_generator(), media_type="text/event-stream")

    @app.get("/ontology/proposals", response_model=ProposalListResponse)
    def list_ontology_proposals(
        status: ProposalStatus | None = None,
        proposal_type: ProposalType | None = None,
        limit: int = 50,
        dep_container: AppContainer = Depends(get_container),
    ) -> ProposalListResponse:
        if dep_container.phase3_ontology is None:
            raise HTTPException(
                status_code=404, detail="phase3 ontology service is disabled"
            )
        proposals = dep_container.phase3_ontology.list_proposals(
            status=status,
            proposal_type=proposal_type,
            limit=limit,
        )
        return ProposalListResponse(proposals=proposals)

    @app.get(
        "/ontology/proposals/{proposal_id}",
        response_model=ProposalDetailResponse,
    )
    def get_ontology_proposal(
        proposal_id: int,
        dep_container: AppContainer = Depends(get_container),
    ) -> ProposalDetailResponse:
        if dep_container.phase3_ontology is None:
            raise HTTPException(
                status_code=404, detail="phase3 ontology service is disabled"
            )
        try:
            return dep_container.phase3_ontology.get_proposal_detail(proposal_id)
        except ProposalNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.post(
        "/ontology/proposals/{proposal_id}/approve",
        response_model=SchemaProposalRecord,
    )
    def approve_ontology_proposal(
        proposal_id: int,
        request: ProposalDecisionRequest,
        dep_container: AppContainer = Depends(get_container),
    ) -> SchemaProposalRecord:
        if dep_container.phase3_ontology is None:
            raise HTTPException(
                status_code=404, detail="phase3 ontology service is disabled"
            )
        try:
            return dep_container.phase3_ontology.approve_proposal(
                proposal_id=proposal_id,
                actor=request.actor,
                note=request.note,
            )
        except ProposalNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except InvalidProposalTransitionError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post(
        "/ontology/proposals/{proposal_id}/reject",
        response_model=SchemaProposalRecord,
    )
    def reject_ontology_proposal(
        proposal_id: int,
        request: ProposalDecisionRequest,
        dep_container: AppContainer = Depends(get_container),
    ) -> SchemaProposalRecord:
        if dep_container.phase3_ontology is None:
            raise HTTPException(
                status_code=404, detail="phase3 ontology service is disabled"
            )
        try:
            return dep_container.phase3_ontology.reject_proposal(
                proposal_id=proposal_id,
                actor=request.actor,
                note=request.note,
            )
        except ProposalNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except InvalidProposalTransitionError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post(
        "/ontology/proposals/{proposal_id}/merge",
        response_model=SchemaProposalRecord,
    )
    def merge_ontology_proposal(
        proposal_id: int,
        request: ProposalMergeRequest,
        dep_container: AppContainer = Depends(get_container),
    ) -> SchemaProposalRecord:
        if dep_container.phase3_ontology is None:
            raise HTTPException(
                status_code=404, detail="phase3 ontology service is disabled"
            )
        try:
            return dep_container.phase3_ontology.merge_proposal(
                proposal_id=proposal_id,
                target_record_id=request.target_record_id,
                actor=request.actor,
                note=request.note,
            )
        except ProposalNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except InvalidProposalTransitionError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/chat/query", response_model=ChatQueryResponse)
    def query_chat(
        request: ChatQueryRequest,
        dep_container: AppContainer = Depends(get_container),
    ) -> ChatQueryResponse:
        if dep_container.phase4_chat is None:
            raise HTTPException(
                status_code=404, detail="phase4 chat service is disabled"
            )
        try:
            return dep_container.phase4_chat.query(request)
        except Phase4ValidationError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except MissingPricingError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    return app

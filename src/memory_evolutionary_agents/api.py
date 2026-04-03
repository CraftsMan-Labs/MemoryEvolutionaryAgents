from __future__ import annotations

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from .container import AppContainer, build_container
from .contracts import (
    ConnectorTestRequest,
    ConnectorTestResponse,
    OnboardingConfigureRequest,
    OnboardingConfigureResponse,
    OnboardingStatusResponse,
    RunSummaryResponse,
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

    @app.get("/status/jobs")
    def list_jobs(
        dep_container: AppContainer = Depends(get_container),
    ) -> dict[str, object]:
        runs = dep_container.run_tracking.list_runs(limit=50)
        return {"runs": [run.model_dump() for run in runs]}

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

    @app.get("/runs/{run_id}/files", response_model=RunSummaryResponse)
    def list_run_files(
        run_id: int, dep_container: AppContainer = Depends(get_container)
    ) -> RunSummaryResponse:
        try:
            return RunSummaryResponse(
                run=dep_container.run_tracking.get_run(run_id),
                files=dep_container.run_tracking.list_file_runs_for_run(run_id),
            )
        except Exception as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

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

    return app

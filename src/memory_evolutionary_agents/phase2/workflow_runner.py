from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from pathlib import Path
from typing import cast

from .contracts import IngestWorkflowInput, WorkflowExecutionResult, WorkflowStatus
from .errors import Phase2ConfigurationError, WorkflowExecutionError


class SimpleAgentsWorkflowRunner:
    def __init__(
        self,
        workflow_path: str,
        provider: str,
        model: str,
        api_base: str | None,
        api_key: str | None,
        stage_timeout_seconds: int,
    ) -> None:
        self._workflow_path = workflow_path
        self._provider = provider
        self._model = model
        self._api_base = api_base
        self._api_key = api_key
        self._stage_timeout_seconds = stage_timeout_seconds

    def run_workflow(self, request: IngestWorkflowInput) -> WorkflowExecutionResult:
        workflow_file = Path(self._workflow_path)
        if workflow_file.exists() is False:
            raise Phase2ConfigurationError(
                f"phase2 workflow file not found: {workflow_file}"
            )
        if self._api_key is None or len(self._api_key.strip()) == 0:
            raise Phase2ConfigurationError("MEA_WORKFLOW_API_KEY is required")

        try:
            from simple_agents_py import Client
        except ImportError as exc:
            raise Phase2ConfigurationError(
                "simple-agents-py is required for phase2 workflow execution"
            ) from exc

        client = Client(self._provider, api_base=self._api_base, api_key=self._api_key)
        payload = {
            "run_id": request.run_id,
            "file_run_id": request.file_run_id,
            "source_id": request.source_id,
            "source_path": request.source_path,
            "file_path": request.file_path,
            "file_content": request.file_content,
            "correlation_id": request.correlation_id,
            "workflow_model": self._model,
        }
        try:
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(
                    client.run_workflow_yaml, str(workflow_file), payload
                )
                raw_output = future.result(timeout=self._stage_timeout_seconds)
        except FutureTimeoutError as exc:
            raise WorkflowExecutionError(
                f"workflow execution timed out after {self._stage_timeout_seconds}s"
            ) from exc
        except RuntimeError as exc:
            raise WorkflowExecutionError(f"workflow execution failed: {exc}") from exc

        if isinstance(raw_output, dict) is False:
            raise WorkflowExecutionError("workflow execution returned non-dict output")
        return WorkflowExecutionResult(
            status=WorkflowStatus.SUCCESS,
            raw_output=cast(dict[str, object], raw_output),
        )

    @property
    def provider(self) -> str:
        return self._provider

    @property
    def model(self) -> str:
        return self._model

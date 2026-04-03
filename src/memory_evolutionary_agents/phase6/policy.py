from __future__ import annotations

from .contracts import FileStage
from .errors import InvalidStageTransitionError


class StageTransitionPolicyService:
    _allowed: dict[FileStage, set[FileStage]] = {
        FileStage.DISCOVERED: {
            FileStage.WORKFLOW_STARTED,
            FileStage.RETRY_QUEUED,
            FileStage.FAILED,
            FileStage.POISONED,
        },
        FileStage.WORKFLOW_STARTED: {
            FileStage.WORKFLOW_COMPLETED,
            FileStage.FAILED,
            FileStage.RETRY_QUEUED,
        },
        FileStage.WORKFLOW_COMPLETED: {
            FileStage.COMPLETED,
            FileStage.FAILED,
            FileStage.RETRY_QUEUED,
        },
        FileStage.FAILED: {
            FileStage.RETRY_QUEUED,
            FileStage.POISONED,
        },
        FileStage.RETRY_QUEUED: {FileStage.RETRYING, FileStage.POISONED},
        FileStage.RETRYING: {
            FileStage.WORKFLOW_STARTED,
            FileStage.FAILED,
            FileStage.POISONED,
        },
        FileStage.POISONED: set(),
        FileStage.COMPLETED: set(),
    }

    def assert_transition(
        self,
        from_stage: FileStage | None,
        to_stage: FileStage,
    ) -> None:
        if from_stage is None:
            if to_stage not in {FileStage.DISCOVERED, FileStage.WORKFLOW_STARTED}:
                raise InvalidStageTransitionError(
                    f"first transition must be discovered/workflow_started, got {to_stage.value}"
                )
            return
        if from_stage == to_stage:
            return
        allowed_next = self._allowed[from_stage]
        if to_stage not in allowed_next:
            raise InvalidStageTransitionError(
                f"illegal stage transition: {from_stage.value} -> {to_stage.value}"
            )

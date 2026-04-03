from __future__ import annotations

from ..run_tracking import RunTrackingService
from .persistence import Phase6Repository
from .policy import StageTransitionPolicyService
from .service import FileProgressService, ProgressEventPublisher, RetryBackoffConfig
from ..database import Database


def build_phase6_service(
    database: Database, run_tracking: RunTrackingService
) -> FileProgressService:
    return FileProgressService(
        run_tracking=run_tracking,
        repository=Phase6Repository(database),
        transition_policy=StageTransitionPolicyService(),
        retry_config=RetryBackoffConfig(),
        publisher=ProgressEventPublisher(),
    )

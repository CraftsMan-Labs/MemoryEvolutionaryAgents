from __future__ import annotations


class Phase2Error(RuntimeError):
    pass


class Phase2ConfigurationError(Phase2Error):
    pass


class WorkflowExecutionError(Phase2Error):
    pass


class AdapterError(Phase2Error):
    pass

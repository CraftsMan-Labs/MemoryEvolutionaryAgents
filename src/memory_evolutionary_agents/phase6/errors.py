from __future__ import annotations


class Phase6Error(Exception):
    pass


class InvalidStageTransitionError(Phase6Error):
    pass


class FileRunNotFoundError(Phase6Error):
    pass


class RetryNotAllowedError(Phase6Error):
    pass

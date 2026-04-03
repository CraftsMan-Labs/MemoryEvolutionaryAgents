from __future__ import annotations


class Phase3Error(RuntimeError):
    pass


class ProposalNotFoundError(Phase3Error):
    pass


class InvalidProposalTransitionError(Phase3Error):
    pass

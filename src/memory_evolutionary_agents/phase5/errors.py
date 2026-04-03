from __future__ import annotations


class Phase5Error(Exception):
    pass


class MissingPricingError(Phase5Error):
    pass


class TelemetryAdapterError(Phase5Error):
    pass

from __future__ import annotations

import time

from .container import build_container


def run_once() -> None:
    container = build_container()
    if container.onboarding.is_completed() is False:
        return
    cycle = container.scheduler.run_cycle()
    if container.phase2_ingestion is not None:
        container.phase2_ingestion.execute_for_run(cycle.run.id)


def run_forever() -> None:
    container = build_container()
    while True:
        if container.onboarding.is_completed() is False:
            time.sleep(container.settings.scan_interval_seconds)
            continue
        cycle = container.scheduler.run_cycle()
        if container.phase2_ingestion is not None:
            container.phase2_ingestion.execute_for_run(cycle.run.id)
        time.sleep(container.settings.scan_interval_seconds)


if __name__ == "__main__":
    run_forever()

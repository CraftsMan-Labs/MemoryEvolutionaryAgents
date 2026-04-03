# Q1 Platform Stabilization

We saw elevated memory ingestion latency during the weekly batch.
The issue was caused by oversized chunks and missing retries in one worker lane.
We fixed this by lowering chunk size and adding bounded retry handling.
Rollout date: 2026-04-03.

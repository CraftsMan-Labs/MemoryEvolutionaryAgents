# Phase 0.1 TODO - First-Run Onboarding Gate

## Objective
Create a first-run onboarding flow that captures data residency choices, validates connectors, and blocks ingestion/chat until setup is complete.

## Implementation Status
- Completed for v1 baseline with onboarding persistence, connector validation, API/worker gates, and a first-run dashboard wizard.

## Required Guardrail
- Follow `plan/CODING_GUARDRAILS.md` for all implementation decisions.

## Detailed Tasks

### A. Data Model and Persistence
- [x] Create `onboarding_state` table with explicit state fields and completion timestamp.
- [x] Create connector settings table entries for Obsidian and Qdrant modes.
- [x] Add encrypted secret storage path for external Qdrant API key.
- [x] Add repository classes with typed input/output models for onboarding persistence.

### B. Validation Services
- [x] Implement `VaultPathValidator` with explicit request/response models.
- [x] Implement `QdrantLocalHealthValidator` for local Docker mode.
- [x] Implement `QdrantExternalValidator` for URL/API key auth test.
- [x] Implement `OnboardingService` orchestration class to coordinate validators and persistence.

### C. API Endpoints
- [x] Implement `GET /onboarding/status` with explicit response contract.
- [x] Implement `POST /onboarding/configure` with explicit request contract.
- [x] Implement connector test endpoint used by onboarding UI.
- [x] Ensure onboarding endpoints never return raw secrets.

### D. UI Wizard
- [x] Build onboarding wizard step for Obsidian vault path.
- [x] Build onboarding wizard step for Qdrant mode selection (`local_docker` or `external`).
- [x] Build external Qdrant credential step with validation feedback.
- [x] Add route guard that blocks app pages until onboarding is complete.

### E. Runtime Gate
- [x] Add API middleware to enforce onboarding completion for protected routes.
- [x] Add worker startup gate to skip ingestion until onboarding state is complete.
- [x] Add clear user-facing status messages for blocked state.

### F. Tests
- [x] Unit tests for all validator classes (success/failure).
- [x] API tests for onboarding status/configure endpoints.
- [x] Integration tests for route gate and worker gate behavior.

## Acceptance Criteria
- [x] User cannot run ingestion/chat before onboarding completion.
- [x] Obsidian path is validated for existence and readability.
- [x] Qdrant mode validates correctly for both local and external options.
- [x] External API keys are encrypted and never returned in plain text.

## Deliverables
- [x] onboarding API + UI wizard
- [x] onboarding gate in API and worker
- [x] validation services and tests

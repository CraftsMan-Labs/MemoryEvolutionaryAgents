# Coding Guardrails

This file is mandatory for all implementation phases.

## Core Rules
- Use object-oriented design with single-purpose classes/services.
- Keep code KISS: simple control flow, minimal moving parts, readable naming.
- Keep code DRY: extract shared logic instead of repeating behavior.
- Keep code concise and human-debuggable; avoid clever or opaque abstractions.
- Eliminate code smells early (god classes, long methods, hidden side effects, duplicated conditionals).

## Tooling Standards
- Python environment and dependency management must use `uv`.
- Vue/TypeScript package management and scripts must use `bun`.
- Do not mix package managers in the same surface (no `pip`/`npm` fallback in normal workflows).

## Function and Method Contracts
- Every function/method must define explicit inputs and outputs.
- Use typed request/response models (Pydantic/dataclass/DTO) at boundaries.
- No ambiguous "anything in, anything out" helper signatures.
- Prefer returning explicit result objects over unstructured dictionaries.
- Keep nullability explicit and separate from emptiness checks.

## Structure Guidelines
- Domain logic stays separate from transport layers (API, CLI, job wiring).
- Keep modules small and responsibility-driven.
- Repositories handle persistence only.
- Services coordinate business logic only.
- Adapters handle external systems (Qdrant, Obsidian, Langfuse) only.

## Python Guidelines
- Prefer Python 3 type hints everywhere (function params, returns, class attributes).
- Keep function signatures explicit; avoid ambiguous `*args/**kwargs` except framework boundaries.
- Use Pydantic/dataclass DTOs for boundary contracts instead of raw dictionaries.
- One class, one responsibility: split orchestration (`Service`) from I/O (`Repository`/`Adapter`).
- Keep methods short and linear; extract helpers when branching grows.
- Never use bare `except`; catch specific exceptions and rethrow typed domain errors.
- Avoid truthy/falsy ambiguity in typed paths (`is None` / `is not None` for null checks).
- Keep async code non-blocking; do not mix blocking I/O into async paths.
- Prefer dependency injection through constructors for testability and clear ownership.
- Use clear, actionable logging with correlation IDs and no secret leakage.

## Vue Guidelines
- Use Vue 3 Composition API with `script setup` and TypeScript for typed props/emits.
- Keep components single-purpose: container components orchestrate, presentational components render.
- Keep templates simple; move non-trivial logic into composables/services.
- Use explicit prop and emit contracts; avoid untyped event payloads.
- Keep API and storage access in composables/adapters, not directly in UI components.
- Use `computed` for derived state and `watch` only for necessary side effects.
- Avoid duplicated UI logic; extract shared behavior into composables.
- Keep state transitions explicit (`idle`, `loading`, `success`, `error`) for debuggability.
- Always handle empty, loading, and error states in the UI.
- Keep components concise and readable; avoid deep nesting and long files.

## Quality Gates (Per PR/Phase)
- [ ] No duplicated business logic across modules.
- [ ] Every new class has one clear responsibility.
- [ ] Every new function has typed input/output.
- [ ] Success and failure tests exist for new behavior.
- [ ] Error messages are actionable and typed.
- [ ] Lint/format/tests pass for touched components.
- [ ] Python code uses explicit typing and DTO contracts at boundaries.
- [ ] Vue components/composables use explicit prop/emit/input/output contracts.

## Suggested Patterns
- `RequestModel -> Service -> ResponseModel`
- `Repository` interfaces for storage operations.
- `Adapter` interfaces for external connectors.
- `UseCase` classes for phase-level orchestration.

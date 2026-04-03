from __future__ import annotations

import urllib.request
from pathlib import Path

from .contracts import (
    ConnectorConfigRecord,
    ConnectorTestRequest,
    ConnectorTestResponse,
    OnboardingConfigureRequest,
    OnboardingConfigureResponse,
    OnboardingStatusResponse,
    QdrantMode,
    ValidationResult,
)
from .database import Database
from .repositories import OnboardingRepository
from .security import SecretCipher


class VaultPathValidator:
    def validate(self, vault_path: str) -> ValidationResult:
        path = Path(vault_path).expanduser()
        if path.exists() is False:
            return ValidationResult(
                is_valid=False, message="obsidian vault path does not exist"
            )
        if path.is_dir() is False:
            return ValidationResult(
                is_valid=False, message="obsidian vault path must be a directory"
            )
        if path.stat().st_mode == 0:
            return ValidationResult(
                is_valid=False, message="obsidian vault path is not readable"
            )
        return ValidationResult(is_valid=True, message="vault path validated")


class QdrantLocalHealthValidator:
    def validate(self, health_url: str) -> ValidationResult:
        try:
            with urllib.request.urlopen(health_url, timeout=3) as response:
                status_code = getattr(response, "status", 0)
            if status_code == 200:
                return ValidationResult(
                    is_valid=True, message="local qdrant is healthy"
                )
            return ValidationResult(
                is_valid=False, message="local qdrant health check failed"
            )
        except Exception as exc:
            return ValidationResult(
                is_valid=False, message=f"local qdrant unreachable: {exc}"
            )


class QdrantExternalValidator:
    def validate(self, url: str | None, api_key: str | None) -> ValidationResult:
        if url is None or api_key is None:
            return ValidationResult(
                is_valid=False,
                message="external qdrant requires url and api key",
            )
        request = urllib.request.Request(
            url=f"{url.rstrip('/')}/collections",
            headers={"api-key": api_key},
            method="GET",
        )
        try:
            with urllib.request.urlopen(request, timeout=5) as response:
                status_code = getattr(response, "status", 0)
            if status_code == 200:
                return ValidationResult(
                    is_valid=True, message="external qdrant validated"
                )
            return ValidationResult(
                is_valid=False, message="external qdrant validation failed"
            )
        except Exception as exc:
            return ValidationResult(
                is_valid=False, message=f"external qdrant validation error: {exc}"
            )


class OnboardingService:
    def __init__(
        self,
        database: Database,
        cipher: SecretCipher,
        local_qdrant_url: str,
    ) -> None:
        self._repository = OnboardingRepository(database)
        self._cipher = cipher
        self._vault_validator = VaultPathValidator()
        self._local_qdrant_validator = QdrantLocalHealthValidator()
        self._external_qdrant_validator = QdrantExternalValidator()
        self._local_qdrant_health_url = f"{local_qdrant_url.rstrip('/')}/healthz"

    def get_status(self) -> OnboardingStatusResponse:
        state = self._repository.get_state()
        connector = self._repository.get_connector_config()
        if state.is_completed:
            return self._status_from_records(
                state.is_completed, state.completed_at, connector, None
            )
        return self._status_from_records(
            state.is_completed,
            state.completed_at,
            connector,
            "complete onboarding before accessing protected routes",
        )

    def configure(
        self, request: OnboardingConfigureRequest
    ) -> OnboardingConfigureResponse:
        test_result = self.test_connector(
            ConnectorTestRequest(
                qdrant_mode=request.qdrant_mode,
                obsidian_vault_path=request.obsidian_vault_path,
                external_qdrant_url=request.external_qdrant_url,
                external_qdrant_api_key=request.external_qdrant_api_key,
            )
        )
        if test_result.obsidian_ok is False or test_result.qdrant_ok is False:
            raise ValueError(test_result.message)

        encrypted_key: str | None = None
        if request.qdrant_mode == QdrantMode.EXTERNAL:
            if request.external_qdrant_api_key is None:
                raise ValueError("external qdrant api key is required")
            encrypted_key = self._cipher.encrypt(request.external_qdrant_api_key)

        self._repository.upsert_connector_config(
            obsidian_vault_path=request.obsidian_vault_path,
            qdrant_mode=request.qdrant_mode,
            external_qdrant_url=request.external_qdrant_url,
            encrypted_api_key=encrypted_key,
        )
        state = self._repository.mark_completed()
        if state.completed_at is None:
            raise RuntimeError("onboarding completion timestamp was not persisted")

        return OnboardingConfigureResponse(
            is_completed=state.is_completed,
            completed_at=state.completed_at,
            qdrant_mode=request.qdrant_mode,
        )

    def test_connector(self, request: ConnectorTestRequest) -> ConnectorTestResponse:
        vault_result = self._vault_validator.validate(request.obsidian_vault_path)
        if request.qdrant_mode == QdrantMode.LOCAL_DOCKER:
            qdrant_result = self._local_qdrant_validator.validate(
                self._local_qdrant_health_url
            )
        else:
            qdrant_result = self._external_qdrant_validator.validate(
                request.external_qdrant_url,
                request.external_qdrant_api_key,
            )

        all_valid = vault_result.is_valid and qdrant_result.is_valid
        message = f"vault: {vault_result.message}; qdrant: {qdrant_result.message}"
        return ConnectorTestResponse(
            obsidian_ok=vault_result.is_valid,
            qdrant_ok=qdrant_result.is_valid,
            message=message,
        )

    def is_completed(self) -> bool:
        return self._repository.get_state().is_completed

    def _status_from_records(
        self,
        is_completed: bool,
        completed_at,
        connector: ConnectorConfigRecord | None,
        block_reason: str | None,
    ) -> OnboardingStatusResponse:
        if connector is None:
            return OnboardingStatusResponse(
                is_completed=is_completed,
                completed_at=completed_at,
                qdrant_mode=None,
                obsidian_vault_path=None,
                external_qdrant_url=None,
                has_external_qdrant_api_key=False,
                block_reason=block_reason,
            )

        return OnboardingStatusResponse(
            is_completed=is_completed,
            completed_at=completed_at,
            qdrant_mode=connector.qdrant_mode,
            obsidian_vault_path=connector.obsidian_vault_path,
            external_qdrant_url=connector.external_qdrant_url,
            has_external_qdrant_api_key=connector.external_qdrant_api_key_encrypted
            is not None,
            block_reason=block_reason,
        )

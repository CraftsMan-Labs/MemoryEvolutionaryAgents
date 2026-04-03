from __future__ import annotations

import json
import os
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from fastapi.testclient import TestClient

from memory_evolutionary_agents.api import create_app
from memory_evolutionary_agents.container import build_container
from memory_evolutionary_agents.contracts import SourceCreateRequest
from memory_evolutionary_agents.worker import run_once


class Phase01TestCase(unittest.TestCase):
    def test_onboarding_gate_blocks_protected_routes_until_completed(self) -> None:
        with _temp_env() as temp_dir:
            app = create_app()
            client = TestClient(app)

            status_response = client.get("/onboarding/status")
            self.assertEqual(status_response.status_code, 200)
            self.assertEqual(status_response.json()["is_completed"], False)

            blocked_response = client.get("/sources")
            self.assertEqual(blocked_response.status_code, 423)

            with _fake_qdrant_server() as qdrant_url:
                configure_payload = {
                    "obsidian_vault_path": temp_dir,
                    "qdrant_mode": "external",
                    "external_qdrant_url": qdrant_url,
                    "external_qdrant_api_key": "secret-token",
                }
                configure_response = client.post(
                    "/onboarding/configure", json=configure_payload
                )
                self.assertEqual(configure_response.status_code, 200)
                self.assertEqual(configure_response.json()["is_completed"], True)

            allowed_response = client.get("/sources")
            self.assertEqual(allowed_response.status_code, 200)

            container = build_container()
            with container.database.connection() as conn:
                row = conn.execute(
                    "SELECT external_qdrant_api_key_encrypted FROM connector_settings WHERE id = 1"
                ).fetchone()
            self.assertIsNotNone(row)
            if row is None:
                return
            self.assertNotEqual(
                row["external_qdrant_api_key_encrypted"], "secret-token"
            )

    def test_worker_gate_skips_cycle_before_onboarding(self) -> None:
        with _temp_env() as temp_dir:
            source_dir = Path(temp_dir) / "source"
            source_dir.mkdir(parents=True, exist_ok=True)
            (source_dir / "sample.log").write_text("hello", encoding="utf-8")

            container = build_container()
            container.source_registry.create_source(
                SourceCreateRequest(path=str(source_dir))
            )

            run_once()

            with container.database.connection() as conn:
                row = conn.execute(
                    "SELECT COUNT(*) AS count FROM ingestion_runs"
                ).fetchone()
            self.assertIsNotNone(row)
            if row is None:
                return
            self.assertEqual(int(row["count"]), 0)


class _FakeQdrantHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path == "/collections":
            payload = {"result": {"collections": []}, "status": "ok"}
            body = json.dumps(payload).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        self.send_response(404)
        self.end_headers()

    def log_message(self, format: str, *args: object) -> None:
        _ = (format, args)
        return


class _fake_qdrant_server:
    def __enter__(self) -> str:
        self._server = HTTPServer(("127.0.0.1", 0), _FakeQdrantHandler)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        host = str(self._server.server_address[0])
        port = int(self._server.server_address[1])
        return f"http://{host}:{port}"

    def __exit__(self, *_: object) -> None:
        self._server.shutdown()
        self._thread.join(timeout=2)
        self._server.server_close()


class _temp_env:
    def __enter__(self) -> str:
        self._temp_dir = tempfile.TemporaryDirectory()
        self._old_db_path = _set_env(
            "MEA_DB_PATH", str(Path(self._temp_dir.name) / "phase01.db")
        )
        self._old_interval = _set_env("MEA_SCAN_INTERVAL_SECONDS", "300")
        self._old_timeout = _set_env("MEA_SCAN_CYCLE_TIMEOUT_SECONDS", "120")
        self._old_key = _set_env(
            "MEA_MASTER_KEY", "zFoMoJWsQ6b97ZKx4z5VHPL0x5uR2wRDRjB7Q12N5o8="
        )
        self._old_phase2_enabled = _set_env("MEA_PHASE2_ENABLED", "false")
        self._old_database_url = _set_env(
            "MEA_DATABASE_URL",
            "postgresql://memory_agents:memory_agents@localhost:5432/memory_agents",
        )
        return self._temp_dir.name

    def __exit__(self, *_: object) -> None:
        _set_env("MEA_DB_PATH", self._old_db_path)
        _set_env("MEA_SCAN_INTERVAL_SECONDS", self._old_interval)
        _set_env("MEA_SCAN_CYCLE_TIMEOUT_SECONDS", self._old_timeout)
        _set_env("MEA_MASTER_KEY", self._old_key)
        _set_env("MEA_PHASE2_ENABLED", self._old_phase2_enabled)
        _set_env("MEA_DATABASE_URL", self._old_database_url)
        self._temp_dir.cleanup()


def _set_env(key: str, value: str | None) -> str | None:
    current = os.getenv(key)
    if value is None:
        os.environ.pop(key, None)
    else:
        os.environ[key] = value
    return current


if __name__ == "__main__":
    unittest.main()

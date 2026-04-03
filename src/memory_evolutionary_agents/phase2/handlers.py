from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from pathlib import Path

import httpx

from .contracts import (
    ChunkRecord,
    ChunkingOutput,
    EmbeddingOutput,
    EmbeddingRecord,
    NormalizeOutput,
)


@dataclass(frozen=True)
class NormalizationService:
    def normalize(self, file_path: str, file_content: str) -> NormalizeOutput:
        raw_content = file_content
        if len(raw_content.strip()) == 0:
            path = Path(file_path)
            if path.exists() and path.is_file():
                raw_content = path.read_text(encoding="utf-8")
        normalized = raw_content.replace("\r\n", "\n").strip()
        suffix = file_path.lower().split(".")[-1] if "." in file_path else "unknown"
        document_type = "markdown" if suffix in {"md", "markdown"} else suffix
        metadata = {"source_extension": suffix, "char_count": str(len(normalized))}
        return NormalizeOutput(
            document_text=normalized,
            document_type=document_type,
            metadata=metadata,
        )


@dataclass(frozen=True)
class ChunkingService:
    chunk_size: int = 600

    def chunk(self, text: str) -> ChunkingOutput:
        if len(text) == 0:
            return ChunkingOutput(chunks=[])
        chunks: list[ChunkRecord] = []
        start = 0
        index = 0
        while start < len(text):
            end = min(start + self.chunk_size, len(text))
            chunk_text = text[start:end]
            chunk_id = hashlib.sha256(
                f"{index}:{chunk_text}".encode("utf-8")
            ).hexdigest()
            chunks.append(
                ChunkRecord(
                    chunk_id=chunk_id,
                    chunk_index=index,
                    text=chunk_text,
                    start_offset=start,
                    end_offset=end,
                )
            )
            index += 1
            start = end
        return ChunkingOutput(chunks=chunks)


@dataclass(frozen=True)
class EmbeddingService:
    model_name: str = "deterministic-hash-embeddings-v1"
    provider: str = "deterministic"
    api_base: str | None = None
    api_key: str | None = None

    @classmethod
    def from_env(cls) -> "EmbeddingService":
        provider = os.getenv("MEA_EMBEDDING_PROVIDER", "deterministic").strip().lower()
        model = os.getenv(
            "MEA_EMBEDDING_MODEL", "nomic-embed-text-v2-moe:latest"
        ).strip()
        api_base = os.getenv("MEA_EMBEDDING_API_BASE", "http://localhost:11434").strip()
        api_key = os.getenv("MEA_EMBEDDING_API_KEY", "").strip()
        return cls(
            model_name=model,
            provider=provider,
            api_base=api_base,
            api_key=None if len(api_key) == 0 else api_key,
        )

    def embed(self, chunks: ChunkingOutput) -> EmbeddingOutput:
        if self.provider == "openai":
            return self._embed_with_openai_compatible(chunks)
        if self.provider == "ollama":
            return self._embed_with_ollama(chunks)
        return self._embed_deterministic(chunks)

    def _embed_with_openai_compatible(self, chunks: ChunkingOutput) -> EmbeddingOutput:
        if self.api_base is None or len(self.api_base) == 0:
            return self._embed_deterministic(chunks)
        endpoint = f"{self.api_base.rstrip('/')}/embeddings"
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if self.api_key is not None:
            headers["Authorization"] = f"Bearer {self.api_key}"
        records: list[EmbeddingRecord] = []
        with httpx.Client(timeout=45.0) as client:
            for chunk in chunks.chunks:
                response = client.post(
                    endpoint,
                    headers=headers,
                    json={
                        "model": self.model_name,
                        "input": chunk.text,
                        "encoding_format": "float",
                    },
                )
                if response.is_success is False:
                    return self._embed_deterministic(chunks)
                payload = response.json()
                raw_data = payload.get("data")
                if isinstance(raw_data, list) is False or len(raw_data) == 0:
                    return self._embed_deterministic(chunks)
                first = raw_data[0]
                if isinstance(first, dict) is False:
                    return self._embed_deterministic(chunks)
                raw_embedding = first.get("embedding")
                if isinstance(raw_embedding, list) is False:
                    return self._embed_deterministic(chunks)
                vector: list[float] = []
                for item in raw_embedding:
                    if isinstance(item, (int, float)):
                        vector.append(float(item))
                if len(vector) == 0:
                    return self._embed_deterministic(chunks)
                records.append(
                    EmbeddingRecord(
                        chunk_id=chunk.chunk_id,
                        vector=vector,
                        model_name=self.model_name,
                    )
                )
        return EmbeddingOutput(embeddings=records)

    def _embed_deterministic(self, chunks: ChunkingOutput) -> EmbeddingOutput:
        records: list[EmbeddingRecord] = []
        for chunk in chunks.chunks:
            digest = hashlib.sha256(chunk.text.encode("utf-8")).digest()
            vector = [float(value) / 255.0 for value in digest[:32]]
            records.append(
                EmbeddingRecord(
                    chunk_id=chunk.chunk_id,
                    vector=vector,
                    model_name=self.model_name,
                )
            )
        return EmbeddingOutput(embeddings=records)

    def _embed_with_ollama(self, chunks: ChunkingOutput) -> EmbeddingOutput:
        if self.api_base is None or len(self.api_base) == 0:
            return self._embed_deterministic(chunks)
        records: list[EmbeddingRecord] = []
        with httpx.Client(timeout=30.0) as client:
            for chunk in chunks.chunks:
                response = client.post(
                    f"{self.api_base.rstrip('/')}/api/embed",
                    json={"model": self.model_name, "input": chunk.text},
                )
                if response.is_success is False:
                    return self._embed_deterministic(chunks)
                payload = response.json()
                raw_embeddings = payload.get("embeddings")
                if (
                    isinstance(raw_embeddings, list) is False
                    or len(raw_embeddings) == 0
                ):
                    return self._embed_deterministic(chunks)
                first = raw_embeddings[0]
                if isinstance(first, list) is False:
                    return self._embed_deterministic(chunks)
                vector: list[float] = []
                for item in first:
                    if isinstance(item, (int, float)):
                        vector.append(float(item))
                if len(vector) == 0:
                    return self._embed_deterministic(chunks)
                records.append(
                    EmbeddingRecord(
                        chunk_id=chunk.chunk_id,
                        vector=vector,
                        model_name=self.model_name,
                    )
                )
        return EmbeddingOutput(embeddings=records)

from __future__ import annotations

import hashlib
from dataclasses import dataclass

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
        normalized = file_content.replace("\r\n", "\n").strip()
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

    def embed(self, chunks: ChunkingOutput) -> EmbeddingOutput:
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

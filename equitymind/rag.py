"""SEC-filing text chunking and pgvector retrieval primitives.

Database and embedding dependencies are optional. Unit tests use a fake cursor.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from typing import Any


def chunk_filing_text(text: str, max_words: int = 350, overlap_words: int = 50) -> list[str]:
    """Split filing text into bounded overlapping chunks while preserving order."""
    if max_words < 1 or overlap_words < 0 or overlap_words >= max_words:
        raise ValueError("Require max_words >= 1 and 0 <= overlap_words < max_words")
    words = re.sub(r"\s+", " ", text).strip().split(" ")
    if not words or words == [""]:
        return []
    chunks: list[str] = []
    step = max_words - overlap_words
    for start in range(0, len(words), step):
        chunk = " ".join(words[start:start + max_words]).strip()
        if chunk:
            chunks.append(chunk)
        if start + max_words >= len(words):
            break
    return chunks


def format_vector(values: Sequence[float]) -> str:
    """Format a finite numeric embedding for PostgreSQL's vector input syntax."""
    if not values:
        raise ValueError("Embedding cannot be empty")
    normalized: list[str] = []
    for value in values:
        number = float(value)
        if not (-1e100 < number < 1e100):
            raise ValueError("Embedding values must be finite")
        normalized.append(f"{number:.10g}")
    return "[" + ",".join(normalized) + "]"


class PgVectorRetriever:
    """Small DB-API adapter for ticker-scoped cosine-similarity retrieval."""

    SQL = """
        SELECT evidence_id, ticker, filing_type, filing_date, section, text,
               1 - (embedding <=> %s::vector) AS similarity, source_url
        FROM filing_chunks
        WHERE ticker = %s
        ORDER BY embedding <=> %s::vector
        LIMIT %s
    """

    def __init__(self, connection_factory: Any):
        self.connection_factory = connection_factory

    def search(self, ticker: str, embedding: Sequence[float], top_k: int = 6) -> list[dict]:
        if not 1 <= top_k <= 50:
            raise ValueError("top_k must be between 1 and 50")
        vector = format_vector(embedding)
        connection = self.connection_factory()
        try:
            cursor = connection.cursor()
            try:
                cursor.execute(self.SQL, (vector, ticker.upper(), vector, top_k))
                rows = cursor.fetchall()
                columns = [description[0] for description in cursor.description]
                return [dict(zip(columns, row, strict=True)) for row in rows]
            finally:
                cursor.close()
        finally:
            connection.close()

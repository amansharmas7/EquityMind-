"""Optional PostgreSQL/pgvector write and search adapter."""

from __future__ import annotations

from datetime import date
from typing import Any, Sequence
from uuid import uuid4

from equitymind.rag import format_vector


class PgVectorStore:
    def __init__(self, database_url: str):
        if not database_url:
            raise ValueError("DATABASE_URL is required for pgvector storage")
        self.database_url = database_url

    def _connect(self):
        try:
            import psycopg
        except ImportError as exc:
            raise RuntimeError("Install database extras: pip install -e '.[database]'") from exc
        return psycopg.connect(self.database_url)

    def insert_chunks(
        self,
        *,
        ticker: str,
        cik: str | None,
        filing_type: str,
        filing_date: date,
        accession_number: str,
        source_url: str,
        chunks: list[str],
        embeddings: list[Sequence[float]],
        market_country: str = "US",
        exchange: str | None = None,
        issuer_id: str | None = None,
    ) -> int:
        if len(chunks) != len(embeddings):
            raise ValueError("Each filing chunk must have exactly one embedding")
        if not chunks:
            return 0
        connection = self._connect()
        try:
            with connection.cursor() as cursor:
                rows = []
                for index, (chunk, vector) in enumerate(zip(chunks, embeddings, strict=True)):
                    rows.append((
                        f"{ticker.upper()}-{accession_number}-{index}-{uuid4().hex[:8]}",
                        ticker.upper(), str(cik).zfill(10) if cik else None, market_country, exchange, issuer_id,
                        filing_type, filing_date, accession_number, "Filing body", index, chunk, source_url, format_vector(vector),
                    ))
                cursor.executemany(
                    """
                    INSERT INTO filing_chunks
                      (evidence_id, ticker, cik, market_country, exchange, issuer_id, filing_type,
                       filing_date, accession_number, section, chunk_index, text, source_url, embedding)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::vector)
                    ON CONFLICT (ticker, accession_number, section, chunk_index)
                    DO UPDATE SET text = EXCLUDED.text, embedding = EXCLUDED.embedding,
                                  source_url = EXCLUDED.source_url, created_at = NOW()
                    """,
                    rows,
                )
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()
        return len(chunks)

    def search(\n        self, ticker: str, embedding: Sequence[float], top_k: int = 6,\n        market_country: str | None = None, exchange: str | None = None,\n    ) -> list[dict[str, Any]]:
        if not 1 <= top_k <= 50:
            raise ValueError("top_k must be between 1 and 50")
        vector = format_vector(embedding)
        connection = self._connect()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT evidence_id, ticker, market_country, exchange, filing_type, filing_date,
                           section, text, 1 - (embedding <=> %s::vector) AS similarity, source_url
                    FROM filing_chunks
                    WHERE ticker = %s
                      AND (%s IS NULL OR market_country = %s)
                      AND (%s IS NULL OR exchange = %s)
                    ORDER BY embedding <=> %s::vector
                    LIMIT %s
                    """,
                    (vector, ticker.upper(), market_country, market_country, exchange, exchange, vector, top_k),
                )
                rows = cursor.fetchall()
                columns = [item.name if hasattr(item, "name") else item[0] for item in cursor.description]
                return [dict(zip(columns, row, strict=True)) for row in rows]
        finally:
            connection.close()

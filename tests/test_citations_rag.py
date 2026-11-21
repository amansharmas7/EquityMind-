import pytest

from equitymind.citations import audit_citations
from equitymind.rag import PgVectorRetriever, chunk_filing_text, format_vector


def test_citation_audit_accepts_known_references_and_flags_unused_evidence():
    result = audit_citations("Revenue increased [E1]. Margin expanded [E2].", ["E1", "E2", "E3"])
    assert result.valid is True
    assert result.missing_ids == []
    assert result.uncited_evidence_ids == ["E3"]
    assert result.citation_coverage == 1


def test_citation_audit_flags_unknown_reference():
    result = audit_citations("Risk increased [E9].", ["E1"])
    assert result.valid is False
    assert result.missing_ids == ["E9"]


def test_citation_audit_requires_at_least_one_citation():
    result = audit_citations("No source cited.", ["E1"])
    assert result.valid is False
    assert result.citation_coverage == 0


def test_chunking_creates_overlapping_chunks_without_losing_words():
    words = [f"w{i}" for i in range(20)]
    chunks = chunk_filing_text(" ".join(words), max_words=8, overlap_words=2)
    assert len(chunks) == 3
    assert chunks[0].split()[-2:] == chunks[1].split()[:2]
    assert chunks[-1].split()[-1] == "w19"


def test_chunking_rejects_invalid_overlap():
    with pytest.raises(ValueError):
        chunk_filing_text("some text", max_words=4, overlap_words=4)


def test_vector_formatter_rejects_empty_or_nonfinite_values():
    assert format_vector([0.5, -0.25]) == "[0.5,-0.25]"
    with pytest.raises(ValueError):
        format_vector([])
    with pytest.raises(ValueError):
        format_vector([float("nan")])


class FakeCursor:
    description = [("ticker",), ("similarity",)]

    def __init__(self):
        self.executed = None
        self.closed = False

    def execute(self, sql, params):
        self.executed = (sql, params)

    def fetchall(self):
        return [("MSFT", 0.91)]

    def close(self):
        self.closed = True


class FakeConnection:
    def __init__(self):
        self.fake_cursor = FakeCursor()
        self.closed = False

    def cursor(self):
        return self.fake_cursor

    def close(self):
        self.closed = True


def test_pgvector_retriever_uses_parameterized_sql_and_closes_resources():
    connection = FakeConnection()
    retriever = PgVectorRetriever(lambda: connection)
    rows = retriever.search("msft", [0.1, 0.2], top_k=3)
    assert rows == [{"ticker": "MSFT", "similarity": 0.91}]
    assert "WHERE ticker = %s" in connection.fake_cursor.executed[0]
    assert connection.fake_cursor.executed[1][1] == "MSFT"
    assert connection.fake_cursor.closed and connection.closed


def test_pgvector_retriever_bounds_top_k():
    retriever = PgVectorRetriever(lambda: FakeConnection())
    with pytest.raises(ValueError):
        retriever.search("MSFT", [0.1], top_k=100)


def test_sec_client_requires_contactable_user_agent():
    from equitymind.sec_edgar import SecEdgarClient

    with pytest.raises(ValueError):
        SecEdgarClient("EquityMind/0.1")
    client = SecEdgarClient("EquityMind/0.1 research@example.com")
    assert client.headers["User-Agent"].endswith("research@example.com")


def test_sec_filing_download_rejects_non_sec_hosts_before_network_call():
    import asyncio
    from equitymind.sec_edgar import SecEdgarClient

    client = SecEdgarClient("EquityMind/0.1 research@example.com")
    with pytest.raises(ValueError):
        asyncio.run(client.fetch_filing_text("https://example.com/fake-filing.html"))


def test_local_embedding_client_enforces_384_dimensions():
    from equitymind.embeddings import LocalEmbeddingClient

    client = LocalEmbeddingClient()
    assert client.dimensions == 384
    with pytest.raises(ValueError):
        LocalEmbeddingClient(dimensions=1536)


def test_sec_filing_download_only_accepts_edgar_archive_paths():
    import asyncio
    from equitymind.sec_edgar import SecEdgarClient

    client = SecEdgarClient("EquityMind/0.1 research@example.com")
    with pytest.raises(ValueError):
        asyncio.run(client.fetch_filing_text("https://www.sec.gov/robots.txt"))

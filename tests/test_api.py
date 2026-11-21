from fastapi.testclient import TestClient

from equitymind.api import app, settings

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_demo_universe_is_explicitly_labeled():
    response = client.get("/api/v1/universe")
    assert response.status_code == 200
    payload = response.json()
    assert payload["mode"] == "demo"
    assert payload["count"] == len(payload["tickers"])


def test_research_endpoint_returns_seven_signals_and_demo_flag():
    response = client.post("/api/v1/research", json={"ticker": "MSFT"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["ticker"] == "MSFT"
    assert len(payload["signals"]) == 7
    assert payload["is_demo_data"] is True


def test_research_endpoint_rejects_unknown_demo_ticker():
    response = client.post("/api/v1/research", json={"ticker": "ZZZZ"})
    assert response.status_code == 404


def test_portfolio_endpoint_returns_concentration_metrics():
    response = client.post("/api/v1/portfolio/analyze", json={
        "positions": [
            {"ticker": "MSFT", "market_value": 50, "sector": "Technology"},
            {"ticker": "JPM", "market_value": 50, "sector": "Financials"},
        ]
    })
    assert response.status_code == 200
    assert response.json()["total_value"] == 100


def test_dcf_endpoint_returns_three_cases():
    response = client.post("/api/v1/scenarios/dcf", json={
        "ticker": "MSFT", "current_price": 430, "revenue": 245000000000,
        "shares_outstanding": 7400000000, "free_cash_flow_margin": 0.28,
        "cash": 80000000000, "debt": 70000000000,
    })
    assert response.status_code == 200
    assert len(response.json()["cases"]) == 3


def test_citation_audit_endpoint():
    response = client.post("/api/v1/citations/audit", json={
        "answer": "Revenue growth was reported [E1].", "evidence_ids": ["E1", "E2"]
    })
    assert response.status_code == 200
    assert response.json()["valid"] is True
    assert response.json()["uncited_evidence_ids"] == ["E2"]


def test_api_key_is_enforced_when_configured(monkeypatch):
    monkeypatch.setattr(settings, "api_key", "test-secret")
    denied = client.get("/api/v1/universe")
    allowed = client.get("/api/v1/universe", headers={"X-API-Key": "test-secret"})
    monkeypatch.setattr(settings, "api_key", None)
    assert denied.status_code == 401
    assert allowed.status_code == 200


def test_filing_ingest_requires_database_and_embedding_configuration(monkeypatch):
    monkeypatch.setattr(settings, "database_url", None)
    monkeypatch.setattr(settings, "groq_api_key", None)
    response = client.post("/api/v1/filings/ingest", json={
        "ticker": "MSFT", "cik": "789019", "filing_type": "10-K",
        "filing_date": "2026-10-01", "accession_number": "0000789019-26-000001",
        "filing_url": "https://www.sec.gov/Archives/edgar/data/789019/example.htm"
    })
    assert response.status_code == 503


def test_evidence_search_requires_database_and_embedding_configuration(monkeypatch):
    monkeypatch.setattr(settings, "database_url", None)
    monkeypatch.setattr(settings, "groq_api_key", None)
    response = client.post("/api/v1/evidence/search", json={
        "ticker": "MSFT", "question": "What are the principal risks?"
    })
    assert response.status_code == 503



def test_rag_endpoint_returns_grounded_answer_and_audited_reference(monkeypatch):
    from datetime import date
    import equitymind.api as api

    monkeypatch.setattr(api.settings, "database_url", "postgresql://test")
    monkeypatch.setattr(api.settings, "groq_api_key", "test-key")
    monkeypatch.setattr(api.settings, "groq_model", "llama-3.3-70b-versatile")

    async def fake_embed(self, question):
        return [0.1, 0.2]

    def fake_search(self, ticker, embedding, top_k):
        return [{
            "evidence_id": "MSFT-test-0", "ticker": ticker, "filing_type": "10-K",
            "filing_date": date(2026, 10, 1), "section": "Risk Factors",
            "text": "The company reports risk from cyber incidents.",
            "similarity": 0.91,
            "source_url": "https://www.sec.gov/Archives/edgar/data/789019/sample.htm",
        }]

    async def fake_answer(self, *, ticker, question, references):
        assert ticker == "MSFT" and references[0]["section"] == "Risk Factors"
        return "Management identifies cyber incidents as a risk [E1]."

    monkeypatch.setattr(api.LocalEmbeddingClient, "embed_query", fake_embed)
    monkeypatch.setattr(api.PgVectorStore, "search", fake_search)
    monkeypatch.setattr(api.GroqChatClient, "generate_answer", fake_answer)

    response = client.post("/api/v1/research/rag", json={
        "ticker": "msft", "question": "What are the principal cyber risks?"
    })
    assert response.status_code == 200
    payload = response.json()
    assert payload["no_evidence"] is False
    assert payload["citation_audit"]["valid"] is True
    assert payload["references"][0]["evidence_id"] == "MSFT-test-0"


def test_rag_endpoint_returns_clear_message_when_no_filings_match(monkeypatch):
    import equitymind.api as api
    monkeypatch.setattr(api.settings, "database_url", "postgresql://test")
    monkeypatch.setattr(api.settings, "groq_api_key", "test-key")

    async def fake_embed(self, question):
        return [0.1, 0.2]

    monkeypatch.setattr(api.LocalEmbeddingClient, "embed_query", fake_embed)
    monkeypatch.setattr(api.PgVectorStore, "search", lambda *args, **kwargs: [])
    response = client.post("/api/v1/research/rag", json={
        "ticker": "MSFT", "question": "What are the risks?"
    })
    assert response.status_code == 200
    assert response.json()["no_evidence"] is True
    assert response.json()["references"] == []


def test_rag_endpoint_requires_groq_and_database_configuration(monkeypatch):
    import equitymind.api as api
    monkeypatch.setattr(api.settings, "database_url", None)
    monkeypatch.setattr(api.settings, "groq_api_key", None)
    response = client.post("/api/v1/research/rag", json={
        "ticker": "MSFT", "question": "What are the risks?"
    })
    assert response.status_code == 503

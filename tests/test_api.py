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
    monkeypatch.setattr(settings, "openai_api_key", None)
    response = client.post("/api/v1/filings/ingest", json={
        "ticker": "MSFT", "cik": "789019", "filing_type": "10-K",
        "filing_date": "2026-10-01", "accession_number": "0000789019-26-000001",
        "filing_url": "https://www.sec.gov/Archives/edgar/data/789019/example.htm"
    })
    assert response.status_code == 503


def test_evidence_search_requires_database_and_embedding_configuration(monkeypatch):
    monkeypatch.setattr(settings, "database_url", None)
    monkeypatch.setattr(settings, "openai_api_key", None)
    response = client.post("/api/v1/evidence/search", json={
        "ticker": "MSFT", "question": "What are the principal risks?"
    })
    assert response.status_code == 503

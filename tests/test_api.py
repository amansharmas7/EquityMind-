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
    response = client.post("/api/v1/research", json={"ticker": "TCS"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["ticker"] == "TCS"
    assert len(payload["signals"]) == 7
    assert payload["is_demo_data"] is True


def test_research_endpoint_rejects_unknown_demo_ticker():
    response = client.post("/api/v1/research", json={"ticker": "ZZZZ"})
    assert response.status_code == 404


def test_portfolio_endpoint_returns_concentration_metrics():
    response = client.post("/api/v1/portfolio/analyze", json={
        "positions": [
            {"ticker": "TCS", "market_value": 50, "sector": "Information Technology"},
            {"ticker": "HDFCBANK", "market_value": 50, "sector": "Financials"},
        ]
    })
    assert response.status_code == 200
    assert response.json()["total_value"] == 100


def test_dcf_endpoint_returns_three_cases():
    response = client.post("/api/v1/scenarios/dcf", json={
        "ticker": "TCS", "current_price": 3850, "revenue": 245000000000,
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
        "ticker": "TCS", "question": "What are the principal risks?"
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

    def fake_search(self, ticker, embedding, top_k, market_country=None, exchange=None):
        return [{
            "evidence_id": "TCS-test-0", "ticker": ticker, "market_country": "IN", "exchange": "NSE", "filing_type": "ANNUAL_REPORT",
            "filing_date": date(2026, 10, 1), "section": "Risk Factors",
            "text": "The company reports risk from cyber incidents.",
            "similarity": 0.91,
            "source_url": "https://www.sec.gov/Archives/edgar/data/789019/sample.htm",
        }]

    async def fake_answer(self, *, ticker, question, references):
        assert ticker == "TCS" and references[0]["section"] == "Risk Factors"
        return "Management identifies cyber incidents as a risk [E1]."

    monkeypatch.setattr(api.LocalEmbeddingClient, "embed_query", fake_embed)
    monkeypatch.setattr(api.PgVectorStore, "search", fake_search)
    monkeypatch.setattr(api.GroqChatClient, "generate_answer", fake_answer)

    response = client.post("/api/v1/research/rag", json={
        "ticker": "tcs", "question": "What are the principal cyber risks?"
    })
    assert response.status_code == 200
    payload = response.json()
    assert payload["no_evidence"] is False
    assert payload["citation_audit"]["valid"] is True
    assert payload["references"][0]["evidence_id"] == "TCS-test-0"


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


def test_indian_market_universe_is_inr_and_nse():
    response = client.get("/api/v1/market/universe")
    assert response.status_code == 200
    payload = response.json()
    assert payload["market_country"] == "IN"
    assert payload["currency"] == "INR"
    assert "RELIANCE" in {row["symbol"] for row in payload["symbols"]}


def test_indian_disclosure_endpoint_uses_official_exchange_sources():
    response = client.get("/api/v1/market/disclosures")
    assert response.status_code == 200
    urls = [row["url"] for row in response.json()["sources"]]
    assert any("nseindia.com" in url for url in urls)
    assert any("bseindia.com" in url for url in urls)


def test_indian_market_quote_returns_inr_without_network(monkeypatch):
    import equitymind.api as api
    from equitymind.schemas import IndianMarketQuote

    def fake_quote(self, symbol, exchange):
        assert symbol == "RELIANCE" and exchange == "NSE"
        return IndianMarketQuote(
            symbol="RELIANCE", yahoo_symbol="RELIANCE.NS", exchange="NSE",
            currency="INR", company_name="Example", price=1000.0,
            previous_close=990.0, change=10.0, change_pct=1.01,
            open=995.0, day_high=1005.0, day_low=990.0, volume=12345,
            market_cap=None, last_session_date="2026-11-20",
            source="test", source_note="synthetic test response",
        )

    monkeypatch.setattr(api.YFinanceIndiaClient, "quote", fake_quote)
    response = client.get("/api/v1/market/quote/RELIANCE?exchange=NSE")
    assert response.status_code == 200
    assert response.json()["currency"] == "INR"
    assert response.json()["price"] == 1000.0


def test_bse_does_not_silently_use_nse_research_fixture():
    response = client.post("/api/v1/research", json={"ticker": "RELIANCE", "exchange": "BSE"})
    assert response.status_code == 422

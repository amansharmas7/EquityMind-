"""Clearly labelled, fictional fixture data for local demonstrations and tests.

The fixtures are not market quotes and must never be presented as current prices.
"""

from datetime import date
import math

from equitymind.schemas import CompanySnapshot, EvidenceItem, NewsItem

_AS_OF = date(2026, 10, 30)


def _price_history(start: float, drift: float, amplitude: float = 0.012) -> list[float]:
    """Produce deterministic illustrative prices, not observed trading data."""
    values = []
    for day in range(300):
        cyclical = math.sin(day / 17) * amplitude
        step = drift / 252 + cyclical / 10
        start *= 1 + step
        values.append(round(start, 3))
    return values


SNAPSHOTS: dict[str, CompanySnapshot] = {
    "AAPL": CompanySnapshot(
        ticker="AAPL", company_name="Apple Inc. (demo fixture)", sector="Technology", as_of=_AS_OF,
        current_price=210.0, market_cap=3.2e12, pe_ratio=29.0, pb_ratio=42.0, peer_median_pe=27.0,
        revenue_growth=0.08, gross_margin=0.46, operating_margin=0.31, return_on_equity=1.45,
        debt_to_equity=1.6, current_ratio=0.95, free_cash_flow_margin=0.25,
        analyst_target_price=225.0, analyst_count=38, short_interest_pct=0.7,
        shares_outstanding=15.2e9, cash=60e9, total_debt=100e9,
        historical_prices=_price_history(170, 0.16), peer_tickers=["MSFT", "GOOGL"],
        news=[NewsItem(title="Illustrative product-cycle headline", sentiment_score=0.35, source="DEMO"),
              NewsItem(title="Illustrative supply-chain risk headline", sentiment_score=-0.15, source="DEMO")],
    ),
    "MSFT": CompanySnapshot(
        ticker="MSFT", company_name="Microsoft Corp. (demo fixture)", sector="Technology", as_of=_AS_OF,
        current_price=430.0, market_cap=3.1e12, pe_ratio=34.0, pb_ratio=12.0, peer_median_pe=31.0,
        revenue_growth=0.14, gross_margin=0.69, operating_margin=0.44, return_on_equity=0.36,
        debt_to_equity=0.35, current_ratio=1.25, free_cash_flow_margin=0.31,
        analyst_target_price=470.0, analyst_count=44, short_interest_pct=0.5,
        shares_outstanding=7.4e9, cash=80e9, total_debt=70e9,
        historical_prices=_price_history(350, 0.19), peer_tickers=["AAPL", "GOOGL"],
        news=[NewsItem(title="Illustrative cloud growth headline", sentiment_score=0.55, source="DEMO")],
    ),
    "NVDA": CompanySnapshot(
        ticker="NVDA", company_name="NVIDIA Corp. (demo fixture)", sector="Technology", as_of=_AS_OF,
        current_price=150.0, market_cap=3.7e12, pe_ratio=48.0, pb_ratio=35.0, peer_median_pe=34.0,
        revenue_growth=0.42, gross_margin=0.75, operating_margin=0.62, return_on_equity=0.68,
        debt_to_equity=0.45, current_ratio=4.0, free_cash_flow_margin=0.34,
        analyst_target_price=165.0, analyst_count=52, short_interest_pct=1.1,
        shares_outstanding=24.5e9, cash=40e9, total_debt=10e9,
        historical_prices=_price_history(95, 0.38, 0.025), peer_tickers=["AMD", "AVGO"],
        news=[NewsItem(title="Illustrative accelerator demand headline", sentiment_score=0.62, source="DEMO"),
              NewsItem(title="Illustrative export-control headline", sentiment_score=-0.42, source="DEMO")],
    ),
    "JPM": CompanySnapshot(
        ticker="JPM", company_name="JPMorgan Chase & Co. (demo fixture)", sector="Financials", as_of=_AS_OF,
        current_price=220.0, market_cap=620e9, pe_ratio=12.0, pb_ratio=1.8, peer_median_pe=13.0,
        revenue_growth=0.06, gross_margin=0.0, operating_margin=0.32, return_on_equity=0.16,
        debt_to_equity=1.2, current_ratio=1.1, free_cash_flow_margin=0.12,
        analyst_target_price=235.0, analyst_count=29, short_interest_pct=0.8,
        shares_outstanding=2.8e9, cash=300e9, total_debt=500e9,
        historical_prices=_price_history(180, 0.12), peer_tickers=["BAC", "WFC"],
        news=[NewsItem(title="Illustrative net interest income headline", sentiment_score=0.18, source="DEMO")],
    ),
    "AMZN": CompanySnapshot(
        ticker="AMZN", company_name="Amazon.com Inc. (demo fixture)", sector="Consumer Discretionary", as_of=_AS_OF,
        current_price=195.0, market_cap=2.0e12, pe_ratio=38.0, pb_ratio=7.0, peer_median_pe=32.0,
        revenue_growth=0.12, gross_margin=0.48, operating_margin=0.11, return_on_equity=0.22,
        debt_to_equity=0.55, current_ratio=1.05, free_cash_flow_margin=0.08,
        analyst_target_price=215.0, analyst_count=46, short_interest_pct=0.9,
        shares_outstanding=10.5e9, cash=85e9, total_debt=130e9,
        historical_prices=_price_history(155, 0.17), peer_tickers=["WMT", "COST"],
        news=[NewsItem(title="Illustrative retail margin headline", sentiment_score=0.2, source="DEMO")],
    ),
}


def get_snapshot(ticker: str) -> CompanySnapshot:
    """Return a copy of a supported demo fixture or raise a clear lookup error."""
    key = ticker.upper().strip()
    if key not in SNAPSHOTS:
        raise KeyError(f"{key} is not in the demo universe. Configure a market-data provider to add it.")
    return SNAPSHOTS[key].model_copy(deep=True)


def get_demo_evidence(ticker: str) -> list[EvidenceItem]:
    """Return unmistakably synthetic evidence placeholders for UI/demo wiring."""
    key = ticker.upper().strip()
    return [
        EvidenceItem(
            evidence_id="DEMO-10K-01", ticker=key, filing_type="10-K", filing_date=_AS_OF,
            section="Risk Factors", text=(
                "DEMO EVIDENCE ONLY: Replace this illustrative passage with a retrieved SEC filing "
                "chunk before drawing any company-specific conclusion."
            ), similarity=0.91, source_url="https://www.sec.gov/edgar/search/",
        ),
        EvidenceItem(
            evidence_id="DEMO-10K-02", ticker=key, filing_type="10-K", filing_date=_AS_OF,
            section="Management Discussion and Analysis", text=(
                "DEMO EVIDENCE ONLY: This placeholder demonstrates source-linked report formatting; "
                "it is not a quotation from the issuer."
            ), similarity=0.84, source_url="https://www.sec.gov/edgar/search/",
        ),
    ]

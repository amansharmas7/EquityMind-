"""Synthetic Indian-equity fixtures. All ratios and prices below are invented."""
from datetime import date
import math

from equitymind.schemas import CompanySnapshot, EvidenceItem, NewsItem

_AS_OF = date(2026, 10, 30)


def _price_history(start: float, drift: float, amplitude: float = 0.012) -> list[float]:
    values = []
    for day in range(300):
        cyclical = math.sin(day / 17) * amplitude
        start *= 1 + drift / 252 + cyclical / 10
        values.append(round(start, 3))
    return values


SNAPSHOTS: dict[str, CompanySnapshot] = {
    "RELIANCE": CompanySnapshot(
        ticker="RELIANCE", company_name="Reliance Industries (SYNTHETIC DEMO DATA)",
        sector="Energy", as_of=_AS_OF, current_price=1420.0, market_cap=19.0e12,
        pe_ratio=24.0, pb_ratio=2.1, peer_median_pe=22.0, revenue_growth=0.09,
        gross_margin=0.25, operating_margin=0.16, return_on_equity=0.10,
        debt_to_equity=0.45, current_ratio=1.1, free_cash_flow_margin=0.08,
        analyst_target_price=1510.0, analyst_count=20, promoter_pledge_pct=0.0,
        shares_outstanding=6.7e9, cash=1.1e12, total_debt=3.0e12,
        historical_prices=_price_history(1250, 0.12), peer_tickers=["ONGC", "IOC"],
        news=[NewsItem(title="Synthetic energy growth headline", sentiment_score=0.25, source="DEMO"),
              NewsItem(title="Synthetic capex risk headline", sentiment_score=-0.12, source="DEMO")],
    ),
    "TCS": CompanySnapshot(
        ticker="TCS", company_name="Tata Consultancy Services (SYNTHETIC DEMO DATA)",
        sector="Information Technology", as_of=_AS_OF, current_price=3850.0,
        market_cap=14.0e12, pe_ratio=28.0, pb_ratio=14.0, peer_median_pe=30.0,
        revenue_growth=0.08, gross_margin=0.30, operating_margin=0.25,
        return_on_equity=0.48, debt_to_equity=0.05, current_ratio=2.1,
        free_cash_flow_margin=0.20, analyst_target_price=4020.0, analyst_count=24,
        promoter_pledge_pct=0.0, shares_outstanding=3.6e9, cash=500e9, total_debt=20e9,
        historical_prices=_price_history(3300, 0.10), peer_tickers=["INFY", "WIPRO"],
        news=[NewsItem(title="Synthetic IT demand headline", sentiment_score=0.32, source="DEMO")],
    ),
    "HDFCBANK": CompanySnapshot(
        ticker="HDFCBANK", company_name="HDFC Bank (SYNTHETIC DEMO DATA)",
        sector="Financials", as_of=_AS_OF, current_price=1680.0, market_cap=12.5e12,
        pe_ratio=19.0, pb_ratio=2.8, peer_median_pe=18.0, revenue_growth=0.11,
        operating_margin=0.24, return_on_equity=0.16, debt_to_equity=6.0,
        current_ratio=1.0, gross_npa_pct=1.4, net_npa_pct=0.4,
        capital_adequacy_pct=19.1, net_interest_margin_pct=3.5,
        casa_ratio_pct=37.0, provision_coverage_pct=75.0,
        analyst_target_price=1810.0, analyst_count=27,
        promoter_pledge_pct=0.0, shares_outstanding=7.5e9, cash=0, total_debt=0,
        historical_prices=_price_history(1500, 0.08), peer_tickers=["ICICIBANK", "AXISBANK"],
        news=[NewsItem(title="Synthetic deposit growth headline", sentiment_score=0.22, source="DEMO")],
    ),
    "INFY": CompanySnapshot(
        ticker="INFY", company_name="Infosys (SYNTHETIC DEMO DATA)",
        sector="Information Technology", as_of=_AS_OF, current_price=1580.0,
        market_cap=6.5e12, pe_ratio=25.0, pb_ratio=8.0, peer_median_pe=28.0,
        revenue_growth=0.07, gross_margin=0.32, operating_margin=0.22,
        return_on_equity=0.31, debt_to_equity=0.02, current_ratio=2.4,
        free_cash_flow_margin=0.18, analyst_target_price=1690.0, analyst_count=22,
        promoter_pledge_pct=0.0, shares_outstanding=4.1e9, cash=300e9, total_debt=8e9,
        historical_prices=_price_history(1350, 0.11), peer_tickers=["TCS", "WIPRO"],
        news=[NewsItem(title="Synthetic digital transformation headline", sentiment_score=0.28, source="DEMO")],
    ),
    "ICICIBANK": CompanySnapshot(
        ticker="ICICIBANK", company_name="ICICI Bank (SYNTHETIC DEMO DATA)",
        sector="Financials", as_of=_AS_OF, current_price=1320.0, market_cap=9.2e12,
        pe_ratio=17.0, pb_ratio=2.7, peer_median_pe=18.0, revenue_growth=0.13,
        operating_margin=0.25, return_on_equity=0.17, debt_to_equity=5.5,
        current_ratio=1.0, gross_npa_pct=1.5, net_npa_pct=0.4,
        capital_adequacy_pct=16.7, net_interest_margin_pct=4.3,
        casa_ratio_pct=40.0, provision_coverage_pct=78.0,
        analyst_target_price=1450.0, analyst_count=25,
        promoter_pledge_pct=0.0, shares_outstanding=7.0e9, cash=0, total_debt=0,
        historical_prices=_price_history(1120, 0.14), peer_tickers=["HDFCBANK", "AXISBANK"],
        news=[NewsItem(title="Synthetic credit growth headline", sentiment_score=0.30, source="DEMO")],
    ),
}


def get_snapshot(ticker: str) -> CompanySnapshot:
    key = ticker.upper().strip()
    if key not in SNAPSHOTS:
        raise KeyError(f"{key} is not in the Indian demo universe. Use /api/v1/market/quote for provider data.")
    return SNAPSHOTS[key].model_copy(deep=True)


def get_demo_evidence(ticker: str) -> list[EvidenceItem]:
    key = ticker.upper().strip()
    return [
        EvidenceItem(
            evidence_id="DEMO-AR-01", ticker=key, market_country="IN", exchange="NSE",
            filing_type="ANNUAL_REPORT", filing_date=_AS_OF, section="Risk Factors",
            text="SYNTHETIC DEMO EVIDENCE ONLY: Replace this passage with an NSE/BSE annual-report extract.",
            similarity=0.91, source_url="https://www.nseindia.com/companies-listing/corporate-filings-announcements",
        ),
        EvidenceItem(
            evidence_id="DEMO-QTR-02", ticker=key, market_country="IN", exchange="NSE",
            filing_type="QUARTERLY_RESULTS", filing_date=_AS_OF, section="Management Discussion",
            text="SYNTHETIC DEMO EVIDENCE ONLY: This is not a quotation or disclosure from the issuer.",
            similarity=0.84, source_url="https://www.nseindia.com/companies-listing/corporate-filings-financial-results",
        ),
    ]

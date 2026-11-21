"""Validated request and response models shared by the API and services."""

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class NewsItem(BaseModel):
    title: str
    published_at: date | None = None
    sentiment_score: float = Field(ge=-1.0, le=1.0)
    source: str | None = None


class CompanySnapshot(BaseModel):
    ticker: str = Field(min_length=1, max_length=20)
    exchange: Literal["NSE", "BSE"] = "NSE"
    currency: Literal["INR"] = "INR"
    company_name: str
    sector: str = "Unknown"
    as_of: date
    current_price: float = Field(gt=0)
    market_cap: float | None = Field(default=None, gt=0)
    pe_ratio: float | None = Field(default=None, gt=0)
    pb_ratio: float | None = Field(default=None, gt=0)
    peer_median_pe: float | None = Field(default=None, gt=0)
    revenue_growth: float | None = None
    gross_margin: float | None = None
    operating_margin: float | None = None
    return_on_equity: float | None = None
    debt_to_equity: float | None = Field(default=None, ge=0)
    current_ratio: float | None = Field(default=None, ge=0)
    free_cash_flow_margin: float | None = None
    analyst_target_price: float | None = Field(default=None, gt=0)
    analyst_count: int | None = Field(default=None, ge=0)
    promoter_pledge_pct: float | None = Field(default=None, ge=0, le=100)
    shares_outstanding: float | None = Field(default=None, gt=0)
    cash: float = Field(default=0, ge=0)
    total_debt: float = Field(default=0, ge=0)
    historical_prices: list[float] = Field(default_factory=list, min_length=0)
    peer_tickers: list[str] = Field(default_factory=list)
    news: list[NewsItem] = Field(default_factory=list)

    @field_validator("ticker")
    @classmethod
    def normalize_ticker(cls, value: str) -> str:
        clean = value.strip().upper()
        if not clean or len(clean) > 20 or not all(ch.isalnum() or ch in ".-&" for ch in clean):
            raise ValueError("Ticker may contain letters, digits, dots, hyphens and ampersands only")
        return clean

    @field_validator("historical_prices")
    @classmethod
    def prices_must_be_positive(cls, values: list[float]) -> list[float]:
        if any(value <= 0 for value in values):
            raise ValueError("Historical prices must be positive")
        return values


class Signal(BaseModel):
    name: str
    score: float = Field(ge=-100, le=100)
    label: Literal["positive", "neutral", "negative", "unavailable"]
    explanation: str
    confidence: Literal["low", "medium", "high"] = "medium"


class EvidenceItem(BaseModel):
    evidence_id: str
    ticker: str
    market_country: str = "US"
    exchange: str | None = None
    market_country: str = "US"
    exchange: str | None = None
    filing_type: str
    filing_date: date | None = None
    section: str
    text: str
    similarity: float = Field(ge=0, le=1)
    source_url: str | None = None


class ResearchRequest(BaseModel):
    ticker: str = Field(min_length=1, max_length=20)
    exchange: Literal["NSE", "BSE"] = "NSE"
    question: str = Field(default="Prepare an evidence-aware equity research brief.", max_length=2000)

    @field_validator("ticker")
    @classmethod
    def normalize_ticker(cls, value: str) -> str:
        return value.strip().upper()


class ResearchResponse(BaseModel):
    ticker: str
    exchange: Literal["NSE", "BSE"] = "NSE"
    currency: Literal["INR"] = "INR"
    exchange: Literal["NSE", "BSE"] = "NSE"
    currency: Literal["INR"] = "INR"
    company_name: str
    as_of: date
    overall_score: float | None
    signals: list[Signal]
    thesis: str
    key_risks: list[str]
    evidence: list[EvidenceItem]
    evidence_coverage: float = Field(ge=0, le=1)
    methodology_notes: list[str]
    is_demo_data: bool = True


class PortfolioPosition(BaseModel):
    ticker: str = Field(min_length=1, max_length=20)
    market_value: float = Field(gt=0)
    sector: str = "Unknown"

    @field_validator("ticker")
    @classmethod
    def normalize_ticker(cls, value: str) -> str:
        return value.strip().upper()


class PortfolioRequest(BaseModel):
    currency: Literal["INR"] = "INR"
    positions: list[PortfolioPosition] = Field(min_length=1, max_length=250)
    sector_shocks: dict[str, float] = Field(default_factory=dict)


class PortfolioResponse(BaseModel):
    currency: Literal["INR"] = "INR"
    total_value: float
    positions: list[dict]
    sector_weights: dict[str, float]
    herfindahl_index: float
    concentration_label: Literal["diversified", "moderate", "concentrated"]
    top_position_weight: float
    estimated_stress_loss_pct: float
    stress_contributions: list[dict]


class ScenarioRequest(BaseModel):
    ticker: str = Field(min_length=1, max_length=20)
    currency: Literal["INR"] = "INR"
    current_price: float = Field(gt=0)
    revenue: float = Field(gt=0)
    shares_outstanding: float = Field(gt=0)
    free_cash_flow_margin: float = Field(gt=-1, lt=1)
    cash: float = Field(default=0, ge=0)
    debt: float = Field(default=0, ge=0)
    revenue_growth: float = Field(default=0.08, gt=-0.5, lt=1.0)
    discount_rate: float = Field(default=0.10, gt=0.01, lt=1.0)
    terminal_growth: float = Field(default=0.025, ge=0, lt=0.15)
    forecast_years: int = Field(default=5, ge=3, le=10)

    @model_validator(mode="after")
    def validate_discount_spread(self) -> "ScenarioRequest":
        if self.discount_rate <= self.terminal_growth:
            raise ValueError("Discount rate must exceed terminal growth")
        return self

    @field_validator("ticker")
    @classmethod
    def normalize_ticker(cls, value: str) -> str:
        return value.strip().upper()


class ScenarioCase(BaseModel):
    name: str
    growth_rate: float
    discount_rate: float
    fair_value_per_share: float
    upside_pct: float


class ScenarioResponse(BaseModel):
    ticker: str
    currency: Literal["INR"] = "INR"
    currency: Literal["INR"] = "INR"
    cases: list[ScenarioCase]
    assumptions: list[str]


class CitationAuditRequest(BaseModel):
    answer: str = Field(min_length=1)
    evidence_ids: list[str]


class CitationAuditResponse(BaseModel):
    valid: bool
    cited_ids: list[str]
    missing_ids: list[str]
    uncited_evidence_ids: list[str]
    citation_coverage: float = Field(ge=0, le=1)


class FilingIngestRequest(BaseModel):
    ticker: str = Field(min_length=1, max_length=10)
    cik: str = Field(min_length=1, max_length=10)
    filing_type: Literal["10-K", "10-Q", "8-K"]
    filing_date: date
    accession_number: str = Field(min_length=10, max_length=30)
    filing_url: str = Field(min_length=15, max_length=1000)

    @field_validator("ticker")
    @classmethod
    def normalize_ticker(cls, value: str) -> str:
        return value.strip().upper()


class EvidenceSearchRequest(BaseModel):
    ticker: str = Field(min_length=1, max_length=20)
    market_country: Literal["IN", "US"] = "IN"
    exchange: Literal["NSE", "BSE"] | None = None
    question: str = Field(min_length=3, max_length=2000)
    top_k: int = Field(default=6, ge=1, le=50)

    @field_validator("ticker")
    @classmethod
    def normalize_ticker(cls, value: str) -> str:
        return value.strip().upper()


class FilingIngestResponse(BaseModel):
    ticker: str
    market_country: str = "US"
    exchange: str | None = None
    market_country: str = "US"
    exchange: str | None = None
    filing_type: str
    filing_date: date
    chunks_stored: int
    source_url: str


class EvidenceSearchResponse(BaseModel):
    ticker: str
    query: str
    results: list[EvidenceItem]



class RAGResearchRequest(BaseModel):
    ticker: str = Field(min_length=1, max_length=20)
    market_country: Literal["IN", "US"] = "IN"
    exchange: Literal["NSE", "BSE"] | None = None
    question: str = Field(min_length=3, max_length=2000)
    top_k: int = Field(default=6, ge=1, le=10)

    @field_validator("ticker")
    @classmethod
    def normalize_ticker(cls, value: str) -> str:
        clean = value.strip().upper()
        if not clean or len(clean) > 20 or not all(ch.isalnum() or ch in ".-&" for ch in clean):
            raise ValueError("Ticker may contain letters, digits, dots, hyphens and ampersands only")
        return clean


class RAGReference(BaseModel):
    citation_id: str
    evidence_id: str
    ticker: str
    market_country: str = "IN"
    exchange: str | None = None
    market_country: str = "IN"
    exchange: str | None = None
    filing_type: str
    filing_date: date
    section: str
    text: str
    similarity: float = Field(ge=0, le=1)
    source_url: str


class RAGResearchResponse(BaseModel):
    ticker: str
    question: str
    answer: str
    references: list[RAGReference]
    citation_audit: CitationAuditResponse
    model: str
    no_evidence: bool = False


class IndianFilingIngestRequest(BaseModel):
    ticker: str = Field(min_length=1, max_length=20)
    exchange: Literal["NSE", "BSE"] = "NSE"
    filing_type: Literal[
        "ANNUAL_REPORT", "QUARTERLY_RESULTS", "CORPORATE_ANNOUNCEMENT",
        "SHAREHOLDING_PATTERN", "INVESTOR_PRESENTATION", "CREDIT_RATING", "OTHER",
    ]
    filing_date: date
    document_id: str = Field(min_length=3, max_length=100)
    filing_url: str = Field(min_length=20, max_length=1000)

    @field_validator("ticker")
    @classmethod
    def normalize_ticker(cls, value: str) -> str:
        clean = value.strip().upper()
        if not clean or len(clean) > 20 or not all(ch.isalnum() or ch in ".-&" for ch in clean):
            raise ValueError("Invalid NSE symbol or BSE scrip code")
        return clean


class IndianMarketQuote(BaseModel):
    symbol: str
    yahoo_symbol: str
    exchange: Literal["NSE", "BSE"]
    currency: Literal["INR"]
    company_name: str
    price: float = Field(gt=0)
    previous_close: float | None = None
    change: float | None = None
    change_pct: float | None = None
    open: float | None = None
    day_high: float | None = None
    day_low: float | None = None
    volume: int = Field(ge=0)
    market_cap: float | None = None
    last_session_date: str
    source: str
    source_note: str


class MarketHistoryBar(BaseModel):
    date: str
    open: float | None = None
    high: float | None = None
    low: float | None = None
    close: float | None = None
    adjusted_close: float | None = None
    volume: int = Field(ge=0)


class IndianMarketHistory(BaseModel):
    symbol: str
    yahoo_symbol: str
    exchange: Literal["NSE", "BSE"]
    currency: Literal["INR"]
    period: str
    interval: Literal["1d"]
    source: str
    source_note: str
    bars: list[MarketHistoryBar]


class IndianFilingIngestRequest(BaseModel):
    ticker: str = Field(min_length=1, max_length=20)
    exchange: Literal["NSE", "BSE"] = "NSE"
    filing_type: Literal[
        "ANNUAL_REPORT", "QUARTERLY_RESULTS", "CORPORATE_ANNOUNCEMENT",
        "SHAREHOLDING_PATTERN", "INVESTOR_PRESENTATION", "CREDIT_RATING", "OTHER",
    ]
    filing_date: date
    document_id: str = Field(min_length=3, max_length=100)
    filing_url: str = Field(min_length=20, max_length=1000)

    @field_validator("ticker")
    @classmethod
    def normalize_ticker(cls, value: str) -> str:
        clean = value.strip().upper()
        if not clean or len(clean) > 20 or not all(ch.isalnum() or ch in ".-&" for ch in clean):
            raise ValueError("Invalid NSE symbol or BSE scrip code")
        return clean


class IndianMarketQuote(BaseModel):
    symbol: str
    yahoo_symbol: str
    exchange: Literal["NSE", "BSE"]
    currency: Literal["INR"]
    company_name: str
    price: float = Field(gt=0)
    previous_close: float | None = None
    change: float | None = None
    change_pct: float | None = None
    open: float | None = None
    day_high: float | None = None
    day_low: float | None = None
    volume: int = Field(ge=0)
    market_cap: float | None = None
    last_session_date: str
    source: str
    source_note: str


class MarketHistoryBar(BaseModel):
    date: str
    open: float | None = None
    high: float | None = None
    low: float | None = None
    close: float | None = None
    adjusted_close: float | None = None
    volume: int = Field(ge=0)


class IndianMarketHistory(BaseModel):
    symbol: str
    yahoo_symbol: str
    exchange: Literal["NSE", "BSE"]
    currency: Literal["INR"]
    period: str
    interval: Literal["1d"]
    source: str
    source_note: str
    bars: list[MarketHistoryBar]

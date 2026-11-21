"""Indian NSE/BSE market data adapter.

yfinance is an optional research/education source, not an exchange-authorised real-time feed.
"""
from __future__ import annotations

import math
import re
from typing import Literal

from equitymind.schemas import IndianMarketQuote, IndianMarketHistory, MarketHistoryBar

Exchange = Literal["NSE", "BSE"]
PERIODS = {"1mo", "3mo", "6mo", "1y", "2y", "5y", "max"}

INDIA_WATCHLIST = [
    {"symbol": "RELIANCE", "company_name": "Reliance Industries", "sector": "Energy"},
    {"symbol": "TCS", "company_name": "Tata Consultancy Services", "sector": "Information Technology"},
    {"symbol": "HDFCBANK", "company_name": "HDFC Bank", "sector": "Financials"},
    {"symbol": "ICICIBANK", "company_name": "ICICI Bank", "sector": "Financials"},
    {"symbol": "INFY", "company_name": "Infosys", "sector": "Information Technology"},
    {"symbol": "SBIN", "company_name": "State Bank of India", "sector": "Financials"},
    {"symbol": "ITC", "company_name": "ITC", "sector": "Consumer Staples"},
    {"symbol": "BHARTIARTL", "company_name": "Bharti Airtel", "sector": "Telecommunications"},
    {"symbol": "LT", "company_name": "Larsen & Toubro", "sector": "Industrials"},
    {"symbol": "HINDUNILVR", "company_name": "Hindustan Unilever", "sector": "Consumer Staples"},
    {"symbol": "AXISBANK", "company_name": "Axis Bank", "sector": "Financials"},
    {"symbol": "KOTAKBANK", "company_name": "Kotak Mahindra Bank", "sector": "Financials"},
    {"symbol": "BAJFINANCE", "company_name": "Bajaj Finance", "sector": "Financials"},
    {"symbol": "MARUTI", "company_name": "Maruti Suzuki India", "sector": "Automobiles"},
    {"symbol": "SUNPHARMA", "company_name": "Sun Pharmaceutical", "sector": "Healthcare"},
    {"symbol": "NTPC", "company_name": "NTPC", "sector": "Utilities"},
    {"symbol": "ONGC", "company_name": "Oil and Natural Gas Corporation", "sector": "Energy"},
    {"symbol": "TATASTEEL", "company_name": "Tata Steel", "sector": "Materials"},
    {"symbol": "TITAN", "company_name": "Titan Company", "sector": "Consumer Discretionary"},
    {"symbol": "ADANIPORTS", "company_name": "Adani Ports", "sector": "Industrials"},
]


def resolve_yahoo_symbol(symbol: str, exchange: Exchange = "NSE") -> tuple[str, Exchange]:
    """Resolve an NSE/BSE symbol to Yahoo Finance's suffix-based symbol."""
    clean = symbol.strip().upper()
    if clean.endswith(".NS"):
        clean, exchange = clean[:-3], "NSE"
    elif clean.endswith(".BO"):
        clean, exchange = clean[:-3], "BSE"
    if not clean or len(clean) > 20 or not re.fullmatch(r"[A-Z0-9&.-]+", clean):
        raise ValueError("Invalid Indian equity symbol")
    return (f"{clean}.NS" if exchange == "NSE" else f"{clean}.BO"), exchange


def _number(value) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def _yfinance():
    try:
        import yfinance as yf
    except ImportError as exc:
        raise RuntimeError(
            'Indian market data dependency is missing. Install with: pip install -e ".[india-market]"'
        ) from exc
    return yf


class YFinanceIndiaClient:
    """Fetch last-available daily NSE/BSE bars through the yfinance adapter."""

    source = "Yahoo Finance via yfinance"
    source_note = (
        "Daily historical/last-available session data sourced through Yahoo Finance. "
        "It may be delayed, incomplete or unavailable; it is not an exchange-authorised "
        "real-time feed. Verify prices with NSE/BSE before acting."
    )

    def quote(self, symbol: str, exchange: Exchange = "NSE") -> IndianMarketQuote:
        yahoo_symbol, resolved_exchange = resolve_yahoo_symbol(symbol, exchange)
        ticker = _yfinance().Ticker(yahoo_symbol)
        history = ticker.history(period="5d", interval="1d", auto_adjust=False)
        if history is None or history.empty:
            raise ValueError(f"No daily price history found for {yahoo_symbol}")
        try:
            info = ticker.get_info()
        except Exception:
            info = {}
        latest = history.iloc[-1]
        previous = history.iloc[-2] if len(history) > 1 else None
        price = _number(latest.get("Close"))
        if price is None or price <= 0:
            raise ValueError(f"No valid closing price found for {yahoo_symbol}")
        previous_close = _number(previous.get("Close")) if previous is not None else _number(info.get("previousClose"))
        change = price - previous_close if previous_close and previous_close > 0 else None
        change_pct = (change / previous_close * 100) if change is not None else None
        stamp = history.index[-1]
        last_date = stamp.date().isoformat() if hasattr(stamp, "date") else str(stamp)[:10]
        provider_currency = info.get("currency")
        if provider_currency and provider_currency != "INR":
            raise ValueError(f"{yahoo_symbol} returned {provider_currency}; expected INR")
        return IndianMarketQuote(
            symbol=yahoo_symbol.rsplit(".", 1)[0], yahoo_symbol=yahoo_symbol,
            exchange=resolved_exchange, currency="INR",
            company_name=info.get("longName") or info.get("shortName") or yahoo_symbol,
            price=price, previous_close=previous_close, change=change, change_pct=change_pct,
            open=_number(latest.get("Open")), day_high=_number(latest.get("High")),
            day_low=_number(latest.get("Low")), volume=int(_number(latest.get("Volume")) or 0),
            market_cap=_number(info.get("marketCap")), last_session_date=last_date,
            source=self.source, source_note=self.source_note,
        )

    def history(
        self, symbol: str, exchange: Exchange = "NSE", period: str = "1y"
    ) -> IndianMarketHistory:
        if period not in PERIODS:
            raise ValueError(f"Unsupported period. Choose one of: {', '.join(sorted(PERIODS))}")
        yahoo_symbol, resolved_exchange = resolve_yahoo_symbol(symbol, exchange)
        frame = _yfinance().Ticker(yahoo_symbol).history(
            period=period, interval="1d", auto_adjust=False
        )
        if frame is None or frame.empty:
            raise ValueError(f"No daily price history found for {yahoo_symbol}")
        bars = []
        for stamp, row in frame.iterrows():
            day = stamp.date().isoformat() if hasattr(stamp, "date") else str(stamp)[:10]
            bars.append(MarketHistoryBar(
                date=day, open=_number(row.get("Open")), high=_number(row.get("High")),
                low=_number(row.get("Low")), close=_number(row.get("Close")),
                adjusted_close=_number(row.get("Adj Close")),
                volume=int(_number(row.get("Volume")) or 0),
            ))
        return IndianMarketHistory(
            symbol=yahoo_symbol.rsplit(".", 1)[0], yahoo_symbol=yahoo_symbol,
            exchange=resolved_exchange, currency="INR", period=period, interval="1d",
            source=self.source, source_note=self.source_note, bars=bars,
        )

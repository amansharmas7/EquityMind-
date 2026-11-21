import pytest

from equitymind.indian_market import resolve_yahoo_symbol, INDIA_WATCHLIST


@pytest.mark.parametrize(
    ("symbol", "exchange", "expected"),
    [
        ("RELIANCE", "NSE", "RELIANCE.NS"),
        ("tcs", "NSE", "TCS.NS"),
        ("500325", "BSE", "500325.BO"),
        ("INFY.NS", "BSE", "INFY.NS"),
        ("500325.BO", "NSE", "500325.BO"),
    ],
)
def test_indian_symbol_resolution(symbol, exchange, expected):
    assert resolve_yahoo_symbol(symbol, exchange)[0] == expected


@pytest.mark.parametrize("symbol", ["", "../etc/passwd", "ABC/EVIL", "ABC?x=1", " "])
def test_invalid_indian_symbols_are_rejected(symbol):
    with pytest.raises(ValueError):
        resolve_yahoo_symbol(symbol)


def test_curated_watchlist_contains_indian_listed_symbols():
    assert len(INDIA_WATCHLIST) >= 15
    assert "RELIANCE" in {row["symbol"] for row in INDIA_WATCHLIST}

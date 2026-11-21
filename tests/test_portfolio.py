import pytest

from equitymind.portfolio import analyze_portfolio
from equitymind.schemas import PortfolioRequest


def test_portfolio_weights_sum_to_one_and_sector_mix_is_reported():
    request = PortfolioRequest(positions=[
        {"ticker": "MSFT", "market_value": 60, "sector": "Technology"},
        {"ticker": "JPM", "market_value": 40, "sector": "Financials"},
    ])
    result = analyze_portfolio(request)
    assert result.total_value == 100
    assert sum(row["weight"] for row in result.positions) == pytest.approx(1.0)
    assert result.sector_weights == {"Technology": 0.6, "Financials": 0.4}


def test_single_position_is_concentrated_and_stress_is_negative():
    result = analyze_portfolio(PortfolioRequest(positions=[
        {"ticker": "NVDA", "market_value": 100, "sector": "Technology"},
    ]))
    assert result.herfindahl_index == 1
    assert result.concentration_label == "concentrated"
    assert result.estimated_stress_loss_pct < 0


def test_custom_sector_shocks_override_defaults():
    request = PortfolioRequest(
        positions=[{"ticker": "A", "market_value": 100, "sector": "Technology"}],
        sector_shocks={"Technology": -0.25},
    )
    result = analyze_portfolio(request)
    assert result.estimated_stress_loss_pct == -25


def test_duplicate_ticker_positions_contribute_to_same_concentration_bucket():
    result = analyze_portfolio(PortfolioRequest(positions=[
        {"ticker": "AAA", "market_value": 25, "sector": "Tech"},
        {"ticker": "AAA", "market_value": 25, "sector": "Tech"},
        {"ticker": "BBB", "market_value": 50, "sector": "Other"},
    ]))
    assert result.herfindahl_index == pytest.approx(0.5)


def test_empty_positions_are_rejected_by_schema():
    with pytest.raises(ValueError):
        PortfolioRequest(positions=[])

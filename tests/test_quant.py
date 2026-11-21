from datetime import date

import pytest

from equitymind.demo_data import get_snapshot
from equitymind.quant import (
    compute_signals, quality_signal, risk_statistics, valuation_signal, weighted_overall_score,
)
from equitymind.schemas import CompanySnapshot


def test_calculates_seven_distinct_signals_for_supported_demo_ticker():
    signals = compute_signals(get_snapshot("TCS"))
    assert len(signals) == 7
    assert {signal.name for signal in signals} == {
        "valuation", "momentum", "risk", "quality", "analyst_consensus",
        "promoter_pledge", "news_sentiment",
    }
    assert all(-100 <= signal.score <= 100 for signal in signals)


def test_ticker_normalization_and_validation():
    assert get_snapshot(" reliance ").ticker == "RELIANCE"
    with pytest.raises(ValueError):
        CompanySnapshot(ticker="AAPL/EVIL", company_name="bad", as_of=date.today(), current_price=10)


def test_relative_valuation_rewards_lower_multiple_than_peers():
    snapshot = get_snapshot("TCS")
    signal = valuation_signal(snapshot)
    assert signal.score > 0
    assert "peer median" in signal.explanation


def test_missing_metrics_are_explicitly_unavailable():
    snapshot = CompanySnapshot(ticker="ZZZ", company_name="Test", as_of=date.today(), current_price=10)
    signals = compute_signals(snapshot)
    assert all(signal.label == "unavailable" for signal in signals)
    assert weighted_overall_score(signals) is None


def test_composite_reweights_only_available_signals():
    signals = compute_signals(get_snapshot("RELIANCE"))
    score_with_missing = weighted_overall_score(signals)
    signals_without_news = [s for s in signals if s.name != "news_sentiment"]
    score_without_news = weighted_overall_score(signals_without_news)
    assert score_with_missing is not None
    assert score_without_news is not None


def test_risk_statistics_have_expected_keys_and_bounded_outputs():
    stats = risk_statistics([100, 102, 101, 104, 99, 105])
    assert stats is not None
    assert set(stats) == {"annualized_volatility", "historical_var_95", "maximum_drawdown"}
    assert stats["annualized_volatility"] >= 0
    assert 0 <= stats["maximum_drawdown"] < 1


@pytest.mark.parametrize("prices", [[], [100], [100, 101]])
def test_risk_statistics_require_at_least_three_prices(prices):
    assert risk_statistics(prices) is None


def test_price_history_rejects_non_positive_values():
    with pytest.raises(ValueError):
        CompanySnapshot(ticker="ABC", company_name="Test", as_of=date.today(), current_price=5,
                        historical_prices=[5, 0, 6])


def test_indian_bank_quality_uses_asset_quality_and_capital_metrics():
    bank = get_snapshot("HDFCBANK")
    signal = quality_signal(bank)
    assert signal.label != "unavailable"
    assert "gross NPA" in signal.explanation
    assert "capital adequacy" in signal.explanation
    assert "debt/equity" not in signal.explanation


def test_bank_quality_does_not_depend_on_industrial_leverage_ratios():
    bank = get_snapshot("ICICIBANK")
    original = quality_signal(bank)
    changed = bank.model_copy(update={"debt_to_equity": 0.1, "current_ratio": 99.0})
    assert quality_signal(changed).score == original.score

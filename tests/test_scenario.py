import pytest

from equitymind.scenario import analyze_scenarios
from equitymind.schemas import ScenarioRequest


def sample_request():
    return ScenarioRequest(
        ticker="MSFT", current_price=430, revenue=245_000_000_000,
        shares_outstanding=7_400_000_000, free_cash_flow_margin=0.28,
        cash=80_000_000_000, debt=70_000_000_000,
        revenue_growth=0.10, discount_rate=0.09, terminal_growth=0.025,
    )


def test_scenario_engine_returns_bear_base_bull_cases():
    result = analyze_scenarios(sample_request())
    assert [case.name for case in result.cases] == ["Bear", "Base", "Bull"]
    assert result.cases[0].fair_value_per_share < result.cases[1].fair_value_per_share
    assert result.cases[1].fair_value_per_share < result.cases[2].fair_value_per_share


def test_scenario_upside_is_relative_to_supplied_current_price():
    result = analyze_scenarios(sample_request())
    base = result.cases[1]
    expected = (base.fair_value_per_share / 430 - 1) * 100
    assert base.upside_pct == pytest.approx(expected, abs=0.02)


def test_discount_rate_must_exceed_terminal_growth():
    data = sample_request().model_dump()
    data["discount_rate"] = 0.02
    data["terminal_growth"] = 0.03
    with pytest.raises(ValueError):
        ScenarioRequest(**data)


def test_forecast_horizon_is_bounded():
    data = sample_request().model_dump()
    data["forecast_years"] = 25
    with pytest.raises(ValueError):
        ScenarioRequest(**data)

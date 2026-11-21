"""DCF sensitivity engine with explicit bull, base and bear assumptions."""

from __future__ import annotations

from equitymind.schemas import ScenarioCase, ScenarioRequest, ScenarioResponse


def _dcf_value(
    revenue: float,
    shares_outstanding: float,
    fcf_margin: float,
    growth: float,
    discount_rate: float,
    terminal_growth: float,
    forecast_years: int,
    cash: float,
    debt: float,
) -> float:
    projected_revenue = revenue
    present_value = 0.0
    final_fcf = 0.0
    for year in range(1, forecast_years + 1):
        projected_revenue *= 1 + growth
        free_cash_flow = projected_revenue * fcf_margin
        present_value += free_cash_flow / ((1 + discount_rate) ** year)
        final_fcf = free_cash_flow
    terminal_value = final_fcf * (1 + terminal_growth) / (discount_rate - terminal_growth)
    present_terminal = terminal_value / ((1 + discount_rate) ** forecast_years)
    equity_value = present_value + present_terminal + cash - debt
    return max(0.0, equity_value / shares_outstanding)


def analyze_scenarios(request: ScenarioRequest) -> ScenarioResponse:
    """Produce a deterministic sensitivity grid; cases are assumptions, not forecasts."""
    cases = [
        ("Bear", request.revenue_growth - 0.04, request.discount_rate + 0.02),
        ("Base", request.revenue_growth, request.discount_rate),
        ("Bull", request.revenue_growth + 0.04, max(request.discount_rate - 0.01, request.terminal_growth + 0.015)),
    ]
    results: list[ScenarioCase] = []
    for name, growth, discount in cases:
        fair_value = _dcf_value(
            revenue=request.revenue, shares_outstanding=request.shares_outstanding,
            fcf_margin=request.free_cash_flow_margin, growth=growth, discount_rate=discount,
            terminal_growth=request.terminal_growth, forecast_years=request.forecast_years,
            cash=request.cash, debt=request.debt,
        )
        results.append(ScenarioCase(
            name=name, growth_rate=round(growth, 4), discount_rate=round(discount, 4),
            fair_value_per_share=round(fair_value, 2),
            upside_pct=round((fair_value / request.current_price - 1) * 100, 2),
        ))
    return ScenarioResponse(
        ticker=request.ticker, cases=results,
        assumptions=[
            f"Revenue grows at the case-specific rate for {request.forecast_years} years.",
            f"Free-cash-flow margin is held constant at {request.free_cash_flow_margin:.1%}.",
            f"Terminal growth is {request.terminal_growth:.1%}; each case uses its own discount rate.",
            "Cash and debt are added/subtracted from enterprise value; dilution and interim capital changes are not modelled.",
            "The bear/base/bull cases are mechanical sensitivities, not probability-weighted forecasts.",
        ],
    )

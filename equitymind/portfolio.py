"""Portfolio concentration and transparent sector-shock diagnostics."""

from __future__ import annotations

from equitymind.schemas import PortfolioRequest, PortfolioResponse

DEFAULT_SECTOR_SHOCKS = {
    "technology": -0.18,
    "financials": -0.12,
    "health care": -0.09,
    "healthcare": -0.09,
    "consumer discretionary": -0.14,
    "consumer staples": -0.07,
    "energy": -0.16,
    "industrials": -0.11,
    "utilities": -0.06,
    "real estate": -0.15,
    "communication services": -0.13,
    "materials": -0.12,
    "unknown": -0.12,
}


def analyze_portfolio(request: PortfolioRequest) -> PortfolioResponse:
    """Return position weights, HHI, sector mix and a configurable shock estimate."""
    total = sum(position.market_value for position in request.positions)
    if total <= 0:
        raise ValueError("Portfolio total value must be positive")

    weights_by_ticker: dict[str, float] = {}
    sector_values: dict[str, float] = {}
    stress_rows: list[dict] = []
    positions: list[dict] = []
    weighted_loss = 0.0

    normalized_shocks = {key.strip().lower(): value for key, value in request.sector_shocks.items()}
    for position in request.positions:
        weight = position.market_value / total
        weights_by_ticker[position.ticker] = weights_by_ticker.get(position.ticker, 0.0) + weight
        sector = position.sector.strip() or "Unknown"
        sector_values[sector] = sector_values.get(sector, 0.0) + position.market_value
        shock = normalized_shocks.get(sector.lower(), DEFAULT_SECTOR_SHOCKS.get(sector.lower(), -0.12))
        if not -1 <= shock <= 1:
            raise ValueError(f"Stress shock for {sector} must be between -1 and 1")
        contribution = weight * shock
        weighted_loss += contribution
        positions.append({"ticker": position.ticker, "market_value": round(position.market_value, 2),
                          "weight": round(weight, 6), "sector": sector})
        stress_rows.append({"ticker": position.ticker, "sector": sector,
                            "portfolio_weight": round(weight, 6),
                            "assumed_shock": round(shock, 4),
                            "estimated_portfolio_impact": round(contribution * 100, 3)})

    sector_weights = {key: round(value / total, 6) for key, value in sector_values.items()}
    hhi = sum(weight * weight for weight in weights_by_ticker.values())
    top_weight = max(weights_by_ticker.values())
    concentration = "diversified" if hhi < 0.12 else "moderate" if hhi < 0.25 else "concentrated"
    return PortfolioResponse(
        total_value=round(total, 2), positions=sorted(positions, key=lambda row: row["weight"], reverse=True),
        sector_weights=sector_weights, herfindahl_index=round(hhi, 6),
        concentration_label=concentration, top_position_weight=round(top_weight, 6),
        estimated_stress_loss_pct=round(weighted_loss * 100, 3),
        stress_contributions=stress_rows,
    )

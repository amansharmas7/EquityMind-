"""Transparent, deterministic financial signal calculations.

All scores are screening aids, not forecasts or investment recommendations.
"""

from __future__ import annotations

from math import sqrt
from statistics import mean, median, stdev

from equitymind.schemas import CompanySnapshot, Signal


SIGNAL_WEIGHTS: dict[str, float] = {
    "valuation": 0.17,
    "momentum": 0.15,
    "risk": 0.16,
    "quality": 0.20,
    "analyst_consensus": 0.10,
    "promoter_pledge": 0.08,
    "news_sentiment": 0.14,
}


def _label(score: float) -> str:
    if score >= 20:
        return "positive"
    if score <= -20:
        return "negative"
    return "neutral"


def _clamp(value: float, lower: float = -100.0, upper: float = 100.0) -> float:
    return max(lower, min(upper, value))


def _unavailable(name: str, explanation: str) -> Signal:
    return Signal(name=name, score=0, label="unavailable", explanation=explanation, confidence="low")


def valuation_signal(snapshot: CompanySnapshot) -> Signal:
    if snapshot.pe_ratio is None or snapshot.peer_median_pe is None:
        return _unavailable("valuation", "P/E and peer median are required for relative valuation.")
    relative_premium = (snapshot.pe_ratio / snapshot.peer_median_pe) - 1
    score = _clamp(-relative_premium * 100)
    explanation = (
        f"P/E is {relative_premium:+.1%} versus the supplied peer median. "
        "A lower multiple is not automatically cheap; growth, leverage and accounting quality still matter."
    )
    return Signal(name="valuation", score=round(score, 2), label=_label(score), explanation=explanation)


def momentum_signal(snapshot: CompanySnapshot) -> Signal:
    prices = snapshot.historical_prices
    if len(prices) < 23:
        return _unavailable("momentum", "At least 23 ordered price observations are required.")
    start = prices[-min(252, len(prices))]
    anchor = prices[-min(22, len(prices))]
    total_return = (prices[-1] / start) - 1
    recent_return = (prices[-1] / anchor) - 1
    score = _clamp(total_return * 100 * 1.5 - max(0, -recent_return * 100) * 0.5)
    confidence = "high" if len(prices) >= 252 else "medium"
    explanation = f"Observed-window return is {total_return:.1%}; latest ~1-month return is {recent_return:.1%}."
    return Signal(name="momentum", score=round(score, 2), label=_label(score), explanation=explanation,
                  confidence=confidence)


def risk_statistics(prices: list[float]) -> dict[str, float] | None:
    """Compute annualized volatility, historical 95% VaR and maximum drawdown."""
    if len(prices) < 3 or any(price <= 0 for price in prices):
        return None
    returns = [(prices[i] / prices[i - 1]) - 1 for i in range(1, len(prices))]
    volatility = stdev(returns) * sqrt(252) if len(returns) > 1 else 0.0
    ordered = sorted(returns)
    var_index = max(0, int(0.05 * (len(ordered) - 1)))
    var_95 = -ordered[var_index]
    peak = prices[0]
    max_drawdown = 0.0
    for price in prices:
        peak = max(peak, price)
        if peak:
            max_drawdown = max(max_drawdown, (peak - price) / peak)
    return {
        "annualized_volatility": round(volatility, 6),
        "historical_var_95": round(var_95, 6),
        "maximum_drawdown": round(max_drawdown, 6),
    }


def risk_signal(snapshot: CompanySnapshot) -> Signal:
    stats = risk_statistics(snapshot.historical_prices)
    if stats is None:
        return _unavailable("risk", "Insufficient price history to estimate historical risk.")
    # A transparent monotonic screening heuristic. The full metrics remain visible.
    risk_load = stats["annualized_volatility"] * 100 * 1.2 + stats["maximum_drawdown"] * 100 * 0.5
    score = _clamp(35 - risk_load)
    explanation = (
        f"Annualized volatility {stats['annualized_volatility']:.1%}; "
        f"historical 95% one-period VaR {stats['historical_var_95']:.1%}; "
        f"maximum drawdown {stats['maximum_drawdown']:.1%}. "
        "Historical risk is not a guarantee of future loss."
    )
    return Signal(name="risk", score=round(score, 2), label=_label(score), explanation=explanation)


def quality_signal(snapshot: CompanySnapshot) -> Signal:
    components: list[float] = []
    notes: list[str] = []
    sector = snapshot.sector.strip().lower()
    is_bank = sector in {"financials", "banking", "banks", "bank"}

    if snapshot.return_on_equity is not None:
        components.append(_clamp(snapshot.return_on_equity * 100))
        notes.append(f"ROE {snapshot.return_on_equity:.1%}")

    if is_bank:
        # Banks require balance-sheet and asset-quality measures; industrial D/E,
        # current ratio and FCF margin are not directly comparable bank quality inputs.
        if snapshot.gross_npa_pct is not None:
            components.append(_clamp(50 - snapshot.gross_npa_pct * 15))
            notes.append(f"gross NPA {snapshot.gross_npa_pct:.2f}%")
        if snapshot.net_npa_pct is not None:
            components.append(_clamp(50 - snapshot.net_npa_pct * 30))
            notes.append(f"net NPA {snapshot.net_npa_pct:.2f}%")
        if snapshot.capital_adequacy_pct is not None:
            components.append(_clamp((snapshot.capital_adequacy_pct - 12) * 6))
            notes.append(f"capital adequacy {snapshot.capital_adequacy_pct:.2f}%")
        if snapshot.net_interest_margin_pct is not None:
            components.append(_clamp(snapshot.net_interest_margin_pct * 10))
            notes.append(f"NIM {snapshot.net_interest_margin_pct:.2f}%")
        if snapshot.casa_ratio_pct is not None:
            components.append(_clamp((snapshot.casa_ratio_pct - 20) * 2))
            notes.append(f"CASA {snapshot.casa_ratio_pct:.2f}%")
        if snapshot.provision_coverage_pct is not None:
            components.append(_clamp((snapshot.provision_coverage_pct - 40) * 1.2))
            notes.append(f"provision coverage {snapshot.provision_coverage_pct:.2f}%")
    else:
        if snapshot.free_cash_flow_margin is not None:
            components.append(_clamp(snapshot.free_cash_flow_margin * 200))
            notes.append(f"FCF margin {snapshot.free_cash_flow_margin:.1%}")
        if snapshot.debt_to_equity is not None:
            components.append(_clamp(60 - snapshot.debt_to_equity * 35))
            notes.append(f"debt/equity {snapshot.debt_to_equity:.2f}")
        if snapshot.current_ratio is not None:
            components.append(_clamp((snapshot.current_ratio - 1) * 40))
            notes.append(f"current ratio {snapshot.current_ratio:.2f}")
        if snapshot.operating_margin is not None:
            components.append(_clamp(snapshot.operating_margin * 150))
            notes.append(f"operating margin {snapshot.operating_margin:.1%}")

    if not components:
        return _unavailable("quality", "No sector-appropriate profitability, capital or asset-quality metrics supplied.")
    score = _clamp(mean(components))
    confidence = "high" if len(components) >= 4 else "medium"
    method = "bank-specific asset-quality/capital/liquidity proxies" if is_bank else "profitability, cash-flow and balance-sheet proxies"
    return Signal(
        name="quality", score=round(score, 2), label=_label(score),
        explanation=f"Quality proxy from {method}: " + "; ".join(notes) +
                    ". This is not a regulatory rating or a formal Piotroski F-score.",
        confidence=confidence,
    )


def analyst_signal(snapshot: CompanySnapshot) -> Signal:
    if snapshot.analyst_target_price is None or snapshot.analyst_count is None:
        return _unavailable("analyst_consensus", "Analyst target and coverage count are required.")
    upside = snapshot.analyst_target_price / snapshot.current_price - 1
    score = _clamp(upside * 150)
    confidence = "high" if snapshot.analyst_count >= 15 else "low" if snapshot.analyst_count < 5 else "medium"
    return Signal(name="analyst_consensus", score=round(score, 2), label=_label(score),
                  explanation=f"Mean target implies {upside:.1%} upside from {snapshot.analyst_count} analysts. "
                              "Sell-side estimates can be biased and are not a price forecast.",
                  confidence=confidence)


def promoter_pledge_signal(snapshot: CompanySnapshot) -> Signal:
    """Screen the share of promoter holdings pledged, as disclosed in shareholding patterns."""
    if snapshot.promoter_pledge_pct is None:
        return _unavailable(
            "promoter_pledge",
            "Promoter pledge data is unavailable; inspect the latest NSE/BSE shareholding-pattern filing.",
        )
    score = _clamp(35 - snapshot.promoter_pledge_pct * 4)
    return Signal(
        name="promoter_pledge", score=round(score, 2), label=_label(score),
        explanation=(
            f"{snapshot.promoter_pledge_pct:.2f}% of promoter shareholding is reported pledged. "
            "A higher pledge level can increase governance and collateral-call risk; verify the "
            "period and denominator in the source shareholding-pattern filing."
        ),
    )


def news_sentiment_signal(snapshot: CompanySnapshot) -> Signal:
    scores = [item.sentiment_score for item in snapshot.news]
    if not scores:
        return _unavailable("news_sentiment", "No scored news items are available.")
    avg = mean(scores)
    score = _clamp(avg * 100)
    confidence = "low" if len(scores) < 5 else "medium" if len(scores) < 15 else "high"
    return Signal(name="news_sentiment", score=round(score, 2), label=_label(score),
                  explanation=f"Average FinBERT-style polarity is {avg:+.2f} across {len(scores)} supplied items. "
                              "Check article relevance and publication dates.",
                  confidence=confidence)


def compute_signals(snapshot: CompanySnapshot) -> list[Signal]:
    """Calculate seven independent signals; unavailable inputs remain explicit."""
    return [
        valuation_signal(snapshot), momentum_signal(snapshot), risk_signal(snapshot),
        quality_signal(snapshot), analyst_signal(snapshot), promoter_pledge_signal(snapshot),
        news_sentiment_signal(snapshot),
    ]


def weighted_overall_score(signals: list[Signal]) -> float | None:
    """Reweight only available signals to avoid treating missing data as neutral."""
    available = [signal for signal in signals if signal.label != "unavailable"]
    if not available:
        return None
    total_weight = sum(SIGNAL_WEIGHTS.get(signal.name, 0) for signal in available)
    if total_weight <= 0:
        return None
    value = sum(signal.score * SIGNAL_WEIGHTS[signal.name] for signal in available) / total_weight
    return round(_clamp(value), 2)

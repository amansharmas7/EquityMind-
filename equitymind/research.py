"""Research orchestration with an optional LangGraph execution path."""

from __future__ import annotations

from typing import Any, TypedDict

from equitymind.demo_data import get_demo_evidence, get_snapshot
from equitymind.quant import compute_signals, risk_statistics, weighted_overall_score
from equitymind.schemas import EvidenceItem, ResearchRequest, ResearchResponse


class ResearchState(TypedDict, total=False):
    request: ResearchRequest
    snapshot: Any
    evidence: list[EvidenceItem]
    signals: list[Any]
    overall_score: float | None
    response: ResearchResponse


def _risk_notes(snapshot) -> list[str]:
    notes: list[str] = []
    if snapshot.debt_to_equity is not None and snapshot.debt_to_equity > 1.5:
        notes.append(f"Elevated debt/equity ({snapshot.debt_to_equity:.2f}) deserves balance-sheet review.")
    if snapshot.revenue_growth is not None and snapshot.revenue_growth < 0:
        notes.append(f"Reported revenue growth is negative ({snapshot.revenue_growth:.1%}).")
    if snapshot.promoter_pledge_pct is not None and snapshot.promoter_pledge_pct >= 20:
        notes.append(f"Promoter shareholding pledge is elevated at {snapshot.promoter_pledge_pct:.1f}%; review the latest exchange filing.")
    risk = risk_statistics(snapshot.historical_prices)
    if risk and risk["maximum_drawdown"] >= 0.30:
        notes.append(f"Observed-window maximum drawdown is {risk['maximum_drawdown']:.1%}.")
    return notes or ["No threshold-based risk flag fired; this is not evidence that the issuer is low risk."]


def _compose_response(state: ResearchState) -> ResearchResponse:
    snapshot = state["snapshot"]
    signals = state["signals"]
    evidence = state.get("evidence", [])
    score = state.get("overall_score")
    if score is None:
        thesis = "Insufficient data to calculate a composite screen. Review source coverage before forming a view."
    elif score >= 25:
        thesis = "The supplied factors lean constructive, but valuation, downside risk and filing evidence require independent review."
    elif score <= -25:
        thesis = "The supplied factors lean cautious. Identify whether the weak signals reflect temporary conditions or structural deterioration."
    else:
        thesis = "The supplied factors are mixed or close to neutral. A differentiated thesis requires more issuer-specific evidence."
    return ResearchResponse(
        ticker=snapshot.ticker, exchange=snapshot.exchange, currency=snapshot.currency, company_name=snapshot.company_name, as_of=snapshot.as_of,
        overall_score=score, signals=signals, thesis=thesis, key_risks=_risk_notes(snapshot),
        evidence=evidence, evidence_coverage=0.0 if not evidence or all(item.evidence_id.startswith("DEMO-") for item in evidence) else 1.0,
        methodology_notes=[
            "Composite score renormalizes weights over available signals; missing inputs are not treated as neutral.",
            "Signals are screening heuristics and are not calibrated probability estimates or investment advice.",
            "DEMO fixtures are fictional illustrative inputs. Replace them with timestamped provider data before use.",
            "For Indian issuers, use primary NSE/BSE disclosures and citation-audit every company-specific factual claim.",
        ],
        is_demo_data=not evidence or all(item.evidence_id.startswith("DEMO-") for item in evidence),
    )


def run_research(
    request: ResearchRequest,
    snapshot_provider=get_snapshot,
    evidence_provider=get_demo_evidence,
) -> ResearchResponse:
    """Run the sequential path; used as fallback when LangGraph is not installed."""
    snapshot = snapshot_provider(request.ticker)
    evidence = evidence_provider(request.ticker)
    signals = compute_signals(snapshot)
    state: ResearchState = {
        "request": request, "snapshot": snapshot, "evidence": evidence,
        "signals": signals, "overall_score": weighted_overall_score(signals),
    }
    return _compose_response(state)


def build_langgraph():
    """Build the optional LangGraph workflow; returns None when dependency is absent."""
    try:
        from langgraph.graph import END, START, StateGraph
    except ImportError:
        return None

    def load_node(state: ResearchState) -> dict:
        ticker = state["request"].ticker
        return {"snapshot": get_snapshot(ticker), "evidence": get_demo_evidence(ticker)}

    def signal_node(state: ResearchState) -> dict:
        signals = compute_signals(state["snapshot"])
        return {"signals": signals, "overall_score": weighted_overall_score(signals)}

    def report_node(state: ResearchState) -> dict:
        return {"response": _compose_response(state)}

    graph = StateGraph(ResearchState)
    graph.add_node("load_sources", load_node)
    graph.add_node("compute_signals", signal_node)
    graph.add_node("compose_research_brief", report_node)
    graph.add_edge(START, "load_sources")
    graph.add_edge("load_sources", "compute_signals")
    graph.add_edge("compute_signals", "compose_research_brief")
    graph.add_edge("compose_research_brief", END)
    return graph.compile()


def run_research_with_graph(request: ResearchRequest) -> ResearchResponse:
    """Execute the LangGraph workflow when installed; otherwise use sequential execution."""
    graph = build_langgraph()
    if graph is None:
        return run_research(request)
    result = graph.invoke({"request": request})
    return result["response"]

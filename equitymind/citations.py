"""Lightweight citation integrity checks for source-grounded research output."""

from __future__ import annotations

import re

from equitymind.schemas import CitationAuditResponse

_CITATION_PATTERN = re.compile(r"\[(E[0-9A-Za-z_-]+)\]")


def audit_citations(answer: str, evidence_ids: list[str]) -> CitationAuditResponse:
    """Verify that cited IDs exist in supplied evidence and report unused evidence."""
    known = set(evidence_ids)
    cited = list(dict.fromkeys(_CITATION_PATTERN.findall(answer)))
    missing = [item for item in cited if item not in known]
    unused = [item for item in evidence_ids if item not in set(cited)]
    denominator = len(set(cited))
    valid_count = denominator - len(missing)
    coverage = valid_count / denominator if denominator else 0.0
    return CitationAuditResponse(
        valid=bool(cited) and not missing,
        cited_ids=cited,
        missing_ids=missing,
        uncited_evidence_ids=unused,
        citation_coverage=round(coverage, 4),
    )

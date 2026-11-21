"""FastAPI service exposing research, portfolio, DCF and citation-audit endpoints."""

from __future__ import annotations

import hmac
import json
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import StreamingResponse

from equitymind import __version__
from equitymind.citations import audit_citations
from equitymind.config import get_settings
from equitymind.demo_data import SNAPSHOTS
from equitymind.portfolio import analyze_portfolio
from equitymind.embeddings import LocalEmbeddingClient
from equitymind.llm import GroqChatClient
from equitymind.pgvector_store import PgVectorStore
from equitymind.rag import chunk_filing_text
from equitymind.sec_edgar import SecEdgarClient
from equitymind.research import run_research_with_graph
from equitymind.scenario import analyze_scenarios
from equitymind.schemas import (
    CitationAuditRequest, CitationAuditResponse, PortfolioRequest, PortfolioResponse,
    ResearchRequest, ResearchResponse, ScenarioRequest, ScenarioResponse,
    FilingIngestRequest, FilingIngestResponse, EvidenceSearchRequest, EvidenceSearchResponse, EvidenceItem,
)
from equitymind.schemas import RAGResearchRequest, RAGResearchResponse, RAGReference

settings = get_settings()
app = FastAPI(
    title="EquityMind Research Studio API",
    version=__version__,
    description="Evidence-aware equity research and portfolio diagnostics. Demo fixtures are clearly labelled.",
)


async def require_api_key(x_api_key: Annotated[str | None, Header()] = None) -> None:
    """Enforce an API key only when one has been configured."""
    expected = settings.api_key
    if expected and (not x_api_key or not hmac.compare_digest(x_api_key, expected)):
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "version": __version__, "demo_mode": settings.demo_mode}


@app.get("/api/v1/universe", dependencies=[Depends(require_api_key)])
async def universe() -> dict:
    """Return the small local demo universe, not a claim of live 250-ticker coverage."""
    return {
        "mode": "demo" if settings.demo_mode else "provider_not_configured",
        "tickers": sorted(SNAPSHOTS),
        "count": len(SNAPSHOTS),
        "note": "Demo fixtures only. Configure a market-data provider for a production universe.",
    }


@app.post("/api/v1/research", response_model=ResearchResponse, dependencies=[Depends(require_api_key)])
async def research(request: ResearchRequest) -> ResearchResponse:
    if not settings.demo_mode:
        raise HTTPException(status_code=503, detail="No live market-data provider is configured. Enable DEMO_MODE for fixtures.")
    try:
        return run_research_with_graph(request)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/api/v1/research/stream", dependencies=[Depends(require_api_key)])
async def research_stream(request: ResearchRequest) -> StreamingResponse:
    """Emit progress and a final JSON event using server-sent events."""
    if not settings.demo_mode:
        raise HTTPException(status_code=503, detail="No live market-data provider is configured")

    async def events():
        yield "event: progress\ndata: " + json.dumps({"stage": "loading", "message": "Loading issuer snapshot"}) + "\n\n"
        try:
            result = run_research_with_graph(request)
        except KeyError as exc:
            yield "event: error\ndata: " + json.dumps({"detail": str(exc)}) + "\n\n"
            return
        yield "event: progress\ndata: " + json.dumps({"stage": "signals", "message": "Computed seven factor signals"}) + "\n\n"
        yield "event: result\ndata: " + result.model_dump_json() + "\n\n"

    return StreamingResponse(events(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"})


@app.post("/api/v1/portfolio/analyze", response_model=PortfolioResponse, dependencies=[Depends(require_api_key)])
async def portfolio(request: PortfolioRequest) -> PortfolioResponse:
    try:
        return analyze_portfolio(request)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/api/v1/scenarios/dcf", response_model=ScenarioResponse, dependencies=[Depends(require_api_key)])
async def scenarios(request: ScenarioRequest) -> ScenarioResponse:
    try:
        return analyze_scenarios(request)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/api/v1/citations/audit", response_model=CitationAuditResponse, dependencies=[Depends(require_api_key)])
async def citations(request: CitationAuditRequest) -> CitationAuditResponse:
    return audit_citations(request.answer, request.evidence_ids)


@app.get("/api/v1/filings/recent/{cik}", dependencies=[Depends(require_api_key)])
async def recent_filings(cik: str) -> dict:
    """Discover recent SEC 10-K and 10-Q filings for a CIK."""
    try:
        client = SecEdgarClient(settings.sec_user_agent)
        filings = await client.recent_filings(cik)
        return {"cik": str(cik).zfill(10), "filings": filings}
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"SEC filing lookup failed: {exc}") from exc


@app.post("/api/v1/filings/ingest", response_model=FilingIngestResponse, dependencies=[Depends(require_api_key)])
async def ingest_filing(request: FilingIngestRequest) -> FilingIngestResponse:
    """Download one SEC filing, chunk it, embed chunks and store them in pgvector."""
    if not settings.database_url:
        raise HTTPException(status_code=503, detail="DATABASE_URL is required for filing ingestion")
    try:
        sec = SecEdgarClient(settings.sec_user_agent)
        text = await sec.fetch_filing_text(request.filing_url)
        chunks = chunk_filing_text(text, max_words=350, overlap_words=50)
        if not chunks:
            raise HTTPException(status_code=422, detail="No filing text could be extracted")
        if len(chunks) > 500:
            raise HTTPException(status_code=413, detail="Filing exceeds the 500-chunk ingestion limit")
        embedder = LocalEmbeddingClient(settings.embedding_model, settings.vector_dimensions)
        vectors = await embedder.embed_texts(chunks)
        store = PgVectorStore(settings.database_url)
        stored = store.insert_chunks(
            ticker=request.ticker, cik=request.cik, filing_type=request.filing_type,
            filing_date=request.filing_date, accession_number=request.accession_number,
            source_url=request.filing_url, chunks=chunks, embeddings=vectors,
        )
        return FilingIngestResponse(
            ticker=request.ticker, filing_type=request.filing_type, filing_date=request.filing_date,
            chunks_stored=stored, source_url=request.filing_url,
        )
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Filing ingestion failed: {exc}") from exc


@app.post("/api/v1/evidence/search", response_model=EvidenceSearchResponse, dependencies=[Depends(require_api_key)])
async def search_evidence(request: EvidenceSearchRequest) -> EvidenceSearchResponse:
    """Retrieve the most similar stored filing passages for one ticker."""
    if not settings.database_url:
        raise HTTPException(status_code=503, detail="DATABASE_URL is required for evidence search")
    try:
        embedder = LocalEmbeddingClient(settings.embedding_model, settings.vector_dimensions)
        vector = await embedder.embed_query(request.question)
        rows = PgVectorStore(settings.database_url).search(request.ticker, vector, request.top_k)
        results = [EvidenceItem(
            evidence_id=row["evidence_id"], ticker=row["ticker"], filing_type=row["filing_type"],
            filing_date=row["filing_date"], section=row["section"], text=row["text"],
            similarity=max(0.0, min(1.0, float(row["similarity"]))), source_url=row["source_url"],
        ) for row in rows]
        return EvidenceSearchResponse(ticker=request.ticker, query=request.question, results=results)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Evidence retrieval failed: {exc}") from exc



@app.post("/api/v1/research/rag", response_model=RAGResearchResponse, dependencies=[Depends(require_api_key)])
async def rag_research(request: RAGResearchRequest) -> RAGResearchResponse:
    """Retrieve filing evidence from pgvector and synthesize a cited answer with OpenAI."""
    if not settings.database_url or not settings.groq_api_key:
        raise HTTPException(
            status_code=503,
            detail="DATABASE_URL and GROQ_API_KEY are required for filing-grounded RAG research",
        )
    try:
        embedder = LocalEmbeddingClient(settings.embedding_model, settings.vector_dimensions)
        query_vector = await embedder.embed_query(request.question)
        rows = PgVectorStore(settings.database_url).search(request.ticker, query_vector, request.top_k)
        if not rows:
            return RAGResearchResponse(
                ticker=request.ticker,
                question=request.question,
                answer=(
                    "No relevant SEC filing passages were found for this ticker and question. "
                    "Ingest a recent filing before requesting a filing-grounded answer."
                ),
                references=[],
                citation_audit=audit_citations("", []),
                model=settings.groq_model,
                no_evidence=True,
            )
        references = [
            RAGReference(
                citation_id=f"E{index}",
                evidence_id=row["evidence_id"],
                ticker=row["ticker"],
                filing_type=row["filing_type"],
                filing_date=row["filing_date"],
                section=row["section"],
                text=row["text"],
                similarity=max(0.0, min(1.0, float(row["similarity"]))),
                source_url=row["source_url"],
            )
            for index, row in enumerate(rows, start=1)
        ]
        answer = await GroqChatClient(
            settings.groq_api_key, settings.groq_model
        ).generate_answer(
            ticker=request.ticker,
            question=request.question,
            references=[
                {
                    "filing_type": item.filing_type,
                    "filing_date": item.filing_date,
                    "section": item.section,
                    "source_url": item.source_url,
                    "similarity": item.similarity,
                    "text": item.text,
                }
                for item in references
            ],
        )
        audit = audit_citations(answer, [item.citation_id for item in references])
        return RAGResearchResponse(
            ticker=request.ticker, question=request.question, answer=answer,
            references=references, citation_audit=audit,
            model=settings.groq_model, no_evidence=False,
        )
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        # Avoid returning provider response bodies or credentials to the API caller.
        raise HTTPException(
            status_code=502,
            detail="RAG research failed. Check server logs and verify OpenAI/pgvector configuration.",
        ) from exc

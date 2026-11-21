CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS filing_chunks (
    evidence_id TEXT PRIMARY KEY,
    ticker VARCHAR(10) NOT NULL,
    cik VARCHAR(10) NOT NULL,
    filing_type VARCHAR(8) NOT NULL CHECK (filing_type IN ('10-K', '10-Q', '8-K')),
    filing_date DATE NOT NULL,
    accession_number TEXT NOT NULL,
    section TEXT NOT NULL,
    chunk_index INTEGER NOT NULL CHECK (chunk_index >= 0),
    text TEXT NOT NULL,
    source_url TEXT NOT NULL,
    embedding VECTOR(1536) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (ticker, accession_number, section, chunk_index)
);

CREATE INDEX IF NOT EXISTS filing_chunks_ticker_date_idx
    ON filing_chunks (ticker, filing_date DESC);

CREATE INDEX IF NOT EXISTS filing_chunks_embedding_idx
    ON filing_chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

CREATE TABLE IF NOT EXISTS research_runs (
    run_id UUID PRIMARY KEY,
    ticker VARCHAR(10) NOT NULL,
    question TEXT NOT NULL,
    overall_score NUMERIC(7, 2),
    result JSONB NOT NULL,
    is_demo_data BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS research_runs_ticker_date_idx
    ON research_runs (ticker, created_at DESC);

CREATE TABLE IF NOT EXISTS investment_theses (
    thesis_id UUID PRIMARY KEY,
    ticker VARCHAR(10) NOT NULL,
    title TEXT NOT NULL,
    thesis_text TEXT NOT NULL,
    catalysts JSONB NOT NULL DEFAULT '[]'::jsonb,
    invalidation_conditions JSONB NOT NULL DEFAULT '[]'::jsonb,
    status VARCHAR(16) NOT NULL DEFAULT 'active'
        CHECK (status IN ('active', 'watch', 'invalidated', 'closed')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS investment_theses_ticker_status_idx
    ON investment_theses (ticker, status);

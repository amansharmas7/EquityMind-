CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS filing_chunks (
    evidence_id TEXT PRIMARY KEY,
    ticker VARCHAR(20) NOT NULL,
    cik VARCHAR(10),
    market_country CHAR(2) NOT NULL DEFAULT 'US',
    exchange VARCHAR(4),
    issuer_id VARCHAR(20),
    filing_type VARCHAR(40) NOT NULL,
    filing_date DATE NOT NULL,
    accession_number TEXT NOT NULL,
    section TEXT NOT NULL,
    chunk_index INTEGER NOT NULL CHECK (chunk_index >= 0),
    text TEXT NOT NULL,
    source_url TEXT NOT NULL,
    embedding VECTOR(384) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (ticker, accession_number, section, chunk_index)
);

-- Idempotent migration for databases created by the earlier SEC-only schema.
ALTER TABLE research_runs ALTER COLUMN ticker TYPE VARCHAR(20);
ALTER TABLE investment_theses ALTER COLUMN ticker TYPE VARCHAR(20);
ALTER TABLE filing_chunks ALTER COLUMN cik DROP NOT NULL;
ALTER TABLE filing_chunks ALTER COLUMN ticker TYPE VARCHAR(20);
ALTER TABLE filing_chunks ALTER COLUMN filing_type TYPE VARCHAR(40);
ALTER TABLE filing_chunks DROP CONSTRAINT IF EXISTS filing_chunks_filing_type_check;
ALTER TABLE filing_chunks ADD COLUMN IF NOT EXISTS market_country CHAR(2) NOT NULL DEFAULT 'US';
ALTER TABLE filing_chunks ADD COLUMN IF NOT EXISTS exchange VARCHAR(4);
ALTER TABLE filing_chunks ADD COLUMN IF NOT EXISTS issuer_id VARCHAR(20);

CREATE INDEX IF NOT EXISTS filing_chunks_ticker_date_idx
    ON filing_chunks (ticker, filing_date DESC);
CREATE INDEX IF NOT EXISTS filing_chunks_market_idx
    ON filing_chunks (market_country, exchange, ticker, filing_date DESC);
CREATE INDEX IF NOT EXISTS filing_chunks_embedding_idx
    ON filing_chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

CREATE TABLE IF NOT EXISTS research_runs (
    run_id UUID PRIMARY KEY,
    ticker VARCHAR(20) NOT NULL,
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
    ticker VARCHAR(20) NOT NULL,
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

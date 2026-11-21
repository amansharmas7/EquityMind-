# Contributing

Thanks for your interest in EquityMind Research Studio.

## Development workflow

1. Open an issue describing the defect or proposed change.
2. Keep pull requests focused and explain the research or engineering impact.
3. Add tests for changed calculation, API, data-ingestion, or retrieval behaviour.
4. Preserve source provenance and keep synthetic fixtures clearly labelled.
5. Update the README or architecture notes when API contracts, configuration, or provider limitations change.
6. Never commit API keys, database passwords, local environment files, or private issuer documents.

## Local setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
pytest
```

Install additional extras only when testing those integrations:

```powershell
python -m pip install -e ".[india-market,database,local-embeddings]"
```

## Pull request checklist

- [ ] Tests pass locally and in GitHub Actions.
- [ ] New behaviour has focused tests.
- [ ] Source dates, exchange, ticker and currency are explicit where applicable.
- [ ] Missing data is represented as unavailable, not silently fabricated.
- [ ] No credentials or private data are included.

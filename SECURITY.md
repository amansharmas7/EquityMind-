# Security Policy

## Supported versions

Security fixes are currently provided for the latest revision on the `main` branch.

## Reporting a vulnerability

Do not disclose exploitable details in a public issue. Use GitHub's private vulnerability reporting feature for this repository, when available. Include the affected commit/version, reproduction steps, impact, and mitigation guidance. Do not include real credentials or private customer/issuer data.

## Deployment safeguards

- Keep `.env` private; never commit Groq API keys, database credentials, or API authentication keys.
- Bind the local development API to localhost unless a properly authenticated deployment is configured.
- Treat yfinance as a non-authoritative daily research source; use appropriately licensed market data for production.
- Ingest documents only from trusted, official NSE/BSE domains and preserve original filing URLs and dates.
- Review database access, retention, and backup settings before storing research documents.
- This prototype is not a broker, order-management system, or source of personalised investment advice.

"""Minimal SEC EDGAR submissions client for discovering recent company filings."""

from __future__ import annotations

from datetime import date
from typing import Any

import httpx


class SecEdgarClient:
    """Fetch public SEC submissions metadata using a descriptive User-Agent."""

    BASE_URL = "https://data.sec.gov/submissions/"

    def __init__(self, user_agent: str, timeout: float = 20.0):
        if not user_agent or "@" not in user_agent:
            raise ValueError("SEC User-Agent must contain a contact email address")
        self.headers = {"User-Agent": user_agent, "Accept-Encoding": "gzip, deflate"}
        self.timeout = timeout

    async def recent_filings(self, cik: str, forms: tuple[str, ...] = ("10-K", "10-Q")) -> list[dict[str, Any]]:
        normalized_cik = str(cik).strip().zfill(10)
        if not normalized_cik.isdigit() or len(normalized_cik) != 10:
            raise ValueError("CIK must be numeric")
        async with httpx.AsyncClient(timeout=self.timeout, headers=self.headers) as client:
            response = await client.get(f"{self.BASE_URL}CIK{normalized_cik}.json")
            response.raise_for_status()
            payload = response.json()
        recent = payload.get("filings", {}).get("recent", {})
        forms_list = recent.get("form", [])
        accession = recent.get("accessionNumber", [])
        filed = recent.get("filingDate", [])
        primary = recent.get("primaryDocument", [])
        company = payload.get("name", "Unknown issuer")
        output = []
        for index, form in enumerate(forms_list):
            if form not in forms:
                continue
            acc = accession[index]
            acc_path = acc.replace("-", "")
            output.append({
                "company": company,
                "cik": normalized_cik,
                "form": form,
                "filing_date": date.fromisoformat(filed[index]),
                "accession_number": acc,
                "primary_document": primary[index],
                "url": f"https://www.sec.gov/Archives/edgar/data/{int(normalized_cik)}/{acc_path}/{primary[index]}",
            })
        return output

    async def fetch_filing_text(self, filing_url: str) -> str:
        """Download a public SEC filing and extract visible text without script/style content."""
        from html.parser import HTMLParser
        from urllib.parse import urlparse

        parsed = urlparse(filing_url)
        if (
            parsed.scheme != "https"
            or parsed.netloc.lower() not in {"www.sec.gov", "sec.gov"}
            or not parsed.path.startswith("/Archives/edgar/data/")
        ):
            raise ValueError("Only HTTPS SEC EDGAR archive filing URLs are accepted")

        class VisibleTextParser(HTMLParser):
            def __init__(self):
                super().__init__(convert_charrefs=True)
                self.parts: list[str] = []
                self.skip_depth = 0

            def handle_starttag(self, tag, attrs):
                if tag.lower() in {"script", "style", "ix:header"}:
                    self.skip_depth += 1
                if tag.lower() in {"p", "div", "br", "tr", "h1", "h2", "h3"}:
                    self.parts.append("\n")

            def handle_endtag(self, tag):
                if tag.lower() in {"script", "style", "ix:header"} and self.skip_depth:
                    self.skip_depth -= 1
                if tag.lower() in {"p", "div", "tr", "h1", "h2", "h3"}:
                    self.parts.append("\n")

            def handle_data(self, data):
                if not self.skip_depth:
                    self.parts.append(data)

        async with httpx.AsyncClient(timeout=45.0, headers=self.headers, follow_redirects=True) as client:
            response = await client.get(filing_url)
            response.raise_for_status()
        if response.url.host.lower() not in {"www.sec.gov", "sec.gov"}:
            raise ValueError("SEC filing download redirected outside sec.gov")
        if len(response.content) > 25_000_000:
            raise ValueError("Filing response exceeds the 25 MB safety limit")
        parser = VisibleTextParser()
        parser.feed(response.text)
        return " ".join(" ".join(parser.parts).split())

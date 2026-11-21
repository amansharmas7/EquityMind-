"""Download searchable documents from official Indian exchange domains."""
from __future__ import annotations

from html.parser import HTMLParser
from urllib.parse import urlparse

import httpx

_ALLOWED_ROOTS = ("nseindia.com", "bseindia.com")


def _is_exchange_host(host: str) -> bool:
    host = host.lower().rstrip(".")
    return any(host == root or host.endswith("." + root) for root in _ALLOWED_ROOTS)


class _VisibleTextParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.skip_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag.lower() in {"script", "style", "noscript", "svg"}:
            self.skip_depth += 1
        if tag.lower() in {"p", "div", "br", "tr", "h1", "h2", "h3", "li"}:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag.lower() in {"script", "style", "noscript", "svg"} and self.skip_depth:
            self.skip_depth -= 1
        if tag.lower() in {"p", "div", "tr", "h1", "h2", "h3", "li"}:
            self.parts.append("\n")

    def handle_data(self, data):
        if not self.skip_depth:
            self.parts.append(data)


class IndianExchangeDocumentClient:
    """Extract text from HTTPS NSE/BSE disclosures or searchable PDFs."""

    async def fetch_document_text(self, source_url: str) -> str:
        parsed = urlparse(source_url)
        if parsed.scheme != "https" or not parsed.hostname or not _is_exchange_host(parsed.hostname):
            raise ValueError("Only HTTPS documents hosted on NSE India or BSE India are accepted")
        async with httpx.AsyncClient(
            timeout=45.0,
            follow_redirects=True,
            headers={"User-Agent": "EquityMindResearchStudio/0.2 (research prototype)"},
        ) as client:
            response = await client.get(source_url)
            response.raise_for_status()
        final_host = (response.url.host or "").lower()
        if not _is_exchange_host(final_host):
            raise ValueError("Exchange document redirected outside NSE India/BSE India")
        if len(response.content) > 25_000_000:
            raise ValueError("Disclosure exceeds the 25 MB safety limit")
        content_type = response.headers.get("content-type", "").lower()
        if "pdf" in content_type or response.content.startswith(b"%PDF"):
            try:
                from io import BytesIO
                from pypdf import PdfReader
            except ImportError as exc:
                raise RuntimeError(
                    'PDF extraction dependency is missing. Install with: pip install -e ".[india-market]"'
                ) from exc
            reader = PdfReader(BytesIO(response.content))
            text = " ".join((page.extract_text() or "") for page in reader.pages)
        else:
            parser = _VisibleTextParser()
            parser.feed(response.text)
            text = " ".join(parser.parts)
        cleaned = " ".join(text.split())
        if not cleaned:
            raise ValueError("No searchable text was extracted from the exchange document")
        return cleaned

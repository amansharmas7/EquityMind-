"""OpenAI embedding adapter implemented over the public HTTPS API."""

from __future__ import annotations

import httpx


class OpenAIEmbeddingClient:
    """Create normalized embeddings with an explicit model and vector size."""

    def __init__(self, api_key: str, model: str = "text-embedding-3-small", dimensions: int = 1536):
        if not api_key:
            raise ValueError("OPENAI_API_KEY is required for embedding generation")
        self.api_key = api_key
        self.model = model
        self.dimensions = dimensions

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        clean = [text.strip() for text in texts]
        if not clean or any(not text for text in clean):
            raise ValueError("Embedding input must contain non-empty text")
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                "https://api.openai.com/v1/embeddings",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={"model": self.model, "input": clean, "dimensions": self.dimensions},
            )
            response.raise_for_status()
            payload = response.json()
        rows = sorted(payload.get("data", []), key=lambda item: item["index"])
        vectors = [row["embedding"] for row in rows]
        if len(vectors) != len(clean) or any(len(vector) != self.dimensions for vector in vectors):
            raise RuntimeError("Embedding API returned an unexpected number of vectors or dimensions")
        return vectors

    async def embed_query(self, text: str) -> list[float]:
        vectors = await self.embed_texts([text])
        return vectors[0]

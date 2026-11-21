"""Free local sentence-transformer embeddings; no hosted embedding API key required."""
from __future__ import annotations
from functools import lru_cache

@lru_cache(maxsize=2)
def _load_model(model_name: str):
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:
        raise RuntimeError("Install local embedding dependencies: pip install -e '.[local-embeddings]'") from exc
    return SentenceTransformer(model_name, device="cpu")

class LocalEmbeddingClient:
    """Generate normalized 384-dimensional vectors locally."""
    def __init__(self, model: str = "sentence-transformers/all-MiniLM-L6-v2", dimensions: int = 384):
        if dimensions != 384:
            raise ValueError("all-MiniLM-L6-v2 returns 384 dimensions; VECTOR_DIMENSIONS must be 384")
        self.model_name, self.dimensions = model, dimensions

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        clean = [text.strip() for text in texts]
        if not clean or any(not text for text in clean):
            raise ValueError("Embedding input must contain non-empty text")
        vectors = _load_model(self.model_name).encode(
            clean, normalize_embeddings=True, convert_to_numpy=True, show_progress_bar=False
        ).tolist()
        if len(vectors) != len(clean) or any(len(v) != self.dimensions for v in vectors):
            raise RuntimeError("Local embedding model returned an unexpected vector shape")
        return vectors

    async def embed_query(self, text: str) -> list[float]:
        return (await self.embed_texts([text]))[0]

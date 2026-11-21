"""Optional FinBERT inference adapter, loaded lazily to keep API startup light."""

from __future__ import annotations

from functools import lru_cache
from typing import Iterable


class FinBertScorer:
    """Score finance headlines using a local ProsusAI/finbert pipeline.

    Install the optional NLP dependencies with ``pip install -e '.[nlp]'``.
    The output is positive probability minus negative probability.
    """

    def __init__(self, model_name: str = "ProsusAI/finbert", device: int = -1):
        self.model_name = model_name
        self.device = device
        self._pipeline = None

    def _load(self):
        if self._pipeline is None:
            try:
                from transformers import pipeline
            except ImportError as exc:
                raise RuntimeError("Install the optional NLP dependencies: pip install -e '.[nlp]'") from exc
            self._pipeline = pipeline(
                task="text-classification", model=self.model_name, tokenizer=self.model_name,
                top_k=None, device=self.device,
            )
        return self._pipeline

    def score(self, texts: Iterable[str]) -> list[float]:
        inputs = [text.strip() for text in texts if text and text.strip()]
        if not inputs:
            return []
        outputs = self._load()(inputs, truncation=True, max_length=512)
        values: list[float] = []
        for item in outputs:
            scores = {row["label"].lower(): float(row["score"]) for row in item}
            values.append(max(-1.0, min(1.0, scores.get("positive", 0.0) - scores.get("negative", 0.0))))
        return values

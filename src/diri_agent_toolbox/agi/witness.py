"""Witness relevance scoring — embedding similarity (RAG-style), no stop-word lists."""

from __future__ import annotations

import math
from typing import Any, Callable, Dict, List, Protocol, Sequence

TextEmbedder = Callable[[Sequence[str]], Sequence[Sequence[float]]]


class SupportsEmbed(Protocol):
    def embed(self, texts: Sequence[str]) -> Sequence[Sequence[float]]: ...


def cosine_similarity(a: Sequence[float], b: Sequence[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


def _overlap_fallback(question: str, quote: str) -> float:
    """Lexical fallback when no embedder is configured (no curated stop-word list)."""
    q_words = set(question.lower().split())
    quote_words = set(quote.lower().split())
    if not q_words:
        return 0.0
    return len(q_words & quote_words) / len(q_words)


def score_witness_match(
    question: str,
    quote: str,
    *,
    embedder: TextEmbedder | SupportsEmbed | None = None,
) -> float:
    """Score question↔quote relevance using embeddings when available."""
    if embedder is not None:
        if hasattr(embedder, "embed"):
            vectors = embedder.embed([question, quote])
        else:
            vectors = embedder([question, quote])
        if len(vectors) >= 2:
            return float(cosine_similarity(vectors[0], vectors[1]))
    return _overlap_fallback(question, quote)


def rank_witness_quotes(
    question: str,
    quotes: Sequence[str],
    *,
    embedder: TextEmbedder | SupportsEmbed | None = None,
    threshold: float = 0.35,
) -> List[Dict[str, Any]]:
    """Rank witness quotes by embedding similarity to the question (RAG retrieval style)."""
    cleaned = [q for q in quotes if q and str(q).strip()]
    if not cleaned:
        return []

    if embedder is not None:
        if hasattr(embedder, "embed"):
            vectors = embedder.embed([question, *cleaned])
        else:
            vectors = embedder([question, *cleaned])
        q_vec = vectors[0]
        scored = [
            {
                "quote": quote,
                "score": float(cosine_similarity(q_vec, vectors[i + 1])),
            }
            for i, quote in enumerate(cleaned)
        ]
    else:
        scored = [
            {"quote": quote, "score": _overlap_fallback(question, quote)} for quote in cleaned
        ]

    scored.sort(key=lambda row: row["score"], reverse=True)
    if threshold > 0:
        scored = [row for row in scored if row["score"] >= threshold]
    return scored

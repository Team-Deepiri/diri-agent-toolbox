"""AGI helpers — witness scoring (RAG embeddings) and training record shaping."""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Mapping, Optional

from diri_agent_toolbox.agi.witness import (
    cosine_similarity,
    rank_witness_quotes,
    score_witness_match,
)


def structured_training_row(
    *,
    instruction: str,
    output: str,
    input_text: str = "",
    category: str = "artifact",
    quality_score: float = 1.0,
    producer: str = "cyrex",
    metadata: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    text = "\n\n".join(p for p in (instruction, input_text, output) if p)
    return {
        "instruction": instruction,
        "input": input_text,
        "output": output,
        "text": text,
        "category": category,
        "quality_score": quality_score,
        "producer": producer,
        "metadata": dict(metadata or {}),
    }


def batch_embed_items(
    texts: Iterable[str],
    *,
    batch_size: int = 32,
) -> List[List[str]]:
    """Chunk texts for embedding workers."""
    batch: List[str] = []
    batches: List[List[str]] = []
    for text in texts:
        batch.append(text)
        if len(batch) >= batch_size:
            batches.append(batch)
            batch = []
    if batch:
        batches.append(batch)
    return batches


__all__ = [
    "batch_embed_items",
    "cosine_similarity",
    "rank_witness_quotes",
    "score_witness_match",
    "structured_training_row",
]

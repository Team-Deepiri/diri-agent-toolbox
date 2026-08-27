"""Tests for embedding-based witness scoring."""

from diri_agent_toolbox.agi.witness import (
    cosine_similarity,
    rank_witness_quotes,
    score_witness_match,
)


def _mock_embedder(texts):
    # Simple 2-d vectors: dim0 = has "rent", dim1 = has "termination"
    out = []
    for t in texts:
        low = t.lower()
        out.append([1.0 if "rent" in low else 0.0, 1.0 if "termination" in low else 0.0])
    return out


class TestWitnessScoring:
    def test_cosine_identical(self):
        assert cosine_similarity([1.0, 0.0], [1.0, 0.0]) == 1.0

    def test_embedder_ranks_rent_question(self):
        ranked = rank_witness_quotes(
            "What is the base rent?",
            [
                "The base rent shall be $4,500 per month.",
                "Termination clause is 90 days.",
            ],
            embedder=_mock_embedder,
            threshold=0.0,
        )
        assert ranked[0]["quote"].startswith("The base rent")

    def test_score_without_embedder_uses_overlap(self):
        score = score_witness_match(
            "base rent amount",
            "The base rent shall be $4,500",
            embedder=None,
        )
        assert score > 0.3

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, cast

try:
    import numpy as np

    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False


class ConfidenceLevel(str, Enum):
    VERY_HIGH = "very_high"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    VERY_LOW = "very_low"


class ConfidenceSource(str, Enum):
    MODEL_PREDICTION = "model_prediction"
    TRAINING_DATA_COVERAGE = "training_data_coverage"
    FEATURE_QUALITY = "feature_quality"
    CONTEXT_MATCH = "context_match"
    HISTORICAL_ACCURACY = "historical_accuracy"
    ENSEMBLE_AGREEMENT = "ensemble_agreement"


@dataclass
class ConfidenceAttributes:
    base_score: float
    level: ConfidenceLevel
    sources: Dict[str, float]
    uncertainty: float
    calibration: float
    reliability: float
    explanation: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "base_score": self.base_score,
            "level": self.level.value,
            "sources": self.sources,
            "uncertainty": self.uncertainty,
            "calibration": self.calibration,
            "reliability": self.reliability,
            "explanation": self.explanation,
        }


class ConfidenceCalculator:
    def __init__(self) -> None:
        self.thresholds = {
            ConfidenceLevel.VERY_HIGH: 0.9,
            ConfidenceLevel.HIGH: 0.75,
            ConfidenceLevel.MEDIUM: 0.5,
            ConfidenceLevel.LOW: 0.25,
            ConfidenceLevel.VERY_LOW: 0.0,
        }

    def calculate(
        self,
        probabilities: list[float],
        top_k_probs: Optional[List[float]] = None,
        training_coverage: Optional[float] = None,
        feature_quality: Optional[float] = None,
        context_match: Optional[float] = None,
        historical_accuracy: Optional[Dict[int, float]] = None,
    ) -> ConfidenceAttributes:
        probs = np.array(probabilities) if HAS_NUMPY else probabilities
        n_classes = len(probs)

        if HAS_NUMPY:
            base_score = float(np.max(probs))
            probs_safe = np.clip(probs, 1e-10, 1.0)
            entropy = -float(np.sum(probs_safe * np.log(probs_safe)))
            max_entropy = math.log(n_classes) if n_classes > 1 else 1.0
            uncertainty = entropy / max_entropy if max_entropy > 0 else 0.0
            sorted_probs = np.sort(probs)[::-1]
            margin = float(sorted_probs[0] - sorted_probs[1]) if len(sorted_probs) > 1 else 1.0
            calibration = float(margin)
        else:
            base_score = max(probs) / sum(probs) if sum(probs) > 0 else 0.0
            uncertainty = 0.5
            calibration = 0.5

        sources: Dict[str, float] = {
            ConfidenceSource.MODEL_PREDICTION.value: base_score,
            ConfidenceSource.TRAINING_DATA_COVERAGE.value: training_coverage
            if training_coverage is not None
            else 0.7,
            ConfidenceSource.FEATURE_QUALITY.value: feature_quality
            if feature_quality is not None
            else 0.8,
            ConfidenceSource.CONTEXT_MATCH.value: context_match
            if context_match is not None
            else 0.7,
            ConfidenceSource.HISTORICAL_ACCURACY.value: 0.7,
            ConfidenceSource.ENSEMBLE_AGREEMENT.value: 0.7,
        }

        if historical_accuracy:
            predicted_class = (
                int(np.argmax(probs))
                if HAS_NUMPY
                else cast(list, probs).index(max(cast(list, probs)))
            )
            sources[ConfidenceSource.HISTORICAL_ACCURACY.value] = historical_accuracy.get(
                predicted_class, 0.7
            )

        if top_k_probs and HAS_NUMPY:
            agreement = float(np.std(top_k_probs))
            sources[ConfidenceSource.ENSEMBLE_AGREEMENT.value] = 1.0 - min(agreement, 1.0)

        weights = {
            ConfidenceSource.MODEL_PREDICTION.value: 0.4,
            ConfidenceSource.TRAINING_DATA_COVERAGE.value: 0.15,
            ConfidenceSource.FEATURE_QUALITY.value: 0.15,
            ConfidenceSource.CONTEXT_MATCH.value: 0.1,
            ConfidenceSource.HISTORICAL_ACCURACY.value: 0.1,
            ConfidenceSource.ENSEMBLE_AGREEMENT.value: 0.1,
        }

        reliability = sum(sources[s] * weights.get(s, 0.0) for s in sources)
        reliability *= (1.0 - uncertainty * 0.3) * (0.7 + calibration * 0.3)
        reliability = max(0.0, min(1.0, reliability))
        level = self._level_for(reliability)
        explanation = self._explain(reliability, level, sources, uncertainty, calibration)

        return ConfidenceAttributes(
            base_score=base_score,
            level=level,
            sources=sources,
            uncertainty=uncertainty,
            calibration=calibration,
            reliability=reliability,
            explanation=explanation,
        )

    def should_accept(
        self,
        confidence: ConfidenceAttributes,
        min_reliability: float = 0.7,
        min_level: ConfidenceLevel = ConfidenceLevel.MEDIUM,
    ) -> Tuple[bool, str]:
        level_order = {
            ConfidenceLevel.VERY_LOW: 0,
            ConfidenceLevel.LOW: 1,
            ConfidenceLevel.MEDIUM: 2,
            ConfidenceLevel.HIGH: 3,
            ConfidenceLevel.VERY_HIGH: 4,
        }
        if confidence.reliability < min_reliability:
            return (
                False,
                f"Reliability {confidence.reliability:.2%} below threshold {min_reliability:.2%}",
            )
        if level_order[confidence.level] < level_order[min_level]:
            return (
                False,
                f"Confidence level {confidence.level.value} below required {min_level.value}",
            )
        return True, "Confidence meets requirements"

    def _level_for(self, reliability: float) -> ConfidenceLevel:
        if reliability >= 0.9:
            return ConfidenceLevel.VERY_HIGH
        elif reliability >= 0.75:
            return ConfidenceLevel.HIGH
        elif reliability >= 0.5:
            return ConfidenceLevel.MEDIUM
        elif reliability >= 0.25:
            return ConfidenceLevel.LOW
        return ConfidenceLevel.VERY_LOW

    def _explain(
        self,
        reliability: float,
        level: ConfidenceLevel,
        sources: Dict[str, float],
        uncertainty: float,
        calibration: float,
    ) -> str:
        parts = [f"Confidence: {level.value.replace('_', ' ').title()} ({reliability:.2%})"]
        factors = []
        if sources.get(ConfidenceSource.MODEL_PREDICTION.value, 0) > 0.8:
            factors.append("strong model prediction")
        if sources.get(ConfidenceSource.TRAINING_DATA_COVERAGE.value, 0) > 0.8:
            factors.append("good training coverage")
        if uncertainty < 0.3:
            factors.append("low uncertainty")
        if calibration > 0.5:
            factors.append("clear class separation")
        if factors:
            parts.append(f"Key factors: {', '.join(factors)}")

        concerns = []
        if uncertainty > 0.6:
            concerns.append("high uncertainty")
        if calibration < 0.2:
            concerns.append("unclear class separation")
        if sources.get(ConfidenceSource.TRAINING_DATA_COVERAGE.value, 0) < 0.5:
            concerns.append("limited training coverage")
        if concerns:
            parts.append(f"Concerns: {', '.join(concerns)}")
        return ". ".join(parts) + "."


_calculator: ConfidenceCalculator | None = None


def get_confidence_calculator() -> ConfidenceCalculator:
    global _calculator
    if _calculator is None:
        _calculator = ConfidenceCalculator()
    return _calculator

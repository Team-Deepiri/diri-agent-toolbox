from diri_agent_toolbox.confidence import (
    ConfidenceAttributes,
    ConfidenceCalculator,
    ConfidenceLevel,
)


def test_confidence_level_values():
    assert ConfidenceLevel.VERY_HIGH.value == "very_high"
    assert ConfidenceLevel.HIGH.value == "high"
    assert ConfidenceLevel.MEDIUM.value == "medium"
    assert ConfidenceLevel.LOW.value == "low"
    assert ConfidenceLevel.VERY_LOW.value == "very_low"


class TestConfidenceCalculator:
    def test_high_confidence(self):
        calc = ConfidenceCalculator()
        result = calc.calculate(probabilities=[0.95, 0.03, 0.02])
        assert result.reliability >= 0.5
        assert result.level in (
            ConfidenceLevel.MEDIUM,
            ConfidenceLevel.HIGH,
            ConfidenceLevel.VERY_HIGH,
        )

    def test_low_confidence(self):
        calc = ConfidenceCalculator()
        result = calc.calculate(probabilities=[0.35, 0.33, 0.32])
        assert result.reliability < 0.7

    def test_custom_sources(self):
        calc = ConfidenceCalculator()
        result = calc.calculate(
            probabilities=[0.8, 0.1, 0.1],
            training_coverage=0.9,
            feature_quality=0.85,
            context_match=0.6,
        )
        assert result.sources["training_data_coverage"] == 0.9
        assert result.sources["feature_quality"] == 0.85
        assert result.sources["context_match"] == 0.6

    def test_historical_accuracy(self):
        calc = ConfidenceCalculator()
        result = calc.calculate(
            probabilities=[0.8, 0.2],
            historical_accuracy={0: 0.95, 1: 0.5},
        )
        assert result.sources["historical_accuracy"] == 0.95

    def test_should_accept_meets_threshold(self):
        calc = ConfidenceCalculator()
        result = calc.calculate(probabilities=[0.9, 0.05, 0.05])
        accepted, msg = calc.should_accept(result, min_reliability=0.5)
        assert accepted is True
        assert "meets" in msg

    def test_should_reject_low_reliability(self):
        calc = ConfidenceCalculator()
        result = calc.calculate(probabilities=[0.4, 0.3, 0.3])
        accepted, msg = calc.should_accept(result, min_reliability=0.8)
        assert accepted is False
        assert "below" in msg

    def test_should_reject_low_level(self):
        calc = ConfidenceCalculator()
        low = calc.calculate(probabilities=[0.4, 0.3, 0.3])
        accepted, msg = calc.should_accept(low, min_level=ConfidenceLevel.HIGH)
        assert accepted is False
        assert "below" in msg

    def test_confidence_attributes_to_dict(self):
        attrs = ConfidenceAttributes(
            base_score=0.9,
            level=ConfidenceLevel.HIGH,
            sources={"model": 0.9},
            uncertainty=0.1,
            calibration=0.8,
            reliability=0.85,
            explanation="Good",
        )
        d = attrs.to_dict()
        assert d["base_score"] == 0.9
        assert d["level"] == "high"

    def test_calculate_with_top_k(self):
        calc = ConfidenceCalculator()
        result = calc.calculate(
            probabilities=[0.7, 0.2, 0.1],
            top_k_probs=[0.7, 0.65, 0.72],
        )
        assert isinstance(result, ConfidenceAttributes)

    def test_get_confidence_calculator(self):
        from diri_agent_toolbox.confidence import get_confidence_calculator

        calc1 = get_confidence_calculator()
        calc2 = get_confidence_calculator()
        assert calc1 is calc2

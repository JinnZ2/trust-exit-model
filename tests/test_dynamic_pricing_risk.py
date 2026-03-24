"""Tests for dynamic pricing risk model."""

import pytest
from src.dynamic_pricing_risk import DynamicPricingRiskModel


@pytest.fixture
def model():
    return DynamicPricingRiskModel()


class TestAssessEvent:
    def test_returns_both_segments(self, model):
        result = model.assess_event(5.0, 0.5, 200.0)
        assert "doer" in result
        assert "gambler" in result

    def test_doer_impact_worse(self, model):
        result = model.assess_event(5.0, 0.5, 200.0)
        assert result["doer"]["total_impact"] < result["gambler"]["total_impact"]

    def test_doer_nev_negative(self, model):
        result = model.assess_event(5.0, 0.5, 200.0)
        assert result["doer"]["net_extraction_value"] < 0


class TestBreakevenDoerFraction:
    def test_in_valid_range(self, model):
        p = model.compute_breakeven_doer_fraction(5.0, 0.5, 200.0)
        assert 0.0 <= p <= 1.0

    def test_small_extraction_low_breakeven(self, model):
        """Small extraction revenue means even a small Doer fraction breaks even."""
        p = model.compute_breakeven_doer_fraction(2.0, 0.5, 200.0)
        assert p < 0.10

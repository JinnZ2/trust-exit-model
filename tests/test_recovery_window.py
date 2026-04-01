"""Tests for recovery window model."""

import pytest
from src.customer import Customer, CustomerSegment
from src.recovery_window import InterventionQuality, RecoveryWindowModel
from src.trust_state import TrustState


@pytest.fixture
def model():
    return RecoveryWindowModel()


class TestRecoveryProbability:
    def test_full_trust_high_probability(self, model):
        state = TrustState.from_level(0.90)
        quality = InterventionQuality(1.0, 1.0, 1.0, 1.0)
        p = model.recovery_probability(state, quality)
        assert p > 0.5

    def test_terminal_zero_probability(self, model):
        state = TrustState.from_level(0.10)
        quality = InterventionQuality(1.0, 1.0, 1.0, 1.0)
        p = model.recovery_probability(state, quality)
        assert p == 0.0

    def test_low_quality_low_probability(self, model):
        state = TrustState.from_level(0.65)
        high_q = InterventionQuality(1.0, 1.0, 1.0, 1.0)
        low_q = InterventionQuality(0.2, 0.0, 0.1, 0.0)
        assert model.recovery_probability(state, high_q) > model.recovery_probability(state, low_q)


class TestIsWindowOpen:
    def test_early_erosion_open(self, model):
        assert model.is_window_open(TrustState.from_level(0.65))

    def test_full_trust_closed(self, model):
        assert not model.is_window_open(TrustState.from_level(0.90))

    def test_terminal_closed(self, model):
        assert not model.is_window_open(TrustState.from_level(0.10))


class TestExpectedInterventionValue:
    def test_intervention_improves_with_quality(self, model):
        """Higher quality intervention yields higher expected value."""
        customer = Customer(
            "c1", CustomerSegment.DOER,
            TrustState.from_level(0.65), 200.0,
        )
        low_q = InterventionQuality(0.2, 0.2, 0.2, 0.2)
        high_q = InterventionQuality(1.0, 1.0, 1.0, 1.0)
        low_result = model.expected_intervention_value(customer, low_q)
        high_result = model.expected_intervention_value(customer, high_q)
        assert high_result["ev_intervene"] > low_result["ev_intervene"]

    def test_terminal_no_benefit(self, model):
        customer = Customer(
            "c2", CustomerSegment.DOER,
            TrustState.from_level(0.10), 200.0,
        )
        quality = InterventionQuality(1.0, 1.0, 1.0, 1.0)
        result = model.expected_intervention_value(customer, quality)
        assert result["recovery_probability"] == 0.0

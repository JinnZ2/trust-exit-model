"""Tests for lifetime value model."""

import pytest
from src.customer import Customer, CustomerSegment
from src.lifetime_value import LifetimeValueModel
from src.trust_state import TrustState


@pytest.fixture
def ltv_model():
    return LifetimeValueModel(horizon_months=60)


@pytest.fixture
def doer():
    return Customer(
        customer_id="doer_1",
        segment=CustomerSegment.DOER,
        trust_state=TrustState.from_level(1.0),
        monthly_revenue=200.0,
    )


class TestComputeLtv:
    def test_full_trust_positive(self, ltv_model, doer):
        ltv = ltv_model.compute_ltv(doer)
        assert ltv > 0

    def test_higher_trust_higher_ltv(self, ltv_model):
        high = Customer("h", CustomerSegment.DOER, TrustState.from_level(1.0), 200.0)
        low = Customer("l", CustomerSegment.DOER, TrustState.from_level(0.30), 200.0)
        assert ltv_model.compute_ltv(high) > ltv_model.compute_ltv(low)

    def test_final_exit_zero_ltv(self, ltv_model):
        exited = Customer("e", CustomerSegment.DOER, TrustState.from_level(0.01), 200.0)
        ltv = ltv_model.compute_ltv(exited)
        assert ltv == pytest.approx(0.0, abs=0.01)

    def test_doer_full_trust_higher_than_gambler(self, ltv_model):
        """Doers have higher retention rate -> higher LTV when trust intact."""
        doer = Customer("d", CustomerSegment.DOER, TrustState.from_level(1.0), 200.0)
        gambler = Customer("g", CustomerSegment.GAMBLER, TrustState.from_level(1.0), 200.0)
        assert ltv_model.compute_ltv(doer) > ltv_model.compute_ltv(gambler)


class TestNetExtractionValue:
    def test_doer_nev_negative(self, ltv_model, doer):
        """Dynamic pricing on Doer should yield negative NEV."""
        nev = ltv_model.compute_net_extraction_value(
            customer=doer,
            extraction_revenue=5.0,
            trust_level_after=0.20,
        )
        assert nev < 0

    def test_gambler_moderate_violation_positive_nev(self, ltv_model):
        gambler = Customer("g", CustomerSegment.GAMBLER, TrustState.from_level(1.0), 200.0)
        nev = ltv_model.compute_net_extraction_value(
            customer=gambler,
            extraction_revenue=10.0,
            trust_level_after=0.85,
        )
        assert nev > 0


class TestSegmentComparison:
    def test_returns_both_segments(self, ltv_model):
        result = ltv_model.compute_segment_comparison(200.0, 5.0, 0.5)
        assert "doer" in result
        assert "gambler" in result

    def test_doer_loss_exceeds_gambler(self, ltv_model):
        result = ltv_model.compute_segment_comparison(200.0, 5.0, 0.5)
        assert result["doer"]["ltv_loss"] > result["gambler"]["ltv_loss"]

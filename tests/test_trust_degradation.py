"""Tests for trust degradation curve."""

import pytest
from src.customer import Customer, CustomerSegment
from src.trust_degradation import TrustDegradationCurve
from src.trust_state import TrustPhase, TrustState


@pytest.fixture
def curve():
    return TrustDegradationCurve()


@pytest.fixture
def doer():
    return Customer(
        customer_id="doer_1",
        segment=CustomerSegment.DOER,
        trust_state=TrustState.from_level(1.0),
        monthly_revenue=200.0,
    )


@pytest.fixture
def gambler():
    return Customer(
        customer_id="gambler_1",
        segment=CustomerSegment.GAMBLER,
        trust_state=TrustState.from_level(1.0),
        monthly_revenue=200.0,
    )


class TestApplyViolation:
    def test_doer_drops_faster_than_gambler(self, curve, doer, gambler):
        """Core thesis: Doers experience steeper trust decay per violation."""
        severity = 0.5
        doer_after = curve.apply_violation(doer, severity)
        gambler_after = curve.apply_violation(gambler, severity)
        assert doer_after.trust_level < gambler_after.trust_level

    def test_severity_zero_no_change(self, curve, doer):
        after = curve.apply_violation(doer, 0.0)
        assert after.trust_level == pytest.approx(1.0)

    def test_high_severity_doer_exits(self, curve, doer):
        """Single high-severity violation can push Doer to terminal."""
        after = curve.apply_violation(doer, 1.0)
        assert after.trust_level < 0.25  # Terminal or worse

    def test_violations_count_increments(self, curve, doer):
        after = curve.apply_violation(doer, 0.3)
        assert after.violations_count == 1

    def test_invalid_severity(self, curve, doer):
        with pytest.raises(ValueError):
            curve.apply_violation(doer, 1.5)

    def test_trust_never_negative(self, curve, doer):
        after = curve.apply_violation(doer, 1.0)
        assert after.trust_level >= 0.0


class TestPassiveErosion:
    def test_no_erosion_in_full_trust(self, curve, doer):
        """Full trust doesn't passively erode (Section 3)."""
        after = curve.apply_passive_erosion(doer, months=12)
        assert after.trust_level == doer.trust_state.trust_level

    def test_erosion_in_degraded_state(self, curve):
        customer = Customer(
            customer_id="eroded",
            segment=CustomerSegment.DOER,
            trust_state=TrustState.from_level(0.60),
            monthly_revenue=200.0,
        )
        after = curve.apply_passive_erosion(customer, months=6)
        assert after.trust_level < 0.60


class TestSimulateViolations:
    def test_trajectory_length(self, curve, doer):
        severities = [0.2, 0.3, 0.4]
        trajectory = curve.simulate_violations(doer, severities)
        assert len(trajectory) == 3

    def test_trajectory_monotonically_decreasing(self, curve, doer):
        severities = [0.2, 0.2, 0.2, 0.2]
        trajectory = curve.simulate_violations(doer, severities)
        levels = [s.trust_level for s in trajectory]
        for i in range(len(levels) - 1):
            assert levels[i] >= levels[i + 1]

    def test_doer_reaches_exit_faster(self, curve, doer, gambler):
        severities = [0.3, 0.3, 0.3, 0.3, 0.3]
        doer_traj = curve.simulate_violations(doer, severities)
        gambler_traj = curve.simulate_violations(gambler, severities)
        assert doer_traj[-1].trust_level < gambler_traj[-1].trust_level

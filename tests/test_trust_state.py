"""Tests for trust state and phase definitions."""

import pytest
from src.trust_state import TrustPhase, TrustState, PHASE_RECOVERY_POTENTIAL


class TestTrustPhase:
    def test_phase_ordering(self):
        """Phases are monotonically increasing (decreasing trust)."""
        assert TrustPhase.FULL_TRUST < TrustPhase.EARLY_EROSION
        assert TrustPhase.EARLY_EROSION < TrustPhase.CRITICAL_THRESHOLD
        assert TrustPhase.CRITICAL_THRESHOLD < TrustPhase.TERMINAL
        assert TrustPhase.TERMINAL < TrustPhase.FINAL_EXIT

    def test_recovery_potential_monotonic(self):
        """Recovery potential is non-increasing across phases."""
        potentials = [PHASE_RECOVERY_POTENTIAL[p] for p in TrustPhase]
        for i in range(len(potentials) - 1):
            assert potentials[i] >= potentials[i + 1]

    def test_terminal_phases_zero_recovery(self):
        assert PHASE_RECOVERY_POTENTIAL[TrustPhase.TERMINAL] == 0.0
        assert PHASE_RECOVERY_POTENTIAL[TrustPhase.FINAL_EXIT] == 0.0


class TestTrustState:
    def test_valid_creation(self):
        state = TrustState(trust_level=0.9, phase=TrustPhase.FULL_TRUST)
        assert state.trust_level == 0.9
        assert state.phase == TrustPhase.FULL_TRUST
        assert state.violations_count == 0

    def test_invalid_trust_level(self):
        with pytest.raises(ValueError):
            TrustState(trust_level=1.5, phase=TrustPhase.FULL_TRUST)
        with pytest.raises(ValueError):
            TrustState(trust_level=-0.1, phase=TrustPhase.FULL_TRUST)

    def test_from_level(self):
        state = TrustState.from_level(0.65, violations_count=2)
        assert state.phase == TrustPhase.EARLY_EROSION
        assert state.violations_count == 2

    def test_phase_from_level_boundaries(self):
        assert TrustState.phase_from_level(1.00) == TrustPhase.FULL_TRUST
        assert TrustState.phase_from_level(0.80) == TrustPhase.FULL_TRUST
        assert TrustState.phase_from_level(0.79) == TrustPhase.EARLY_EROSION
        assert TrustState.phase_from_level(0.50) == TrustPhase.EARLY_EROSION
        assert TrustState.phase_from_level(0.49) == TrustPhase.CRITICAL_THRESHOLD
        assert TrustState.phase_from_level(0.25) == TrustPhase.CRITICAL_THRESHOLD
        assert TrustState.phase_from_level(0.24) == TrustPhase.TERMINAL
        assert TrustState.phase_from_level(0.05) == TrustPhase.TERMINAL
        assert TrustState.phase_from_level(0.04) == TrustPhase.FINAL_EXIT
        assert TrustState.phase_from_level(0.00) == TrustPhase.FINAL_EXIT

    def test_frozen(self):
        state = TrustState.from_level(0.5)
        with pytest.raises(AttributeError):
            state.trust_level = 0.3

"""Tests for the ZNP gate-failure bridge."""

import pytest

from src.behavioral_fingerprint import SignalVector
from src.support_cartography import Gate
from src.znp_gate_bridge import (
    SIGNAL_GATE_MAP,
    GateFailureProfile,
    classify_gate_failures,
)


class TestSignalGateMap:
    def test_every_signal_vector_field_is_mapped(self):
        signal_fields = {
            "abrupt_cancellation", "trigger_correlation",
            "browsing_linearity", "category_exploration",
            "communication_response", "platform_feature_usage",
            "abandonment_recovery", "offer_response",
            "exit_data_quality", "complaint_absence",
        }
        assert set(SIGNAL_GATE_MAP.keys()) == signal_fields

    def test_every_gate_has_at_least_one_signal(self):
        mapped_gates = set(SIGNAL_GATE_MAP.values())
        assert mapped_gates == {Gate.EMISSION, Gate.CAPTURE, Gate.RETENTION}


class TestClassifyGateFailures:
    def test_all_zero_signals_produce_zero_scores(self):
        profile = classify_gate_failures(SignalVector())
        assert profile.emission_score == 0.0
        assert profile.capture_score == 0.0
        assert profile.retention_score == 0.0

    def test_pure_emission_failure_dominates(self):
        signals = SignalVector(
            communication_response=1.0,
            platform_feature_usage=1.0,
            abandonment_recovery=1.0,
            offer_response=1.0,
            complaint_absence=1.0,
            exit_data_quality=1.0,
        )
        profile = classify_gate_failures(signals)
        assert profile.dominant_gate == Gate.EMISSION
        assert profile.emission_score == 1.0
        assert profile.capture_score == 0.0
        assert profile.retention_score == 0.0

    def test_pure_capture_failure_dominates(self):
        signals = SignalVector(
            browsing_linearity=1.0,
            category_exploration=1.0,
        )
        profile = classify_gate_failures(signals)
        assert profile.dominant_gate == Gate.CAPTURE
        assert profile.capture_score == 1.0
        assert profile.emission_score == 0.0
        assert profile.retention_score == 0.0

    def test_pure_retention_failure_dominates(self):
        signals = SignalVector(
            abrupt_cancellation=1.0,
            trigger_correlation=1.0,
        )
        profile = classify_gate_failures(signals)
        assert profile.dominant_gate == Gate.RETENTION
        assert profile.retention_score == 1.0
        assert profile.emission_score == 0.0
        assert profile.capture_score == 0.0

    def test_max_signals_all_gates_saturate(self):
        signals = SignalVector(
            abrupt_cancellation=1.0, trigger_correlation=1.0,
            browsing_linearity=1.0, category_exploration=1.0,
            communication_response=1.0, platform_feature_usage=1.0,
            abandonment_recovery=1.0, offer_response=1.0,
            exit_data_quality=1.0, complaint_absence=1.0,
        )
        profile = classify_gate_failures(signals)
        assert profile.emission_score == pytest.approx(1.0)
        assert profile.capture_score == pytest.approx(1.0)
        assert profile.retention_score == pytest.approx(1.0)
        # Tie-break resolves to emission (most upstream).
        assert profile.dominant_gate == Gate.EMISSION

    def test_partial_emission_signals_average(self):
        signals = SignalVector(
            communication_response=1.0,
            platform_feature_usage=0.5,
            # four other emission fields default to 0.0
        )
        profile = classify_gate_failures(signals)
        # Mean of (1.0, 0.5, 0, 0, 0, 0) over 6 emission signals
        assert profile.emission_score == pytest.approx(0.25)

    def test_dominant_gate_breaks_ties_emission_first(self):
        # Equal retention and capture (both 1.0), zero emission
        signals = SignalVector(
            abrupt_cancellation=1.0, trigger_correlation=1.0,
            browsing_linearity=1.0, category_exploration=1.0,
        )
        profile = classify_gate_failures(signals)
        # Both gates tie at 1.0; capture comes before retention in tie order.
        assert profile.dominant_gate == Gate.CAPTURE


class TestGateFailureProfile:
    def test_intervention_hint_varies_by_gate(self):
        hints = {
            classify_gate_failures(SignalVector(communication_response=1.0))
            .intervention_hint(),
            classify_gate_failures(SignalVector(browsing_linearity=1.0))
            .intervention_hint(),
            classify_gate_failures(SignalVector(abrupt_cancellation=1.0))
            .intervention_hint(),
        }
        assert len(hints) == 3

    def test_to_dict_serializes_gate_as_string(self):
        profile = classify_gate_failures(
            SignalVector(complaint_absence=1.0)
        )
        d = profile.to_dict()
        assert d["dominant_gate"] == "emission"
        assert "intervention_hint" in d
        assert isinstance(d["emission_score"], float)

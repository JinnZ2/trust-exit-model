"""Tests for behavioral fingerprint scoring."""

import pytest
from src.behavioral_fingerprint import (
    BehavioralFingerprint,
    SignalCategory,
    SignalVector,
)


@pytest.fixture
def fingerprint():
    return BehavioralFingerprint()


class TestSignalVector:
    def test_default_all_zero(self):
        signals = SignalVector()
        scores = signals.to_category_scores()
        assert all(v == 0.0 for v in scores.values())

    def test_max_signals(self):
        signals = SignalVector(
            abrupt_cancellation=1.0, trigger_correlation=1.0,
            browsing_linearity=1.0, category_exploration=1.0,
            communication_response=1.0, platform_feature_usage=1.0,
            abandonment_recovery=1.0, offer_response=1.0,
            exit_data_quality=1.0, complaint_absence=1.0,
        )
        scores = signals.to_category_scores()
        assert all(v == 1.0 for v in scores.values())


class TestBehavioralFingerprint:
    def test_zero_signals_zero_score(self, fingerprint):
        score = fingerprint.compute_score(SignalVector())
        assert score == 0.0

    def test_max_signals_max_score(self, fingerprint):
        signals = SignalVector(
            abrupt_cancellation=1.0, trigger_correlation=1.0,
            browsing_linearity=1.0, category_exploration=1.0,
            communication_response=1.0, platform_feature_usage=1.0,
            abandonment_recovery=1.0, offer_response=1.0,
            exit_data_quality=1.0, complaint_absence=1.0,
        )
        score = fingerprint.compute_score(signals)
        assert score == pytest.approx(1.0)

    def test_znp_classification(self, fingerprint):
        """High ZNP signals should classify as ZNP."""
        znp_signals = SignalVector(
            abrupt_cancellation=0.9, trigger_correlation=0.8,
            browsing_linearity=0.9, category_exploration=0.8,
            communication_response=1.0, platform_feature_usage=0.9,
            abandonment_recovery=1.0, offer_response=1.0,
            exit_data_quality=0.8, complaint_absence=1.0,
        )
        result = fingerprint.classify(znp_signals)
        assert result["is_znp"] is True
        assert result["score"] > 0.6

    def test_normal_customer_not_znp(self, fingerprint):
        normal_signals = SignalVector(
            abrupt_cancellation=0.1, trigger_correlation=0.0,
            browsing_linearity=0.2, category_exploration=0.1,
            communication_response=0.3, platform_feature_usage=0.2,
            abandonment_recovery=0.2, offer_response=0.1,
            exit_data_quality=0.0, complaint_absence=0.1,
        )
        result = fingerprint.classify(normal_signals)
        assert result["is_znp"] is False

    def test_invalid_weights(self):
        with pytest.raises(ValueError):
            BehavioralFingerprint(weights={
                SignalCategory.TEMPORAL_MARKERS: 0.5,
                SignalCategory.SESSION_CHARACTERISTICS: 0.5,
                SignalCategory.ENGAGEMENT_PROFILE: 0.5,
                SignalCategory.REENGAGEMENT_RESPONSE: 0.5,
                SignalCategory.EXIT_CHARACTERISTICS: 0.5,
            })

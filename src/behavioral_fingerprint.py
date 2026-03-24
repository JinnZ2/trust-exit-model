"""Behavioral fingerprint scoring model.

Formalizes Section 5 of the ZNP paper.

Composite fingerprint score:

    F = sum_{i=1}^{N} w_i * s_i

Where:
    w_i = weight for signal i (sum to 1.0)
    s_i = normalized signal value for signal i, in [0, 1]
          0 = normal behavior, 1 = maximum terminal-trust indicator

Signal categories (from Section 5):
    1. Temporal markers       — abrupt cancellation, trigger correlation
    2. Session characteristics — linear browsing, no exploration
    3. Engagement profile     — zero communication response
    4. Re-engagement response — zero conversion on all attempts
    5. Exit characteristics   — minimal data, no complaint

When F exceeds a threshold (default 0.60), the customer is flagged
as probable ZNP in terminal trust state.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class SignalCategory(Enum):
    """Signal categories from the behavioral fingerprint (Section 5)."""

    TEMPORAL_MARKERS = "temporal_markers"
    SESSION_CHARACTERISTICS = "session_characteristics"
    ENGAGEMENT_PROFILE = "engagement_profile"
    REENGAGEMENT_RESPONSE = "reengagement_response"
    EXIT_CHARACTERISTICS = "exit_characteristics"


# Default weights per signal category.
# Derived from diagnostic significance described in Sections 5 and 3.4.
DEFAULT_WEIGHTS: dict[SignalCategory, float] = {
    SignalCategory.TEMPORAL_MARKERS: 0.25,
    SignalCategory.SESSION_CHARACTERISTICS: 0.15,
    SignalCategory.ENGAGEMENT_PROFILE: 0.25,
    SignalCategory.REENGAGEMENT_RESPONSE: 0.25,
    SignalCategory.EXIT_CHARACTERISTICS: 0.10,
}


@dataclass
class SignalVector:
    """Raw behavioral signals for a single customer.

    Each signal is in [0, 1] where 0 = normal and 1 = max ZNP indicator.

    Attributes:
        abrupt_cancellation: 1.0 if recurring orders cancelled abruptly
            (not tapered). Section 3.4: "abrupt cessation is diagnostically
            significant."
        trigger_correlation: Correlation strength between cancellation
            timing and a known trust-violation event.
        browsing_linearity: Session linearity score. 1.0 = strictly
            search-find-leave with no exploration.
        category_exploration: Inverse of adjacent category browsing.
            1.0 = zero exploration.
        communication_response: Inverse of response rate to all channels.
            1.0 = zero response.
        platform_feature_usage: Inverse of social/review/survey usage.
            1.0 = zero usage.
        abandonment_recovery: Inverse of conversion on recovery attempts.
            1.0 = zero conversion on all attempts.
        offer_response: Inverse of response to discount/loyalty offers.
            1.0 = zero response regardless of value.
        exit_data_quality: 1.0 = minimal/misleading exit data.
        complaint_absence: 1.0 = no complaint filed, no review, no trace.
    """

    abrupt_cancellation: float = 0.0
    trigger_correlation: float = 0.0
    browsing_linearity: float = 0.0
    category_exploration: float = 0.0
    communication_response: float = 0.0
    platform_feature_usage: float = 0.0
    abandonment_recovery: float = 0.0
    offer_response: float = 0.0
    exit_data_quality: float = 0.0
    complaint_absence: float = 0.0

    def to_category_scores(self) -> dict[SignalCategory, float]:
        """Aggregate raw signals into per-category scores.

        Each category score is the mean of its constituent signals.
        """
        return {
            SignalCategory.TEMPORAL_MARKERS: _mean(
                self.abrupt_cancellation, self.trigger_correlation
            ),
            SignalCategory.SESSION_CHARACTERISTICS: _mean(
                self.browsing_linearity, self.category_exploration
            ),
            SignalCategory.ENGAGEMENT_PROFILE: _mean(
                self.communication_response, self.platform_feature_usage
            ),
            SignalCategory.REENGAGEMENT_RESPONSE: _mean(
                self.abandonment_recovery, self.offer_response
            ),
            SignalCategory.EXIT_CHARACTERISTICS: _mean(
                self.exit_data_quality, self.complaint_absence
            ),
        }


@dataclass
class BehavioralFingerprint:
    """Compute composite ZNP fingerprint score from behavioral signals.

    Attributes:
        weights: Per-category weights. Must sum to 1.0.
        threshold: Score above which a customer is flagged as probable ZNP.
    """

    weights: dict[SignalCategory, float] = field(default_factory=lambda: dict(DEFAULT_WEIGHTS))
    threshold: float = 0.60

    def __post_init__(self) -> None:
        total = sum(self.weights.values())
        if abs(total - 1.0) > 1e-6:
            raise ValueError(f"Weights must sum to 1.0, got {total}")

    def compute_score(self, signals: SignalVector) -> float:
        """Compute composite fingerprint score.

        F = sum(w_i * s_i) for each signal category i.

        Args:
            signals: Raw behavioral signal vector.

        Returns:
            Composite score in [0, 1].
        """
        category_scores = signals.to_category_scores()
        score = sum(
            self.weights[cat] * category_scores[cat]
            for cat in SignalCategory
        )
        return min(1.0, max(0.0, score))

    def classify(self, signals: SignalVector) -> dict[str, object]:
        """Classify a customer based on behavioral fingerprint.

        Returns:
            Dict with score, is_znp flag, category_scores breakdown,
            and dominant_signal (highest-scoring category).
        """
        category_scores = signals.to_category_scores()
        score = self.compute_score(signals)
        dominant = max(category_scores, key=category_scores.get)

        return {
            "score": round(score, 4),
            "is_znp": score >= self.threshold,
            "category_scores": {k.value: round(v, 4) for k, v in category_scores.items()},
            "dominant_signal": dominant.value,
        }


def _mean(*values: float) -> float:
    """Compute mean of values, returning 0.0 for empty input."""
    if not values:
        return 0.0
    return sum(values) / len(values)

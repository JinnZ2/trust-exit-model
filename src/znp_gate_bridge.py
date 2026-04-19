"""Bridge between behavioral_fingerprint and support_cartography.

When a customer is flagged as ZNP by BehavioralFingerprint, this module
classifies *why* they were invisible to existing instrumentation by
mapping the raw behavioral signals onto the three-gate framework from
support_cartography:

    EMISSION   — customer does not externalize dissatisfaction at all
    CAPTURE    — signal is present in the data stream but standard
                 instruments do not extract the relevant pattern
    RETENTION  — data existed at the time but was pruned or unjoined
                 before anyone could analyze it

The dominant gate indicates what kind of instrumentation change would
make future customers like this one detectable before exit.

Signal-to-gate mapping rationale:

    EMISSION signals — the customer produced no observable output.
        communication_response, platform_feature_usage,
        abandonment_recovery, offer_response, complaint_absence,
        exit_data_quality

    CAPTURE signals — clickstream recorded the events, but standard
    analytics does not flag the decisive-vs-exploratory pattern.
        browsing_linearity, category_exploration

    RETENTION signals — patterns that require joined or long-horizon
    history. Visible only if transaction timelines and trust-violation
    event streams are both retained at granularity and joined.
        abrupt_cancellation, trigger_correlation
"""

from __future__ import annotations

from dataclasses import dataclass

from src.behavioral_fingerprint import SignalVector
from src.support_cartography import Gate


SIGNAL_GATE_MAP: dict[str, Gate] = {
    "communication_response": Gate.EMISSION,
    "platform_feature_usage": Gate.EMISSION,
    "abandonment_recovery": Gate.EMISSION,
    "offer_response": Gate.EMISSION,
    "complaint_absence": Gate.EMISSION,
    "exit_data_quality": Gate.EMISSION,
    "browsing_linearity": Gate.CAPTURE,
    "category_exploration": Gate.CAPTURE,
    "abrupt_cancellation": Gate.RETENTION,
    "trigger_correlation": Gate.RETENTION,
}


INTERVENTION_HINTS: dict[Gate, str] = {
    Gate.EMISSION: (
        "Customer does not externalize dissatisfaction. No survey "
        "redesign will reach them. Detection must move upstream of "
        "feedback — flag at the behavioral layer (session, transaction, "
        "reengagement) before exit."
    ),
    Gate.CAPTURE: (
        "Signal is present in the data stream but standard analytics "
        "does not extract the relevant pattern. Add pattern detectors "
        "(linearity, adjacent-category exploration) to the existing "
        "clickstream pipeline."
    ),
    Gate.RETENTION: (
        "Pattern requires joined or long-horizon history. Extend "
        "retention of granular transaction and event data, and join "
        "customer timelines against trust-violation event streams "
        "before aggregation."
    ),
}


@dataclass
class GateFailureProfile:
    """Per-customer breakdown of which gate failure makes them invisible.

    Attributes:
        emission_score: Mean of raw signals mapped to the emission gate,
            in [0, 1]. Higher = stronger emission failure.
        capture_score: Same, for capture.
        retention_score: Same, for retention.
        dominant_gate: The gate with the highest score. Ties broken in
            emission > capture > retention order, reflecting that
            emission failure is the most upstream.
    """

    emission_score: float
    capture_score: float
    retention_score: float
    dominant_gate: Gate

    def intervention_hint(self) -> str:
        return INTERVENTION_HINTS[self.dominant_gate]

    def to_dict(self) -> dict[str, object]:
        return {
            "emission_score": self.emission_score,
            "capture_score": self.capture_score,
            "retention_score": self.retention_score,
            "dominant_gate": self.dominant_gate.value,
            "intervention_hint": self.intervention_hint(),
        }


def classify_gate_failures(signals: SignalVector) -> GateFailureProfile:
    """Decompose a ZNP signal vector into per-gate failure scores.

    Each gate's score is the mean of its constituent raw signals.
    The dominant gate identifies the primary reason the customer is
    invisible to current instrumentation and therefore the type of
    instrumentation change that would detect future customers like them.
    """
    by_gate: dict[Gate, list[float]] = {
        Gate.EMISSION: [],
        Gate.CAPTURE: [],
        Gate.RETENTION: [],
    }
    for signal_name, gate in SIGNAL_GATE_MAP.items():
        by_gate[gate].append(float(getattr(signals, signal_name)))

    scores = {
        gate: (sum(values) / len(values)) if values else 0.0
        for gate, values in by_gate.items()
    }

    # Tie-break order: emission > capture > retention (most upstream first)
    dominant = max(
        (Gate.EMISSION, Gate.CAPTURE, Gate.RETENTION),
        key=lambda g: scores[g],
    )

    return GateFailureProfile(
        emission_score=round(scores[Gate.EMISSION], 4),
        capture_score=round(scores[Gate.CAPTURE], 4),
        retention_score=round(scores[Gate.RETENTION], 4),
        dominant_gate=dominant,
    )

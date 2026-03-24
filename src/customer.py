"""Customer and segment definitions.

Standardized terminology:
    CustomerSegment - The two behavioral segments (Doer / Gambler).
    Customer        - Individual customer with trust state and value attributes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from src.trust_state import TrustPhase, TrustState


class CustomerSegment(Enum):
    """Two-segment classification by manipulation tolerance (README).

    DOER:    Zero tolerance for manipulation. Hard exit on trust violation.
    GAMBLER: Tolerates variable pricing, negotiates, rationalizes, stays.
    """

    DOER = "doer"
    GAMBLER = "gambler"


# Default manipulation tolerance thresholds per segment.
# A trust violation's perceived severity is compared against this threshold.
# If severity >= threshold, trust drops immediately to the next phase.
DEFAULT_MANIPULATION_TOLERANCE: dict[CustomerSegment, float] = {
    CustomerSegment.DOER: 0.95,     # Low tolerance (amplifies decay)
    CustomerSegment.GAMBLER: 0.95,  # Same baseline; segment difference is in alpha
}


@dataclass
class Customer:
    """Individual customer with behavioral attributes.

    Attributes:
        customer_id: Unique identifier.
        segment: Doer or Gambler classification.
        trust_state: Current trust snapshot.
        monthly_revenue: Average monthly spend when trust is intact (dollars).
        tenure_months: Months as active customer.
        social_reach: Number of people in direct social network
            influenced by word-of-mouth (Section 2.2 of ZNP paper).
        manipulation_tolerance: Threshold in [0,1] for tolerating a
            trust violation without phase transition. Lower = less tolerant.
        violation_history: List of (month, severity) tuples.
    """

    customer_id: str
    segment: CustomerSegment
    trust_state: TrustState
    monthly_revenue: float
    tenure_months: int = 0
    social_reach: int = 5
    manipulation_tolerance: float | None = None
    violation_history: list[tuple[int, float]] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.manipulation_tolerance is None:
            self.manipulation_tolerance = DEFAULT_MANIPULATION_TOLERANCE[self.segment]

    @property
    def is_active(self) -> bool:
        return self.trust_state.phase != TrustPhase.FINAL_EXIT

    @property
    def is_recoverable(self) -> bool:
        return self.trust_state.phase in (
            TrustPhase.FULL_TRUST,
            TrustPhase.EARLY_EROSION,
        )

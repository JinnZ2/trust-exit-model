"""Trust state and phase definitions.

Standardized terminology:
    TrustPhase  - Enum of the 5 degradation phases from the ZNP paper.
    TrustState  - Immutable snapshot of a customer's trust at a point in time.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum


class TrustPhase(IntEnum):
    """Five phases of the trust degradation curve (Section 3 of ZNP paper).

    Phase ordering is monotonically decreasing in trust level:
        FULL_TRUST > EARLY_EROSION > CRITICAL_THRESHOLD > TERMINAL > FINAL_EXIT
    """

    FULL_TRUST = 1
    EARLY_EROSION = 2
    CRITICAL_THRESHOLD = 3
    TERMINAL = 4
    FINAL_EXIT = 5


# Recovery potential per phase (Section 3 of ZNP paper).
# Values represent probability that a *perfect* intervention recovers the customer.
PHASE_RECOVERY_POTENTIAL: dict[TrustPhase, float] = {
    TrustPhase.FULL_TRUST: 1.0,        # Not applicable / no recovery needed
    TrustPhase.EARLY_EROSION: 0.70,     # HIGH
    TrustPhase.CRITICAL_THRESHOLD: 0.15, # LOW
    TrustPhase.TERMINAL: 0.0,           # ZERO
    TrustPhase.FINAL_EXIT: 0.0,         # ZERO
}


@dataclass(frozen=True)
class TrustState:
    """Immutable snapshot of customer trust.

    Attributes:
        trust_level: Continuous trust score in [0, 1].
            1.0 = full trust, 0.0 = zero trust.
        phase: Discrete phase derived from trust_level thresholds.
        violations_count: Cumulative trust-violation events experienced.
    """

    trust_level: float
    phase: TrustPhase
    violations_count: int = 0

    def __post_init__(self) -> None:
        if not 0.0 <= self.trust_level <= 1.0:
            raise ValueError(f"trust_level must be in [0,1], got {self.trust_level}")

    @property
    def recovery_potential(self) -> float:
        """Maximum recovery probability given current phase."""
        return PHASE_RECOVERY_POTENTIAL[self.phase]

    @staticmethod
    def phase_from_level(trust_level: float) -> TrustPhase:
        """Map continuous trust_level to discrete TrustPhase.

        Threshold mapping (derived from paper Sections 3.1-3.5):
            [0.80, 1.00] -> FULL_TRUST
            [0.50, 0.80) -> EARLY_EROSION
            [0.25, 0.50) -> CRITICAL_THRESHOLD
            [0.05, 0.25) -> TERMINAL
            [0.00, 0.05) -> FINAL_EXIT
        """
        if trust_level >= 0.80:
            return TrustPhase.FULL_TRUST
        elif trust_level >= 0.50:
            return TrustPhase.EARLY_EROSION
        elif trust_level >= 0.25:
            return TrustPhase.CRITICAL_THRESHOLD
        elif trust_level >= 0.05:
            return TrustPhase.TERMINAL
        else:
            return TrustPhase.FINAL_EXIT

    @classmethod
    def from_level(cls, trust_level: float, violations_count: int = 0) -> TrustState:
        """Construct TrustState from a continuous trust level."""
        return cls(
            trust_level=trust_level,
            phase=cls.phase_from_level(trust_level),
            violations_count=violations_count,
        )

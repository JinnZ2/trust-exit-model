"""Trust degradation curve model.

Formalizes Section 3 of the ZNP paper.

Core equation — trust level after a violation event:

    T(n) = T(n-1) * exp(-alpha * S_n / M)

Where:
    T(n)    = trust level after the nth violation event
    T(n-1)  = trust level before the event
    alpha   = segment-specific decay rate (Doer >> Gambler)
    S_n     = perceived severity of violation n, in [0, 1]
    M       = customer's manipulation tolerance threshold, in (0, 1]

The exponential form ensures:
    - Trust is monotonically non-increasing (violations never add trust).
    - Low-tolerance customers (small M) experience amplified decay.
    - Multiple small violations compound multiplicatively.

Time-based passive decay (between violations):

    T(t) = T_0 * (1 - beta * delta_t)   clamped to [0, T_0]

Where:
    beta     = passive erosion rate per month (default: 0 for Doers in
               full-trust state — trust doesn't erode without cause)
    delta_t  = months since last violation or state change
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from src.customer import Customer, CustomerSegment
from src.trust_state import TrustState


# Segment-specific decay rate multipliers.
# Calibrated so that:
#   - Doer: 1 moderate violation (0.5) drops trust to ~0.35 (critical threshold).
#           2 moderate violations reach terminal. 3 reach final exit.
#   - Gambler: 1 moderate violation drops trust to ~0.86 (still full trust).
#              Takes 5+ violations to reach critical threshold.
DEFAULT_ALPHA: dict[CustomerSegment, float] = {
    CustomerSegment.DOER: 2.0,     # Steep decay per violation
    CustomerSegment.GAMBLER: 0.3,  # Gradual decay per violation
}

# Passive erosion rate (per month) when in degraded trust phases.
DEFAULT_BETA: dict[CustomerSegment, float] = {
    CustomerSegment.DOER: 0.02,    # Slight passive erosion once trust is damaged
    CustomerSegment.GAMBLER: 0.01, # Very slow passive erosion
}


@dataclass
class TrustDegradationCurve:
    """Computes trust state transitions from violation events.

    Attributes:
        alpha: Decay rate multiplier per violation. Higher = steeper drop.
        beta: Passive erosion rate per month between violations.
    """

    alpha: float | None = None
    beta: float | None = None

    def apply_violation(
        self, customer: Customer, severity: float
    ) -> TrustState:
        """Compute new trust state after a violation event.

        Equation:
            T_new = T_old * exp(-alpha * severity / tolerance)

        Args:
            customer: The customer experiencing the violation.
            severity: Perceived severity of the violation, in [0, 1].

        Returns:
            New TrustState reflecting the post-violation trust level.
        """
        if not 0.0 <= severity <= 1.0:
            raise ValueError(f"severity must be in [0,1], got {severity}")

        alpha = self.alpha if self.alpha is not None else DEFAULT_ALPHA[customer.segment]
        tolerance = max(customer.manipulation_tolerance, 1e-9)  # avoid division by zero

        old_level = customer.trust_state.trust_level
        new_level = old_level * math.exp(-alpha * severity / tolerance)
        new_level = max(0.0, min(1.0, new_level))

        return TrustState.from_level(
            trust_level=new_level,
            violations_count=customer.trust_state.violations_count + 1,
        )

    def apply_passive_erosion(
        self, customer: Customer, months: float
    ) -> TrustState:
        """Compute trust erosion over time without new violations.

        Equation:
            T_new = T_old * (1 - beta * months)   clamped to [0, T_old]

        Only applies when customer is already in a degraded phase
        (EARLY_EROSION or worse). Full-trust customers don't passively erode.

        Args:
            customer: The customer.
            months: Time elapsed since last state change.

        Returns:
            New TrustState after passive erosion.
        """
        from src.trust_state import TrustPhase

        if customer.trust_state.phase == TrustPhase.FULL_TRUST:
            return customer.trust_state  # No passive erosion in full trust

        beta = self.beta if self.beta is not None else DEFAULT_BETA[customer.segment]
        old_level = customer.trust_state.trust_level
        new_level = old_level * (1.0 - beta * months)
        new_level = max(0.0, new_level)

        return TrustState.from_level(
            trust_level=new_level,
            violations_count=customer.trust_state.violations_count,
        )

    def simulate_violations(
        self, customer: Customer, severities: list[float]
    ) -> list[TrustState]:
        """Simulate a sequence of violations and return the trust trajectory.

        Args:
            customer: Starting customer state.
            severities: List of violation severities applied in order.

        Returns:
            List of TrustState snapshots (one per violation, length = len(severities)).
        """
        trajectory: list[TrustState] = []
        current_customer = customer

        for severity in severities:
            new_state = self.apply_violation(current_customer, severity)
            trajectory.append(new_state)
            # Update customer in-place for next iteration
            current_customer = Customer(
                customer_id=current_customer.customer_id,
                segment=current_customer.segment,
                trust_state=new_state,
                monthly_revenue=current_customer.monthly_revenue,
                tenure_months=current_customer.tenure_months,
                social_reach=current_customer.social_reach,
                manipulation_tolerance=current_customer.manipulation_tolerance,
                violation_history=current_customer.violation_history,
            )

        return trajectory

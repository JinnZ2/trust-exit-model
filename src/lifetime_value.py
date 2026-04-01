"""Lifetime value model with trust-state adjustment.

Formalizes Section 7 of the ZNP paper.

Standard LTV (trust-intact):

    LTV = sum_{t=1}^{H} (R_t * r_t) / (1 + d)^t

Where:
    R_t  = monthly revenue at month t
    r_t  = retention probability at month t
    d    = monthly discount rate
    H    = time horizon in months

Trust-adjusted LTV — incorporates trust degradation:

    LTV_adjusted = sum_{t=1}^{H} (R_t * r_t * T(t)) / (1 + d)^t

Where:
    T(t) = trust level at month t, in [0, 1]
           Acts as a revenue multiplier: degraded trust reduces spending
           before full exit (Phase 3-4 reconnaissance behavior).

Net extraction value of a dynamic pricing event:

    NEV = Delta_R - (LTV_before - LTV_after)

Where:
    Delta_R     = incremental revenue from the pricing manipulation
    LTV_before  = trust-adjusted LTV before the event
    LTV_after   = trust-adjusted LTV after the event

NEV < 0 means the manipulation destroyed more value than it captured.
For Doer customers, NEV is almost always deeply negative.
"""

from __future__ import annotations

from dataclasses import dataclass

from src.customer import Customer, CustomerSegment
from src.trust_state import TrustPhase


# Base monthly retention rates by segment (trust-intact state).
DEFAULT_BASE_RETENTION: dict[CustomerSegment, float] = {
    CustomerSegment.DOER: 0.98,     # Very high loyalty when trust is intact
    CustomerSegment.GAMBLER: 0.92,  # Lower baseline loyalty
}

# Revenue multiplier by trust phase.
# Reflects spending reduction during trust degradation (Sections 3.3-3.4).
PHASE_REVENUE_MULTIPLIER: dict[TrustPhase, float] = {
    TrustPhase.FULL_TRUST: 1.00,
    TrustPhase.EARLY_EROSION: 0.85,
    TrustPhase.CRITICAL_THRESHOLD: 0.40,  # Strictly transactional
    TrustPhase.TERMINAL: 0.10,            # Reconnaissance only
    TrustPhase.FINAL_EXIT: 0.00,
}


@dataclass
class LifetimeValueModel:
    """Compute customer lifetime value with trust-state adjustment.

    Attributes:
        horizon_months: Projection horizon.
        monthly_discount_rate: Time-value discount rate per month.
    """

    horizon_months: int = 60
    monthly_discount_rate: float = 0.005  # ~6% annual

    def compute_ltv(
        self,
        customer: Customer,
        trust_levels: list[float] | None = None,
    ) -> float:
        """Compute trust-adjusted lifetime value.

        LTV = sum_{t=1}^{H} (R * r^t * revenue_mult(T(t))) / (1+d)^t

        Args:
            customer: Customer with current attributes.
            trust_levels: Optional per-month trust level trajectory.
                If None, assumes trust stays at current level.

        Returns:
            Discounted lifetime value in dollars.
        """
        base_retention = DEFAULT_BASE_RETENTION[customer.segment]
        R = customer.monthly_revenue
        d = self.monthly_discount_rate

        ltv = 0.0
        for t in range(1, self.horizon_months + 1):
            # Trust level at month t
            if trust_levels and t <= len(trust_levels):
                T_t = trust_levels[t - 1]
            else:
                T_t = customer.trust_state.trust_level

            phase = customer.trust_state.phase_from_level(T_t)
            rev_mult = PHASE_REVENUE_MULTIPLIER[phase]

            # Retention compounds: probability still active at month t
            retention_t = base_retention ** t

            monthly_value = R * retention_t * rev_mult
            discounted = monthly_value / (1 + d) ** t
            ltv += discounted

        return ltv

    def compute_net_extraction_value(
        self,
        customer: Customer,
        extraction_revenue: float,
        trust_level_after: float,
    ) -> float:
        """Compute net extraction value of a dynamic pricing event.

        NEV = Delta_R - (LTV_before - LTV_after)

        Args:
            customer: Customer state before the event.
            extraction_revenue: Incremental revenue from the manipulation.
            trust_level_after: Trust level after the event.

        Returns:
            Net extraction value. Negative = value-destroying.
        """
        ltv_before = self.compute_ltv(customer)

        # Create post-violation state
        from src.trust_state import TrustState

        post_customer = Customer(
            customer_id=customer.customer_id,
            segment=customer.segment,
            trust_state=TrustState.from_level(trust_level_after),
            monthly_revenue=customer.monthly_revenue,
            tenure_months=customer.tenure_months,
            social_reach=customer.social_reach,
            manipulation_tolerance=customer.manipulation_tolerance,
        )
        ltv_after = self.compute_ltv(post_customer)

        ltv_loss = ltv_before - ltv_after
        return extraction_revenue - ltv_loss

    def compute_segment_comparison(
        self,
        monthly_revenue: float,
        extraction_revenue: float,
        violation_severity: float,
    ) -> dict[str, dict[str, float]]:
        """Compare NEV across Doer and Gambler segments.

        Demonstrates why dynamic pricing is segment-dependent.

        Returns:
            Dict with segment names as keys, containing ltv_before,
            ltv_after, ltv_loss, nev for each.
        """
        from src.trust_degradation import TrustDegradationCurve
        from src.trust_state import TrustState

        curve = TrustDegradationCurve()
        results = {}

        for segment in CustomerSegment:
            customer = Customer(
                customer_id=f"example_{segment.value}",
                segment=segment,
                trust_state=TrustState.from_level(1.0),
                monthly_revenue=monthly_revenue,
            )
            new_state = curve.apply_violation(customer, violation_severity)

            ltv_before = self.compute_ltv(customer)
            post_customer = Customer(
                customer_id=customer.customer_id,
                segment=segment,
                trust_state=new_state,
                monthly_revenue=monthly_revenue,
            )
            ltv_after = self.compute_ltv(post_customer)
            ltv_loss = ltv_before - ltv_after
            nev = extraction_revenue - ltv_loss

            results[segment.value] = {
                "ltv_before": round(ltv_before, 2),
                "ltv_after": round(ltv_after, 2),
                "ltv_loss": round(ltv_loss, 2),
                "net_extraction_value": round(nev, 2),
            }

        return results

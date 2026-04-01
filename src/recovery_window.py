"""Recovery window detection and intervention model.

Formalizes Section 6 of the ZNP paper.

Recovery probability as a function of trust level and intervention quality:

    P_recover(T, Q) = max(0, R_phase * Q * (T - T_critical) / (T_full - T_critical))

Where:
    T            = current trust level
    R_phase      = phase-specific recovery potential ceiling
    Q            = intervention quality score in [0, 1]
                   (1.0 = perfect transparent communication per Section 6.2)
    T_critical   = critical threshold boundary (0.50)
    T_full       = full trust boundary (0.80)

Intervention quality factors (Section 6.2):
    - Honesty:       Is the communication honest and specific?
    - No promotion:  Is there zero promotional intent?
    - Plain language: Is it operational, not PR-script?
    - Acknowledgment: Does it acknowledge the specific practice?

    Q = mean(honesty, no_promotion, plain_language, acknowledgment)

Expected value of intervention:

    EV_intervene = P_recover * LTV_recovered - C_intervention
    EV_no_action = LTV_degraded

    Net value = EV_intervene - EV_no_action
"""

from __future__ import annotations

from dataclasses import dataclass

from src.customer import Customer
from src.trust_state import TrustPhase, TrustState, PHASE_RECOVERY_POTENTIAL


# Trust level boundaries between phases.
T_FULL = 0.80
T_CRITICAL = 0.50


@dataclass
class InterventionQuality:
    """Quality score components for a recovery intervention (Section 6.2).

    Each factor in [0, 1]. Higher = better.
    """

    honesty: float = 0.0
    no_promotion: float = 0.0
    plain_language: float = 0.0
    acknowledgment: float = 0.0

    @property
    def score(self) -> float:
        """Composite quality score Q = mean of all factors."""
        return (
            self.honesty + self.no_promotion + self.plain_language + self.acknowledgment
        ) / 4.0


@dataclass
class RecoveryWindowModel:
    """Detect recovery windows and model intervention outcomes.

    Attributes:
        t_full: Trust level boundary for full-trust phase.
        t_critical: Trust level boundary for critical threshold.
    """

    t_full: float = T_FULL
    t_critical: float = T_CRITICAL

    def recovery_probability(
        self,
        trust_state: TrustState,
        intervention_quality: InterventionQuality,
    ) -> float:
        """Compute probability of successful recovery.

        P = R_phase * Q * (T - T_critical) / (T_full - T_critical)

        Returns 0 if customer is below critical threshold.
        """
        R_phase = PHASE_RECOVERY_POTENTIAL[trust_state.phase]
        Q = intervention_quality.score
        T = trust_state.trust_level

        if T <= self.t_critical:
            return 0.0

        position = (T - self.t_critical) / (self.t_full - self.t_critical)
        probability = R_phase * Q * position
        return max(0.0, min(1.0, probability))

    def is_window_open(self, trust_state: TrustState) -> bool:
        """Check if recovery window is still open.

        Window is open only in EARLY_EROSION phase (Section 6).
        """
        return trust_state.phase == TrustPhase.EARLY_EROSION

    def expected_intervention_value(
        self,
        customer: Customer,
        intervention_quality: InterventionQuality,
        intervention_cost: float = 0.0,
    ) -> dict[str, float]:
        """Compute expected value of intervening vs. doing nothing.

        Args:
            customer: Customer in degraded trust state.
            intervention_quality: Quality of the proposed intervention.
            intervention_cost: Direct cost of the intervention.

        Returns:
            Dict with recovery_probability, ev_intervene, ev_no_action,
            and net_value.
        """
        from src.lifetime_value import LifetimeValueModel

        ltv_model = LifetimeValueModel()
        p_recover = self.recovery_probability(
            customer.trust_state, intervention_quality
        )

        # LTV if recovered (assume return to 0.90 trust, not perfect 1.0)
        recovered_customer = Customer(
            customer_id=customer.customer_id,
            segment=customer.segment,
            trust_state=TrustState.from_level(0.90),
            monthly_revenue=customer.monthly_revenue,
            tenure_months=customer.tenure_months,
            social_reach=customer.social_reach,
            manipulation_tolerance=customer.manipulation_tolerance,
        )
        ltv_recovered = ltv_model.compute_ltv(recovered_customer)

        # LTV at current degraded state
        ltv_degraded = ltv_model.compute_ltv(customer)

        ev_intervene = p_recover * ltv_recovered - intervention_cost
        ev_no_action = ltv_degraded

        return {
            "recovery_probability": round(p_recover, 4),
            "ltv_if_recovered": round(ltv_recovered, 2),
            "ltv_if_degraded": round(ltv_degraded, 2),
            "ev_intervene": round(ev_intervene, 2),
            "ev_no_action": round(ev_no_action, 2),
            "net_value": round(ev_intervene - ev_no_action, 2),
        }

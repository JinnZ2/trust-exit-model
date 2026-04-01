"""Dynamic pricing risk assessment model.

Formalizes the core insight from README and Sections 7 of the ZNP paper.

Total cost of a dynamic pricing event applied to a mixed population:

    TC = sum_{i in customers} [NEV_i + CAC_impact_i]

Where:
    NEV_i        = net extraction value for customer i
                   (see lifetime_value.py)
    CAC_impact_i = downstream acquisition cost from WOM if customer i
                   is a Doer who exits (see community_amplification.py)

Expected value of dynamic pricing across unknown segment mix:

    EV = p_doer * NEV_doer + (1 - p_doer) * NEV_gambler

Where:
    p_doer      = estimated fraction of Doers in the target population
    NEV_doer    = net extraction value when applied to a Doer (usually << 0)
    NEV_gambler = net extraction value when applied to a Gambler (usually > 0)

Break-even Doer fraction (the population fraction at which dynamic
pricing becomes net-negative):

    p_break = NEV_gambler / (NEV_gambler - NEV_doer)

If the actual Doer fraction exceeds p_break, dynamic pricing destroys
net value across the population.
"""

from __future__ import annotations

from dataclasses import dataclass

from src.community_amplification import CommunityAmplificationModel
from src.customer import Customer, CustomerSegment
from src.lifetime_value import LifetimeValueModel
from src.trust_degradation import TrustDegradationCurve
from src.trust_state import TrustState


@dataclass
class DynamicPricingRiskModel:
    """Assess risk of dynamic pricing events across customer segments.

    Attributes:
        ltv_model: Lifetime value calculator.
        degradation_curve: Trust degradation model.
        amplification_model: Community WOM model.
    """

    ltv_model: LifetimeValueModel | None = None
    degradation_curve: TrustDegradationCurve | None = None
    amplification_model: CommunityAmplificationModel | None = None

    def __post_init__(self) -> None:
        if self.ltv_model is None:
            self.ltv_model = LifetimeValueModel()
        if self.degradation_curve is None:
            self.degradation_curve = TrustDegradationCurve()
        if self.amplification_model is None:
            self.amplification_model = CommunityAmplificationModel()

    def assess_event(
        self,
        extraction_revenue: float,
        violation_severity: float,
        monthly_revenue: float,
        social_reach: int = 5,
        cac_per_customer: float = 50.0,
        wom_months: int = 12,
    ) -> dict[str, dict[str, float]]:
        """Assess a dynamic pricing event across both segments.

        Returns per-segment and aggregate metrics.
        """
        results = {}

        for segment in CustomerSegment:
            customer = Customer(
                customer_id=f"assess_{segment.value}",
                segment=segment,
                trust_state=TrustState.from_level(1.0),
                monthly_revenue=monthly_revenue,
                social_reach=social_reach,
            )

            ltv_before = self.ltv_model.compute_ltv(customer)
            new_state = self.degradation_curve.apply_violation(customer, violation_severity)

            post_customer = Customer(
                customer_id=customer.customer_id,
                segment=segment,
                trust_state=new_state,
                monthly_revenue=monthly_revenue,
                social_reach=social_reach,
            )
            ltv_after = self.ltv_model.compute_ltv(post_customer)
            ltv_loss = ltv_before - ltv_after
            nev = extraction_revenue - ltv_loss

            # WOM impact (only meaningful for Doers who exit)
            wom_cost = 0.0
            if segment == CustomerSegment.DOER and new_state.trust_level < 0.50:
                wom_cost = self.amplification_model.cac_impact(
                    num_exits=1,
                    avg_social_reach=social_reach,
                    months=wom_months,
                    cac_per_customer=cac_per_customer,
                )

            total_cost = -nev + wom_cost if nev < 0 else -nev + wom_cost

            results[segment.value] = {
                "ltv_before": round(ltv_before, 2),
                "ltv_after": round(ltv_after, 2),
                "ltv_loss": round(ltv_loss, 2),
                "net_extraction_value": round(nev, 2),
                "wom_cost": round(wom_cost, 2),
                "total_impact": round(nev - wom_cost, 2),
            }

        return results

    def compute_breakeven_doer_fraction(
        self,
        extraction_revenue: float,
        violation_severity: float,
        monthly_revenue: float,
    ) -> float:
        """Compute the Doer population fraction at which dynamic pricing breaks even.

        p_break = NEV_gambler / (NEV_gambler - NEV_doer)

        Returns:
            Break-even fraction in [0, 1]. If actual Doer fraction exceeds
            this, dynamic pricing is net-negative.
        """
        results = self.assess_event(
            extraction_revenue=extraction_revenue,
            violation_severity=violation_severity,
            monthly_revenue=monthly_revenue,
        )

        nev_doer = results["doer"]["net_extraction_value"]
        nev_gambler = results["gambler"]["net_extraction_value"]

        denominator = nev_gambler - nev_doer
        if abs(denominator) < 1e-9:
            return 0.0  # Both segments respond identically (degenerate case)

        p_break = nev_gambler / denominator
        return round(max(0.0, min(1.0, p_break)), 4)

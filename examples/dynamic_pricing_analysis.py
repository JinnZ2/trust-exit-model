#!/usr/bin/env python3
"""Example: Analyze a dynamic pricing event across customer segments.

Demonstrates the core insight of the trust-exit-model:
a $5 price manipulation can destroy thousands in lifetime value
when applied to Doer (zero-tolerance) customers.
"""

import sys
sys.path.insert(0, ".")

from src.customer import Customer, CustomerSegment
from src.dynamic_pricing_risk import DynamicPricingRiskModel
from src.lifetime_value import LifetimeValueModel
from src.trust_degradation import TrustDegradationCurve
from src.trust_state import TrustState


def main():
    # --- Scenario ---
    monthly_revenue = 200.0      # Customer spends $200/month
    extraction_revenue = 5.0     # Dynamic pricing adds $5 to one transaction
    violation_severity = 0.5     # Moderate manipulation (50% severity)

    print("=" * 65)
    print("DYNAMIC PRICING RISK ANALYSIS")
    print("=" * 65)
    print(f"Monthly revenue per customer:  ${monthly_revenue:.2f}")
    print(f"Extraction revenue (one-time): ${extraction_revenue:.2f}")
    print(f"Violation severity:            {violation_severity:.0%}")
    print()

    # --- Trust degradation comparison ---
    curve = TrustDegradationCurve()
    print("-" * 65)
    print("TRUST DEGRADATION (single violation)")
    print("-" * 65)

    for segment in CustomerSegment:
        customer = Customer(
            customer_id=f"example_{segment.value}",
            segment=segment,
            trust_state=TrustState.from_level(1.0),
            monthly_revenue=monthly_revenue,
        )
        after = curve.apply_violation(customer, violation_severity)
        print(f"  {segment.value.upper():8s}: trust 1.000 -> {after.trust_level:.3f}"
              f"  (phase: {after.phase.name})")
    print()

    # --- Full risk assessment ---
    risk_model = DynamicPricingRiskModel()
    results = risk_model.assess_event(
        extraction_revenue=extraction_revenue,
        violation_severity=violation_severity,
        monthly_revenue=monthly_revenue,
        social_reach=5,
        cac_per_customer=50.0,
        wom_months=12,
    )

    print("-" * 65)
    print("NET EXTRACTION VALUE ANALYSIS")
    print("-" * 65)
    for seg_name, metrics in results.items():
        print(f"\n  {seg_name.upper()}:")
        print(f"    LTV before:          ${metrics['ltv_before']:>10,.2f}")
        print(f"    LTV after:           ${metrics['ltv_after']:>10,.2f}")
        print(f"    LTV loss:            ${metrics['ltv_loss']:>10,.2f}")
        print(f"    Net extraction value: ${metrics['net_extraction_value']:>10,.2f}")
        print(f"    WOM cost:            ${metrics['wom_cost']:>10,.2f}")
        print(f"    Total impact:        ${metrics['total_impact']:>10,.2f}")

    # --- Break-even analysis ---
    p_break = risk_model.compute_breakeven_doer_fraction(
        extraction_revenue, violation_severity, monthly_revenue
    )
    print(f"\n{'=' * 65}")
    print(f"BREAK-EVEN DOER FRACTION: {p_break:.2%}")
    print(f"{'=' * 65}")
    print(f"If more than {p_break:.2%} of your customers are Doers,")
    print(f"dynamic pricing destroys net value across the population.")
    print()

    # --- Multi-violation trajectory ---
    print("-" * 65)
    print("DOER TRUST TRAJECTORY (repeated 0.3-severity violations)")
    print("-" * 65)
    doer = Customer(
        customer_id="trajectory_doer",
        segment=CustomerSegment.DOER,
        trust_state=TrustState.from_level(1.0),
        monthly_revenue=monthly_revenue,
    )
    trajectory = curve.simulate_violations(doer, [0.3] * 5)
    for i, state in enumerate(trajectory, 1):
        bar = "#" * int(state.trust_level * 40)
        print(f"  Violation {i}: trust={state.trust_level:.3f} "
              f"phase={state.phase.name:20s} |{bar}")


if __name__ == "__main__":
    main()

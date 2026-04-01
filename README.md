# trust-exit-model

Behavioral segmentation framework for identifying zero-tolerance-manipulation customer segments and modeling permanent churn from trust violations.

## The Problem

Dynamic pricing algorithms optimize for short-term extraction by testing what each customer will tolerate. They assume all customers respond to manipulation the same way.

They don't.

## The Segmentation Gap

Current behavioral models classify customers by price sensitivity, purchase frequency, and brand loyalty. They're missing a critical axis: **manipulation tolerance**.

Two segments exist:

- **Gamblers** — tolerate variable pricing, negotiate, rationalize, stay. These customers can be gamed.
- **Doers** — zero tolerance for manipulation. One trust violation triggers permanent exit, word-of-mouth defection, and ecosystem abandonment.

Algorithmic pricing systems treat both segments identically. This is a fundamental classification error.

## The Cascading Failure

When a Doer detects dynamic pricing:

1. Trust is broken immediately and permanently
2. Customer exits the platform — not the transaction, the relationship
3. Word-of-mouth defection spreads to community
4. Customer actively chooses friction over dishonesty
5. Company loses thousands in lifetime value to recover single-transaction margin

The algorithm logs this as normal churn. It is not.

## What This Repo Models

- **Trust degradation curve** — exponential decay with segment-specific parameters
- **Lifetime value with trust adjustment** — NPV calculation incorporating trust-phase revenue multipliers
- **Behavioral fingerprint scoring** — composite signal detection for ZNP classification
- **Community amplification** — word-of-mouth contagion with second-order propagation
- **Dynamic pricing risk** — net extraction value analysis and break-even Doer fraction
- **Recovery window** — intervention probability modeling with quality-adjusted outcomes

## Repository Structure

```
trust-exit-model/
├── src/                          # Python implementation
│   ├── trust_state.py            # TrustPhase enum, TrustState dataclass
│   ├── customer.py               # Customer, CustomerSegment definitions
│   ├── trust_degradation.py      # Trust decay curve (exponential model)
│   ├── lifetime_value.py         # LTV with trust-state adjustment, NEV
│   ├── behavioral_fingerprint.py # Composite ZNP detection scoring
│   ├── community_amplification.py# WOM contagion and CAC impact
│   ├── dynamic_pricing_risk.py   # Full risk assessment, break-even analysis
│   └── recovery_window.py        # Recovery probability and intervention EV
├── tests/                        # Test suite (54 tests)
├── examples/
│   └── dynamic_pricing_analysis.py  # End-to-end scenario analysis
├── docs/
│   ├── equations.md              # Formalized mathematical equations
│   └── zero-nudge-population.md  # Original ZNP research paper
├── CLAUDE.md                     # Development guide
└── README.md
```

## Quick Start

```bash
# Run the example analysis
python examples/dynamic_pricing_analysis.py

# Run tests
python -m pytest tests/ -v
```

## Example Output

```
DYNAMIC PRICING RISK ANALYSIS
Monthly revenue per customer:  $200.00
Extraction revenue (one-time): $5.00
Violation severity:            50%

  DOER:
    LTV before:          $  6,110.51
    LTV after:           $  2,444.21
    LTV loss:            $  3,666.31
    Net extraction value: $ -3,661.31

  GAMBLER:
    LTV before:          $  2,153.92
    LTV after:           $  2,153.92
    Net extraction value: $      5.00

BREAK-EVEN DOER FRACTION: 0.14%
```

A $5 manipulation destroys $3,661 in Doer lifetime value. If even 0.14% of customers are Doers, dynamic pricing is net-negative across the population.

## Core Insight

> "I will adapt what I prefer around integrity."

Doers don't negotiate with dishonesty. They exit. The companies that figure this out first will retain the most stable, highest-integrity customer base in their market.

## Standardized Terminology

| Term | Definition |
|------|-----------|
| **Doer** | Zero-tolerance customer segment. Hard exit on trust violation. |
| **Gambler** | Manipulation-tolerant segment. Negotiates, rationalizes, stays. |
| **ZNP** | Zero-Nudge Population. Structurally invisible to engagement-based models. |
| **Trust level** | Continuous score in [0, 1]. 1.0 = full trust, 0.0 = zero trust. |
| **Trust phase** | Discrete state: FULL_TRUST, EARLY_EROSION, CRITICAL_THRESHOLD, TERMINAL, FINAL_EXIT. |
| **NEV** | Net Extraction Value. Revenue gained minus LTV destroyed. Negative = value-destroying. |
| **WOM** | Word-of-mouth. ZNP customers influence via direct social networks, not digital traces. |
| **CAC** | Customer Acquisition Cost. Downstream cost of replacing WOM-influenced defections. |

## License

CC0 1.0 Universal — No rights reserved.

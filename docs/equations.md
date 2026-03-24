# Formalized Equations

Mathematical formalization of the Zero-Nudge Population (ZNP) behavioral model.

All equations correspond to sections of the [ZNP paper](../docs/zero-nudge-population.md).

---

## 1. Trust Degradation Curve (Paper Section 3)

### 1.1 Violation-Driven Decay

Trust level after the *n*th violation event:

```
T(n) = T(n-1) * exp(-alpha * S_n / M)
```

| Symbol   | Definition                                    | Range    |
|----------|-----------------------------------------------|----------|
| `T(n)`   | Trust level after violation *n*                | [0, 1]   |
| `T(n-1)` | Trust level before violation *n*               | [0, 1]   |
| `alpha`  | Segment-specific decay rate (Doer=2.0, Gambler=0.3) | > 0 |
| `S_n`    | Perceived severity of violation *n*            | [0, 1]   |
| `M`      | Customer manipulation tolerance threshold      | (0, 1]   |

**Properties:**
- Monotonically non-increasing (violations never restore trust)
- Low-tolerance customers experience amplified decay (small `M` -> larger exponent)
- Multiple small violations compound multiplicatively

### 1.2 Passive Erosion (Between Violations)

```
T(t) = T_0 * (1 - beta * delta_t)       clamped to [0, T_0]
```

| Symbol    | Definition                                    | Default        |
|-----------|-----------------------------------------------|----------------|
| `beta`    | Passive erosion rate per month                | Doer=0.02, Gambler=0.01 |
| `delta_t` | Months since last state change                | >= 0           |

Only applies in degraded phases (EARLY_EROSION or worse). Full-trust customers do not passively erode.

### 1.3 Phase Mapping

Continuous trust level maps to discrete phases:

| Trust Level Range | Phase               | Recovery Potential |
|-------------------|---------------------|--------------------|
| [0.80, 1.00]      | FULL_TRUST          | N/A (intact)       |
| [0.50, 0.80)      | EARLY_EROSION       | HIGH (0.70)        |
| [0.25, 0.50)      | CRITICAL_THRESHOLD  | LOW (0.15)         |
| [0.05, 0.25)      | TERMINAL            | ZERO (0.00)        |
| [0.00, 0.05)      | FINAL_EXIT          | ZERO (0.00)        |

---

## 2. Lifetime Value (Paper Section 7)

### 2.1 Trust-Adjusted LTV

```
LTV = sum_{t=1}^{H} (R * r^t * mu(T(t))) / (1 + d)^t
```

| Symbol   | Definition                                    | Default          |
|----------|-----------------------------------------------|------------------|
| `R`      | Monthly revenue (trust-intact)                | Customer-specific |
| `r`      | Base monthly retention rate                   | Doer=0.98, Gambler=0.92 |
| `mu(T)`  | Revenue multiplier from trust phase           | See table below  |
| `d`      | Monthly discount rate                         | 0.005 (~6% annual) |
| `H`      | Time horizon in months                        | 60               |

**Revenue multiplier by phase:**

| Phase               | `mu` | Behavioral Meaning                        |
|---------------------|------|-------------------------------------------|
| FULL_TRUST          | 1.00 | Normal spending                           |
| EARLY_EROSION       | 0.85 | Slight reduction, still purchasing        |
| CRITICAL_THRESHOLD  | 0.40 | Strictly transactional                    |
| TERMINAL            | 0.10 | Reconnaissance only                       |
| FINAL_EXIT          | 0.00 | Gone                                      |

### 2.2 Net Extraction Value (NEV)

```
NEV = Delta_R - (LTV_before - LTV_after)
```

| Symbol       | Definition                                    |
|--------------|-----------------------------------------------|
| `Delta_R`    | Incremental revenue from the price manipulation |
| `LTV_before` | Trust-adjusted LTV before the event           |
| `LTV_after`  | Trust-adjusted LTV after the event            |

**NEV < 0 means the manipulation destroyed more value than it captured.**

---

## 3. Behavioral Fingerprint (Paper Section 5)

### 3.1 Composite Score

```
F = sum_{i=1}^{N} w_i * s_i
```

| Symbol | Definition                                    | Constraint       |
|--------|-----------------------------------------------|------------------|
| `w_i`  | Weight for signal category *i*                | sum(w_i) = 1.0   |
| `s_i`  | Normalized score for category *i*             | [0, 1]           |
| `F`    | Composite fingerprint score                   | [0, 1]           |

**Default weights:**

| Category                | Weight | Signals                                    |
|-------------------------|--------|--------------------------------------------|
| Temporal markers        | 0.25   | Abrupt cancellation, trigger correlation   |
| Session characteristics | 0.15   | Browsing linearity, category exploration   |
| Engagement profile      | 0.25   | Communication response, feature usage      |
| Re-engagement response  | 0.25   | Abandonment recovery, offer response       |
| Exit characteristics    | 0.10   | Exit data quality, complaint absence       |

**Classification:** `F >= 0.60` -> probable ZNP in terminal trust state.

---

## 4. Community Amplification (Paper Sections 2.2, 7)

### 4.1 First-Order Word-of-Mouth Defections

```
A(t) = N_exit * R_social * C_trust * (1 - decay^t)
```

| Symbol     | Definition                                    | Default |
|------------|-----------------------------------------------|---------|
| `N_exit`   | Number of ZNP customers who exited            |         |
| `R_social` | Average social reach per ZNP customer         | 5       |
| `C_trust`  | WOM conversion rate (fraction who also defect)| 0.08    |
| `decay`    | Monthly WOM influence decay                   | 0.85    |
| `t`        | Months since exit                             |         |

### 4.2 Second-Order Propagation

```
A_total(t) = A_1(t) + gamma * A_1(t) * R_social_2 * C_trust_2
```

| Symbol       | Definition                                    | Default |
|--------------|-----------------------------------------------|---------|
| `gamma`      | Probability first-order defector spreads WOM  | 0.30    |
| `R_social_2` | Social reach of first-order defectors         | 3       |
| `C_trust_2`  | Second-order conversion rate                  | 0.03    |

### 4.3 Customer Acquisition Cost Impact

```
CAC_impact = A_total(t) * CAC_per_customer
```

---

## 5. Recovery Window (Paper Section 6)

### 5.1 Recovery Probability

```
P_recover = R_phase * Q * (T - T_critical) / (T_full - T_critical)
```

| Symbol       | Definition                                    | Default |
|--------------|-----------------------------------------------|---------|
| `R_phase`    | Phase-specific recovery potential ceiling     | See 1.3 |
| `Q`          | Intervention quality score                    | [0, 1]  |
| `T`          | Current trust level                           |         |
| `T_critical` | Critical threshold boundary                  | 0.50    |
| `T_full`     | Full trust boundary                           | 0.80    |

Returns 0 when `T <= T_critical` (window closed).

### 5.2 Intervention Quality

```
Q = mean(honesty, no_promotion, plain_language, acknowledgment)
```

Each factor in [0, 1]. Based on Section 6.2 requirements.

### 5.3 Expected Value of Intervention

```
EV_intervene = P_recover * LTV_recovered - C_intervention
EV_no_action = LTV_degraded
Net_value    = EV_intervene - EV_no_action
```

---

## 6. Break-Even Analysis

### 6.1 Break-Even Doer Fraction

```
p_break = NEV_gambler / (NEV_gambler - NEV_doer)
```

If the actual Doer fraction in the customer population exceeds `p_break`, dynamic pricing is net-negative across the entire population.

### 6.2 Population-Level Expected Value

```
EV = p_doer * NEV_doer + (1 - p_doer) * NEV_gambler
```

When `EV < 0`, the pricing strategy destroys aggregate value.

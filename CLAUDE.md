# CLAUDE.md — Development Guide for trust-exit-model

## What This Project Is

Behavioral segmentation framework modeling how trust violations cause permanent customer churn. Based on the Zero-Nudge Population (ZNP) research paper. Implements mathematical models for trust degradation, lifetime value loss, behavioral fingerprint detection, community amplification, and dynamic pricing risk assessment.

## Project Structure

- `src/` — Python modules (the model implementation)
- `tests/` — pytest test suite (110 tests)
- `examples/` — runnable scenario scripts
- `docs/` — formalized equations, the method record, and the ZNP research paper
- `tools/` — instruments pointed at the repo's own claims, not at the model
- `legacy/` — superseded or unwired modules, retained not retracted (see below)

## Commands

```bash
# Run all tests
python -m pytest tests/ -v

# Run a specific test file
python -m pytest tests/test_trust_degradation.py -v

# Run the example analysis
python examples/dynamic_pricing_analysis.py

# Search for instruments that could close the open unknowns
python tools/instrument_explorer.py            # probes + ranked catalog
python tools/instrument_explorer.py --probes   # runnable probes only
python tools/instrument_explorer.py --unknown U2
```

## Architecture

Eight core models plus three integration modules, all in `src/`:

| Module | Purpose | Key Equation |
|--------|---------|-------------|
| `trust_state.py` | Phase/level definitions | `phase_from_level(T)` maps continuous to discrete |
| `customer.py` | Customer & segment types | Doer vs Gambler segmentation |
| `trust_degradation.py` | Decay curve | `T(n) = T(n-1) * exp(-alpha * S / M)` |
| `lifetime_value.py` | Trust-adjusted LTV, NEV | `LTV = sum(R * r^t * mu(T)) / (1+d)^t` |
| `behavioral_fingerprint.py` | ZNP detection scoring | `F = sum(w_i * s_i)`, threshold at 0.60 |
| `community_amplification.py` | WOM contagion | `A(t) = N * R * C * (1 - decay^t)` |
| `dynamic_pricing_risk.py` | Full risk assessment | Combines LTV + WOM + break-even |
| `recovery_window.py` | Intervention modeling | `P = R_phase * Q * (T - T_crit) / (T_full - T_crit)` |

Integration modules (not core equations, but on the live import path):

| Module | Purpose |
|--------|---------|
| `support_cartography.py` | Three-gate framework: EMISSION / CAPTURE / RETENTION. Only `Gate` is currently consumed — see U4 in `docs/method.md`. |
| `znp_gate_bridge.py` | Maps ZNP fingerprint signals onto the three gates to explain *why* a customer was invisible |
| `contract_export.py` | Canonical emitter for the published contract surface (see below) |

## Method and Precedence

This repo runs an explicit hypothesize → run → falsify → revise → find-unknowns →
rerun loop. [`docs/method.md`](docs/method.md) is the record: claim register,
falsification log, and open unknowns.

Two rules that bind development here:

1. **Superseded work is retired to `legacy/`, never deleted.** Precedence carries —
   a falsified version is the only record of how the current claim was reached.
   `legacy/README.md` distinguishes *superseded* (tested and replaced) from
   *unwired* (never falsified, never load-bearing) and requires each entry to say
   which applies. Nothing in `src/` may import from `legacy/`.
2. **When a claim breaks, log it and log what it exposed.** A fix without a
   recorded unknown is half the loop. Unknowns get a `U` number and persist until
   something measures them.

The tests can falsify equation claims and descriptive claims. They **cannot**
falsify calibration constants — a green suite means the constants are
self-consistent, not correct. U2 (Doer population fraction unmeasured) and U7
(phase boundaries dominate every output) are load-bearing for every dollar
figure the README quotes.

Before treating an unknown as a data problem, run the instrument search — three
of the six original unknowns turned out not to need field data at all:

```bash
python tools/instrument_explorer.py --probes
```

## Standardized Naming Conventions

- **Segments**: `CustomerSegment.DOER`, `CustomerSegment.GAMBLER` (never "type A/B" or other labels)
- **Trust phases**: `TrustPhase.FULL_TRUST`, `EARLY_EROSION`, `CRITICAL_THRESHOLD`, `TERMINAL`, `FINAL_EXIT`
- **Trust level**: Always `trust_level`, continuous float in [0, 1]
- **Severity**: Always `severity`, float in [0, 1], represents perceived severity of a violation
- **Alpha/beta**: `alpha` = violation decay rate, `beta` = passive erosion rate
- **NEV**: Net Extraction Value (revenue gained minus LTV destroyed)
- **WOM**: Word-of-mouth (not "viral" or "network effects")
- **CAC**: Customer Acquisition Cost

## Key Design Decisions

- `TrustState` is immutable (frozen dataclass) — state transitions produce new instances
- All monetary values are in dollars
- Time units are months throughout
- Decay is exponential (multiplicative compounding), not linear
- Phase boundaries: 0.80 / 0.50 / 0.25 / 0.05
- Default calibration: Doer reaches terminal in ~2 moderate violations, exit in ~3. Gambler stays in early erosion through 4+ violations.

## Code Style

- Python 3.11+, type hints throughout
- `from __future__ import annotations` in all modules
- Dataclasses for models, enums for categories
- No external dependencies beyond stdlib + pytest

## Published Contract (for external consumers)

The Thermodynamic Accountability Framework (TAF) mirrors this repo's stable surface at [`schemas/trust_exit_contract.py`](https://github.com/JinnZ2/thermodynamic-accountability-framework/blob/main/schemas/trust_exit_contract.py) (`CONTRACT_VERSION = "1.0.0"`). External consumers should import that mirror rather than this package — it stays stdlib-only and is versioned independently.

**Contract-stable surface** (breaking changes bump the mirror's major version):
- `TrustPhase` (5-member IntEnum, name + ordering fixed)
- `TrustState` (`trust_level`, `phase`, `violations_count`, `recovery_potential`)
- `CustomerSegment` (`DOER`, `GAMBLER`)
- `Customer` public fields
- Derived scalars: `nev`, `ltv`, `fingerprint_score`, `is_znp`, `gate_failure` profile

**Not in the contract** (calibration knobs, may retune without a version bump):
- `alpha`/`beta` decay constants
- 0.80 / 0.50 / 0.25 / 0.05 phase-boundary thresholds
- 0.60 ZNP fingerprint cutoff

> **Warning — this fence is in the wrong place (U7).** Probe P2 in
> `tools/instrument_explorer.py` shows `compute_ltv` emits exactly **5 distinct
> values** across the whole trust range: the phase boundaries, not the
> continuous trust level, determine every dollar figure. Retuning the 0.50
> boundary moves a Doer's LTV by **$2,749.73** on the README's own inputs — with
> no version signal to any downstream consumer. Treat boundary changes as
> breaking until U7 is resolved, whatever this list says.

**Wire-format commitment**: `TrustPhase` is serialized as its name-string (`"FULL_TRUST"` etc.), never as its `IntEnum` integer. `src/contract_export.py` is the canonical emitter; regression tests in `tests/test_contract_export.py` pin this.

<!-- clone-refspec-note v1.1 -->
## Cloning and pushing
Shallow clones are single-branch by default.
Before pushing any branch other than the default
branch, run:

    git config remote.origin.fetch '+refs/heads/*:refs/remotes/origin/*'
    git fetch --depth 1

Or clone with: git clone --depth 1 --no-single-branch <url>
Without this, the first push of a new branch
fails the tracking-ref check even when the
commit landed.
<!-- /clone-refspec-note v1.1 -->

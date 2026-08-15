# Method — how claims in this repo are made, broken, and revised

This repo is a set of claims about behavior, expressed as equations and pinned by
tests. Claims here are not settled by argument. They are settled by running them.

This document is the record of that process, so that a future reader — human or
model — can see not just what the model currently says, but what it used to say,
what broke it, and what is still unmeasured.

---

## The loop

```
        ┌──────────────────────────────────────────────────┐
        │                                                  │
        ▼                                                  │
    HYPOTHESIZE ──► RUN ──► result ──┬── holds ──► record & move on
    state the claim  test it         │
    with a falsifier                 └── FALSIFIED
                                              │
                                              ▼
                                        EDIT THE CLAIM
                                        (old version → legacy/,
                                         entry → log below)
                                              │
                                              ▼
                                    SEARCH FOR UNKNOWNS ─────┘
                                    what did this expose
                                    that nothing tests?
```

Six steps, and the last two are the ones usually skipped.

**1. Hypothesize.** State the claim so that it *could* fail. A claim with no
falsifier is not a claim, it is a preference. Every entry in the register below
carries a "falsified by" column; if you cannot fill that column, the claim is not
ready.

**2. Run.** Execute it. `python -m pytest tests/ -v`, or run the example, or
compute the constant by hand and compare. Reading the code is not running it —
this repo has had claims that were true of the code as written and false of the
code as executed.

**3. Result.** Holds, or falsified. There is no third outcome, and "mostly holds"
means the claim was stated too loosely to test — go back to step 1.

**4. Edit the claim.** Not delete it. The superseded version moves to
[`legacy/`](../legacy/README.md) and gets a log entry here. Precedence carries:
the falsified version is the only record of how the current claim was reached,
and without it the next person re-runs the same failed experiment.

**5. Search for unknowns.** A falsification usually exposes something adjacent
that nothing tests at all. This is the highest-value step and it produces no
green checkmark, which is why it gets dropped. Unknowns go in the register below
with a `U` number and stay there until something measures them.

**6. Rerun.** From the top, with the edited claim. A revision that has not been
re-run is a hypothesis wearing a result's clothes.

---

## What is and is not falsifiable here

Not everything in the repo is a claim about the world.

| Layer | Falsifiable by | Example |
|-------|----------------|---------|
| **Equations** (`docs/equations.md`) | Internal check: does `src/` compute what the doc says? | `T(n) = T(n-1) * exp(-alpha*S/M)` |
| **Calibration constants** | External data only. Nothing in this repo can falsify them. | `alpha` = 2.0 / 0.3 |
| **Contract surface** (`src/contract_export.py`) | Regression tests + downstream decode failure | phase emitted as name-string |
| **Descriptive claims** (README, CLAUDE.md) | Direct comparison against the tree | "79 tests" |

The distinction matters. `tests/` can falsify an equation claim or a descriptive
claim outright. It **cannot** falsify a calibration constant — a passing suite
means the constants are self-consistent, not that they are right. Everything in
the "Calibration constants" row is an assumption until field data arrives, and
`CLAUDE.md` already fences those off from the published contract for this reason.

---

## Claim register

Live claims and what would break each one.

| ID | Claim | Falsified by | Status |
|----|-------|--------------|--------|
| C1 | Trust decays multiplicatively per violation; violations never restore trust | Any observed trust recovery without intervention | Holds (pinned, `test_trust_degradation.py`) |
| C2 | Phase boundaries at 0.80 / 0.50 / 0.25 / 0.05 partition [0,1] with no gaps or overlap | A trust level mapping to two phases or none | Holds (pinned, `test_trust_state.py`) |
| C3 | Full-trust customers do not passively erode | Erosion applied at `phase == FULL_TRUST` | Holds (guarded, `trust_degradation.py:120`) |
| C4 | Doer reaches TERMINAL in ~2 moderate violations, FINAL_EXIT in ~3 | Recomputing the decay and landing elsewhere | Holds (computed: 0.349 → 0.122 → 0.043) |
| C5 | Gambler stays in EARLY_EROSION through 4 moderate violations | Same | Holds (computed: 0.854/0.729/0.623/0.532, critical at 5th) |
| C6 | `TrustPhase` serializes as name-string, never as its IntEnum integer | An emitted payload containing an integer phase | Holds (pinned, `test_contract_export.py`) |
| C7 | A $5 extraction destroys $3,661 of Doer LTV at severity 0.50 | Running the example and getting another number | Holds (verified against live run, to the cent) |
| C8 | Break-even Doer fraction is 0.14% | Same | Holds internally — but see U2 |
| C9 | Low manipulation tolerance amplifies decay for Doers | Both segments carrying the same `M` | **FALSIFIED** — see F5 |

---

## Falsification log

Newest first. Each entry: what was claimed, what running it showed, what changed.

### 2026-08-15 — audit pass over the descriptive layer

Ran the full suite (79 passed), ran the example, and hand-checked every constant
in `docs/equations.md` against `src/`.

**Held — the math layer is clean.** Every constant in the equations doc matches
the code: `alpha` 2.0/0.3, `beta` 0.02/0.01, retention 0.98/0.92, the five-row
`mu` table, `d` = 0.005, `H` = 60, and the phase boundaries. The README's example
output matches a live run exactly. C1–C8 above all survived. No equation was
edited in this pass.

**Falsified — the descriptive layer had drifted.** Five claims, all in the files
that *describe* the model rather than implement it:

| # | Claim | Where | Result | Fix |
|---|-------|-------|--------|-----|
| F1 | "Test suite (54 tests)" | `README.md` | 79 tests | Corrected |
| F2 | Structure block lists 8 `src/` modules | `README.md` | 11 modules present | Rewritten |
| F3 | "Six interconnected models, all in `src/`" | `CLAUDE.md` | Table beneath it had 8 rows; tree had 13 modules | Corrected to 8 core + 3 integration |
| F4 | Package exports the model's public surface | `src/__init__.py` | Exported 10 names; omitted `znp_gate_bridge`, `contract_export`, and `Gate` — all three named in CLAUDE.md's published contract | Exports added |
| F5 | "Low tolerance (amplifies decay)" for Doers | `customer.py:31`, `equations.md:29` | `M` = 0.95 for **both** segments; no test varies it | Comment corrected; see below |

**F5 is the substantive one.** The decay equation divides by `M`:

```
T(n) = T(n-1) * exp(-alpha * S / M)
```

so a lower `M` should steepen the drop. The Doer constant is annotated
"Low tolerance (amplifies decay)" — but it is `0.95`, identical to the Gambler's,
and no test anywhere varies it. Under default calibration `M` is a shared
constant divisor: it rescales both segments equally and cancels out of every
comparison the repo actually makes. **The entire Doer/Gambler difference is
carried by `alpha`.** The `M` pathway is live code and correct arithmetic, but it
is inert — a second lever documented as load-bearing that currently bears nothing.

Fixed the comment, not the constant. Retuning `M` would change model behavior and
shift C4/C5/C7/C8, and there is no data justifying a particular value — that is a
calibration decision, and calibration is exactly what this repo cannot falsify
from the inside. Recorded as **U5** instead.

**Moved to legacy.** `architecture_mismatch.py` and `schema.py` — 1,113 lines,
zero inbound imports, zero tests. Unwired rather than superseded: never
falsified, never load-bearing. Reasoning and the contrast with
`support_cartography.py` (same provenance, opposite outcome) in
[`legacy/README.md`](../legacy/README.md).

**Pinned, so this class of drift fails loudly next time.** All five falsified
claims were prose that nothing executed — which is exactly why they rotted
unnoticed across four merges. Added `tests/test_repo_invariants.py` (11 tests):
the documented test count must match the suite, README and CLAUDE.md must name
every `src/` module, `__all__` must resolve and must carry the published contract
surface, nothing live may import from `legacy/`, legacy modules must stay
importable, and this document must keep its three required sections.

The guard proved itself on the first run: it failed immediately, reporting
`README claims 79 tests, suite has 90` — its own 11 tests were the drift.
Corrected to 90.

**Reran.** 90 passed, example output unchanged. Loop closed.

---

## Open unknowns

Things nothing in this repo currently measures. These are not bugs. They are the
edges of what the model is entitled to claim, and every one of them is a place
where a green test suite means less than it appears to.

| ID | Unknown | Why it matters | What would close it |
|----|---------|----------------|---------------------|
| **U1** | `alpha` = 2.0 / 0.3 is asserted, never fitted | Every downstream number — LTV loss, NEV, break-even — inherits this. The suite is self-consistent, not validated. | Observed trust/spend trajectories after a dated pricing violation, fitted per segment |
| **U2** | The real Doer fraction is unmeasured | C8 says dynamic pricing turns net-negative above 0.14% Doers. Whether that threshold is crossed is the entire practical question, and this repo cannot answer it. | Population survey or a churn cohort scored by the fingerprint |
| **U3** | The ZNP cutoff `F >= 0.60` is unvalidated | It sets who counts as ZNP at all. No test exercises its sensitivity; a shift to 0.55 or 0.65 has never been priced. | Labeled exits, false-positive/false-negative curve across cutoffs |
| **U4** | 12 of `support_cartography.py`'s 13 public names are unused | Only `Gate` is consumed, by `znp_gate_bridge.py`. `CollapseRateEstimator`, `ProjectionLossSimulator`, `SupportBoundaryMapper` and the rest are untested here — same "no evidence either way" position as `legacy/`, but on the live import path. | Either bridge and test them, or move the unused surface to `legacy/` |
| **U5** | Is `M` supposed to differ by segment? | Raised by F5. If yes, the current calibration is wrong and C4/C5/C7/C8 all move. If no, `M` is redundant with `alpha` and the two-lever design is misleading. | An intended Doer tolerance value with a rationale, or a decision to collapse `M` into `alpha` |
| **U6** | WOM constants (reach 5, conversion 0.08, decay 0.85, second-order 0.30/3/0.03) are all assumed | Drives the `$17.50` WOM cost and every CAC-impact number | Referral/defection tracing from a known exit cohort |

**U1 and U2 are the load-bearing ones.** Everything the README asserts about
dollars rests on them. The model's internal logic is pinned by 90 tests; its
contact with reality is pinned by nothing yet, and no amount of additional
testing inside this repo can change that. Saying so plainly is part of the method.

---

## Running the loop yourself

```bash
python -m pytest tests/ -v                    # run every pinned claim
python examples/dynamic_pricing_analysis.py   # run the end-to-end scenario
```

When a claim breaks:

1. Add a row to the falsification log — claim, what running it showed, what changed.
2. If a whole module is superseded, move it to `legacy/` and note which of the two
   retention reasons applies. Do not delete it.
3. Update the claim register.
4. Write down what the break exposed that nothing tests. Give it a `U` number.
5. Rerun.

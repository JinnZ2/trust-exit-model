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
| C9 | Low manipulation tolerance amplifies decay for Doers | Both segments carrying the same `M` | **FALSIFIED** — see F5, and structurally void per P1 |
| C10 | `alpha` and `M` are separate levers | Ratio-preserving pairs producing identical output | **FALSIFIED** — P1: they enter only as `alpha/M` |
| C11 | LTV responds continuously to trust level | LTV taking finitely many values across [0,1] | **FALSIFIED** — P2: exactly 5 values, one per phase |
| C12 | Break-even stays under 1% across plausible `alpha` | A sweep leaving that range | Holds (pinned, `test_instrument_explorer.py`) |

---

## Falsification log

Newest first. Each entry: what was claimed, what running it showed, what changed.

### 2026-08-15 — instrument search over the open unknowns

The previous entry closed with "no test inside this repo can close U1 or U2."
That is a statement about *measurement*, and it went unexamined. Built
[`tools/instrument_explorer.py`](../tools/instrument_explorer.py) to search the
instrument space instead of asserting it, and ran its three probes against the
live model.

Two of the six unknowns turned out not to need field data at all. One of them
was not a measurement question in the first place.

**P1 — `alpha` and `M` are structurally non-identifiable. U5 is resolved.**

In `T(n) = T(n-1) * exp(-alpha * S / M)` the two constants enter *only* through
the ratio `alpha/M`. Four (alpha, M) pairs sharing ratio 2.1053 — all with M
inside the documented (0,1] domain — produce bit-identical post-violation trust
(`0.3490180709`) and identical NEV:

| alpha | M | alpha/M | post-trust | NEV |
|------:|--:|--------:|-----------:|----:|
| 2.00 | 0.9500 | 2.1053 | 0.3490180709 | -$3,661.31 |
| 1.50 | 0.7125 | 2.1053 | 0.3490180709 | -$3,661.31 |
| 1.00 | 0.4750 | 2.1053 | 0.3490180709 | -$3,661.31 |
| 0.50 | 0.2375 | 2.1053 | 0.3490180709 | -$3,661.31 |

No observation of trust, spend, or exit can distinguish these. U5 asked "should
`M` differ by segment, and what is the right value?" — the question has no
empirical answer, because `M` is redundant with `alpha` by construction. This
is a proof, not a budget problem. Status changed from open-unknown to
**non-identifiable**, kept in the register with its result per the precedence
rule. The remaining decision is a design one: collapse `M` into `alpha`, or fix
`M` by convention and document that only the ratio is ever fitted.

**P2 — every dollar figure is quantized to five values. New unknown U7.**

Swept 1,001 trust levels across [0,1]. `compute_ltv` emits exactly **5 distinct
values**, jumping only at 0.05 / 0.25 / 0.50 / 0.80 — the phase boundaries:

| boundary | LTV below → above | step |
|---------:|------------------|-----:|
| 0.05 | $0.00 → $611.05 | $611.05 |
| 0.25 | $611.05 → $2,444.21 | $1,833.15 |
| 0.50 | $2,444.21 → $5,193.94 | **$2,749.73** |
| 0.80 | $5,193.94 → $6,110.51 | $916.58 |

`compute_ltv` multiplies by `PHASE_REVENUE_MULTIPLIER[phase]`, so the continuous
`trust_level` does nothing except select a bucket. All the continuous machinery
— exponential decay, `alpha`, `beta`, `M` — is a phase classifier wearing a
curve's clothes at the point where dollars are computed.

The consequence is uncomfortable. `CLAUDE.md` lists the phase boundaries and the
`mu` multipliers under *"Not in the contract (calibration knobs, may retune
without a version bump)"* — but moving the 0.50 boundary shifts a Doer's LTV by
$2,749.73 on the README's own inputs, with no version signal to any downstream
consumer. **The parameters declared freely retunable are the ones that actually
set every published number.** Logged as **U7**, weighted 0.95.

**P3 — the headline claim is robust to `alpha`. U1 downgraded.**

Swept Doer `alpha` from 0.5 to 8.0 — a 16× range spanning every plausible value.
Break-even Doer fraction stayed within **[0.082%, 0.546%]**, never approaching
1%. The qualitative claim ("a fraction of one percent of Doers makes dynamic
pricing net-negative") survives the entire range; what U1 threatens is the third
decimal place of C8, not the conclusion.

U1's load-bearing weight drops from 1.00 to 0.60, and **U2 moves to the top of
the queue**. The number that cannot be wrong is the population fraction, not the
decay rate. The previous entry's claim that "U1 and U2 are the load-bearing
ones" was half right, and the wrong half was the one it listed first.

**The blocked-instrument finding.** Ranking candidate instruments by leverage
surfaced something the prose in the unknowns table had glossed. U2's stated
route was "population survey or a churn cohort scored by the fingerprint" —
and both self-report instruments are structurally defeated:

- Exit interviews: `complaint_absence` and `exit_data_quality` are *scored ZNP
  signals* in `behavioral_fingerprint.py`. Non-completion of an exit survey is a
  positive ZNP indicator. Sizing the population from its completions inverts the
  sign of the evidence.
- Tolerance surveys: Doers under-respond by definition, so the instrument
  undercounts exactly the segment it exists to measure.

You cannot survey a population defined by non-response. The one unblocked route
found is **silent-churn cohort reconstruction** — read the absence from retained
logs without contacting anyone, which is precisely what `support_cartography`'s
RETENTION gate describes. The explorer flags it as the only viable path to U2,
and a test pins that finding so it fails loudly if a second route is added or
this one is removed.

The ranking also, on first run, recommended a randomized price-variation trial
as the #4 instrument while its own caveat said not to run it — measuring harm by
inflicting it on a randomly chosen arm. Added an explicit ethics gate that is
deliberately *excluded* from the leverage score: cost-effectiveness and
permission are separate axes, and collapsing them is how a tool launders its own
warning into a recommendation.

**Pinned.** `tests/test_instrument_explorer.py` (20 tests) fixes P1's exact
collapse, P2's five-value quantization and boundary locations, P3's sub-1%
range, and the catalog invariants — blocked and ethics-gated instruments must
never appear in the actionable queue, every instrument must state a falsifier,
and the register must not drift from this document.

**Reran.** 110 passed, example output unchanged. Loop closed.

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

Weights and statuses below are mirrored in `tools/instrument_explorer.py`, and a
test fails if the two drift apart. Run `python tools/instrument_explorer.py
--unknown U2` for the candidate instruments behind any row.

| ID | Unknown | Weight | Status | Route |
|----|---------|-------:|--------|-------|
| **U7** | Phase boundaries + `mu` multipliers dominate every dollar figure | 0.95 | identifiable | Discovered by P2. `CLAUDE.md` lists them as freely retunable knobs outside the contract; moving the 0.50 boundary shifts a Doer's LTV by $2,749.73. Needs either a boundary-fitting instrument (I1/I4) or promotion into the versioned contract. |
| **U2** | The real Doer fraction is unmeasured | 1.00 | **blocked** except one route | C8 says dynamic pricing turns net-negative above 0.14% Doers. Every self-report instrument is defeated by non-emission. Only I6 (silent-churn cohort reconstruction) is viable — read the absence from retained logs, contact nobody. |
| **U3** | The ZNP cutoff `F >= 0.60` is unvalidated | 0.70 | **blocked** upstream | Needs labeled exits, and labels come from people who answer — the complement of ZNP. Unblocks only once I6 or I1 supplies labels; then I7 draws the ROC. |
| **U1** | `alpha` = 2.0 / 0.3 asserted, never fitted | 0.60 | identifiable | Downgraded from 1.00 by P3: break-even holds in [0.082%, 0.546%] across a 16× sweep. Threatens C8's third decimal, not the conclusion. |
| **U6** | WOM constants (reach 5, conv 0.08, decay 0.85, second-order 0.30/3/0.03) assumed | 0.40 | identifiable | Drives the $17.50 WOM cost. I5 traces referral defection — behavioral, not self-report, so it is not blocked. Misses offline WOM, which the ZNP paper argues is the dominant channel. |
| **U5** | Should `M` differ by segment? | 0.30 | **non-identifiable** | **Resolved by P1.** `alpha` and `M` enter only as the ratio `alpha/M`; no dataset can separate them. Retained per the precedence rule. Remaining decision is design, not measurement. |
| **U4** | 12 of `support_cartography.py`'s 13 public names unused | 0.10 | internal | Closable by a decision, not data: bridge and test them, or retire the unused surface to `legacy/`. |

**U2 is the one that matters, and it is the hardest to reach.** P3 demoted U1;
P2 promoted U7 above it. Everything the README asserts about dollars now rests
on U2 and U7 — how many Doers there are, and where the phase boundaries sit.

The model's internal logic is pinned by 110 tests. Its contact with reality is
pinned by nothing yet, and no amount of additional testing inside this repo can
change that. Saying so plainly is part of the method.

What did change is the shape of the gap. Three of the six original unknowns
turned out not to require field data at all — one was a proof (U5), one was a
robustness result (U1), and one was a decision (U4). Searching the instrument
space before budgeting for it is cheaper than any of the instruments.

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

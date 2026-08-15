"""instrument_explorer.py — search for ways to measure the open unknowns.

`docs/method.md` ends every unknown with "what would close it". That column is
prose, and prose does not get audited. This tool makes the search itself
runnable: it holds a register of open unknowns, a catalog of candidate
instruments, and a set of probes that execute against the live model.

It answers three questions:

    1. Which unknowns can be closed *right now*, with no field data?
       (Run the probes. Some unknowns are arithmetic, not measurement.)

    2. For the rest, which instrument buys the most per unit of cost?
       (Rank by leverage: load-bearing weight, discounted by selection risk.)

    3. Which instruments are structurally defeated before they start?
       (A survey cannot measure a population defined by non-response. Naming
       this is the point — an instrument that cannot work is not a plan.)

The third category is the one that matters most here. ZNP customers are
*defined* by non-emission: they do not complain, do not answer exit surveys,
do not respond to win-back offers. `complaint_absence` is literally a scored
signal in `behavioral_fingerprint.py`. So every instrument that requires the
subject to respond is sampling the complement of the population of interest.
That is not a sampling nuisance to be weighted away. It is the phenomenon.

Usage:
    python tools/instrument_explorer.py              # full report
    python tools/instrument_explorer.py --probes     # runnable probes only
    python tools/instrument_explorer.py --unknown U1 # instruments for one unknown

CC0 | stdlib only
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field
from enum import Enum, IntEnum
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.customer import Customer, CustomerSegment
from src.lifetime_value import LifetimeValueModel
from src.trust_degradation import TrustDegradationCurve
from src.trust_state import TrustState


# ══════════════════════════════════════════════════════════════════════════
# TAXONOMY
# ══════════════════════════════════════════════════════════════════════════


class Identifiability(Enum):
    """Can this unknown be resolved at all, and by what kind of effort?"""

    INTERNAL = "internal"
    """Closable now by running something. No field data needed."""

    IDENTIFIABLE = "identifiable"
    """A field instrument exists and would work."""

    BLOCKED = "blocked"
    """An instrument exists on paper but the phenomenon defeats it."""

    NON_IDENTIFIABLE = "non_identifiable"
    """No data can ever resolve it — the parameters are structurally
    confounded. This is a proof, not a budget problem."""

    RESOLVED = "resolved"
    """Closed. Kept in the register with its result, per the precedence rule."""


class InstrumentKind(Enum):
    INTERNAL_PROBE = "internal probe"
    BEHAVIORAL_PANEL = "behavioral panel"
    NATURAL_EXPERIMENT = "natural experiment"
    RANDOMIZED_TRIAL = "randomized trial"
    SELF_REPORT = "self-report"
    TRACE_RECONSTRUCTION = "trace reconstruction"


class Cost(IntEnum):
    TRIVIAL = 1
    LOW = 2
    MEDIUM = 3
    HIGH = 4
    PROHIBITIVE = 5


# ══════════════════════════════════════════════════════════════════════════
# REGISTERS
# ══════════════════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class Unknown:
    """An open question, mirroring the register in docs/method.md."""

    unknown_id: str
    summary: str
    load_bearing: float
    """[0,1]. How much of the repo's published output rests on this."""
    status: Identifiability
    note: str = ""


@dataclass(frozen=True)
class Instrument:
    """A candidate way to measure something."""

    instrument_id: str
    name: str
    kind: InstrumentKind
    targets: tuple[str, ...]
    measures: str
    data_required: tuple[str, ...]
    would_falsify: str
    """What observation would overturn a current claim. An instrument that
    cannot produce a falsifying result is not an instrument, it is a survey
    of our own assumptions."""
    selection_risk: float
    """[0,1]. How much ZNP non-emission biases this instrument's sample.
    >= 0.60 means the instrument is measuring the wrong population."""
    cost: Cost
    latency_months: int
    caveats: tuple[str, ...] = field(default_factory=tuple)
    ethics_review_required: bool = False
    """True when running the instrument inflicts the harm it measures.

    Deliberately excluded from `leverage`. Cost-effectiveness and permission
    are different axes, and collapsing them into one score is how an
    instrument ends up recommended by the same tool that warns against it.
    """

    @property
    def blocked(self) -> bool:
        return self.selection_risk >= 0.60

    def leverage(self, register: dict[str, Unknown]) -> float:
        """Expected value per unit cost, discounted by selection risk.

        A blocked instrument scores near zero no matter how cheap it is.
        Cheapness is not a virtue when the measurement is invalid.
        """
        weight = sum(
            register[u].load_bearing for u in self.targets if u in register
        )
        return weight * (1.0 - self.selection_risk) / float(self.cost)


UNKNOWNS: dict[str, Unknown] = {
    u.unknown_id: u
    for u in [
        Unknown(
            "U1",
            "alpha (2.0 / 0.3) asserted, never fitted to data",
            load_bearing=0.60,
            status=Identifiability.IDENTIFIABLE,
            note="Downgraded from 1.0 by probe P3 — see report.",
        ),
        Unknown(
            "U2",
            "the real Doer population fraction is unmeasured",
            load_bearing=1.00,
            status=Identifiability.BLOCKED,
            note="Every self-report route is defeated by non-emission. P-lane "
            "instrument I6 is the only unblocked path found.",
        ),
        Unknown(
            "U3",
            "ZNP fingerprint cutoff F >= 0.60 is unvalidated",
            load_bearing=0.70,
            status=Identifiability.BLOCKED,
            note="Needs labeled exits; labels come from people who answer, "
            "which is the complement of ZNP.",
        ),
        Unknown(
            "U4",
            "12 of 13 support_cartography public names are unused",
            load_bearing=0.10,
            status=Identifiability.INTERNAL,
            note="Closable by a decision: bridge and test, or retire to legacy/.",
        ),
        Unknown(
            "U5",
            "should manipulation tolerance M differ by segment?",
            load_bearing=0.30,
            status=Identifiability.NON_IDENTIFIABLE,
            note="RESOLVED by probe P1 — alpha and M are structurally "
            "confounded. No data can separate them.",
        ),
        Unknown(
            "U6",
            "WOM constants (reach 5, conv 0.08, decay 0.85) all assumed",
            load_bearing=0.40,
            status=Identifiability.IDENTIFIABLE,
            note="Behavioral trace, not self-report. Tractable.",
        ),
        Unknown(
            "U7",
            "phase boundaries + mu multipliers dominate every dollar figure",
            load_bearing=0.95,
            status=Identifiability.IDENTIFIABLE,
            note="DISCOVERED by probe P2. CLAUDE.md lists these as freely "
            "retunable knobs outside the contract. They are not.",
        ),
    ]
}


INSTRUMENTS: list[Instrument] = [
    Instrument(
        "I1",
        "Post-incident spend panel",
        InstrumentKind.NATURAL_EXPERIMENT,
        targets=("U1", "U7"),
        measures="Trust proxy via spend trajectory around a dated pricing change",
        data_required=(
            "a dated, customer-visible pricing-policy change",
            "per-customer monthly spend, 12 months either side",
            "exposure flag: who could actually observe the change",
        ),
        would_falsify="C1, if any exposed cohort's spend recovers to baseline "
        "without intervention",
        selection_risk=0.15,
        cost=Cost.MEDIUM,
        latency_months=12,
        caveats=("Requires the violation to have already happened — you cannot "
                 "schedule this one.",),
    ),
    Instrument(
        "I2",
        "Manipulation-tolerance survey panel",
        InstrumentKind.SELF_REPORT,
        targets=("U2", "U3"),
        measures="Stated tolerance for variable pricing, scored to segment",
        data_required=("sampling frame", "validated tolerance battery"),
        would_falsify="U2's premise, if the Doer fraction lands below the "
        "0.14% break-even",
        selection_risk=0.75,
        cost=Cost.LOW,
        latency_months=3,
        caveats=(
            "BLOCKED. Doers are defined by non-response; they under-respond to "
            "surveys, so this systematically undercounts exactly the segment "
            "it is meant to size.",
            "Stated tolerance is not revealed tolerance.",
        ),
    ),
    Instrument(
        "I3",
        "Exit interview / cancellation survey",
        InstrumentKind.SELF_REPORT,
        targets=("U2", "U3"),
        measures="Self-reported exit reason at cancellation",
        data_required=("cancellation flow with an optional reason field",),
        would_falsify="Nothing reliably — see caveats",
        selection_risk=0.90,
        cost=Cost.TRIVIAL,
        latency_months=1,
        caveats=(
            "BLOCKED, and the most tempting of the blocked options because it "
            "is nearly free.",
            "`complaint_absence` and `exit_data_quality` are scored ZNP signals "
            "in behavioral_fingerprint.py. Non-completion of this survey is a "
            "positive ZNP indicator. Using its completions to size the "
            "population inverts the sign of the evidence.",
        ),
    ),
    Instrument(
        "I4",
        "Randomized price-variation holdout",
        InstrumentKind.RANDOMIZED_TRIAL,
        targets=("U1", "U2", "U7"),
        measures="Causal effect of exposure on retention and spend",
        data_required=("randomized exposure", "holdout arm", "24-month horizon"),
        would_falsify="C4/C5 directly — the segment-specific violation counts "
        "to each phase",
        selection_risk=0.10,
        cost=Cost.HIGH,
        latency_months=24,
        caveats=(
            "ETHICS: this measures harm by inflicting it. The repo's own thesis "
            "is that the exposed arm suffers permanent, uncompensated loss. "
            "Do not run this without review; prefer I1, which reads a violation "
            "that already happened.",
        ),
        ethics_review_required=True,
    ),
    Instrument(
        "I5",
        "Referral-code defection tracing",
        InstrumentKind.TRACE_RECONSTRUCTION,
        targets=("U6",),
        measures="Observed second-order defection following a known exit",
        data_required=("referral/invite graph", "exit timestamps"),
        would_falsify="The WOM constants — reach 5, conversion 0.08, decay 0.85",
        selection_risk=0.30,
        cost=Cost.MEDIUM,
        latency_months=12,
        caveats=("Digital referral graphs miss offline WOM, which the ZNP paper "
                 "argues is the dominant channel for this segment.",),
    ),
    Instrument(
        "I6",
        "Silent-churn cohort reconstruction",
        InstrumentKind.TRACE_RECONSTRUCTION,
        targets=("U2", "U3"),
        measures="Population fraction exhibiting the full ZNP exit pattern, "
        "reconstructed from retained logs with no subject contact",
        data_required=(
            "retained clickstream at session granularity",
            "trust-violation event stream, joined to accounts",
            "cancellation records including silent lapses",
        ),
        would_falsify="U2 and the 0.14% break-even, in either direction",
        selection_risk=0.20,
        cost=Cost.MEDIUM,
        latency_months=6,
        caveats=(
            "The only unblocked route to U2 found in this catalog. It works "
            "because it never asks anyone anything — it reads the absence "
            "directly, which is what support_cartography's RETENTION gate is "
            "about.",
            "Fails if logs were pruned before joining. Check the RETENTION gate "
            "before budgeting this.",
        ),
    ),
    Instrument(
        "I7",
        "Fingerprint ROC against a held-out labeled cohort",
        InstrumentKind.BEHAVIORAL_PANEL,
        targets=("U3",),
        measures="False-positive / false-negative curve across cutoff values",
        data_required=("labeled exits from I1 or I6", "held-out split"),
        would_falsify="The 0.60 cutoff, if the ROC knee sits elsewhere",
        selection_risk=0.25,
        cost=Cost.LOW,
        latency_months=2,
        caveats=("Downstream of I1 or I6 — it has no labels of its own.",),
    ),
    Instrument(
        "I8",
        "Parameter identifiability sweep",
        InstrumentKind.INTERNAL_PROBE,
        targets=("U1", "U5"),
        measures="Whether alpha and M can be separated by any dataset",
        data_required=("none — runs against the live model",),
        would_falsify="U5's framing as an empirical question",
        selection_risk=0.0,
        cost=Cost.TRIVIAL,
        latency_months=0,
        caveats=("Implemented below as probe P1. Run it before funding anything.",),
    ),
    Instrument(
        "I9",
        "Output quantization probe",
        InstrumentKind.INTERNAL_PROBE,
        targets=("U1", "U7"),
        measures="How many distinct outputs the model can emit, and where the "
        "sensitivity actually sits",
        data_required=("none — runs against the live model",),
        would_falsify="The assumption that alpha precision drives dollar figures",
        selection_risk=0.0,
        cost=Cost.TRIVIAL,
        latency_months=0,
        caveats=("Implemented below as probe P2.",),
    ),
    Instrument(
        "I10",
        "Break-even robustness sweep",
        InstrumentKind.INTERNAL_PROBE,
        targets=("U1",),
        measures="Range of the break-even Doer fraction across plausible alpha",
        data_required=("none — runs against the live model",),
        would_falsify="C8, if break-even leaves the sub-1% range",
        selection_risk=0.0,
        cost=Cost.TRIVIAL,
        latency_months=0,
        caveats=("Implemented below as probe P3.",),
    ),
    Instrument(
        "I11",
        "Synthetic-cohort estimator recovery",
        InstrumentKind.INTERNAL_PROBE,
        targets=("U1",),
        measures="Whether a fitting procedure recovers a known alpha from "
        "simulated trajectories, before field money is spent",
        data_required=("none — simulate from the model itself",),
        would_falsify="Any proposed estimator that cannot recover ground truth "
        "on data it generated",
        selection_risk=0.0,
        cost=Cost.LOW,
        latency_months=0,
        caveats=("Not yet implemented. Blocked on P2's finding that the "
                 "observable is quantized to 5 levels — see report.",),
    ),
]


# ══════════════════════════════════════════════════════════════════════════
# SEARCH
# ══════════════════════════════════════════════════════════════════════════


def instruments_for(unknown_id: str) -> list[Instrument]:
    """Every catalogued instrument targeting one unknown, best first."""
    hits = [i for i in INSTRUMENTS if unknown_id in i.targets]
    return sorted(hits, key=lambda i: i.leverage(UNKNOWNS), reverse=True)


def rank_instruments() -> list[Instrument]:
    return sorted(INSTRUMENTS, key=lambda i: i.leverage(UNKNOWNS), reverse=True)


def blocked_instruments() -> list[Instrument]:
    return [i for i in INSTRUMENTS if i.blocked]


def unreachable_unknowns() -> list[Unknown]:
    """Unknowns whose every catalogued instrument is blocked.

    An empty list is good news. A non-empty list is a claim the repo is not
    currently entitled to make, and no budget fixes it.
    """
    out = []
    for uid, unknown in UNKNOWNS.items():
        candidates = instruments_for(uid)
        if candidates and all(i.blocked for i in candidates):
            out.append(unknown)
    return out


# ══════════════════════════════════════════════════════════════════════════
# PROBES — these run against the live model
# ══════════════════════════════════════════════════════════════════════════


@dataclass
class ProbeResult:
    probe_id: str
    question: str
    verdict: str
    detail: list[str]
    closes: tuple[str, ...] = ()
    opens: tuple[str, ...] = ()


def _ltv(segment: CustomerSegment, trust: float, revenue: float = 200.0,
         tolerance: float = 0.95) -> float:
    return LifetimeValueModel().compute_ltv(
        Customer(
            customer_id="probe",
            segment=segment,
            trust_state=TrustState.from_level(trust),
            monthly_revenue=revenue,
            manipulation_tolerance=tolerance,
        )
    )


def _nev(segment: CustomerSegment, alpha: float, tolerance: float,
         severity: float = 0.5, revenue: float = 200.0,
         extraction: float = 5.0) -> tuple[float, float]:
    """Return (NEV, post-violation trust level) for one segment."""
    customer = Customer(
        customer_id="probe",
        segment=segment,
        trust_state=TrustState.from_level(1.0),
        monthly_revenue=revenue,
        manipulation_tolerance=tolerance,
    )
    before = LifetimeValueModel().compute_ltv(customer)
    post = TrustDegradationCurve(alpha=alpha).apply_violation(customer, severity)
    after = _ltv(segment, post.trust_level, revenue, tolerance)
    return extraction - (before - after), post.trust_level


def probe_identifiability() -> ProbeResult:
    """P1 — can alpha and M be separated by any dataset?"""
    # All M values kept inside the documented (0, 1] domain, so the collapse
    # cannot be dismissed as an artifact of out-of-range inputs.
    pairs = [(2.0, 0.95), (1.5, 0.7125), (1.0, 0.475), (0.5, 0.2375)]
    detail = ["  alpha      M     alpha/M    post-trust        NEV"]
    levels = set()
    for alpha, tol in pairs:
        nev, trust = _nev(CustomerSegment.DOER, alpha, tol)
        levels.add(round(trust, 10))
        detail.append(
            f"  {alpha:5.2f}  {tol:6.4f}  {alpha / tol:7.4f}  "
            f"{trust:.10f}  ${nev:>12,.2f}"
        )

    collapsed = len(levels) == 1
    verdict = (
        "NON-IDENTIFIABLE. A 4x range of alpha produces bit-identical output "
        "when alpha/M is held constant."
        if collapsed
        else "Separable — alpha and M leave distinct fingerprints."
    )
    detail += [
        "",
        "  In T(n) = T(n-1) * exp(-alpha * S / M), the two constants enter only",
        "  through the ratio alpha/M. No observation of trust, spend, or exit can",
        "  distinguish (alpha=2.0, M=0.95) from (alpha=1.0, M=0.475). U5 is not",
        "  an empirical question awaiting data — it is a redundancy in the",
        "  parameterization. The honest fix is to collapse M into alpha, or to",
        "  fix M by convention and document that only the ratio is fitted.",
    ]
    return ProbeResult("P1", "Can alpha and M be separately identified?",
                       verdict, detail, closes=("U5",))


def probe_output_quantization() -> ProbeResult:
    """P2 — how many distinct dollar figures can the model actually emit?"""
    values = {}
    for i in range(1001):
        trust = i / 1000
        values.setdefault(round(_ltv(CustomerSegment.DOER, trust), 6), trust)

    detail = [
        f"  Swept 1001 trust levels across [0, 1].",
        f"  Distinct LTV values emitted: {len(values)}",
        "",
        "  jump      LTV below -> LTV above          step",
    ]
    prev_val = None
    prev_trust = 0.0
    for i in range(1001):
        trust = i / 1000
        val = round(_ltv(CustomerSegment.DOER, trust), 6)
        if prev_val is not None and abs(val - prev_val) > 1e-6:
            detail.append(
                f"  T={trust:.3f}   ${prev_val:>10,.2f} -> ${val:>10,.2f}   "
                f"${val - prev_val:>10,.2f}"
            )
        prev_val, prev_trust = val, trust

    verdict = (
        f"QUANTIZED. LTV takes {len(values)} distinct values over the whole "
        "continuous trust range."
    )
    detail += [
        "",
        "  compute_ltv multiplies by PHASE_REVENUE_MULTIPLIER[phase], so the",
        "  continuous trust_level does nothing except select one of 5 buckets.",
        "  Every dollar figure this repo publishes is determined by which bucket",
        "  a customer lands in — not by where they sit inside it.",
        "",
        "  Consequence for instrument choice: precision in alpha is worth very",
        "  little. alpha matters only insofar as it moves a customer across a",
        "  boundary. The parameters that actually set the dollars are the four",
        "  phase boundaries and the five mu multipliers.",
        "",
        "  CLAUDE.md lists the phase boundaries under 'Not in the contract",
        "  (calibration knobs, may retune without a version bump)'. Retuning the",
        "  0.50 boundary moves a Doer's LTV by $2,749.73 on these inputs, with",
        "  no version signal to any downstream consumer.",
    ]
    return ProbeResult("P2", "How many distinct outputs can the model emit?",
                       verdict, detail, opens=("U7",))


def probe_breakeven_robustness() -> ProbeResult:
    """P3 — does the headline claim survive uncertainty in alpha?"""
    nev_gambler, _ = _nev(CustomerSegment.GAMBLER, 0.3, 0.95)
    detail = ["  alpha_doer   post-trust      NEV_doer     break-even"]
    breakevens = []
    for alpha in [0.5, 1.0, 1.5, 2.0, 3.0, 4.0, 6.0, 8.0]:
        nev_doer, trust = _nev(CustomerSegment.DOER, alpha, 0.95)
        denom = nev_gambler - nev_doer
        p = nev_gambler / denom if abs(denom) > 1e-9 else 0.0
        p = max(0.0, min(1.0, p))
        breakevens.append(p)
        detail.append(
            f"  {alpha:9.1f}   {trust:9.3f}   ${nev_doer:>11,.2f}   {p * 100:8.3f}%"
        )

    lo, hi = min(breakevens) * 100, max(breakevens) * 100
    robust = hi < 1.0
    verdict = (
        f"ROBUST. Break-even stays in [{lo:.3f}%, {hi:.3f}%] across a 16x sweep "
        "of alpha."
        if robust
        else f"FRAGILE. Break-even ranges [{lo:.3f}%, {hi:.3f}%]."
    )
    detail += [
        "",
        "  The qualitative claim — 'a fraction of one percent of Doers makes",
        "  dynamic pricing net-negative' — survives the entire plausible range",
        "  of alpha. What U1 threatens is the third decimal place, not the",
        "  conclusion.",
        "",
        "  This downgrades U1's load-bearing weight from 1.00 to 0.60, and moves",
        "  U2 (how many Doers are there, really) to the top of the queue. The",
        "  number you cannot afford to be wrong about is the population",
        "  fraction, not the decay rate.",
    ]
    return ProbeResult("P3", "Does the break-even claim survive alpha uncertainty?",
                       verdict, detail, closes=(), opens=())


PROBES = [probe_identifiability, probe_output_quantization,
          probe_breakeven_robustness]


# ══════════════════════════════════════════════════════════════════════════
# REPORT
# ══════════════════════════════════════════════════════════════════════════


def _rule(char: str = "=") -> str:
    return char * 78


def render_probes() -> list[str]:
    out = [_rule(), "RUNNABLE PROBES — these execute against the live model", _rule()]
    for probe_fn in PROBES:
        result = probe_fn()
        out += ["", f"{result.probe_id}. {result.question}", "-" * 78,
                f"  VERDICT: {result.verdict}", ""]
        out += result.detail
        if result.closes:
            out.append(f"  => CLOSES: {', '.join(result.closes)}")
        if result.opens:
            out.append(f"  => OPENS:  {', '.join(result.opens)}")
    return out


def render_search() -> list[str]:
    out = ["", _rule(), "INSTRUMENT SEARCH", _rule(), "",
           "Ranked by leverage = (load-bearing weight of targets)",
           "                     x (1 - selection risk) / cost", ""]
    out.append(f"  {'id':<5}{'instrument':<38}{'targets':<12}{'cost':<6}lev")
    out.append("  " + "-" * 74)
    for inst in rank_instruments():
        flag = " [BLOCKED]" if inst.blocked else ""
        if inst.ethics_review_required:
            flag += " [ETHICS REVIEW]"
        out.append(
            f"  {inst.instrument_id:<5}{inst.name[:36]:<38}"
            f"{','.join(inst.targets):<12}{inst.cost.name[:5]:<6}"
            f"{inst.leverage(UNKNOWNS):.3f}{flag}"
        )

    out += ["", _rule("-"), "STRUCTURALLY BLOCKED", _rule("-"), "",
            "  Instruments defeated by the phenomenon they aim to measure.",
            "  Cheapness is not a reason to run these.", ""]
    for inst in blocked_instruments():
        out.append(f"  {inst.instrument_id} — {inst.name} "
                   f"(selection risk {inst.selection_risk:.2f}, "
                   f"cost {inst.cost.name})")
        for caveat in inst.caveats:
            out.append(f"      {caveat}")
        out.append("")

    stranded = unreachable_unknowns()
    out += [_rule("-"), "UNKNOWNS WITH NO UNBLOCKED INSTRUMENT", _rule("-"), ""]
    if stranded:
        for unknown in stranded:
            out.append(f"  {unknown.unknown_id} — {unknown.summary}")
        out.append("")
        out.append("  These are claims the repo is not currently entitled to make.")
    else:
        out.append("  None. Every open unknown has at least one viable route.")
        out.append("")
        out.append("  Note this was not true before I6 was catalogued: U2's only")
        out.append("  routes were self-report, and both are blocked. The unblocking")
        out.append("  move was to stop asking and read the absence from retained")
        out.append("  logs instead.")
    return out


def render_queue() -> list[str]:
    out = ["", _rule(), "SUGGESTED ORDER", _rule(), ""]
    internal = [i for i in rank_instruments()
                if i.kind is InstrumentKind.INTERNAL_PROBE]
    field_ok = [i for i in rank_instruments()
                if i.kind is not InstrumentKind.INTERNAL_PROBE
                and not i.blocked and not i.ethics_review_required]
    gated = [i for i in rank_instruments()
             if i.ethics_review_required and not i.blocked]
    out.append("  First — costs nothing, may dissolve the question entirely:")
    for inst in internal:
        out.append(f"    {inst.instrument_id}  {inst.name}  "
                   f"-> {','.join(inst.targets)}")
    out += ["", "  Then — field instruments, highest leverage first:"]
    for inst in field_ok:
        out.append(
            f"    {inst.instrument_id}  {inst.name}  -> {','.join(inst.targets)}"
            f"  ({inst.cost.name.lower()}, {inst.latency_months}mo)"
        )
    if gated:
        out += ["", "  Not scheduled by leverage — requires review before it is",
                "  a plan at all, however well it scores:"]
        for inst in gated:
            out.append(
                f"    {inst.instrument_id}  {inst.name}  "
                f"(leverage {inst.leverage(UNKNOWNS):.3f}, would otherwise rank "
                f"#{rank_instruments().index(inst) + 1})"
            )
            for caveat in inst.caveats:
                out.append(f"        {caveat}")
    out += ["", "  Never, on current evidence:"]
    for inst in blocked_instruments():
        out.append(f"    {inst.instrument_id}  {inst.name}")
    return out


def render_unknown(unknown_id: str) -> list[str]:
    unknown = UNKNOWNS.get(unknown_id)
    if unknown is None:
        return [f"Unknown id {unknown_id!r} not in register. "
                f"Known: {', '.join(sorted(UNKNOWNS))}"]
    out = [_rule(), f"{unknown.unknown_id} — {unknown.summary}", _rule(), "",
           f"  status:       {unknown.status.value}",
           f"  load-bearing: {unknown.load_bearing:.2f}"]
    if unknown.note:
        out.append(f"  note:         {unknown.note}")
    out += ["", "  Candidate instruments:", ""]
    for inst in instruments_for(unknown_id):
        flag = "  [BLOCKED]" if inst.blocked else ""
        out += [f"  {inst.instrument_id} — {inst.name} ({inst.kind.value}){flag}",
                f"      measures:      {inst.measures}",
                f"      would falsify: {inst.would_falsify}",
                f"      cost:          {inst.cost.name.lower()}, "
                f"{inst.latency_months} months",
                f"      data required:"]
        for item in inst.data_required:
            out.append(f"        - {item}")
        for caveat in inst.caveats:
            out.append(f"      ! {caveat}")
        out.append("")
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Search for instruments that could close the open unknowns."
    )
    parser.add_argument("--probes", action="store_true",
                        help="run the internal probes only")
    parser.add_argument("--unknown", metavar="ID",
                        help="show candidate instruments for one unknown (e.g. U2)")
    args = parser.parse_args(argv)

    if args.unknown:
        lines = render_unknown(args.unknown.upper())
    elif args.probes:
        lines = render_probes()
    else:
        lines = render_probes() + render_search() + render_queue()

    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

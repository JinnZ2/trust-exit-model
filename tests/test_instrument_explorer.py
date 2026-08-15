"""Pins the instrument explorer's findings and its self-consistency.

Two kinds of claim here.

The probe results (P1-P3) are *structural* facts about the model, not
calibration guesses — they follow from the shape of the equations, so they are
legitimately testable from inside the repo. If one of these fails, the model's
parameterization changed and docs/method.md needs a new log entry.

The catalog invariants guard against the explorer contradicting itself: a tool
that ranks an instrument first while warning against it in the same output is
worse than no tool, because it launders the warning into a recommendation.
"""

from __future__ import annotations

import re
from pathlib import Path

from src.customer import CustomerSegment
from tools.instrument_explorer import (
    INSTRUMENTS,
    UNKNOWNS,
    Identifiability,
    InstrumentKind,
    _ltv,
    _nev,
    blocked_instruments,
    instruments_for,
    probe_breakeven_robustness,
    probe_identifiability,
    probe_output_quantization,
    rank_instruments,
    render_queue,
    unreachable_unknowns,
)

METHOD_DOC = Path(__file__).resolve().parent.parent / "docs" / "method.md"


class TestP1Identifiability:
    """alpha and M enter only as the ratio alpha/M."""

    def test_ratio_preserving_pairs_are_indistinguishable(self) -> None:
        baseline, _ = _nev(CustomerSegment.DOER, alpha=2.0, tolerance=0.95)
        for alpha, tolerance in [(1.5, 0.7125), (1.0, 0.475), (0.5, 0.2375)]:
            nev, _ = _nev(CustomerSegment.DOER, alpha, tolerance)
            assert nev == baseline, (
                f"(alpha={alpha}, M={tolerance}) has the same alpha/M ratio as "
                f"(2.0, 0.95) but produced a different NEV — the equation no "
                f"longer collapses to the ratio"
            )

    def test_trust_levels_are_bit_identical(self) -> None:
        levels = {
            _nev(CustomerSegment.DOER, a, m)[1]
            for a, m in [(2.0, 0.95), (1.5, 0.7125), (1.0, 0.475), (0.5, 0.2375)]
        }
        assert len(levels) == 1, f"expected exact collapse, got {levels}"

    def test_differing_ratio_does_separate(self) -> None:
        # Guards the converse: the collapse is specific to the ratio, not a
        # sign that the model ignores its parameters entirely.
        a, _ = _nev(CustomerSegment.DOER, alpha=2.0, tolerance=0.95)
        b, _ = _nev(CustomerSegment.DOER, alpha=0.5, tolerance=0.95)
        assert a != b

    def test_probe_reports_non_identifiable(self) -> None:
        assert "NON-IDENTIFIABLE" in probe_identifiability().verdict
        assert "U5" in probe_identifiability().closes


class TestP2OutputQuantization:
    """LTV is a step function of phase, not a function of trust level."""

    def test_ltv_emits_exactly_five_values(self) -> None:
        values = {
            round(_ltv(CustomerSegment.DOER, i / 1000), 6) for i in range(1001)
        }
        assert len(values) == 5, (
            f"expected one LTV per trust phase, got {len(values)} distinct values"
        )

    def test_jumps_land_on_the_documented_phase_boundaries(self) -> None:
        jumps = []
        prev = None
        for i in range(1001):
            trust = i / 1000
            val = round(_ltv(CustomerSegment.DOER, trust), 6)
            if prev is not None and abs(val - prev) > 1e-6:
                jumps.append(round(trust, 3))
            prev = val
        assert jumps == [0.05, 0.25, 0.50, 0.80], (
            f"LTV discontinuities at {jumps}, expected the phase boundaries"
        )

    def test_within_phase_variation_is_zero(self) -> None:
        # Anywhere strictly inside CRITICAL_THRESHOLD [0.25, 0.50) must be flat.
        inside = {round(_ltv(CustomerSegment.DOER, t), 6)
                  for t in (0.26, 0.30, 0.40, 0.49)}
        assert len(inside) == 1, (
            "trust level moved LTV without crossing a phase boundary"
        )

    def test_probe_flags_the_new_unknown(self) -> None:
        assert "U7" in probe_output_quantization().opens


class TestP3BreakevenRobustness:
    """The headline claim survives a wide sweep of alpha."""

    def test_breakeven_stays_sub_one_percent(self) -> None:
        result = probe_breakeven_robustness()
        assert "ROBUST" in result.verdict
        percentages = [float(m) for m in re.findall(r"(\d+\.\d+)%", "\n".join(result.detail))]
        assert percentages, "probe emitted no break-even values"
        assert max(percentages) < 1.0, (
            f"break-even exceeded 1% somewhere in the sweep: max {max(percentages)}%"
        )

    def test_u1_weight_was_downgraded(self) -> None:
        # P3 is the reason U1 is no longer weighted 1.00. If someone restores
        # the old weight without new evidence, this fails.
        assert UNKNOWNS["U1"].load_bearing < UNKNOWNS["U2"].load_bearing, (
            "U2 (population fraction) must outrank U1 (decay rate) — P3 showed "
            "alpha only moves the third decimal place"
        )


class TestCatalogConsistency:
    """The explorer must not contradict itself."""

    def test_every_instrument_targets_a_known_unknown(self) -> None:
        for inst in INSTRUMENTS:
            unknown_targets = [t for t in inst.targets if t not in UNKNOWNS]
            assert not unknown_targets, (
                f"{inst.instrument_id} targets unregistered {unknown_targets}"
            )

    def test_every_instrument_states_a_falsifier(self) -> None:
        for inst in INSTRUMENTS:
            assert inst.would_falsify.strip(), (
                f"{inst.instrument_id} has no falsifier — that makes it a survey "
                f"of our own assumptions, not an instrument"
            )

    def test_blocked_instruments_never_reach_the_run_queue(self) -> None:
        queue = "\n".join(render_queue())
        run_section = queue.split("Never, on current evidence")[0]
        for inst in blocked_instruments():
            assert inst.instrument_id not in run_section, (
                f"{inst.instrument_id} is structurally blocked but appears in "
                f"the actionable part of the queue"
            )

    def test_ethics_gated_instruments_are_not_scheduled_by_score(self) -> None:
        gated = [i for i in INSTRUMENTS if i.ethics_review_required]
        assert gated, "expected at least one ethics-gated instrument in the catalog"
        queue = "\n".join(render_queue())
        field_section = queue.split("Not scheduled by leverage")[0]
        for inst in gated:
            assert inst.instrument_id not in field_section, (
                f"{inst.instrument_id} requires review but was listed in the "
                f"ordinary run-this-next section"
            )

    def test_ethics_flag_does_not_alter_leverage(self) -> None:
        # Permission and cost-effectiveness are separate axes on purpose.
        inst = next(i for i in INSTRUMENTS if i.ethics_review_required)
        assert inst.leverage(UNKNOWNS) > 0, (
            "ethics gating must not be implemented by silently zeroing the score"
        )

    def test_load_bearing_unknowns_have_an_unblocked_route(self) -> None:
        stranded = [u.unknown_id for u in unreachable_unknowns()]
        assert not stranded, (
            f"no viable instrument for {stranded} — these are claims the repo "
            f"is not entitled to make"
        )

    def test_internal_probes_rank_above_field_work(self) -> None:
        ranked = rank_instruments()
        top = ranked[0]
        assert top.kind is InstrumentKind.INTERNAL_PROBE, (
            "a free probe that might dissolve the question should outrank paid "
            "field work"
        )

    def test_u2_has_exactly_one_unblocked_route(self) -> None:
        # The substantive finding: every self-report route to U2 is defeated by
        # non-emission. If a second unblocked route appears, good — update the
        # explorer's note. If this one disappears, U2 becomes unmeasurable.
        viable = [i for i in instruments_for("U2")
                  if not i.blocked and not i.ethics_review_required]
        assert [i.instrument_id for i in viable] == ["I6"]


class TestRegisterMatchesMethodDoc:
    """The explorer's register and docs/method.md must not drift apart."""

    def test_all_method_doc_unknowns_are_registered(self) -> None:
        text = METHOD_DOC.read_text(encoding="utf-8")
        documented = set(re.findall(r"\*\*(U\d+)\*\*", text))
        missing = sorted(documented - set(UNKNOWNS))
        assert not missing, (
            f"docs/method.md documents {missing} but the explorer register does not"
        )

    def test_resolved_unknowns_keep_their_entry(self) -> None:
        # Precedence rule: resolving an unknown does not delete it.
        assert "U5" in UNKNOWNS
        assert UNKNOWNS["U5"].status is Identifiability.NON_IDENTIFIABLE

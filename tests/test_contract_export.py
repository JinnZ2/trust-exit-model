"""Tests for contract-export helpers.

Primary goal: pin the name-string serialization of TrustPhase so the
mirror-vs-upstream int-value discrepancy can never silently recur.
"""

import json

import pytest

from src.behavioral_fingerprint import SignalVector
from src.customer import Customer, CustomerSegment
from src.support_cartography import Gate
from src.trust_state import TrustPhase, TrustState
from src.znp_gate_bridge import GateFailureProfile, classify_gate_failures
from src.contract_export import (
    CONTRACT_VERSION,
    export_customer,
    export_derived,
    export_gate_failure,
    export_payload,
    export_trust_state,
)


class TestContractVersion:
    def test_matches_taf_mirror(self):
        assert CONTRACT_VERSION == "1.0.0"


class TestPhaseSerialization:
    """Regression guard for the int-vs-name-string discrepancy."""

    def test_phase_emitted_as_name_string(self):
        d = export_trust_state(TrustState.from_level(0.55))
        assert d["phase"] == "EARLY_EROSION"
        assert isinstance(d["phase"], str)

    def test_phase_never_emitted_as_int(self):
        for level in [0.9, 0.6, 0.3, 0.1, 0.0]:
            d = export_trust_state(TrustState.from_level(level))
            assert not isinstance(d["phase"], int)
            assert not isinstance(d["phase"], bool)

    def test_every_phase_name_round_trips(self):
        for phase in TrustPhase:
            ts = TrustState(trust_level=0.5, phase=phase)
            d = export_trust_state(ts)
            assert d["phase"] == phase.name

    def test_exported_dict_is_json_native(self):
        ts = TrustState.from_level(0.55, violations_count=1)
        reloaded = json.loads(json.dumps(export_trust_state(ts)))
        assert reloaded["phase"] == "EARLY_EROSION"
        assert reloaded["trust_level"] == pytest.approx(0.55)

    def test_recovery_potential_carried_through(self):
        ts = TrustState.from_level(0.6)  # EARLY_EROSION
        d = export_trust_state(ts)
        assert d["recovery_potential"] == pytest.approx(0.70)


class TestCustomerSerialization:
    def _customer(self, segment=CustomerSegment.DOER) -> Customer:
        return Customer(
            customer_id="c-0001",
            segment=segment,
            trust_state=TrustState.from_level(0.55, violations_count=1),
            monthly_revenue=120.0,
            tenure_months=18,
            social_reach=250,
        )

    def test_segment_emitted_as_value_string(self):
        d = export_customer(self._customer(CustomerSegment.DOER))
        assert d["segment"] == "doer"
        d = export_customer(self._customer(CustomerSegment.GAMBLER))
        assert d["segment"] == "gambler"

    def test_all_public_fields_present(self):
        d = export_customer(self._customer())
        expected = {
            "customer_id", "segment", "trust_state", "monthly_revenue",
            "tenure_months", "social_reach", "manipulation_tolerance",
            "violation_history",
        }
        assert expected <= set(d.keys())

    def test_nested_trust_state_uses_name_string(self):
        d = export_customer(self._customer())
        assert d["trust_state"]["phase"] == "EARLY_EROSION"


class TestGateFailureSerialization:
    def test_dominant_gate_emitted_as_value_string(self):
        signals = SignalVector(complaint_absence=1.0)
        d = export_gate_failure(classify_gate_failures(signals))
        assert d["dominant_gate"] == "emission"

    def test_intervention_hint_not_in_contract_shape(self):
        """The advisory hint field is not part of contract v1.0.0."""
        signals = SignalVector(complaint_absence=1.0)
        d = export_gate_failure(classify_gate_failures(signals))
        assert "intervention_hint" not in d

    def test_gate_enum_values_match_contract(self):
        """Sanity check: our Gate enum values are the strings the contract expects."""
        assert Gate.EMISSION.value == "emission"
        assert Gate.CAPTURE.value == "capture"
        assert Gate.RETENTION.value == "retention"


class TestPayloadEnvelope:
    def test_envelope_carries_contract_version(self):
        customer = Customer(
            customer_id="c-0001",
            segment=CustomerSegment.GAMBLER,
            trust_state=TrustState.from_level(0.6),
            monthly_revenue=120.0,
        )
        signals = SignalVector(complaint_absence=1.0, communication_response=1.0)
        derived = export_derived(
            nev=100.0, ltv=1000.0,
            fingerprint_score=0.7, is_znp=True,
            gate_failure=classify_gate_failures(signals),
        )
        payload = export_payload(customer=customer, derived=derived)
        assert payload["contract_version"] == "1.0.0"
        assert payload["customer"]["customer_id"] == "c-0001"
        assert payload["derived"]["is_znp"] is True

    def test_payload_survives_json_round_trip(self):
        customer = Customer(
            customer_id="c-0001",
            segment=CustomerSegment.DOER,
            trust_state=TrustState.from_level(0.1),  # TERMINAL
            monthly_revenue=120.0,
        )
        signals = SignalVector(
            complaint_absence=1.0,
            communication_response=1.0,
            abrupt_cancellation=1.0,
        )
        derived = export_derived(
            nev=-500.0, ltv=800.0,
            fingerprint_score=0.9, is_znp=True,
            gate_failure=classify_gate_failures(signals),
        )
        payload = export_payload(customer=customer, derived=derived)
        reloaded = json.loads(json.dumps(payload))
        assert reloaded["customer"]["trust_state"]["phase"] == "TERMINAL"
        assert reloaded["derived"]["gate_failure"]["dominant_gate"] in {
            "emission", "capture", "retention",
        }

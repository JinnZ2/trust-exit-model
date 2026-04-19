"""Contract export helpers for external consumers.

Emits the stable surface of trust-exit-model in the shape matching
schemas/trust_exit_contract.py on the Thermodynamic Accountability
Framework side (CONTRACT_VERSION 1.0.0).

Key stability commitment: `TrustPhase` is serialized as its *name*
string (e.g. "FULL_TRUST"), never as its `IntEnum` integer value.
This prevents silent misdecoding if either side's int numbering
drifts. Tests pin this behavior.

These helpers produce plain-dict / JSON-native output only. Consumers
should import the contract mirror (TAF repo) to decode; this package
stays stdlib + pytest only and does not depend on TAF.
"""

from __future__ import annotations

from src.customer import Customer
from src.trust_state import TrustState
from src.znp_gate_bridge import GateFailureProfile


CONTRACT_VERSION = "1.0.0"


def export_trust_state(state: TrustState) -> dict:
    """Emit a TrustState in contract-shape.

    Phase is emitted as its name-string, not its IntEnum integer.
    """
    return {
        "trust_level": state.trust_level,
        "phase": state.phase.name,
        "violations_count": state.violations_count,
        "recovery_potential": state.recovery_potential,
    }


def export_customer(customer: Customer) -> dict:
    """Emit a Customer in contract-shape with nested TrustState."""
    return {
        "customer_id": customer.customer_id,
        "segment": customer.segment.value,
        "trust_state": export_trust_state(customer.trust_state),
        "monthly_revenue": customer.monthly_revenue,
        "tenure_months": customer.tenure_months,
        "social_reach": customer.social_reach,
        "manipulation_tolerance": customer.manipulation_tolerance,
        "violation_history": list(customer.violation_history),
    }


def export_gate_failure(profile: GateFailureProfile) -> dict:
    """Emit a GateFailureProfile in contract-shape.

    Drops the intervention_hint from the payload since that field is
    advisory output, not part of the 1.0.0 contract.
    """
    return {
        "emission_score": profile.emission_score,
        "capture_score": profile.capture_score,
        "retention_score": profile.retention_score,
        "dominant_gate": profile.dominant_gate.value,
    }


def export_derived(
    *,
    nev: float,
    ltv: float,
    fingerprint_score: float,
    is_znp: bool,
    gate_failure: GateFailureProfile,
) -> dict:
    """Emit the derived-scalars block in contract-shape."""
    return {
        "nev": float(nev),
        "ltv": float(ltv),
        "fingerprint_score": float(fingerprint_score),
        "is_znp": bool(is_znp),
        "gate_failure": export_gate_failure(gate_failure),
    }


def export_payload(*, customer: Customer, derived: dict) -> dict:
    """Emit the top-level envelope with contract_version stamp."""
    return {
        "contract_version": CONTRACT_VERSION,
        "customer": export_customer(customer),
        "derived": derived,
    }

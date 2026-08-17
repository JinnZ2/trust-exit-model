"""trust-exit-model: Behavioral segmentation framework for trust-violation churn modeling."""

from src.trust_state import TrustState, TrustPhase
from src.customer import Customer, CustomerSegment
from src.trust_degradation import TrustDegradationCurve
from src.lifetime_value import LifetimeValueModel
from src.behavioral_fingerprint import BehavioralFingerprint
from src.community_amplification import CommunityAmplificationModel
from src.dynamic_pricing_risk import DynamicPricingRiskModel
from src.recovery_window import RecoveryWindowModel
from src.support_cartography import Gate
from src.znp_gate_bridge import GateFailureProfile, classify_gate_failures
from src.contract_export import (
    CONTRACT_VERSION,
    export_customer,
    export_derived,
    export_gate_failure,
    export_payload,
    export_trust_state,
)

__all__ = [
    # Core model
    "TrustState",
    "TrustPhase",
    "Customer",
    "CustomerSegment",
    "TrustDegradationCurve",
    "LifetimeValueModel",
    "BehavioralFingerprint",
    "CommunityAmplificationModel",
    "DynamicPricingRiskModel",
    "RecoveryWindowModel",
    # Gate bridge (three-gate framework from support_cartography)
    "Gate",
    "GateFailureProfile",
    "classify_gate_failures",
    # Contract export (see CLAUDE.md "Published Contract")
    "CONTRACT_VERSION",
    "export_customer",
    "export_derived",
    "export_gate_failure",
    "export_payload",
    "export_trust_state",
]

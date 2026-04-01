"""trust-exit-model: Behavioral segmentation framework for trust-violation churn modeling."""

from src.trust_state import TrustState, TrustPhase
from src.customer import Customer, CustomerSegment
from src.trust_degradation import TrustDegradationCurve
from src.lifetime_value import LifetimeValueModel
from src.behavioral_fingerprint import BehavioralFingerprint
from src.community_amplification import CommunityAmplificationModel
from src.dynamic_pricing_risk import DynamicPricingRiskModel
from src.recovery_window import RecoveryWindowModel

__all__ = [
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
]

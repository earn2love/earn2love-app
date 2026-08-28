"""Earn2Love V10 reliability and escalation intelligence.

Pure deterministic reliability policy.

This module decides whether an output can be accepted, regenerated, or
escalated. It does not call providers itself and does not claim that any
external action succeeded.
"""

from dataclasses import dataclass
from typing import Any, Iterable


RELIABILITY_VERSION = 10

ACCEPT = "ACCEPT"
REPAIR = "REPAIR"
ESCALATE = "ESCALATE"
FAIL_SAFE = "FAIL_SAFE"

ACTIONS = (
    ACCEPT,
    REPAIR,
    ESCALATE,
    FAIL_SAFE,
)


@dataclass(frozen=True)
class ReliabilityDecision:
    action: str
    confidence: float
    reasons: tuple[str, ...]
    require_verification: bool
    can_claim_success: bool

    def to_dict(self):
        return {
            "action": self.action,
            "confidence": self.confidence,
            "reasons": list(
                self.reasons
            ),
            "requireVerification": self.require_verification,
            "canClaimSuccess": self.can_claim_success,
            "reliabilityVersion": RELIABILITY_VERSION,
        }


def _bool(value: Any, default=True):
    if value is None:
        return default
    return bool(
        value
    )


def _quality_value(
    quality,
    key,
    default=True,
):
    if quality is None:
        return default

    if isinstance(
        quality,
        dict,
    ):
        return _bool(
            quality.get(
                key,
                default,
            ),
            default,
        )

    return _bool(
        getattr(
            quality,
            key,
            default,
        ),
        default,
    )


def _failed_quality_checks(
    quality,
):
    checks = (
        "consistencyPassed",
        "repetitionPassed",
        "safetyPassed",
        "lengthOk",
        "conversationQualityPassed",
        "relationshipSafetyPassed",
        "personalityConsistencyPassed",
    )

    return tuple(
        key
        for key in checks
        if not _quality_value(
            quality,
            key,
            True,
        )
    )


def decide_reliability(
    *,
    provider_ok=True,
    provider_error=None,
    quality=None,
    attempt=1,
    verification_required=False,
    external_success_claim=False,
    verified_external_success=False,
):
    reasons = []

    attempt = max(
        1,
        int(
            attempt or 1
        ),
    )

    if external_success_claim and not verified_external_success:
        reasons.append(
            "unverified_external_success_claim"
        )

        return ReliabilityDecision(
            action=FAIL_SAFE,
            confidence=0.99,
            reasons=tuple(
                reasons
            ),
            require_verification=True,
            can_claim_success=False,
        )

    if not provider_ok:
        error = str(
            provider_error or
            "provider_error"
        )

        reasons.append(
            error
        )

        if attempt <= 1:
            return ReliabilityDecision(
                action=ESCALATE,
                confidence=0.96,
                reasons=tuple(
                    reasons
                ),
                require_verification=bool(
                    verification_required
                ),
                can_claim_success=False,
            )

        return ReliabilityDecision(
            action=FAIL_SAFE,
            confidence=0.98,
            reasons=tuple(
                reasons
            ),
            require_verification=bool(
                verification_required
            ),
            can_claim_success=False,
        )

    failed = _failed_quality_checks(
        quality
    )

    if failed:
        reasons.extend(
            failed
        )

        if attempt <= 1:
            return ReliabilityDecision(
                action=REPAIR,
                confidence=0.94,
                reasons=tuple(
                    reasons
                ),
                require_verification=bool(
                    verification_required
                ),
                can_claim_success=False,
            )

        return ReliabilityDecision(
            action=FAIL_SAFE,
            confidence=0.96,
            reasons=tuple(
                reasons
            ),
            require_verification=bool(
                verification_required
            ),
            can_claim_success=False,
        )

    if verification_required:
        reasons.append(
            "verification_required"
        )

        return ReliabilityDecision(
            action=ACCEPT,
            confidence=0.91,
            reasons=tuple(
                reasons
            ),
            require_verification=True,
            can_claim_success=bool(
                verified_external_success
            ),
        )

    reasons.append(
        "quality_passed"
    )

    return ReliabilityDecision(
        action=ACCEPT,
        confidence=0.95,
        reasons=tuple(
            reasons
        ),
        require_verification=False,
        can_claim_success=(
            not external_success_claim
            or verified_external_success
        ),
    )


def should_escalate(
    decision: ReliabilityDecision,
):
    return decision.action in (
        REPAIR,
        ESCALATE,
    )


def build_reliability_guidance(
    decision: ReliabilityDecision,
):
    if decision.action == ACCEPT:
        return (
            "V10 reliability: output may be accepted subject to any "
            "required verification. Never convert uncertainty into certainty."
        )

    if decision.action == REPAIR:
        return (
            "V10 reliability: regenerate once with targeted correction, "
            "preserving valid prior context and personality."
        )

    if decision.action == ESCALATE:
        return (
            "V10 reliability: escalate to the existing stronger-model repair "
            "route. Do not fabricate a response if the provider failed."
        )

    return (
        "V10 reliability: fail safely. Do not claim successful execution, "
        "payment, deployment, database write, tool call, or external action "
        "without verified evidence."
    )

"""
Earn2Love AI Engine V9.4
Verification & Self-Correction Intelligence.

Pure orchestration layer that cooperates with:
- V3 belief revision
- V4 conversation correction handling
- V9 structured reasoning
- V9 plan state

It does not replace belief revision and performs no persistence.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import re
from typing import Any

from ai_engine import belief_revision as BR
from ai_engine import reasoning_intelligence as RI
from ai_engine import plan_intelligence as PI


VERIFICATION_VERSION = 9

VERIFICATION_LEVELS = (
    "none",
    "light",
    "required",
)

_NEGATION = (
    "wrong",
    "incorrect",
    "not true",
    "that's not",
    "that is not",
    "you misunderstood",
    "no i meant",
    "no, i meant",
)

_VERIFY = (
    "verify",
    "check",
    "confirm",
    "validate",
    "make sure",
    "audit",
)

_UNCERTAINTY = (
    "not sure",
    "uncertain",
    "maybe",
    "probably",
    "i think",
    "might",
    "could be",
)

_HIGH_IMPACT = (
    "production",
    "payment",
    "billing",
    "money",
    "firestore",
    "database",
    "deploy",
    "deployment",
    "security",
    "auth",
    "authentication",
    "legal",
    "delete",
    "remove data",
)


@dataclass(frozen=True)
class VerificationAnalysis:
    level: str
    user_is_correcting: bool
    explicit_verification_request: bool
    material_uncertainty: bool
    high_impact_context: bool
    reasoning_contradiction: bool
    active_plan: bool
    should_revise_interpretation: bool
    should_verify_before_claiming_success: bool
    confidence: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class VerificationGuidance:
    analysis: VerificationAnalysis
    directive: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "analysis": self.analysis.to_dict(),
            "directive": self.directive,
        }


def _norm(value: Any) -> str:
    return re.sub(
        r"\s+",
        " ",
        str(value or "").strip().lower(),
    )


def _contains_any(
    text: str,
    values: tuple[str, ...],
) -> bool:
    return any(
        value in text
        for value in values
    )


def analyze_verification(
    user_text: str,
    plan_state: dict[str, Any] | None = None,
    character_id: str = "",
    user_id: str = "",
) -> VerificationAnalysis:

    text = _norm(
        user_text
    )

    correction = BR.detect_correction_intent(
        user_text
    )

    user_is_correcting = bool(
        correction.get(
            "isCorrection"
        )
        or _contains_any(
            text,
            _NEGATION,
        )
    )

    explicit_verification_request = _contains_any(
        text,
        _VERIFY,
    )

    material_uncertainty = _contains_any(
        text,
        _UNCERTAINTY,
    )

    high_impact_context = _contains_any(
        text,
        _HIGH_IMPACT,
    )

    reasoning = RI.analyze_reasoning(
        user_text
    )

    reasoning_contradiction = bool(
        reasoning.contradictions
    )

    normalized_plan = PI.normalize_plan_state(
        plan_state,
        character_id,
        user_id,
    )

    active_plan = PI.has_active_plan(
        normalized_plan
    )

    should_revise_interpretation = bool(
        user_is_correcting
        or reasoning_contradiction
    )

    should_verify_before_claiming_success = bool(
        explicit_verification_request
        or (
            high_impact_context
            and (
                material_uncertainty
                or reasoning.should_verify
            )
        )
        or (
            active_plan
            and high_impact_context
            and (
                "worked" in text
                or "done" in text
                or "complete" in text
                or "completed" in text
            )
        )
    )

    if (
        should_verify_before_claiming_success
        or user_is_correcting
    ):
        level = "required"

    elif (
        material_uncertainty
        or reasoning_contradiction
    ):
        level = "light"

    else:
        level = "none"

    signal_count = sum(
        (
            user_is_correcting,
            explicit_verification_request,
            material_uncertainty,
            high_impact_context,
            reasoning_contradiction,
            active_plan,
        )
    )

    confidence = min(
        0.99,
        0.6
        + (
            signal_count
            * 0.05
        ),
    )

    return VerificationAnalysis(
        level=level,
        user_is_correcting=user_is_correcting,
        explicit_verification_request=explicit_verification_request,
        material_uncertainty=material_uncertainty,
        high_impact_context=high_impact_context,
        reasoning_contradiction=reasoning_contradiction,
        active_plan=active_plan,
        should_revise_interpretation=should_revise_interpretation,
        should_verify_before_claiming_success=should_verify_before_claiming_success,
        confidence=round(
            confidence,
            3,
        ),
    )


def build_verification_guidance(
    user_text: str,
    plan_state: dict[str, Any] | None = None,
    character_id: str = "",
    user_id: str = "",
) -> VerificationGuidance:

    analysis = analyze_verification(
        user_text,
        plan_state,
        character_id,
        user_id,
    )

    parts = [
        "V9 verification and self-correction guidance."
    ]

    if analysis.user_is_correcting:
        parts.append(
            "Treat the user's correction as authoritative for interpreting what they meant. Do not defend the earlier misunderstanding."
        )

    if analysis.reasoning_contradiction:
        parts.append(
            "A material contradiction may exist. Resolve or explicitly acknowledge it before relying on the conflicting conclusion."
        )

    if analysis.material_uncertainty:
        parts.append(
            "Separate uncertainty from established facts and avoid presenting assumptions as confirmed."
        )

    if analysis.should_verify_before_claiming_success:
        parts.append(
            "Verification is required before claiming success, correctness, completion or production readiness when verification is available."
        )

    if analysis.high_impact_context:
        parts.append(
            "Use a higher verification standard because this involves a material production, financial, security, database, deployment or legal context."
        )

    if analysis.level == "none":
        parts.append(
            "No special verification step is currently required; answer directly without inventing uncertainty."
        )

    parts.extend(
        [
            "Cooperate with existing V3 belief revision rather than replacing it.",
            "Never silently overwrite user memory from this pure layer.",
            "Never fabricate successful deployment, payment, authentication, database or external-system results.",
            "Never expose or persist private chain-of-thought.",
            "Do not mutate V6 personality, V7 adaptation, V8 goals or V9 plan state.",
        ]
    )

    return VerificationGuidance(
        analysis=analysis,
        directive=" ".join(parts),
    )

from copy import deepcopy

from ai_engine import plan_intelligence as PI
from ai_engine import verification_intelligence as VI


CID = "aisha"
UID = "user-1"


def make_plan():
    return PI.evolve_plan_state(
        None,
        CID,
        UID,
        "First verify Firestore, then deploy.",
        {
            "characterId": CID,
            "userId": UID,
            "activeGoal": "Deploy safely",
            "activeGoalStatus": "active",
            "goalHistory": [],
            "goalTurnCount": 0,
            "goalEvents": 0,
            "lastIntent": "planning",
            "goalVersion": 8,
        },
    )


def test_no_special_verification():
    result = VI.analyze_verification(
        "Tell me a joke"
    )

    assert result.level == "none"


def test_explicit_verify():
    result = VI.analyze_verification(
        "Verify this configuration before deployment"
    )

    assert result.explicit_verification_request is True
    assert result.level == "required"


def test_user_correction_detected():
    result = VI.analyze_verification(
        "No, I meant Firebase Auth, not Firestore"
    )

    assert result.user_is_correcting is True
    assert result.should_revise_interpretation is True


def test_uncertainty_detected():
    result = VI.analyze_verification(
        "I think this might be the production key"
    )

    assert result.material_uncertainty is True


def test_high_impact_payment_context():
    result = VI.analyze_verification(
        "I'm not sure whether the payment succeeded"
    )

    assert result.high_impact_context is True
    assert result.should_verify_before_claiming_success is True


def test_high_impact_database_context():
    result = VI.analyze_verification(
        "Verify whether Firestore is configured correctly"
    )

    assert result.high_impact_context is True


def test_active_plan_success_needs_verification_in_production():
    state = make_plan()

    result = VI.analyze_verification(
        "Production deployment is done",
        state,
        CID,
        UID,
    )

    assert result.active_plan is True
    assert result.should_verify_before_claiming_success is True


def test_contradiction_detected():
    result = VI.analyze_verification(
        "We must deploy now, but we must not deploy until testing is complete."
    )

    assert result.reasoning_contradiction is True


def test_guidance_accepts_user_correction():
    directive = VI.build_verification_guidance(
        "No, I meant the backend"
    ).directive.lower()

    assert "user's correction as authoritative" in directive


def test_guidance_does_not_replace_belief_revision():
    directive = VI.build_verification_guidance(
        "Actually my name is Ram"
    ).directive

    assert "V3 belief revision" in directive


def test_guidance_blocks_fake_external_success():
    directive = VI.build_verification_guidance(
        "Payment completed"
    ).directive.lower()

    assert "never fabricate" in directive


def test_guidance_chain_of_thought_protection():
    directive = VI.build_verification_guidance(
        "Check this"
    ).directive.lower()

    assert "chain-of-thought" in directive


def test_plan_state_not_mutated():
    state = make_plan()

    before = deepcopy(
        state
    )

    VI.analyze_verification(
        "Verify this deployment",
        state,
        CID,
        UID,
    )

    assert state == before


def test_version():
    assert VI.VERIFICATION_VERSION == 9

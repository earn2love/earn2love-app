from dataclasses import FrozenInstanceError

import pytest

from ai_engine import emotional_intelligence as EI
from ai_engine import relationship_emotional_intelligence as RE15
from ai_engine import relationship_intelligence as RI


CHAR = "char-v15"
USER = "user-v15"


def relationship_state(
    *,
    stage="new",
):
    state = RI.default_state(
        CHAR,
        USER,
    )

    if stage == "familiar":
        state.update({
            "turnCount": 10,
            "familiarity": 0.25,
        })

    elif stage == "comfortable":
        state.update({
            "turnCount": 40,
            "trust": 0.55,
            "familiarity": 0.60,
            "warmth": 0.60,
            "depth": 0.45,
        })

    elif stage == "established":
        state.update({
            "turnCount": 100,
            "trust": 0.80,
            "familiarity": 0.85,
            "warmth": 0.80,
            "depth": 0.75,
        })

    state["state"] = RI.stage_for(
        state
    )

    return state


def guidance(
    text,
    *,
    stage="new",
    previous_text=None,
):
    emotional = EI.analyze_emotional_state_v15(
        text,
        previous_text=previous_text,
    )

    return RE15.build_relationship_emotional_guidance(
        text,
        emotional,
        relationship_state(
            stage=stage,
        ),
    )


def test_v15_2_marker():
    assert (
        RE15.V15_2_RELATIONSHIP_EMOTIONAL_INTELLIGENCE
        is True
    )


def test_normal_message_needs_no_repair():
    result = guidance(
        "How was your day?"
    )

    assert result.conflict_detected is False
    assert result.correction_detected is False
    assert result.repair_needed is False
    assert result.repair_mode == "none"


def test_correction_requests_repair():
    result = guidance(
        "No, I mean tomorrow."
    )

    assert result.correction_detected is True
    assert result.repair_needed is True
    assert result.repair_mode == "accept_correction"
    assert result.acknowledge_misunderstanding is True
    assert result.reduce_defensiveness is True


def test_conflict_requests_deescalation():
    result = guidance(
        "You misunderstood me. Stop saying that."
    )

    assert result.conflict_detected is True
    assert result.repair_needed is True
    assert result.repair_mode in {
        "deescalate_and_clarify",
        "acknowledge_and_repair",
    }

    assert result.reduce_defensiveness is True
    assert result.reduce_teasing is True
    assert result.reduce_challenge is True


def test_conflict_does_not_use_closeness_as_leverage():
    result = guidance(
        "You misunderstood me. Stop saying that.",
        stage="established",
    )

    assert (
        result.familiarity_mode
        == "do_not_leverage_closeness"
    )

    directive = result.directive.casefold()

    assert "prior closeness" in directive
    assert "leverage" in directive


def test_sad_user_gets_gentle_warmth():
    result = guidance(
        "I'm really sad and hurt today.",
        stage="comfortable",
    )

    assert result.warmth_mode == "gentle"
    assert result.reduce_teasing is True
    assert result.reduce_challenge is True


def test_anxious_user_reduces_challenge():
    result = guidance(
        "I'm extremely anxious and worried.",
        stage="comfortable",
    )

    assert result.reduce_challenge is True
    assert result.warmth_mode == "gentle"


def test_affection_new_relationship_stays_bounded():
    result = guidance(
        "I love talking to you ??",
        stage="new",
    )

    assert result.warmth_mode == "warm_but_bounded"
    assert result.avoid_overfamiliarity is True


def test_affection_established_relationship_can_be_warmer():
    result = guidance(
        "I love talking to you ??",
        stage="established",
    )

    assert result.warmth_mode == "warm_familiar"
    assert result.avoid_overfamiliarity is False


def test_vulnerability_is_relationship_relevant():
    result = guidance(
        "I feel lonely.",
        stage="familiar",
    )

    assert result.vulnerability_detected is True
    assert result.relationship_relevant is True


def test_positive_event_is_relationship_relevant():
    result = guidance(
        "Great news, I got promoted!"
    )

    assert result.positive_event_detected is True
    assert result.relationship_relevant is True


def test_no_persistent_mutation_authority():
    result = guidance(
        "I'm really happy."
    )

    assert (
        result.persistent_mutation_allowed
        is False
    )

    assert result.preserve_personality is True


def test_guidance_blocks_dependency():
    result = guidance(
        "I feel lonely.",
        stage="established",
    )

    directive = result.directive.casefold()

    assert "dependency" in directive
    assert "exclusivity" in directive
    assert "possessiveness" in directive


def test_relationship_input_not_mutated():
    state = relationship_state(
        stage="comfortable"
    )

    original = dict(state)

    emotional = EI.analyze_emotional_state_v15(
        "I'm sad."
    )

    RE15.build_relationship_emotional_guidance(
        "I'm sad.",
        emotional,
        state,
    )

    assert state == original


def test_guidance_is_immutable():
    result = guidance(
        "I'm happy."
    )

    with pytest.raises(
        FrozenInstanceError
    ):
        result.repair_needed = True


def test_policy_has_no_persistence():
    policy = (
        RE15.relationship_emotional_policy_v15()
    )

    assert policy["providerCalls"] is False
    assert policy["firestoreWrites"] is False
    assert policy["relationshipMutation"] is False
    assert policy["personalityMutation"] is False
    assert policy["responseGuidanceOnly"] is True


def test_existing_v5_evolution_remains_separate():
    state = relationship_state()

    emotional = EI.analyze_emotional_state_v15(
        "I'm happy."
    )

    result = RE15.build_relationship_emotional_guidance(
        "I'm happy.",
        emotional,
        state,
    )

    assert result.persistent_mutation_allowed is False

    assert state["turnCount"] == 0
    assert state["trust"] == 0.05
    assert state["familiarity"] == 0.05


def test_deterministic():
    a = guidance(
        "You misunderstood me.",
        stage="comfortable",
    )

    b = guidance(
        "You misunderstood me.",
        stage="comfortable",
    )

    assert a == b

from dataclasses import FrozenInstanceError

import pytest

from ai_engine import emotional_intelligence as EI


def test_v15_marker():
    assert (
        EI.V15_1_EMOTIONAL_STATE_INTELLIGENCE
        is True
    )


def test_neutral_message_remains_neutral():
    state = EI.analyze_emotional_state_v15(
        "Okay, sounds good."
    )

    assert state.primary_emotion == "neutral"
    assert state.response_mode == "natural"
    assert state.response_temperature == "balanced"
    assert state.acknowledgement_level == "none"
    assert state.valence == 0.0
    assert state.relationship_relevant is False
    assert state.transient_only is True


def test_joy_has_positive_valence():
    state = EI.analyze_emotional_state_v15(
        "I'm really happy! I got the job!"
    )

    assert state.primary_emotion == "joy"
    assert state.valence > 0
    assert state.arousal > 0
    assert state.response_mode == "share_positive_energy"
    assert state.response_temperature == "bright"


def test_sadness_uses_gentle_delivery():
    state = EI.analyze_emotional_state_v15(
        "I'm really sad and hurt today."
    )

    assert state.primary_emotion == "sadness"
    assert state.valence < 0
    assert state.response_temperature == "gentle"
    assert state.question_pressure == "low"
    assert state.advice_pressure == "low"


def test_anxiety_uses_calm_delivery():
    state = EI.analyze_emotional_state_v15(
        "I'm extremely anxious and worried!"
    )

    assert state.primary_emotion == "anxiety"
    assert state.valence < 0
    assert state.response_temperature == "calm"
    assert state.response_mode in {
        "calm_reassurance",
        "steady_acknowledgement",
    }


def test_affection_is_relationship_relevant_when_strong():
    state = EI.analyze_emotional_state_v15(
        "I really love talking to you ??"
    )

    assert state.primary_emotion == "affection"
    assert state.valence > 0
    assert state.response_temperature == "warm"
    assert state.relationship_relevant is True


def test_ordinary_emotion_is_not_persisted_by_v15():
    state = EI.analyze_emotional_state_v15(
        "I'm a bit annoyed."
    )

    assert state.transient_only is True
    assert state.meaningful_event is False


def test_meaningful_event_is_identified():
    state = EI.analyze_emotional_state_v15(
        "I'm so happy, I got the job!"
    )

    assert state.meaningful_event is True
    assert state.relationship_relevant is True
    assert state.transient_only is False


def test_emotional_load_is_bounded():
    state = EI.analyze_emotional_state_v15(
        "I'm extremely stressed and overwhelmed!!!"
    )

    assert 0.0 <= state.emotional_load <= 1.0
    assert 0.0 <= state.arousal <= 1.0
    assert -1.0 <= state.valence <= 1.0


def test_previous_turn_trajectory_is_preserved():
    state = EI.analyze_emotional_state_v15(
        "I'm really really sad!!!",
        previous_text="I'm a bit sad.",
    )

    assert state.trajectory in {
        "intensifying",
        "stable",
    }


def test_shifted_emotional_trajectory():
    state = EI.analyze_emotional_state_v15(
        "I'm so happy!",
        previous_text="I'm really sad.",
    )

    assert state.trajectory == "shifted"


def test_settling_trajectory():
    state = EI.analyze_emotional_state_v15(
        "Okay.",
        previous_text="I'm really angry!",
    )

    assert state.trajectory == "settling"


def test_does_not_manufacture_emotion():
    state = EI.analyze_emotional_state_v15(
        "What time is the meeting?"
    )

    assert (
        "do not manufacture emotion"
        in state.directive.casefold()
    )


def test_directive_preserves_personality():
    state = EI.analyze_emotional_state_v15(
        "I'm really stressed."
    )

    assert state.preserve_personality is True

    assert (
        "global character personality"
        in state.directive.casefold()
    )


def test_directive_blocks_dependency_behavior():
    state = EI.analyze_emotional_state_v15(
        "I feel lonely."
    )

    directive = state.directive.casefold()

    assert "dependency" in directive
    assert "possessive" in directive
    assert "exclusive" in directive
    assert "guilt" in directive


def test_state_is_immutable():
    state = EI.analyze_emotional_state_v15(
        "I'm happy."
    )

    with pytest.raises(
        FrozenInstanceError
    ):
        state.primary_emotion = "anger"


def test_to_dict_returns_safe_structured_copy():
    state = EI.analyze_emotional_state_v15(
        "I'm happy."
    )

    data = state.to_dict()

    assert data[
        "primary_emotion"
    ] == "joy"

    data[
        "primary_emotion"
    ] = "tampered"

    assert (
        state.primary_emotion
        == "joy"
    )


def test_existing_v35_analyze_emotion_contract_preserved():
    result = EI.analyze_emotion(
        "I'm really happy!"
    )

    assert set(
        result.keys()
    ) == {
        "primaryEmotion",
        "confidence",
        "scores",
        "intensity",
        "meaningfulEvent",
        "strategy",
    }


def test_existing_v35_neutral_contract_preserved():
    result = EI.analyze_emotion(
        "Okay."
    )

    assert result[
        "primaryEmotion"
    ] == "neutral"

    assert result[
        "intensity"
    ] == 0.0


def test_policy_is_pure_and_non_persistent():
    policy = EI.emotional_state_policy_v15()

    assert policy[
        "persistentMoodState"
    ] is False

    assert policy[
        "relationshipMutation"
    ] is False

    assert policy[
        "personalityMutation"
    ] is False

    assert policy[
        "providerCalls"
    ] is False

    assert policy[
        "firestoreWrites"
    ] is False

    assert policy[
        "clinicalDiagnosis"
    ] is False


def test_v15_does_not_create_relationship_stage():
    state = EI.analyze_emotional_state_v15(
        "I love talking to you ??"
    )

    data = state.to_dict()

    assert "relationship_stage" not in data
    assert "relationshipStage" not in data
    assert "trust" not in data
    assert "familiarity" not in data


def test_v15_does_not_claim_user_needs_support():
    state = EI.analyze_emotional_state_v15(
        "I'm sad."
    )

    assert state.social_orientation in {
        "support_seeking_possible",
        "neutral",
    }

    assert (
        "needs therapy"
        not in state.directive.casefold()
    )


def test_dimensions_are_deterministic():
    a = EI.analyze_emotional_state_v15(
        "I'm extremely happy!"
    )

    b = EI.analyze_emotional_state_v15(
        "I'm extremely happy!"
    )

    assert a == b

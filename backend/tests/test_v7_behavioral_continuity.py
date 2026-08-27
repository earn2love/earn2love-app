from copy import deepcopy

from ai_engine import adaptive_intelligence as AI
from ai_engine import personality_engine as PE


CHAR = "global-aisha"


def aisha():
    return {
        "characterId": "global-aisha",
        "personalityTraits": [
            "warm",
            "playful",
            "curious",
            "witty",
        ],
        "personality": {
            "warmth": 0.88,
            "playfulness": 0.82,
            "curiosity": 0.85,
            "humor": 0.72,
            "verbosity": 0.50,
        },
    }


def meera():
    return {
        "characterId": "global-meera",
        "personalityTraits": [
            "calm",
            "reserved",
            "direct",
        ],
        "personality": {
            "warmth": 0.45,
            "playfulness": 0.15,
            "curiosity": 0.45,
            "directness": 0.84,
            "energy": 0.28,
            "verbosity": 0.25,
        },
    }


def test_preference_confidence_starts_zero():
    state = AI.default_user_adaptation(
        CHAR,
        "user-a",
    )

    assert (
        AI.preference_confidence(
            state
        )
        ==
        0.0
    )


def test_preference_confidence_grows():
    state = AI.default_user_adaptation(
        CHAR,
        "user-a",
    )

    for _ in range(6):
        state = AI.evolve_user_adaptation(
            state,
            CHAR,
            "user-a",
            "Keep it short",
        )

    confidence = AI.preference_confidence(
        state
    )

    assert confidence == 0.5


def test_preference_confidence_saturates():
    state = AI.default_user_adaptation(
        CHAR,
        "user-a",
    )

    for _ in range(100):
        state = AI.evolve_user_adaptation(
            state,
            CHAR,
            "user-a",
            "Keep it short",
        )

    assert (
        AI.preference_confidence(
            state
        )
        ==
        1.0
    )


def test_dominant_preferences_detect_short_style():
    state = AI.default_user_adaptation(
        CHAR,
        "user-a",
    )

    for _ in range(5):
        state = AI.evolve_user_adaptation(
            state,
            CHAR,
            "user-a",
            "Keep it short",
        )

    result = AI.dominant_preferences(
        state
    )

    assert (
        result["detailPreference"]
        ==
        "low"
    )


def test_continuity_signature_same_state_same_result():
    state = AI.default_user_adaptation(
        CHAR,
        "user-a",
    )

    first = AI.continuity_signature(
        state
    )

    second = AI.continuity_signature(
        deepcopy(state)
    )

    assert first == second


def test_continuity_signature_is_user_specific():
    a = AI.default_user_adaptation(
        CHAR,
        "user-a",
    )

    b = AI.default_user_adaptation(
        CHAR,
        "user-b",
    )

    assert (
        AI.continuity_signature(a)
        !=
        AI.continuity_signature(b)
    )


def test_preference_distance_to_self_zero():
    state = AI.default_user_adaptation(
        CHAR,
        "user-a",
    )

    assert (
        AI.preference_distance(
            state,
            state,
        )
        ==
        0.0
    )


def test_different_users_can_have_large_preference_distance():
    a = AI.default_user_adaptation(
        CHAR,
        "user-a",
    )

    b = AI.default_user_adaptation(
        CHAR,
        "user-b",
    )

    for _ in range(10):
        a = AI.evolve_user_adaptation(
            a,
            CHAR,
            "user-a",
            "Keep it short, don't ask questions, no jokes",
        )

        b = AI.evolve_user_adaptation(
            b,
            CHAR,
            "user-b",
            "Explain everything in detail, use bullet points and be funny",
        )

    assert (
        AI.preference_distance(
            a,
            b,
        )
        >
        0.30
    )


def test_single_preference_event_remains_gradual():
    state = AI.default_user_adaptation(
        CHAR,
        "user-a",
    )

    after = AI.evolve_user_adaptation(
        state,
        CHAR,
        "user-a",
        "Keep it short",
    )

    assert AI.adaptation_is_stable(
        state,
        after,
        tolerance=0.10,
    )


def test_context_only_message_does_not_rewrite_preference():
    state = AI.default_user_adaptation(
        CHAR,
        "user-a",
    )

    for _ in range(8):
        state = AI.evolve_user_adaptation(
            state,
            CHAR,
            "user-a",
            "Keep it short",
        )

    before = deepcopy(
        state
    )

    # Context analysis is separate from stored preference evolution.
    guidance = AI.combined_adaptation_guidance(
        "I feel really worried about tomorrow",
        state,
    )

    assert state == before

    assert (
        guidance.context.context_type
        ==
        "emotional"
    )


def test_explicit_preference_can_reverse_gradually():
    state = AI.default_user_adaptation(
        CHAR,
        "user-a",
    )

    for _ in range(8):
        state = AI.evolve_user_adaptation(
            state,
            CHAR,
            "user-a",
            "Keep it short",
        )

    low_value = state[
        "detailPreference"
    ]

    for _ in range(8):
        state = AI.reverse_preference(
            state,
            CHAR,
            "user-a",
            "Explain everything in detail",
        )

    assert (
        state["detailPreference"]
        >
        low_value
    )


def test_preference_reversal_does_not_change_user_identity():
    state = AI.default_user_adaptation(
        CHAR,
        "user-a",
    )

    state = AI.reverse_preference(
        state,
        CHAR,
        "user-a",
        "Explain in detail",
    )

    assert state["userId"] == "user-a"
    assert state["characterId"] == CHAR


def test_combined_guidance_contains_continuity_rule():
    state = AI.default_user_adaptation(
        CHAR,
        "user-a",
    )

    guidance = AI.combined_adaptation_guidance(
        "hello",
        state,
    )

    assert (
        "Preserve established communication preferences"
        in guidance.directive
    )

    assert (
        "must not permanently rewrite stored communication preferences"
        in guidance.directive
    )


def test_combined_guidance_contains_v6_boundary_rule():
    state = AI.default_user_adaptation(
        CHAR,
        "user-a",
    )

    guidance = AI.combined_adaptation_guidance(
        "hello",
        state,
    )

    assert (
        "Never allow user adaptation to replace the global V6 personality."
        in guidance.directive
    )


def test_global_personality_boundary_passes():
    fp = PE.build_fingerprint(
        aisha()
    )

    state = AI.default_user_adaptation(
        "global-aisha",
        "user-a",
    )

    ok, reason = (
        AI.adaptation_personality_boundary_check(
            fp,
            state,
        )
    )

    assert ok is True
    assert reason == "ok"


def test_global_personality_boundary_rejects_wrong_character():
    fp = PE.build_fingerprint(
        meera()
    )

    state = AI.default_user_adaptation(
        "global-aisha",
        "user-a",
    )

    ok, reason = (
        AI.adaptation_personality_boundary_check(
            fp,
            state,
        )
    )

    assert ok is False
    assert reason == "character_identity_mismatch"


def test_user_adaptation_never_changes_v6_fingerprint():
    character = aisha()

    before = PE.build_fingerprint(
        character
    )

    state = AI.default_user_adaptation(
        character["characterId"],
        "user-a",
    )

    for _ in range(1000):
        state = AI.evolve_user_adaptation(
            state,
            character["characterId"],
            "user-a",
            "Keep it short, be direct, no jokes",
        )

    after = PE.build_fingerprint(
        character
    )

    assert (
        before.identity_signature
        ==
        after.identity_signature
    )

    assert (
        before.dimensions
        ==
        after.dimensions
    )


def test_same_user_can_have_separate_preferences_per_character():
    aisha_state = AI.default_user_adaptation(
        "global-aisha",
        "same-user",
    )

    meera_state = AI.default_user_adaptation(
        "global-meera",
        "same-user",
    )

    for _ in range(5):
        aisha_state = AI.evolve_user_adaptation(
            aisha_state,
            "global-aisha",
            "same-user",
            "Keep it short",
        )

        meera_state = AI.evolve_user_adaptation(
            meera_state,
            "global-meera",
            "same-user",
            "Explain everything in detail",
        )

    assert (
        aisha_state["detailPreference"]
        <
        meera_state["detailPreference"]
    )

    assert (
        aisha_state["characterId"]
        !=
        meera_state["characterId"]
    )


def test_two_global_characters_pass_anti_convergence():
    a = PE.build_fingerprint(
        aisha()
    )

    m = PE.build_fingerprint(
        meera()
    )

    distance = PE.personality_distance(
        a,
        m,
    )

    ok, reason = AI.anti_convergence_check(
        a,
        m,
        personality_distance_value=distance,
    )

    assert ok is True
    assert reason == "ok"


def test_identical_global_signature_fails_anti_convergence():
    a = PE.build_fingerprint(
        aisha()
    )

    ok, reason = AI.anti_convergence_check(
        a,
        a,
        personality_distance_value=0.0,
    )

    assert ok is False
    assert reason in {
        "global_identity_collision",
        "personality_convergence",
    }


def test_near_identical_personality_can_be_flagged():
    a = {
        "characterId": "global-a",
        "personality": {
            "warmth": 0.50,
            "playfulness": 0.50,
        },
    }

    b = {
        "characterId": "global-b",
        "personality": {
            "warmth": 0.51,
            "playfulness": 0.51,
        },
    }

    af = PE.build_fingerprint(a)
    bf = PE.build_fingerprint(b)

    distance = PE.personality_distance(
        af,
        bf,
    )

    ok, reason = AI.anti_convergence_check(
        af,
        bf,
        personality_distance_value=distance,
        minimum_distance=0.05,
    )

    assert ok is False
    assert reason == "personality_convergence"


def test_long_conversation_preferences_stabilize_at_bounds():
    state = AI.default_user_adaptation(
        CHAR,
        "user-a",
    )

    for _ in range(5000):
        state = AI.evolve_user_adaptation(
            state,
            CHAR,
            "user-a",
            "Keep it short and don't ask questions",
        )

    assert state["detailPreference"] == 0.0
    assert state["questionPreference"] == 0.0

    assert (
        AI.preference_confidence(
            state
        )
        ==
        1.0
    )


def test_many_neutral_turns_do_not_erase_learned_preference():
    state = AI.default_user_adaptation(
        CHAR,
        "user-a",
    )

    for _ in range(10):
        state = AI.evolve_user_adaptation(
            state,
            CHAR,
            "user-a",
            "Keep it short",
        )

    learned = state[
        "detailPreference"
    ]

    for _ in range(5000):
        state = AI.evolve_user_adaptation(
            state,
            CHAR,
            "user-a",
            "I went shopping today",
        )

    assert (
        state["detailPreference"]
        ==
        learned
    )


def test_1000_users_do_not_converge_into_one_adaptation_state():
    states = []

    for number in range(1000):

        state = AI.default_user_adaptation(
            CHAR,
            f"user-{number}",
        )

        if number % 3 == 0:

            for _ in range(4):
                state = AI.evolve_user_adaptation(
                    state,
                    CHAR,
                    f"user-{number}",
                    "Keep it short",
                )

        elif number % 3 == 1:

            for _ in range(4):
                state = AI.evolve_user_adaptation(
                    state,
                    CHAR,
                    f"user-{number}",
                    "Explain everything in detail",
                )

        else:

            for _ in range(4):
                state = AI.evolve_user_adaptation(
                    state,
                    CHAR,
                    f"user-{number}",
                    "Be direct and give me steps",
                )

        states.append(
            AI.continuity_signature(
                state
            )
        )

    assert len(
        set(states)
    ) == 1000


def test_1000_users_same_global_personality_still_one_signature():
    character = aisha()

    global_signature = (
        PE.build_fingerprint(
            character
        ).identity_signature
    )

    signatures = set()

    for number in range(1000):

        state = AI.default_user_adaptation(
            character["characterId"],
            f"user-{number}",
        )

        for _ in range(
            number % 5
        ):
            state = AI.evolve_user_adaptation(
                state,
                character["characterId"],
                f"user-{number}",
                "Keep it short",
            )

        # Per-user V7 adaptation is deliberately not passed to PE.
        signatures.add(
            PE.build_fingerprint(
                character
            ).identity_signature
        )

    assert signatures == {
        global_signature
    }

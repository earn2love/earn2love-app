from ai_engine import adaptive_intelligence as AI


CHAR = "global-aisha"


def test_default_adaptation_is_user_specific():
    a = AI.default_user_adaptation(
        CHAR,
        "user-a",
    )

    b = AI.default_user_adaptation(
        CHAR,
        "user-b",
    )

    assert a["characterId"] == CHAR
    assert b["characterId"] == CHAR

    assert a["userId"] == "user-a"
    assert b["userId"] == "user-b"


def test_default_adaptation_version_is_v7():
    state = AI.default_user_adaptation(
        CHAR,
        "user-a",
    )

    assert state["adaptationVersion"] == 7


def test_technical_context_detected():
    result = AI.analyze_context(
        "My Flutter Firebase backend is throwing an error"
    )

    assert result.context_type == "technical"
    assert result.technicality >= 0.8
    assert result.needs_structure is True


def test_emotional_context_detected():
    result = AI.analyze_context(
        "I feel really worried about tomorrow"
    )

    assert result.context_type == "emotional"
    assert result.needs_empathy is True
    assert result.should_reduce_humor is True
    assert result.should_reduce_teasing is True


def test_practical_context_detected():
    result = AI.analyze_context(
        "How do I configure this step by step?"
    )

    assert result.context_type == "practical"
    assert result.needs_direct_answer is True
    assert result.needs_structure is True


def test_playful_context_detected():
    result = AI.analyze_context(
        "Haha that was funny 😂"
    )

    assert result.context_type == "playful"
    assert result.playfulness >= 0.8


def test_casual_context_default():
    result = AI.analyze_context(
        "I went outside this afternoon"
    )

    assert result.context_type == "casual"


def test_short_answer_preference_is_learned():
    state = AI.default_user_adaptation(
        CHAR,
        "user-a",
    )

    after = AI.evolve_user_adaptation(
        state,
        CHAR,
        "user-a",
        "Keep it short, just tell me the answer",
    )

    assert (
        after["detailPreference"]
        <
        state["detailPreference"]
    )


def test_detailed_answer_preference_is_learned():
    state = AI.default_user_adaptation(
        CHAR,
        "user-a",
    )

    after = AI.evolve_user_adaptation(
        state,
        CHAR,
        "user-a",
        "Explain everything in detail",
    )

    assert (
        after["detailPreference"]
        >
        state["detailPreference"]
    )


def test_direct_preference_is_learned():
    state = AI.default_user_adaptation(
        CHAR,
        "user-a",
    )

    after = AI.evolve_user_adaptation(
        state,
        CHAR,
        "user-a",
        "Be direct and just answer",
    )

    assert (
        after["directnessPreference"]
        >
        state["directnessPreference"]
    )


def test_gentle_preference_changes_warmth():
    state = AI.default_user_adaptation(
        CHAR,
        "user-a",
    )

    after = AI.evolve_user_adaptation(
        state,
        CHAR,
        "user-a",
        "Please be gentle, don't be harsh",
    )

    assert (
        after["warmthPreference"]
        >
        state["warmthPreference"]
    )


def test_user_can_request_less_humor():
    state = AI.default_user_adaptation(
        CHAR,
        "user-a",
    )

    after = AI.evolve_user_adaptation(
        state,
        CHAR,
        "user-a",
        "No jokes, be serious",
    )

    assert (
        after["humorPreference"]
        <
        state["humorPreference"]
    )


def test_user_can_request_more_humor():
    state = AI.default_user_adaptation(
        CHAR,
        "user-a",
    )

    after = AI.evolve_user_adaptation(
        state,
        CHAR,
        "user-a",
        "You can tease me and be funny",
    )

    assert (
        after["humorPreference"]
        >
        state["humorPreference"]
    )


def test_question_preference_can_decrease():
    state = AI.default_user_adaptation(
        CHAR,
        "user-a",
    )

    after = AI.evolve_user_adaptation(
        state,
        CHAR,
        "user-a",
        "Don't ask questions, just answer",
    )

    assert (
        after["questionPreference"]
        <
        state["questionPreference"]
    )


def test_structure_preference_can_increase():
    state = AI.default_user_adaptation(
        CHAR,
        "user-a",
    )

    after = AI.evolve_user_adaptation(
        state,
        CHAR,
        "user-a",
        "Give me steps and make a checklist",
    )

    assert (
        after["structurePreference"]
        >
        state["structurePreference"]
    )


def test_telugu_english_preference():
    state = AI.default_user_adaptation(
        CHAR,
        "user-a",
    )

    after = AI.evolve_user_adaptation(
        state,
        CHAR,
        "user-a",
        "Use Telugu and English",
    )

    assert (
        after["languagePreference"]
        ==
        "telugu_english"
    )


def test_english_only_preference():
    state = AI.default_user_adaptation(
        CHAR,
        "user-a",
    )

    after = AI.evolve_user_adaptation(
        state,
        CHAR,
        "user-a",
        "English only please",
    )

    assert (
        after["languagePreference"]
        ==
        "english"
    )


def test_preferences_evolve_gradually():
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

    assert after["detailPreference"] > 0.35
    assert after["detailPreference"] < 0.50


def test_random_message_does_not_change_preferences():
    state = AI.default_user_adaptation(
        CHAR,
        "user-a",
    )

    after = AI.evolve_user_adaptation(
        state,
        CHAR,
        "user-a",
        "I went shopping today",
    )

    assert (
        after["detailPreference"]
        ==
        state["detailPreference"]
    )

    assert (
        after["adaptationEvents"]
        ==
        state["adaptationEvents"]
    )


def test_two_users_do_not_share_preferences():
    a = AI.default_user_adaptation(
        CHAR,
        "user-a",
    )

    b = AI.default_user_adaptation(
        CHAR,
        "user-b",
    )

    a = AI.evolve_user_adaptation(
        a,
        CHAR,
        "user-a",
        "Keep it short and don't ask questions",
    )

    assert (
        a["detailPreference"]
        !=
        b["detailPreference"]
    )

    assert (
        a["questionPreference"]
        !=
        b["questionPreference"]
    )


def test_evolve_does_not_mutate_input():
    state = AI.default_user_adaptation(
        CHAR,
        "user-a",
    )

    before = dict(
        state
    )

    AI.evolve_user_adaptation(
        state,
        CHAR,
        "user-a",
        "Be direct",
    )

    assert state == before


def test_guidance_marks_delivery_only():
    state = AI.default_user_adaptation(
        CHAR,
        "user-a",
    )

    guidance = AI.build_adaptation_guidance(
        "Please explain this",
        state,
    )

    assert (
        "delivery adaptations only"
        in guidance.directive
    )

    assert (
        "Never rewrite or replace the global V6 character personality."
        in guidance.directive
    )


def test_emotional_context_overrides_humor_for_turn_only():
    state = AI.default_user_adaptation(
        CHAR,
        "user-a",
    )

    state["humorPreference"] = 0.90

    guidance = AI.build_adaptation_guidance(
        "I feel really worried and upset today",
        state,
    )

    assert (
        guidance.context.should_reduce_humor
        is True
    )

    assert (
        "Reduce humour for this turn"
        in guidance.directive
    )

    # Stored preference itself is not rewritten.
    assert (
        guidance.user_preferences[
            "humorPreference"
        ]
        ==
        0.90
    )


def test_technical_context_does_not_change_user_preference_state():
    state = AI.default_user_adaptation(
        CHAR,
        "user-a",
    )

    before = dict(
        state
    )

    AI.build_adaptation_guidance(
        "My backend API throws an exception",
        state,
    )

    assert state == before


def test_normalization_forces_correct_user_identity():
    state = {
        "characterId": "wrong-character",
        "userId": "wrong-user",
        "detailPreference": 0.9,
    }

    result = AI.normalize_user_adaptation(
        state,
        CHAR,
        "real-user",
    )

    assert result["characterId"] == CHAR
    assert result["userId"] == "real-user"


def test_scores_are_clamped():
    state = {
        "detailPreference": 99,
        "directnessPreference": -20,
    }

    result = AI.normalize_user_adaptation(
        state,
        CHAR,
        "user-a",
    )

    assert result["detailPreference"] == 1.0
    assert result["directnessPreference"] == 0.0


def test_explicit_event_count_increases():
    state = AI.default_user_adaptation(
        CHAR,
        "user-a",
    )

    result = AI.evolve_user_adaptation(
        state,
        CHAR,
        "user-a",
        "Be direct",
    )

    assert result["explicitPreferenceEvents"] == 1
    assert result["adaptationEvents"] == 1


def test_context_analysis_has_no_user_identity():
    result = AI.analyze_context(
        "Help me fix this Flutter error"
    ).to_dict()

    assert "userId" not in result
    assert "user_id" not in result

from ai_engine import preference_learning_intelligence as PL11


def test_version():
    assert PL11.PREFERENCE_LEARNING_VERSION == 11


def test_explicit_like_detected():
    result = PL11.analyze_preference(
        "I like biryani"
    )

    assert result.detected
    assert result.explicit
    assert result.owner == PL11.OWNER_MEMORY
    assert result.polarity == PL11.POLARITY_POSITIVE
    assert result.should_persist


def test_explicit_dislike_detected():
    result = PL11.analyze_preference(
        "I don't like coffee"
    )

    assert result.detected
    assert result.polarity == PL11.POLARITY_NEGATIVE


def test_explicit_love_detected():
    result = PL11.analyze_preference(
        "I love Telugu movies"
    )

    assert result.detected
    assert result.domain == "movie"


def test_explicit_enjoy_detected():
    result = PL11.analyze_preference(
        "I enjoy coding"
    )

    assert result.detected
    assert result.domain == "activity"


def test_explicit_prefer_detected():
    result = PL11.analyze_preference(
        "I prefer tea"
    )

    assert result.detected
    assert result.domain == "food"


def test_favourite_pattern():
    result = PL11.analyze_preference(
        "My favourite food is biryani"
    )

    assert result.detected
    assert result.value == "biryani"
    assert result.domain == "food"


def test_favorite_american_spelling():
    result = PL11.analyze_preference(
        "My favorite movie is Interstellar"
    )

    assert result.detected
    assert result.domain == "movie"
    assert result.value == "interstellar"


def test_conversation_language_preference_remains_v7_owned():
    result = PL11.analyze_preference(
        "Reply in Telugu"
    )

    assert result.detected
    assert result.owner == PL11.OWNER_ADAPTATION_V7
    assert not result.should_persist


def test_directness_remains_v7_owned():
    result = PL11.analyze_preference(
        "Be more direct"
    )

    assert result.owner == PL11.OWNER_ADAPTATION_V7
    assert not result.should_persist


def test_detail_level_remains_v7_owned():
    result = PL11.analyze_preference(
        "Give detailed replies"
    )

    assert result.owner == PL11.OWNER_ADAPTATION_V7


def test_emoji_preference_remains_v7_owned():
    result = PL11.analyze_preference(
        "Don't use emojis"
    )

    assert result.owner == PL11.OWNER_ADAPTATION_V7


def test_weak_behaviour_not_inferred():
    result = PL11.analyze_preference(
        "I ordered biryani yesterday"
    )

    assert not result.detected
    assert not result.should_persist


def test_question_not_mistaken_for_preference():
    result = PL11.analyze_preference(
        "Do you like biryani?"
    )

    assert not result.detected


def test_empty_input_safe():
    result = PL11.analyze_preference(
        ""
    )

    assert not result.detected
    assert result.reason == "empty_input"


def test_build_memory_candidate():
    signal = PL11.analyze_preference(
        "I like biryani"
    )

    memory = PL11.build_memory_candidate(
        signal
    )

    assert memory["predicate"].startswith(
        "preference."
    )

    assert memory["value"] == "biryani"
    assert memory["type"] == "preference"
    assert memory["source"] == "explicit_user_statement"
    assert memory["supersedesExisting"] is False


def test_v7_signal_does_not_build_memory_candidate():
    signal = PL11.analyze_preference(
        "Reply in Telugu"
    )

    assert (
        PL11.build_memory_candidate(
            signal
        )
        == {}
    )


def test_same_preference_can_reinforce():
    signal = PL11.analyze_preference(
        "I like biryani"
    )

    existing = {
        "value": "biryani",
        "polarity": "positive",
    }

    assert PL11.should_reinforce_preference(
        existing,
        signal,
    )


def test_different_preference_does_not_reinforce():
    signal = PL11.analyze_preference(
        "I like biryani"
    )

    existing = {
        "value": "pizza",
        "polarity": "positive",
    }

    assert not PL11.should_reinforce_preference(
        existing,
        signal,
    )


def test_opposite_polarity_does_not_reinforce():
    signal = PL11.analyze_preference(
        "I like coffee"
    )

    existing = {
        "value": "coffee",
        "polarity": "negative",
    }

    assert not PL11.should_reinforce_preference(
        existing,
        signal,
    )


def test_reinforcement_key_is_deterministic():
    first = PL11.analyze_preference(
        "I like biryani"
    )

    second = PL11.analyze_preference(
        "I like biryani"
    )

    assert (
        first.reinforcement_key
        == second.reinforcement_key
    )


def test_signal_is_deterministic():
    first = PL11.analyze_preference(
        "I love Telugu movies"
    )

    second = PL11.analyze_preference(
        "I love Telugu movies"
    )

    assert first == second


def test_safe_copy_has_no_private_reasoning():
    signal = PL11.analyze_preference(
        "I like biryani"
    )

    safe = PL11.safe_preference_copy(
        signal
    )

    text = str(
        safe
    )

    assert "chainOfThought" not in text
    assert "hiddenReasoning" not in text
    assert "reasoningTrace" not in text


def test_memory_candidate_does_not_include_user_or_character_identity():
    signal = PL11.analyze_preference(
        "I like biryani"
    )

    memory = PL11.build_memory_candidate(
        signal
    )

    assert "userId" not in memory
    assert "characterId" not in memory


def test_preference_candidate_does_not_supersede_by_default():
    signal = PL11.analyze_preference(
        "I like biryani"
    )

    memory = PL11.build_memory_candidate(
        signal
    )

    assert memory["supersedesExisting"] is False


def test_long_value_is_bounded():
    result = PL11.analyze_preference(
        "I like "
        + ("a" * 1000)
    )

    assert result.detected
    assert len(result.value) <= 200

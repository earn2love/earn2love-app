from ai_engine import emotional_intelligence as E


def test_neutral_message():
    result = E.analyze_emotion(
        "What movie should I watch tonight?"
    )

    assert result["primaryEmotion"] == "neutral"
    assert result["intensity"] == 0.0


def test_joy_detection():
    result = E.analyze_emotion(
        "I'm so excited, I got the job!"
    )

    assert result["primaryEmotion"] == "joy"
    assert result["intensity"] > 0.5
    assert result["meaningfulEvent"] is True


def test_sadness_detection():
    result = E.analyze_emotion(
        "I'm really sad. Today was a terrible day."
    )

    assert result["primaryEmotion"] == "sadness"
    assert result["strategy"]["energy"] == "gentle"


def test_anger_detection():
    result = E.analyze_emotion(
        "I'm furious about what happened!"
    )

    assert result["primaryEmotion"] == "anger"
    assert result["strategy"]["humor"] == "low"


def test_anxiety_detection():
    result = E.analyze_emotion(
        "I'm really nervous about tomorrow."
    )

    assert result["primaryEmotion"] == "anxiety"
    assert result["strategy"]["energy"] == "calm"


def test_stress_detection():
    result = E.analyze_emotion(
        "I'm completely overwhelmed with everything."
    )

    assert result["primaryEmotion"] == "stress"
    assert result["strategy"]["advicePressure"] == "low"


def test_loneliness_detection():
    result = E.analyze_emotion(
        "I feel lonely tonight."
    )

    assert result["primaryEmotion"] == "loneliness"
    assert result["strategy"]["energy"] == "gentle"


def test_joking_detection():
    result = E.analyze_emotion(
        "I'm just joking 😂"
    )

    assert result["primaryEmotion"] == "amusement"


def test_reducer_lowers_intensity():
    weak = E.analyze_emotion(
        "I'm a little nervous."
    )

    strong = E.analyze_emotion(
        "I'm extremely nervous!"
    )

    assert (
        strong["intensity"]
        > weak["intensity"]
    )


def test_job_event_becomes_memory():
    analysis = E.analyze_emotion(
        "I'm so excited, I got the job!"
    )

    memory = E.emotional_event_memory(
        "I'm so excited, I got the job!",
        analysis,
    )

    assert memory is not None
    assert memory["predicate"] == "emotional.event"
    assert memory["emotion"] == "joy"
    assert memory["relationshipRelevant"] is True


def test_ordinary_emotion_not_always_memory():
    analysis = E.analyze_emotion(
        "I'm a little annoyed."
    )

    memory = E.emotional_event_memory(
        "I'm a little annoyed.",
        analysis,
    )

    assert memory is None


def test_trajectory_intensifying():
    previous = E.analyze_emotion(
        "I'm a little nervous."
    )

    current = E.analyze_emotion(
        "I'm extremely nervous!!!"
    )

    assert E.trajectory(
        current,
        previous,
    ) == "intensifying"


def test_trajectory_easing():
    previous = E.analyze_emotion(
        "I'm extremely nervous!!!"
    )

    current = E.analyze_emotion(
        "I'm a little nervous now."
    )

    assert E.trajectory(
        current,
        previous,
    ) == "easing"


def test_trajectory_shifted():
    previous = E.analyze_emotion(
        "I'm nervous."
    )

    current = E.analyze_emotion(
        "I'm excited now!"
    )

    assert E.trajectory(
        current,
        previous,
    ) == "shifted"


def test_trajectory_settling():
    previous = E.analyze_emotion(
        "I'm really angry!"
    )

    current = E.analyze_emotion(
        "Anyway, what movie should I watch?"
    )

    assert E.trajectory(
        current,
        previous,
    ) == "settling"


def test_guidance_does_not_overreact_to_neutral():
    analysis = E.analyze_emotion(
        "Tell me something interesting."
    )

    guidance = E.format_emotional_guidance(
        analysis
    )

    assert "No strong emotional signal" in guidance


def test_guidance_preserves_character_personality():
    analysis = E.analyze_emotion(
        "I'm really sad."
    )

    guidance = E.format_emotional_guidance(
        analysis
    )

    assert "Preserve the character's own personality" in guidance

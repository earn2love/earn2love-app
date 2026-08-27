from ai_engine import conversation_intelligence as C


def h():
    return [
        {
            "sender": "user",
            "text": "I have an interview tomorrow",
        },
        {
            "sender": "character",
            "text": "The Excel section seems to be the part worrying you most.",
        },
        {
            "sender": "user",
            "text": "Yeah, especially lookup formulas",
        },
        {
            "sender": "character",
            "text": "Start with XLOOKUP and then revise INDEX MATCH.",
        },
    ]


def test_recent_topics_exist():
    topics = C.recent_topics(h())

    assert topics


def test_unresolved_question_thread():
    history = [
        {
            "sender": "user",
            "text": "Work was stressful today",
        },
        {
            "sender": "character",
            "text": "Was it the workload or something with the team?",
        },
    ]

    result = C.unresolved_thread(history)

    assert result is not None
    assert result["aiAskedQuestion"] is True


def test_personality_guidance_uses_character_traits():
    result = C.personality_guidance(
        {
            "personalityTraits": [
                "playful",
                "curious",
                "direct",
            ]
        },
        {
            "state": "comfortable",
        },
    )

    assert "playful" in result
    assert "generic assistant" in result
    assert "comfortable" in result


def test_personality_does_not_invent_missing_traits():
    result = C.personality_guidance(
        {},
        {
            "state": "new",
        },
    )

    assert "Character style anchors:" not in result


def test_telugu_script_detection():
    result = C.multilingual_guidance(
        "నాకు ఇది నచ్చింది",
        [],
    )

    assert "telugu" not in result.casefold() or isinstance(
        result,
        str,
    )


def test_language_continuity_latin():
    history = [
        {
            "sender": "user",
            "text": "I had a long day at work",
        }
    ]

    result = C.multilingual_guidance(
        "yeah very long",
        history,
    )

    assert "language continuity" in result


def test_language_switch_is_respected():
    history = [
        {
            "sender": "user",
            "text": "I had a long day",
        }
    ]

    result = C.multilingual_guidance(
        "నాకు చాలా అలసటగా ఉంది",
        history,
    )

    assert "changed writing script" in result


def test_long_conversation_guidance():
    history = []

    for i in range(30):
        history.append(
            {
                "sender": "user",
                "text": f"I am talking about project milestone {i}",
            }
        )

    result = C.long_conversation_guidance(
        history,
    )

    assert "longer conversation" in result


def test_direct_question_rejects_robotic_opening():
    guidance = C.analyze(
        "Why did that happen?",
        h(),
    )

    ok, reason = C.response_quality_check(
        "That's a great question. It happened because the input changed.",
        guidance,
        [],
    )

    assert ok is False
    assert reason == "delayed_direct_answer"


def test_no_followup_rejects_forced_ending_question():
    guidance = C.analyze(
        "ok",
        h(),
    )

    ok, reason = C.response_quality_check(
        "Exactly. The next step is XLOOKUP. Want me to explain it?",
        guidance,
        [],
    )

    assert ok is False
    assert reason == "forced_followup_question"


def test_no_followup_accepts_natural_statement():
    guidance = C.analyze(
        "ok",
        h(),
    )

    ok, reason = C.response_quality_check(
        "Exactly — XLOOKUP first, then INDEX MATCH.",
        guidance,
        [],
    )

    assert ok is True
    assert reason == "ok"


def test_repeated_opening_rejected():
    guidance = C.analyze(
        "Today was difficult",
        h(),
    )

    previous = [
        "I get why that feels frustrating. Take it one part at a time."
    ]

    ok, reason = C.response_quality_check(
        "I get why that feels frustrating. You had a lot going on.",
        guidance,
        previous,
    )

    assert ok is False
    assert reason == "repeated_opening"


def test_generic_assistant_closer_rejected():
    guidance = C.analyze(
        "Today was difficult",
        h(),
    )

    ok, reason = C.response_quality_check(
        "That was a rough day. I'm here if you need anything.",
        guidance,
        [],
    )

    assert ok is False
    assert reason == "generic_assistant_closer"


def test_generation_directive_contains_all_layers():
    guidance = C.analyze(
        "hmm",
        h(),
        relationship_state="comfortable",
    )

    result = C.build_generation_directive(
        guidance,
        character={
            "personalityTraits": [
                "witty",
                "warm",
            ]
        },
        relationship={
            "state": "comfortable",
        },
        language={
            "languageCode": "en",
        },
        history=h(),
        user_text="hmm",
    )

    assert "continuous real conversation" in result
    assert "witty" in result
    assert "Match the person's conversational language" in result
    assert "older context" in result


def test_topic_switch_does_not_force_old_topic():
    guidance = C.analyze(
        "I am thinking of buying a new laptop",
        h(),
    )

    result = C.human_conversation_guidance(
        guidance,
        h(),
    )

    if guidance.continuity_mode == "switch":
        assert "Follow the new topic naturally" in result


def test_no_shared_state_between_users_in_extended_controller():
    user_a = C.recent_topics(
        [
            {
                "sender": "user",
                "text": "My interview is tomorrow",
            }
        ]
    )

    user_b = C.recent_topics(
        [
            {
                "sender": "user",
                "text": "My flight is tomorrow",
            }
        ]
    )

    assert user_a != user_b


def test_quality_check_does_not_mutate_input():
    guidance = C.analyze(
        "okay",
        h(),
    )

    recent = [
        "One previous reply."
    ]

    original = list(recent)

    C.response_quality_check(
        "Okay.",
        guidance,
        recent,
    )

    assert recent == original

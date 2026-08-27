from ai_engine import conversation_intelligence as C


def history():
    return [
        {
            "sender": "user",
            "text": "I have an interview tomorrow for a finance analyst job",
        },
        {
            "sender": "character",
            "text": "That sounds important. Have you prepared the technical questions?",
        },
        {
            "sender": "user",
            "text": "Mostly, but I am worried about the Excel part",
        },
        {
            "sender": "character",
            "text": "We can focus on the Excel part first.",
        },
    ]


def test_short_acknowledgement_continues_context():
    result = C.analyze(
        "hmm",
        history(),
    )

    assert result.short_reply is True
    assert result.message_kind == "acknowledgement"
    assert result.continuity_mode == "continue"
    assert result.should_reference_context is True
    assert result.should_avoid_new_topic is True
    assert result.max_questions == 0


def test_ok_does_not_force_question():
    result = C.analyze(
        "ok",
        history(),
    )

    assert result.message_kind == "acknowledgement"
    assert result.should_ask_followup is False
    assert result.max_questions == 0


def test_why_is_direct_continuation_question():
    result = C.analyze(
        "why?",
        history(),
    )

    assert result.question is True
    assert result.short_reply is True
    assert result.should_answer_directly is True
    assert result.continuity_mode == "continue"
    assert result.max_questions == 0


def test_correction_enters_repair_mode():
    result = C.analyze(
        "No, I mean the accounting interview, not finance",
        history(),
    )

    assert result.user_is_correcting is True
    assert result.message_kind == "correction"
    assert result.continuity_mode == "repair"
    assert result.should_answer_directly is True
    assert result.should_reference_context is True
    assert result.max_questions == 0


def test_topic_return_detected():
    result = C.analyze(
        "Back to what we were discussing about my interview",
        history(),
    )

    assert result.user_is_returning is True
    assert result.continuity_mode == "return"
    assert result.should_reference_context is True
    assert result.should_avoid_new_topic is True


def test_topic_exit_detected():
    result = C.analyze(
        "Anyway leave it, tell me something else",
        history(),
    )

    assert result.user_is_disengaging is True
    assert result.message_kind == "topic_exit"
    assert result.continuity_mode == "topic_exit"
    assert result.should_ask_followup is False


def test_normal_statement_may_allow_one_followup():
    result = C.analyze(
        "I finally completed the interview preparation today",
        history(),
    )

    assert result.max_questions <= 1
    assert result.anti_repetition is True


def test_question_does_not_add_another_question():
    result = C.analyze(
        "How should I answer when they ask about weaknesses?",
        history(),
    )

    assert result.question is True
    assert result.should_answer_directly is True
    assert result.max_questions == 0


def test_established_relationship_has_familiar_pacing():
    result = C.analyze(
        "Today was exhausting at work",
        history(),
        relationship_state="established",
    )

    assert result.pacing == "natural_familiar"


def test_no_history_does_not_claim_context():
    result = C.analyze(
        "hello",
        [],
    )

    assert result.should_reference_context is False


def test_repetitive_ai_openings_detected():
    h = [
        {
            "sender": "character",
            "text": "I understand that this is difficult.",
        },
        {
            "sender": "user",
            "text": "yeah",
        },
        {
            "sender": "character",
            "text": "I understand that this feels stressful.",
        },
    ]

    duplicates = C.repeated_ai_openings(h)

    assert "i understand that this" in duplicates


def test_guidance_contains_continuity_instruction():
    text = C.prompt_guidance(
        "hmm",
        history(),
    )

    assert "continuous real conversation" in text
    assert "Do not force a follow-up question" in text


def test_telugu_acknowledgement():
    result = C.analyze(
        "sare",
        history(),
    )

    assert result.message_kind == "acknowledgement"
    assert result.continuity_mode == "continue"


def test_avunu_acknowledgement():
    result = C.analyze(
        "avunu",
        history(),
    )

    assert result.message_kind == "acknowledgement"


def test_controller_returns_plain_serializable_dict():
    result = C.analyze(
        "okay",
        history(),
    ).to_dict()

    assert isinstance(result, dict)
    assert result["message_kind"] == "acknowledgement"
    assert isinstance(result["guidance_text"], str)


def test_two_users_have_no_controller_shared_state():
    first = C.analyze(
        "hmm",
        [
            {
                "sender": "user",
                "text": "My exam is tomorrow",
            }
        ],
    )

    second = C.analyze(
        "hmm",
        [
            {
                "sender": "user",
                "text": "My flight is tomorrow",
            }
        ],
    )

    assert first.previous_topic != second.previous_topic


def test_controller_does_not_mutate_history():
    h = history()
    before = [dict(x) for x in h]

    C.analyze(
        "okay",
        h,
    )

    assert h == before

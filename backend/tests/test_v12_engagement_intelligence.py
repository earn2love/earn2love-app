from types import SimpleNamespace

from ai_engine import engagement_intelligence as E


def guidance(
    *,
    followup=False,
    max_questions=0,
):
    return SimpleNamespace(
        should_ask_followup=followup,
        max_questions=max_questions,
    )


def test_acknowledgement_continues_without_forced_question():
    result = E.analyze_engagement(
        "Okay.",
        guidance(
            followup=False,
            max_questions=0,
        ),
    )

    assert result.acknowledgement is True
    assert result.allow_question is False
    assert result.max_questions == 0
    assert result.continuation_mode == E.CONTINUATION_STATEMENT
    assert "Do not force a question" in result.directive


def test_v12_never_increases_v4_question_allowance():
    result = E.analyze_engagement(
        "I'm fine.",
        guidance(
            followup=True,
            max_questions=0,
        ),
    )

    assert result.allow_question is False
    assert result.max_questions == 0


def test_v4_authorized_followup_allows_at_most_one():
    result = E.analyze_engagement(
        "Today was pretty good actually",
        guidance(
            followup=True,
            max_questions=4,
        ),
    )

    assert result.allow_question is True
    assert result.max_questions == 1
    assert (
        result.continuation_mode
        == E.CONTINUATION_OPTIONAL_QUESTION
    )


def test_question_input_does_not_get_extra_followup_authority():
    result = E.analyze_engagement(
        "What do you think?",
        guidance(
            followup=True,
            max_questions=1,
        ),
    )

    assert result.allow_question is False
    assert result.max_questions == 0


def test_disengagement_is_respected():
    result = E.analyze_engagement(
        "Leave it",
        guidance(
            followup=True,
            max_questions=1,
        ),
        selected_memories=[
            {
                "summary": "User likes biryani",
                "status": "active",
            }
        ],
    )

    assert result.disengaging is True
    assert result.reply_depth == E.DEPTH_MINIMAL
    assert result.continuation_mode == E.CONTINUATION_NONE
    assert result.allow_question is False
    assert result.allow_memory_callback is False
    assert "do not chase" in result.directive


def test_selected_v11_memory_can_enable_compact_callback():
    result = E.analyze_engagement(
        "Food gurinchi matladham",
        guidance(
            followup=True,
            max_questions=1,
        ),
        selected_memories=[
            {
                "predicate": "preference.food",
                "value": "biryani",
                "status": "active",
            }
        ],
    )

    assert result.allow_memory_callback is True
    assert result.memory_candidates == 1
    assert "V11-selected memory" in result.directive
    assert "never invent" in result.directive


def test_no_selected_memory_means_no_claimed_callback():
    result = E.analyze_engagement(
        "Food gurinchi matladham",
        guidance(
            followup=True,
            max_questions=1,
        ),
        selected_memories=[],
    )

    assert result.allow_memory_callback is False
    assert result.memory_candidates == 0
    assert "Do not invent a memory callback" in result.directive


def test_inactive_memory_does_not_authorize_callback():
    result = E.analyze_engagement(
        "Food gurinchi matladham",
        guidance(),
        selected_memories=[
            {
                "summary": "Old preference",
                "status": "superseded",
            }
        ],
    )

    assert result.allow_memory_callback is False


def test_relationship_warmth_is_guidance_not_personality_mutation():
    relationship = {
        "state": "comfortable",
        "nested": {
            "unchanged": True,
        },
    }

    before = {
        "state": relationship["state"],
        "nested": dict(
            relationship["nested"]
        ),
    }

    result = E.analyze_engagement(
        "I'm fine.",
        guidance(),
        relationship=relationship,
    )

    assert result.warmth == "friendly_warm"
    assert relationship == before
    assert "locked global character personality" in result.directive


def test_love_context_can_be_warm_without_question():
    result = E.analyze_engagement(
        "Okay",
        guidance(
            followup=False,
            max_questions=0,
        ),
        relationship={
            "state": "love",
        },
    )

    assert result.warmth == "warm"
    assert result.allow_question is False


def test_short_input_gets_natural_depth_not_forced_minimal():
    result = E.analyze_engagement(
        "I'm good",
        guidance(
            followup=False,
            max_questions=0,
        ),
    )

    assert result.reply_depth == E.DEPTH_NATURAL
    assert result.continuation_mode == E.CONTINUATION_STATEMENT


def test_long_input_can_expand_naturally():
    text = " ".join(
        ["detail"] * 35
    )

    result = E.analyze_engagement(
        text,
        guidance(
            followup=False,
            max_questions=0,
        ),
    )

    assert result.reply_depth == E.DEPTH_EXPANDED


def test_to_dict_contains_safe_metadata_only():
    result = E.analyze_engagement(
        "Okay",
        guidance(),
    )

    data = result.to_dict()

    assert data["version"] == 12
    assert data["allowQuestion"] is False
    assert data["allowMemoryCallback"] is False
    assert data["memoryCandidates"] == 0
    assert "directive" not in data

    # Structured metadata may describe whether a memory callback
    # is allowed, but must never expose actual memory content.
    serialized = str(data).casefold()

    assert "biryani" not in serialized
    assert "preference.food" not in serialized
    assert "summary" not in data
    assert "memoryText" not in data
    assert "memoryValue" not in data


def test_module_is_deterministic():
    args = dict(
        user_text="I'm fine.",
        conversation_guidance=guidance(
            followup=True,
            max_questions=1,
        ),
        selected_memories=[
            {
                "summary": "Likes biryani",
                "status": "active",
            }
        ],
        relationship={
            "state": "comfortable",
        },
        history=[],
    )

    first = E.analyze_engagement(
        **args
    )

    second = E.analyze_engagement(
        **args
    )

    assert first == second

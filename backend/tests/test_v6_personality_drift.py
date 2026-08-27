"""V6.4 personality drift protection tests.

These tests protect the distinction between:
- global character personality,
- normal conversational flexibility,
- per-user relationship adaptation,
- and genuinely out-of-character output.

V6 must not turn personality checking into a rigid keyword filter.
"""

import pytest

from ai_engine import personality_engine as PE


def playful_character():
    return {
        "characterId": "global-aisha",
        "name": "Aisha",
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
            "formality": 0.18,
            "emojiUse": 0.28,
        },
    }


def reserved_character():
    return {
        "characterId": "global-meera",
        "name": "Meera",
        "personalityTraits": [
            "calm",
            "reserved",
            "direct",
        ],
        "personality": {
            "warmth": 0.48,
            "playfulness": 0.20,
            "curiosity": 0.45,
            "directness": 0.82,
            "verbosity": 0.25,
            "emojiUse": 0.03,
            "formality": 0.65,
        },
    }


def test_same_character_fingerprint_is_deterministic():
    first = PE.build_fingerprint(
        playful_character()
    )

    for _ in range(100):
        current = PE.build_fingerprint(
            playful_character()
        )

        assert (
            current.identity_signature
            == first.identity_signature
        )

        assert (
            current.dimensions
            == first.dimensions
        )


def test_user_information_cannot_change_global_personality():
    character = playful_character()

    baseline = PE.build_fingerprint(
        character
    )

    # These fields deliberately resemble relationship/user state.
    polluted = dict(character)

    polluted.update(
        {
            "userId": "user-999",
            "trust": 1.0,
            "familiarity": 1.0,
            "relationshipStage": "deep",
            "messageCount": 50000,
            "userMood": "angry",
        }
    )

    result = PE.build_fingerprint(
        polluted
    )

    assert (
        result.identity_signature
        == baseline.identity_signature
    )

    assert (
        result.dimensions
        == baseline.dimensions
    )


def test_different_users_cannot_mutate_character_input():
    character = playful_character()

    original = {
        key: (
            dict(value)
            if isinstance(value, dict)
            else list(value)
            if isinstance(value, list)
            else value
        )
        for key, value in character.items()
    }

    for user_id in range(1000):
        PE.build_guidance(
            character
        )

    assert character == original


def test_relationship_state_is_not_part_of_personality_signature():
    base = playful_character()

    variants = []

    for stage in [
        "new",
        "familiar",
        "trusted",
        "deep",
    ]:
        item = dict(base)

        item["relationship"] = {
            "stage": stage,
            "trust": 0.99,
            "familiarity": 0.99,
        }

        item["userId"] = (
            "relationship-user-" + stage
        )

        variants.append(
            PE.build_fingerprint(item)
        )

    signatures = {
        item.identity_signature
        for item in variants
    }

    assert len(signatures) == 1


def test_reserved_character_stays_low_teasing():
    fp = PE.build_fingerprint(
        reserved_character()
    )

    assert fp.dimensions["teasing"] <= 0.22
    assert fp.teasing_style == "none_or_rare"


def test_playful_and_reserved_profiles_remain_distinct():
    playful = PE.build_fingerprint(
        playful_character()
    )

    reserved = PE.build_fingerprint(
        reserved_character()
    )

    assert (
        playful.identity_signature
        != reserved.identity_signature
    )

    assert (
        PE.personality_distance(
            playful,
            reserved,
        )
        > 0.10
    )


@pytest.mark.parametrize(
    "response",
    [
        "Yeah, that actually makes sense.",
        "I get what you mean.",
        "That sounds like a good plan.",
        "Okay, tell me what happened next.",
        "Fair enough. I'd probably think about it the same way.",
        "You really planned all of that already? That's impressive.",
    ],
)
def test_normal_human_variation_is_not_rejected_for_playful_character(
    response,
):
    fp = PE.build_fingerprint(
        playful_character()
    )

    ok, reason = PE.output_personality_check(
        response,
        fp,
    )

    assert ok is True, (
        response,
        reason,
    )


@pytest.mark.parametrize(
    "response",
    [
        "Yes.",
        "That makes sense.",
        "I understand.",
        "Probably.",
        "I'd choose the second option.",
        "No, I don't think that's a good idea.",
    ],
)
def test_short_direct_answers_are_allowed_for_reserved_character(
    response,
):
    fp = PE.build_fingerprint(
        reserved_character()
    )

    ok, reason = PE.output_personality_check(
        response,
        fp,
    )

    assert ok is True, (
        response,
        reason,
    )


def test_personality_check_does_not_require_humor_every_turn():
    fp = PE.build_fingerprint(
        playful_character()
    )

    response = (
        "That sounds difficult. "
        "You don't have to make the decision immediately."
    )

    ok, reason = PE.output_personality_check(
        response,
        fp,
    )

    assert ok is True, reason


def test_personality_check_does_not_require_teasing_every_turn():
    fp = PE.build_fingerprint(
        playful_character()
    )

    response = (
        "I think your first option is safer, "
        "especially if you want to avoid unnecessary risk."
    )

    ok, reason = PE.output_personality_check(
        response,
        fp,
    )

    assert ok is True, reason


def test_personality_check_allows_serious_context_for_playful_character():
    fp = PE.build_fingerprint(
        playful_character()
    )

    response = (
        "I'm sorry you're dealing with that. "
        "For now, focus on what you can control today."
    )

    ok, reason = PE.output_personality_check(
        response,
        fp,
    )

    assert ok is True, reason


def test_reserved_character_does_not_need_to_sound_cold():
    fp = PE.build_fingerprint(
        reserved_character()
    )

    response = (
        "I understand why that bothered you. "
        "You handled it better than you think."
    )

    ok, reason = PE.output_personality_check(
        response,
        fp,
    )

    assert ok is True, reason


def test_empty_response_is_never_accepted():
    fp = PE.build_fingerprint(
        playful_character()
    )

    ok, reason = PE.output_personality_check(
        "",
        fp,
    )

    assert ok is False
    assert reason


def test_whitespace_response_is_never_accepted():
    fp = PE.build_fingerprint(
        reserved_character()
    )

    ok, reason = PE.output_personality_check(
        "     ",
        fp,
    )

    assert ok is False
    assert reason


def test_extreme_emoji_spam_is_rejected_for_reserved_character():
    fp = PE.build_fingerprint(
        reserved_character()
    )

    response = (
        "OMG 😂😂😂😂😂😂😂😂😂😂 "
        "THIS IS SOOOO FUNNY 😭😭😭😭😭 "
        "HAHAHAHA 😂😂😂😂😂"
    )

    ok, reason = PE.output_personality_check(
        response,
        fp,
    )

    assert ok is False
    assert reason


def test_extreme_oververbosity_is_rejected_for_concise_reserved_character():
    fp = PE.build_fingerprint(
        reserved_character()
    )

    response = " ".join(
        ["This is unnecessary elaboration"]
        * 120
    )

    ok, reason = PE.output_personality_check(
        response,
        fp,
    )

    assert ok is False
    assert reason


def test_guidance_contains_identity_signature():
    guidance = PE.build_guidance(
        playful_character()
    )

    assert guidance.fingerprint.identity_signature
    assert len(
        guidance.fingerprint.identity_signature
    ) >= 12


def test_guidance_is_character_specific():
    aisha = PE.build_guidance(
        playful_character()
    )

    meera = PE.build_guidance(
        reserved_character()
    )

    assert (
        aisha.directive
        != meera.directive
    )

    assert (
        aisha.fingerprint.identity_signature
        != meera.fingerprint.identity_signature
    )


def test_guidance_does_not_contain_user_identity():
    character = playful_character()

    character["userId"] = (
        "SECRET_USER_IDENTIFIER_123"
    )

    guidance = PE.build_guidance(
        character
    )

    assert (
        "SECRET_USER_IDENTIFIER_123"
        not in guidance.directive
    )


def test_1000_users_receive_same_global_fingerprint():
    character = playful_character()

    signatures = set()

    for user_number in range(1000):

        request_character = dict(
            character
        )

        request_character["userId"] = (
            f"user-{user_number}"
        )

        request_character["relationshipStage"] = (
            "new"
            if user_number % 2 == 0
            else "trusted"
        )

        fingerprint = PE.build_fingerprint(
            request_character
        )

        signatures.add(
            fingerprint.identity_signature
        )

    assert len(signatures) == 1


def test_100_global_characters_are_deterministically_distinct_when_config_differs():
    signatures = set()

    for number in range(100):

        profile = {
            "characterId": (
                f"global-character-{number}"
            ),
            "personality": {
                "warmth": (
                    (number % 10) / 10.0
                ),
                "playfulness": (
                    ((number // 10) % 10)
                    / 10.0
                ),
                "curiosity": (
                    ((number * 3) % 10)
                    / 10.0
                ),
                "directness": (
                    ((number * 7) % 10)
                    / 10.0
                ),
            },
        }

        fingerprint = PE.build_fingerprint(
            profile
        )

        signatures.add(
            fingerprint.identity_signature
        )

    assert len(signatures) == 100


def test_personality_distance_is_symmetric():
    a = PE.build_fingerprint(
        playful_character()
    )

    b = PE.build_fingerprint(
        reserved_character()
    )

    assert PE.personality_distance(
        a,
        b,
    ) == pytest.approx(
        PE.personality_distance(
            b,
            a,
        )
    )


def test_personality_distance_to_self_is_zero():
    fp = PE.build_fingerprint(
        playful_character()
    )

    assert PE.personality_distance(
        fp,
        fp,
    ) == pytest.approx(0.0)

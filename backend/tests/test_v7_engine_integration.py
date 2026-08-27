import inspect

from ai_engine import adaptive_intelligence as AI
from ai_engine import personality_engine as PE
from ai_engine.engine import CharacterEngine
from ai_engine.repository import InMemoryCharacterRepository


CHARACTER = {
    "characterId": "global-aisha",
    "personalityTraits": [
        "warm",
        "playful",
        "curious",
        "witty",
    ],
}


def test_character_engine_source_contains_v7():

    source = inspect.getsource(
        CharacterEngine
    )

    required = [
        "self.repo.get_adaptation(",
        "AI.combined_adaptation_guidance(",
        "V7_ADAPTIVE_INTELLIGENCE",
        "self.repo.advance_adaptation(",
        "adaptation_guidance=None",
    ]

    for marker in required:
        assert marker in source


def test_v7_and_v6_are_distinct_layers():

    state = AI.default_user_adaptation(
        "global-aisha",
        "user-a",
    )

    guidance = AI.combined_adaptation_guidance(
        "Keep it short",
        state,
    )

    fingerprint = PE.build_fingerprint(
        CHARACTER
    )

    assert (
        guidance.user_preferences["userId"]
        ==
        "user-a"
    )

    personality = fingerprint.to_dict()

    assert "userId" not in personality
    assert "user_id" not in personality


def test_user_adaptation_cannot_change_global_fingerprint():

    before = PE.build_fingerprint(
        CHARACTER
    )

    repo = InMemoryCharacterRepository()

    for _ in range(50):

        repo.advance_adaptation(
            "global-aisha",
            "user-a",
            "Keep it short and be direct",
        )

    after = PE.build_fingerprint(
        CHARACTER
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


def test_two_users_get_separate_engine_side_states():

    repo = InMemoryCharacterRepository()

    for _ in range(5):

        repo.advance_adaptation(
            "global-aisha",
            "user-a",
            "Keep it short",
        )

        repo.advance_adaptation(
            "global-aisha",
            "user-b",
            "Explain everything in detail",
        )

    a = repo.get_adaptation(
        "global-aisha",
        "user-a",
    )

    b = repo.get_adaptation(
        "global-aisha",
        "user-b",
    )

    assert (
        a["detailPreference"]
        <
        b["detailPreference"]
    )


def test_context_guidance_does_not_persist_by_itself():

    repo = InMemoryCharacterRepository()

    state = repo.get_adaptation(
        "global-aisha",
        "user-a",
    )

    before = dict(
        state
    )

    AI.combined_adaptation_guidance(
        "I feel really worried today",
        state,
    )

    after = repo.get_adaptation(
        "global-aisha",
        "user-a",
    )

    assert before == after


def test_explicit_persistence_is_required():

    repo = InMemoryCharacterRepository()

    before = repo.get_adaptation(
        "global-aisha",
        "user-a",
    )

    repo.advance_adaptation(
        "global-aisha",
        "user-a",
        "Keep it short",
    )

    after = repo.get_adaptation(
        "global-aisha",
        "user-a",
    )

    assert (
        after["detailPreference"]
        <
        before["detailPreference"]
    )


def test_same_user_different_characters_still_isolated():

    repo = InMemoryCharacterRepository()

    repo.advance_adaptation(
        "global-aisha",
        "same-user",
        "Keep it short",
    )

    repo.advance_adaptation(
        "global-meera",
        "same-user",
        "Explain everything in detail",
    )

    a = repo.get_adaptation(
        "global-aisha",
        "same-user",
    )

    m = repo.get_adaptation(
        "global-meera",
        "same-user",
    )

    assert (
        a["characterId"]
        !=
        m["characterId"]
    )

    assert (
        a["detailPreference"]
        <
        m["detailPreference"]
    )

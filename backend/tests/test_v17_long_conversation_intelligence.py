"""
Earn2Love AI Engine V17.2

Final long-conversation intelligence invariants.

This suite does not create a new memory, personality, adaptation or
relationship system. It verifies that the existing systems remain isolated
and stable when exercised together over long-running user histories.
"""

from copy import deepcopy

from ai_engine import adaptive_intelligence as AI
from ai_engine import personality_engine as PE
from ai_engine import preference_learning_intelligence as PL11
from ai_engine.repository import InMemoryCharacterRepository


V17_2_LONG_CONVERSATION_INTELLIGENCE = True


CHARACTER_ID = "global-aisha"

CHARACTER = {
    "characterId": CHARACTER_ID,
    "personalityTraits": [
        "warm",
        "playful",
        "curious",
        "witty",
    ],
}


EXPECTED_PERSONALITY_SIGNATURE = (
    "eee045b0ebce2ded526ef78d"
)


def _fingerprint():
    return PE.build_fingerprint(
        CHARACTER
    )


def _store_preference(
    repo,
    user_id,
    value,
):
    signal = PL11.analyze_preference(
        f"I like {value}"
    )

    assert signal.detected
    assert signal.explicit
    assert signal.should_persist

    candidate = PL11.build_memory_candidate(
        signal
    )

    assert candidate is not None

    stored = repo.add_memory(
        CHARACTER_ID,
        user_id,
        candidate,
    )

    assert stored is not None

    return stored


def test_v17_personality_stays_immutable_during_long_user_history():
    original_character = deepcopy(
        CHARACTER
    )

    baseline = _fingerprint()

    assert (
        baseline.identity_signature
        == EXPECTED_PERSONALITY_SIGNATURE
    )

    state = AI.default_user_adaptation(
        CHARACTER_ID,
        "long-user",
    )

    for turn in range(10000):
        text = (
            "Please keep replies short"
            if turn % 3 == 0
            else
            "Tell me a little more detail"
            if turn % 3 == 1
            else
            "Thanks, continue"
        )

        state = AI.evolve_user_adaptation(
            state,
            CHARACTER_ID,
            "long-user",
            text,
        )

        if turn % 250 == 0:
            current = _fingerprint()

            assert (
                current.identity_signature
                == baseline.identity_signature
            )

    final = _fingerprint()

    assert (
        final.identity_signature
        == baseline.identity_signature
        == EXPECTED_PERSONALITY_SIGNATURE
    )

    assert CHARACTER == original_character


def test_v17_long_history_memory_remains_user_scoped():
    repo = InMemoryCharacterRepository()

    users = [
        "long-user-a",
        "long-user-b",
        "long-user-c",
    ]

    expected = {
        user_id: []
        for user_id in users
    }

    for turn in range(600):
        user_id = users[
            turn % len(users)
        ]

        value = (
            f"{user_id}-preference-{turn:04d}"
        )

        stored = _store_preference(
            repo,
            user_id,
            value,
        )

        expected[user_id].append(
            (
                stored["memoryId"],
                value,
            )
        )

    for user_id in users:
        memories = repo.list_memories(
            CHARACTER_ID,
            user_id,
        )

        values = {
            memory.get("value")
            for memory in memories
        }

        expected_values = {
            value
            for _, value
            in expected[user_id]
        }

        assert values == expected_values

        foreign_values = set()

        for other_user in users:
            if other_user == user_id:
                continue

            foreign_values.update(
                value
                for _, value
                in expected[other_user]
            )

        assert values.isdisjoint(
            foreign_values
        )


def test_v17_wrong_user_cannot_reinforce_long_history_memory():
    repo = InMemoryCharacterRepository()

    owner = "memory-owner"
    attacker = "other-user"

    stored = _store_preference(
        repo,
        owner,
        "masala-dosa",
    )

    memory_id = stored[
        "memoryId"
    ]

    for _ in range(1000):
        result = repo.reinforce_memory(
            CHARACTER_ID,
            attacker,
            memory_id,
        )

        assert result is None

    owner_memories = repo.list_memories(
        CHARACTER_ID,
        owner,
    )

    assert len(owner_memories) == 1

    assert (
        owner_memories[0].get(
            "reinforcementCount",
            0,
        )
        == 0
    )


def test_v17_adaptation_identity_never_crosses_users():
    user_a = AI.default_user_adaptation(
        CHARACTER_ID,
        "adaptive-user-a",
    )

    user_b = AI.default_user_adaptation(
        CHARACTER_ID,
        "adaptive-user-b",
    )

    for _ in range(2500):
        user_a = AI.evolve_user_adaptation(
            user_a,
            CHARACTER_ID,
            "adaptive-user-a",
            "Please keep your replies short",
        )

        user_b = AI.evolve_user_adaptation(
            user_b,
            CHARACTER_ID,
            "adaptive-user-b",
            "I prefer detailed explanations",
        )

    assert (
        user_a["userId"]
        == "adaptive-user-a"
    )

    assert (
        user_b["userId"]
        == "adaptive-user-b"
    )

    assert (
        user_a["characterId"]
        == CHARACTER_ID
    )

    assert (
        user_b["characterId"]
        == CHARACTER_ID
    )

    assert user_a != user_b


def test_v17_same_user_remains_character_scoped():
    second_character = (
        "global-second-character"
    )

    first = AI.default_user_adaptation(
        CHARACTER_ID,
        "shared-user",
    )

    second = AI.default_user_adaptation(
        second_character,
        "shared-user",
    )

    for _ in range(1000):
        first = AI.evolve_user_adaptation(
            first,
            CHARACTER_ID,
            "shared-user",
            "Keep replies short",
        )

        second = AI.evolve_user_adaptation(
            second,
            second_character,
            "shared-user",
            "Give detailed replies",
        )

    assert (
        first["userId"]
        == second["userId"]
        == "shared-user"
    )

    assert (
        first["characterId"]
        == CHARACTER_ID
    )

    assert (
        second["characterId"]
        == second_character
    )

    assert first != second


def test_v17_memory_activity_cannot_mutate_global_personality():
    repo = InMemoryCharacterRepository()

    baseline = _fingerprint()

    for index in range(2000):
        uid = (
            f"combined-user-{index % 100:03d}"
        )

        stored = _store_preference(
            repo,
            uid,
            f"item-{index:05d}",
        )

        repo.reinforce_memory(
            CHARACTER_ID,
            uid,
            stored["memoryId"],
        )

        if index % 100 == 0:
            current = _fingerprint()

            assert (
                current.identity_signature
                == baseline.identity_signature
            )

    after = _fingerprint()

    assert (
        after.identity_signature
        == baseline.identity_signature
        == EXPECTED_PERSONALITY_SIGNATURE
    )


def test_v17_long_conversation_marker():
    assert (
        V17_2_LONG_CONVERSATION_INTELLIGENCE
        is True
    )

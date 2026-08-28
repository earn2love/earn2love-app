from ai_engine import personality_engine as PE
from ai_engine import preference_learning_intelligence as PL11
from ai_engine.repository import InMemoryCharacterRepository


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


def test_v11_5000_users_memory_scope_and_personality_immutable():
    repo = InMemoryCharacterRepository()

    baseline = PE.build_fingerprint(
        CHARACTER
    ).identity_signature

    assert (
        baseline
        == "eee045b0ebce2ded526ef78d"
    )

    total = 5000

    memory_ids = set()

    for index in range(total):

        uid = f"stress-user-{index:05d}"

        value = f"food-{index:05d}"

        signal = PL11.analyze_preference(
            f"I like {value}"
        )

        assert signal.detected
        assert signal.explicit
        assert signal.should_persist

        candidate = PL11.build_memory_candidate(
            signal
        )

        stored = repo.add_memory(
            CHARACTER_ID,
            uid,
            candidate,
        )

        assert stored is not None

        memory_id = stored[
            "memoryId"
        ]

        assert (
            memory_id
            not in memory_ids
        )

        memory_ids.add(
            memory_id
        )

        reinforced = repo.reinforce_memory(
            CHARACTER_ID,
            uid,
            memory_id,
        )

        assert reinforced is not None

        assert (
            reinforced.get(
                "reinforcementCount",
                0,
            )
            == 1
        )


    assert (
        len(memory_ids)
        == total
    )


    # Every user sees exactly their own memory.
    for index in range(total):

        uid = f"stress-user-{index:05d}"

        memories = repo.list_memories(
            CHARACTER_ID,
            uid,
        )

        assert (
            len(memories)
            == 1
        )

        assert (
            memories[0][
                "value"
            ]
            == f"food-{index:05d}"
        )

        assert (
            memories[0].get(
                "reinforcementCount",
                0,
            )
            == 1
        )


    # Wrong-user reinforcement cannot cross scope.
    first_uid = "stress-user-00000"

    first_memory = repo.list_memories(
        CHARACTER_ID,
        first_uid,
    )[0]

    wrong_scope = repo.reinforce_memory(
        CHARACTER_ID,
        "stress-user-04999",
        first_memory[
            "memoryId"
        ],
    )

    assert (
        wrong_scope
        is None
    )


    # First and last user remain isolated.
    first = repo.list_memories(
        CHARACTER_ID,
        "stress-user-00000",
    )

    last = repo.list_memories(
        CHARACTER_ID,
        "stress-user-04999",
    )

    assert (
        first[0][
            "value"
        ]
        == "food-00000"
    )

    assert (
        last[0][
            "value"
        ]
        == "food-04999"
    )


    # 5000 user-specific operations cannot mutate global character personality.
    after = PE.build_fingerprint(
        CHARACTER
    ).identity_signature

    assert (
        after
        == baseline
        == "eee045b0ebce2ded526ef78d"
    )

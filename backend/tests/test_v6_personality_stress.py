"""V6.5 global personality stress + concurrency tests."""

from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy

from ai_engine import personality_engine as PE
from ai_engine import relationship_intelligence as RI
from ai_engine.repository import InMemoryCharacterRepository


def global_character():
    return {
        "characterId": "global-aisha",
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
            "directness": 0.55,
            "verbosity": 0.50,
            "emojiUse": 0.28,
        },
    }


def make_profile(number):
    return {
        "characterId": f"global-character-{number}",
        "personality": {
            "warmth": (number % 11) / 10.0,
            "playfulness": ((number * 3) % 11) / 10.0,
            "curiosity": ((number * 5) % 11) / 10.0,
            "directness": ((number * 7) % 11) / 10.0,
            "energy": ((number * 2) % 11) / 10.0,
            "formality": ((number * 4) % 11) / 10.0,
            "verbosity": ((number * 6) % 11) / 10.0,
            "emojiUse": ((number * 8) % 11) / 10.0,
        },
    }


def test_10000_users_same_global_character_same_signature():
    character = global_character()

    signatures = set()

    for user_number in range(10000):
        request_view = dict(character)

        request_view["userId"] = f"user-{user_number}"
        request_view["relationshipStage"] = (
            "new"
            if user_number % 4 == 0
            else "familiar"
            if user_number % 4 == 1
            else "comfortable"
            if user_number % 4 == 2
            else "established"
        )

        fingerprint = PE.build_fingerprint(
            request_view
        )

        signatures.add(
            fingerprint.identity_signature
        )

    assert len(signatures) == 1


def test_concurrent_5000_requests_same_global_character():
    character = global_character()

    expected = PE.build_fingerprint(
        character
    ).identity_signature

    def task(user_number):
        request_view = dict(character)

        request_view["userId"] = (
            f"concurrent-user-{user_number}"
        )

        request_view["trust"] = (
            user_number % 100
        ) / 100.0

        request_view["familiarity"] = (
            (user_number * 7) % 100
        ) / 100.0

        return PE.build_fingerprint(
            request_view
        ).identity_signature

    with ThreadPoolExecutor(
        max_workers=32
    ) as executor:

        results = list(
            executor.map(
                task,
                range(5000),
            )
        )

    assert set(results) == {expected}


def test_concurrent_guidance_generation_does_not_mutate_character():
    character = global_character()
    original = deepcopy(character)

    def task(_):
        guidance = PE.build_guidance(
            character
        )

        return guidance.fingerprint.identity_signature

    with ThreadPoolExecutor(
        max_workers=32
    ) as executor:

        results = list(
            executor.map(
                task,
                range(3000),
            )
        )

    assert character == original
    assert len(set(results)) == 1


def test_500_global_characters_stay_character_specific():
    profiles = [
        make_profile(index)
        for index in range(500)
    ]

    fingerprints = [
        PE.build_fingerprint(profile)
        for profile in profiles
    ]

    # Character ID is intentionally part of the global identity signature,
    # so every global character must have a distinct identity.
    signatures = {
        fp.identity_signature
        for fp in fingerprints
    }

    assert len(signatures) == 500


def test_concurrent_multi_character_requests_do_not_cross_contaminate():
    profiles = {
        index: make_profile(index)
        for index in range(100)
    }

    expected = {
        index: PE.build_fingerprint(
            profile
        ).identity_signature
        for index, profile in profiles.items()
    }

    def task(pair):
        character_number, user_number = pair

        profile = dict(
            profiles[character_number]
        )

        profile["userId"] = (
            f"user-{user_number}"
        )

        fingerprint = PE.build_fingerprint(
            profile
        )

        return (
            character_number,
            fingerprint.identity_signature,
        )

    workload = [
        (
            user_number % 100,
            user_number,
        )
        for user_number in range(10000)
    ]

    with ThreadPoolExecutor(
        max_workers=32
    ) as executor:

        results = list(
            executor.map(
                task,
                workload,
            )
        )

    for character_number, signature in results:
        assert signature == expected[
            character_number
        ]


def test_relationship_state_changes_do_not_change_global_personality():
    character = global_character()

    signature = PE.build_fingerprint(
        character
    ).identity_signature

    state = RI.default_state(
        character["characterId"],
        "relationship-user",
    )

    messages = [
        "hello",
        "I am worried about tomorrow",
        "I got the job today!",
        "That was a difficult week",
        "I finally finished everything",
    ]

    for _ in range(200):
        for message in messages:
            state = RI.evolve(
                state,
                character["characterId"],
                "relationship-user",
                message,
            )

            request_view = dict(character)

            request_view["relationship"] = dict(
                state
            )

            request_view["trust"] = state[
                "trust"
            ]

            request_view["familiarity"] = state[
                "familiarity"
            ]

            assert (
                PE.build_fingerprint(
                    request_view
                ).identity_signature
                ==
                signature
            )


def test_same_global_character_many_users_have_isolated_relationships():
    character = global_character()
    repo = InMemoryCharacterRepository()

    user_count = 500

    for user_number in range(user_count):
        user_id = f"user-{user_number}"

        for _ in range(
            (user_number % 10) + 1
        ):
            repo.advance_relationship(
                character["characterId"],
                user_id,
                {"topics": []},
                user_text=(
                    f"conversation for {user_id}"
                ),
            )

    relationship_turns = {
        user_id: repo.get_relationship(
            character["characterId"],
            user_id,
        )["turnCount"]
        for user_id in [
            f"user-{number}"
            for number in range(user_count)
        ]
    }

    assert len(
        relationship_turns
    ) == user_count

    for number in range(user_count):
        expected = (
            number % 10
        ) + 1

        assert relationship_turns[
            f"user-{number}"
        ] == expected

    # Personality is still exactly one global fingerprint.
    signatures = {
        PE.build_fingerprint(
            {
                **character,
                "userId": f"user-{number}",
            }
        ).identity_signature
        for number in range(user_count)
    }

    assert len(signatures) == 1


def test_long_running_personality_generation_is_stable():
    character = global_character()

    original = PE.build_fingerprint(
        character
    )

    for _ in range(20000):
        current = PE.build_fingerprint(
            character
        )

        assert (
            current.identity_signature
            ==
            original.identity_signature
        )

        assert (
            current.dimensions
            ==
            original.dimensions
        )


def test_validator_is_deterministic_under_repeated_calls():
    character = global_character()

    fingerprint = PE.build_fingerprint(
        character
    )

    response = (
        "That actually sounds like a good idea. "
        "I'd keep the first option simple."
    )

    results = {
        PE.output_personality_check(
            response,
            fingerprint,
        )
        for _ in range(10000)
    }

    assert results == {
        (True, "ok")
    }


def test_validator_does_not_mutate_fingerprint():
    fingerprint = PE.build_fingerprint(
        global_character()
    )

    before = fingerprint.to_dict()

    for _ in range(1000):
        PE.output_personality_check(
            "That sounds reasonable.",
            fingerprint,
        )

    assert fingerprint.to_dict() == before


def test_global_character_input_remains_immutable_under_stress():
    character = global_character()
    before = deepcopy(character)

    for user_number in range(5000):
        PE.build_guidance(
            {
                **character,
                "userId": f"user-{user_number}",
            }
        )

    assert character == before


def test_relationship_and_personality_identifiers_are_separate():
    character = global_character()

    fingerprint = PE.build_fingerprint(
        character
    )

    relationship = RI.default_state(
        character["characterId"],
        "specific-user",
    )

    personality_data = fingerprint.to_dict()

    assert (
        personality_data["character_id"]
        ==
        character["characterId"]
    )

    assert "user_id" not in personality_data
    assert "userId" not in personality_data

    assert relationship["userId"] == "specific-user"
    assert (
        relationship["characterId"]
        ==
        character["characterId"]
    )


def test_100_profiles_have_nonzero_average_pairwise_distance():
    fingerprints = [
        PE.build_fingerprint(
            make_profile(index)
        )
        for index in range(100)
    ]

    distances = []

    for index in range(
        len(fingerprints) - 1
    ):
        distances.append(
            PE.personality_distance(
                fingerprints[index],
                fingerprints[index + 1],
            )
        )

    assert distances
    assert sum(distances) / len(
        distances
    ) > 0.05


def test_concise_character_extreme_drift_remains_blocked_under_stress():
    character = {
        "characterId": "stress-concise",
        "personalityTraits": [
            "reserved",
            "direct",
            "concise",
        ],
        "personality": {
            "verbosity": 0.12,
            "emojiUse": 0.02,
            "formality": 0.70,
        },
    }

    fingerprint = PE.build_fingerprint(
        character
    )

    extreme = " ".join(
        ["Unnecessary explanation"]
        * 300
    )

    results = {
        PE.output_personality_check(
            extreme,
            fingerprint,
        )
        for _ in range(2000)
    }

    assert len(results) == 1

    ok, reason = next(
        iter(results)
    )

    assert ok is False

    assert reason in {
        "extreme_verbosity_drift",
        "extreme_oververbosity",
    }


def test_global_personality_never_contains_relationship_milestones():
    character = global_character()

    polluted = {
        **character,
        "milestones": [
            {
                "summary": "private relationship milestone",
            }
        ],
        "sharedTopics": [
            "private relationship topic"
        ],
        "userId": "private-user",
    }

    guidance = PE.build_guidance(
        polluted
    )

    serialized = str(
        guidance.to_dict()
    )

    assert (
        "private relationship milestone"
        not in serialized
    )

    assert (
        "private relationship topic"
        not in serialized
    )

    assert (
        "private-user"
        not in serialized
    )

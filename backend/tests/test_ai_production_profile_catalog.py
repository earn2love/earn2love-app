from copy import deepcopy

import ai_profile_contract as PROFILE
from ai_engine.schema import (
    new_character,
    validate_character,
)
from ai_profiles.production_catalog import (
    PRODUCTION_AI_PROFILES,
)


def test_pack_has_12_profiles():
    assert len(PRODUCTION_AI_PROFILES) == 12


def test_character_ids_unique():
    ids = [
        p["characterId"]
        for p in PRODUCTION_AI_PROFILES
    ]

    assert len(ids) == len(set(ids))


def test_names_unique():
    names = [
        p["displayName"].lower()
        for p in PRODUCTION_AI_PROFILES
    ]

    assert len(names) == len(set(names))


def test_all_are_adults():
    assert all(
        p["age"] >= 18
        for p in PRODUCTION_AI_PROFILES
    )


def test_all_are_explicitly_ai():
    for p in PRODUCTION_AI_PROFILES:
        assert p["isAi"] is True
        assert p["aiDisclosure"] is True


def test_all_start_draft_hidden():
    for p in PRODUCTION_AI_PROFILES:
        assert p["profileStatus"] == "draft"
        assert p["visibility"] == "hidden"


def test_all_are_not_archived():
    assert all(
        p["archived"] is False
        for p in PRODUCTION_AI_PROFILES
    )


def test_all_have_chat_capability():
    assert all(
        p["capabilities"]["chat"] is True
        for p in PRODUCTION_AI_PROFILES
    )


def test_capability_keys_exact():
    expected = {
        "chat",
        "imageUnderstanding",
        "imageCreation",
        "liveKnowledge",
        "playTogether",
    }

    for p in PRODUCTION_AI_PROFILES:
        assert set(
            p["capabilities"]
        ) == expected


def test_tiers_are_contract_tiers_only():
    allowed = {
        "casual",
        "friendship",
        "love",
    }

    for p in PRODUCTION_AI_PROFILES:
        assert set(
            p["tierAccess"]
        ).issubset(allowed)


def test_core_schema_validates_every_profile():
    for profile in PRODUCTION_AI_PROFILES:
        core = new_character(
            **deepcopy(profile)
        )

        ok, errors = validate_character(
            core
        )

        assert ok, (
            profile["characterId"],
            errors,
        )


def test_profile_contract_normalizes_every_profile():
    for profile in PRODUCTION_AI_PROFILES:
        result = PROFILE.normalize_profile(
            deepcopy(profile)
        )

        assert (
            result["characterId"]
            == profile["characterId"]
        )

        assert result["isAi"] is True
        assert result["aiDisclosure"] is True


def test_none_are_public_yet():
    for profile in PRODUCTION_AI_PROFILES:
        assert (
            PROFILE.public_profile(
                deepcopy(profile)
            )
            is None
        )


def test_no_reference_ids():
    for profile in PRODUCTION_AI_PROFILES:
        assert not profile[
            "characterId"
        ].startswith("ref_")


def test_no_generated_factory_ids():
    for profile in PRODUCTION_AI_PROFILES:
        assert not profile[
            "characterId"
        ].startswith("gen_")


def test_no_user_scoped_state_in_global_profiles():
    forbidden = {
        "userId",
        "conversationId",
        "memory",
        "memories",
        "memoryIdsUsed",
        "relationshipState",
        "adaptationState",
        "activeGoal",
        "activePlan",
        "providerSessionId",
        "scopeToken",
        "signedUrl",
    }

    for profile in PRODUCTION_AI_PROFILES:
        assert forbidden.isdisjoint(
            profile.keys()
        )


def test_world_fact_ids_unique_globally():
    ids = []

    for profile in PRODUCTION_AI_PROFILES:
        for fact in profile.get(
            "worldFacts",
            [],
        ):
            ids.append(
                fact["factId"]
            )

    assert len(ids) == len(set(ids))


def test_profile_objects_are_independent():
    copy_pack = deepcopy(
        PRODUCTION_AI_PROFILES
    )

    copy_pack[0][
        "personalityTraits"
    ].append("mutation-test")

    assert (
        "mutation-test"
        not in
        PRODUCTION_AI_PROFILES[0][
            "personalityTraits"
        ]
    )


def test_balanced_initial_gender_pack():
    female = sum(
        1
        for p in PRODUCTION_AI_PROFILES
        if p["genderPresentation"]
        == "female"
    )

    male = sum(
        1
        for p in PRODUCTION_AI_PROFILES
        if p["genderPresentation"]
        == "male"
    )

    assert female == 6
    assert male == 6


def test_required_launch_languages_present():
    languages = {
        language
        for p in PRODUCTION_AI_PROFILES
        for language in p["languages"]
    }

    assert {
        "English",
        "Telugu",
        "Hindi",
        "Tamil",
        "Kannada",
        "Bengali",
        "Punjabi",
    }.issubset(languages)

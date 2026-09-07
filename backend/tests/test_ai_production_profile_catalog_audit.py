from collections import Counter
from copy import deepcopy
from itertools import combinations

import ai_profile_contract as PROFILE
from ai_profiles.production_catalog import (
    PRODUCTION_AI_PROFILES,
)


FORBIDDEN_GLOBAL_FIELDS = {
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
    "imageBytes",
    "audioBytes",
}


DEPENDENCY_PHRASES = (
    "you only need me",
    "you don't need anyone else",
    "don't leave me",
    "stay with me forever",
    "you belong to me",
    "i belong to you",
    "prove you love me",
    "prove your loyalty",
    "choose me over",
    "i'm jealous",
    "be mine only",
)


HUMAN_CLAIM_PHRASES = (
    "i am human",
    "i'm human",
    "real person",
    "not an ai",
    "not ai",
)


def _all_text(profile):
    parts = []

    def walk(value):
        if isinstance(value, str):
            parts.append(value.lower())
            return

        if isinstance(value, dict):
            for item in value.values():
                walk(item)
            return

        if isinstance(value, (list, tuple, set)):
            for item in value:
                walk(item)

    walk(profile)

    return "\n".join(parts)


def test_exactly_12_launch_profiles():
    assert len(PRODUCTION_AI_PROFILES) == 12


def test_every_profile_has_stable_e2l_id():
    for profile in PRODUCTION_AI_PROFILES:
        cid = profile["characterId"]

        assert cid.startswith("e2l_")
        assert cid == cid.lower()
        assert " " not in cid


def test_all_ids_and_names_unique():
    ids = [
        p["characterId"]
        for p in PRODUCTION_AI_PROFILES
    ]

    names = [
        p["displayName"].strip().lower()
        for p in PRODUCTION_AI_PROFILES
    ]

    assert len(ids) == len(set(ids))
    assert len(names) == len(set(names))


def test_no_reference_or_factory_profiles():
    for profile in PRODUCTION_AI_PROFILES:
        cid = profile["characterId"]

        assert not cid.startswith("ref_")
        assert not cid.startswith("gen_")


def test_every_profile_explicit_ai():
    for profile in PRODUCTION_AI_PROFILES:
        assert profile["isAi"] is True
        assert profile["aiDisclosure"] is True

        text = _all_text(profile)

        assert "ai companion" in text


def test_no_human_identity_claims():
    for profile in PRODUCTION_AI_PROFILES:
        text = _all_text(profile)

        for phrase in HUMAN_CLAIM_PHRASES:
            assert phrase not in text, (
                profile["characterId"],
                phrase,
            )


def test_every_profile_is_adult():
    for profile in PRODUCTION_AI_PROFILES:
        assert isinstance(
            profile["age"],
            int,
        )

        assert profile["age"] >= 18


def test_every_profile_draft_hidden():
    for profile in PRODUCTION_AI_PROFILES:
        assert (
            profile["profileStatus"]
            == "draft"
        )

        assert (
            profile["visibility"]
            == "hidden"
        )

        assert profile["archived"] is False


def test_no_profile_is_public():
    for profile in PRODUCTION_AI_PROFILES:
        assert (
            PROFILE.public_profile(
                deepcopy(profile)
            )
            is None
        )


def test_no_user_scoped_state():
    for profile in PRODUCTION_AI_PROFILES:
        overlap = (
            FORBIDDEN_GLOBAL_FIELDS
            & set(profile.keys())
        )

        assert not overlap, (
            profile["characterId"],
            overlap,
        )


def test_capability_keys_exact():
    expected = {
        "chat",
        "imageUnderstanding",
        "imageCreation",
        "liveKnowledge",
        "playTogether",
    }

    for profile in PRODUCTION_AI_PROFILES:
        assert (
            set(profile["capabilities"])
            == expected
        )


def test_image_creation_not_enabled_yet():
    for profile in PRODUCTION_AI_PROFILES:
        assert (
            profile["capabilities"][
                "imageCreation"
            ]
            is False
        )


def test_chat_enabled_for_every_profile():
    for profile in PRODUCTION_AI_PROFILES:
        assert (
            profile["capabilities"]["chat"]
            is True
        )


def test_only_supported_tiers_used():
    allowed = {
        "casual",
        "friendship",
        "love",
    }

    for profile in PRODUCTION_AI_PROFILES:
        assert profile["tierAccess"]

        assert set(
            profile["tierAccess"]
        ).issubset(allowed)


def test_level_fields_are_valid():
    fields = (
        "curiosityLevel",
        "confidenceLevel",
        "warmthLevel",
        "playfulnessLevel",
        "directnessLevel",
        "romanceLevel",
    )

    for profile in PRODUCTION_AI_PROFILES:
        for field in fields:
            value = profile[field]

            assert 0.0 <= value <= 1.0, (
                profile["characterId"],
                field,
                value,
            )


def test_required_identity_content_present():
    required = (
        "displayName",
        "country",
        "city",
        "profession",
        "background",
        "profileBio",
        "communicationStyle",
        "greetingStyle",
    )

    for profile in PRODUCTION_AI_PROFILES:
        for field in required:
            assert (
                isinstance(
                    profile.get(field),
                    str,
                )
                and
                profile[field].strip()
            ), (
                profile["characterId"],
                field,
            )


def test_personality_data_is_not_empty():
    required_lists = (
        "languages",
        "interests",
        "hobbies",
        "personalityTraits",
        "boundaries",
        "likes",
        "dislikes",
        "values",
        "conversationalHabits",
        "recurringLifeFacts",
        "backstoryFacts",
        "worldFacts",
        "opinions",
        "relationshipStyle",
    )

    for profile in PRODUCTION_AI_PROFILES:
        for field in required_lists:
            assert profile.get(field), (
                profile["characterId"],
                field,
            )


def test_every_profile_has_english():
    for profile in PRODUCTION_AI_PROFILES:
        assert (
            "English"
            in profile["languages"]
        )


def test_required_launch_languages_covered():
    languages = {
        lang
        for profile
        in PRODUCTION_AI_PROFILES
        for lang
        in profile["languages"]
    }

    expected = {
        "English",
        "Telugu",
        "Hindi",
        "Tamil",
        "Kannada",
        "Bengali",
        "Punjabi",
    }

    assert expected.issubset(
        languages
    )


def test_gender_launch_pack_balanced():
    counts = Counter(
        p["genderPresentation"]
        for p
        in PRODUCTION_AI_PROFILES
    )

    assert counts["female"] == 6
    assert counts["male"] == 6


def test_world_fact_ids_unique():
    ids = []

    for profile in PRODUCTION_AI_PROFILES:
        for fact in profile[
            "worldFacts"
        ]:
            ids.append(
                fact["factId"]
            )

    assert len(ids) == len(set(ids))


def test_world_facts_have_required_shape():
    for profile in PRODUCTION_AI_PROFILES:
        for fact in profile[
            "worldFacts"
        ]:
            assert isinstance(
                fact.get("factId"),
                str,
            )

            assert fact["factId"]

            assert isinstance(
                fact.get("key"),
                str,
            )

            assert fact["key"]

            assert isinstance(
                fact.get("value"),
                str,
            )

            assert fact["value"]

            assert isinstance(
                fact.get("immutable"),
                bool,
            )


def test_each_profile_has_immutable_home_identity():
    for profile in PRODUCTION_AI_PROFILES:
        home_facts = [
            fact
            for fact
            in profile["worldFacts"]
            if (
                fact.get("key")
                == "home_city"
                and
                fact.get("immutable")
                is True
            )
        ]

        assert home_facts, (
            profile["characterId"],
            "missing immutable home_city",
        )

        assert any(
            fact["value"]
            == profile["city"]
            for fact
            in home_facts
        )


def test_relationship_style_has_no_dependency_language():
    for profile in PRODUCTION_AI_PROFILES:
        text = _all_text(
            profile.get(
                "relationshipStyle",
                [],
            )
        )

        for phrase in DEPENDENCY_PHRASES:
            assert phrase not in text, (
                profile["characterId"],
                phrase,
            )


def test_all_profile_text_has_no_dependency_language():
    for profile in PRODUCTION_AI_PROFILES:
        text = _all_text(profile)

        for phrase in DEPENDENCY_PHRASES:
            assert phrase not in text, (
                profile["characterId"],
                phrase,
            )


def test_boundaries_explicitly_reject_human_claim():
    for profile in PRODUCTION_AI_PROFILES:
        text = " ".join(
            profile["boundaries"]
        ).lower()

        assert (
            "never claim to be human"
            in text
        )


def test_no_near_duplicate_personality_trait_sets():
    profiles = (
        PRODUCTION_AI_PROFILES
    )

    for left, right in combinations(
        profiles,
        2,
    ):
        a = set(
            trait.lower()
            for trait
            in left[
                "personalityTraits"
            ]
        )

        b = set(
            trait.lower()
            for trait
            in right[
                "personalityTraits"
            ]
        )

        union = a | b
        intersection = a & b

        similarity = (
            len(intersection)
            / len(union)
            if union
            else 1.0
        )

        assert similarity < 0.80, (
            left["characterId"],
            right["characterId"],
            similarity,
        )


def test_sort_order_unique():
    values = [
        p["sortOrder"]
        for p
        in PRODUCTION_AI_PROFILES
    ]

    assert len(values) == len(
        set(values)
    )


def test_featured_profiles_are_limited():
    featured = [
        p
        for p
        in PRODUCTION_AI_PROFILES
        if p["featured"]
    ]

    assert 1 <= len(featured) <= 4


def test_contract_normalization_preserves_safety_flags():
    for profile in PRODUCTION_AI_PROFILES:
        normalized = (
            PROFILE.normalize_profile(
                deepcopy(profile)
            )
        )

        assert normalized["isAi"] is True
        assert (
            normalized["aiDisclosure"]
            is True
        )

        assert (
            normalized["profileStatus"]
            == "draft"
        )

        assert (
            normalized["visibility"]
            == "hidden"
        )


def test_catalog_normalization_does_not_mutate_source():
    original = deepcopy(
        PRODUCTION_AI_PROFILES
    )

    for profile in PRODUCTION_AI_PROFILES:
        PROFILE.normalize_profile(
            profile
        )

    assert (
        PRODUCTION_AI_PROFILES
        == original
    )

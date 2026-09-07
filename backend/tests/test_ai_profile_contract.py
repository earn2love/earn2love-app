from copy import deepcopy

import pytest

import ai_profile_contract as P


def character(**overrides):
    data = {
        "characterId": "char-production-a",
        "displayName": "Aisha",
        "isAi": True,
        "enabled": True,
        "archived": False,
        "languages": [
            "English",
            "Telugu",
        ],
        "tierAccess": [
            "casual",
            "friendship",
            "love",
        ],
        "profileStatus": "published",
        "visibility": "public",
    }

    data.update(overrides)

    return data


def test_ai_disclosure_is_authoritative():
    profile = P.normalize_profile(
        character(
            isAi=False,
            aiDisclosure=False,
        )
    )

    assert profile["isAi"] is True
    assert profile["aiDisclosure"] is True


def test_normalization_does_not_mutate_source():
    source = character(
        capabilities={
            "chat": True,
        }
    )

    original = deepcopy(source)

    P.normalize_profile(source)

    assert source == original


def test_capabilities_default_false():
    profile = P.normalize_profile(
        character()
    )

    assert all(
        value is False
        for value
        in profile["capabilities"].values()
    )


def test_known_capability_can_be_enabled():
    profile = P.normalize_profile(
        character(
            capabilities={
                "chat": True,
            }
        )
    )

    assert profile["capabilities"]["chat"] is True


def test_unknown_capability_is_removed():
    profile = P.normalize_profile(
        character(
            capabilities={
                "chat": True,
                "unknownCapability": True,
            }
        )
    )

    assert "unknownCapability" not in profile["capabilities"]


def test_invalid_tier_removed():
    profile = P.normalize_profile(
        character(
            tierAccess=[
                "casual",
                "invalid",
                "love",
            ]
        )
    )

    assert profile["tierAccess"] == [
        "casual",
        "love",
    ]


def test_duplicate_tiers_removed():
    profile = P.normalize_profile(
        character(
            tierAccess=[
                "casual",
                "casual",
                "friendship",
            ]
        )
    )

    assert profile["tierAccess"] == [
        "casual",
        "friendship",
    ]


def test_draft_profile_not_public():
    assert not P.is_public_profile(
        character(
            profileStatus="draft"
        )
    )


def test_paused_profile_not_public():
    assert not P.is_public_profile(
        character(
            profileStatus="paused"
        )
    )


def test_hidden_profile_not_public():
    assert not P.is_public_profile(
        character(
            visibility="hidden"
        )
    )


def test_disabled_profile_not_public():
    assert not P.is_public_profile(
        character(
            enabled=False
        )
    )


def test_archived_profile_not_public():
    assert not P.is_public_profile(
        character(
            archived=True
        )
    )


def test_published_public_enabled_profile_is_public():
    assert P.is_public_profile(
        character()
    )


def test_public_profile_excludes_user_state():
    result = P.public_profile(
        character(
            userId="private-user",
            memoryIdsUsed=["memory-1"],
            relationshipState={
                "state": "comfortable",
            },
            adaptationState={
                "detailPreference": 0.8,
            },
            activeGoal={
                "goal": "private",
            },
            activePlan={
                "steps": [],
            },
        )
    )

    assert result is not None

    forbidden = {
        "userId",
        "memoryIdsUsed",
        "relationshipState",
        "adaptationState",
        "activeGoal",
        "activePlan",
    }

    assert forbidden.isdisjoint(
        result.keys()
    )


def test_public_profile_preserves_identity():
    result = P.public_profile(
        character(
            profession="designer",
            profileBio="Creative AI companion",
            personalityTraits=[
                "warm",
                "creative",
            ],
        )
    )

    assert result is not None
    assert result["characterId"] == "char-production-a"
    assert result["displayName"] == "Aisha"
    assert result["profession"] == "designer"

    assert result["personalityTraits"] == [
        "warm",
        "creative",
    ]


def test_missing_character_id_fails_closed():
    with pytest.raises(ValueError):
        P.normalize_profile(
            {
                "displayName": "Aisha",
            }
        )


def test_missing_display_name_fails_closed():
    with pytest.raises(ValueError):
        P.normalize_profile(
            {
                "characterId": "char-a",
            }
        )


def test_invalid_status_becomes_draft():
    profile = P.normalize_profile(
        character(
            profileStatus="invalid-status"
        )
    )

    assert profile["profileStatus"] == "draft"


def test_invalid_visibility_becomes_hidden():
    profile = P.normalize_profile(
        character(
            visibility="invalid-visibility"
        )
    )

    assert profile["visibility"] == "hidden"


def test_profile_media_defaults_empty():
    profile = P.normalize_profile(
        character()
    )

    assert profile["profileMedia"] == []


def test_relationship_style_is_global_profile_metadata():
    profile = P.normalize_profile(
        character(
            relationshipStyle="warm friendship"
        )
    )

    assert (
        profile["relationshipStyle"]
        == "warm friendship"
    )


def test_public_profile_forces_ai_transparency():
    result = P.public_profile(
        character(
            isAi=False,
            aiDisclosure=False,
        )
    )

    assert result is not None
    assert result["isAi"] is True
    assert result["aiDisclosure"] is True

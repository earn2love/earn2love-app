from copy import deepcopy
from pathlib import Path

import pytest

import ai_profile_contract as PROFILE
import ai_service as SVC
from ai_engine.registry import REFERENCE_CHARACTERS
from ai_engine.repository import InMemoryCharacterRepository


@pytest.fixture
def repo(monkeypatch):
    value = InMemoryCharacterRepository()

    monkeypatch.setattr(
        SVC,
        "_prod_repo",
        value,
    )

    return value


def character(
    character_id="prod-secure-a",
    **overrides,
):
    value = deepcopy(
        REFERENCE_CHARACTERS[0]
    )

    value.update(
        {
            "characterId": character_id,
            "profileStatus": "published",
            "visibility": "public",
            "enabled": True,
            "archived": False,
            "isAi": True,
            "aiDisclosure": True,
            "capabilities": {
                "chat": True,
                "imageUnderstanding": False,
                "imageCreation": False,
                "liveKnowledge": False,
                "playTogether": False,
            },
            "tierAccess": [
                "casual",
                "friendship",
                "love",
            ],
        }
    )

    value.update(overrides)

    return value


def server_source():
    return Path(
        "server.py"
    ).read_text(
        encoding="utf-8-sig"
    )


def test_profile_list_route_requires_auth():
    source = server_source()

    start = source.index(
        "async def ai_profiles_list"
    )

    section = source[
        start:
        start + 500
    ]

    assert (
        "Depends(get_current_user)"
        in section
    )


def test_profile_detail_route_requires_auth():
    source = server_source()

    start = source.index(
        "async def ai_profile_get"
    )

    section = source[
        start:
        start + 600
    ]

    assert (
        "Depends(get_current_user)"
        in section
    )


def test_profile_detail_missing_is_404_contract():
    source = server_source()

    start = source.index(
        "async def ai_profile_get"
    )

    section = source[
        start:
        start + 800
    ]

    assert "status_code=404" in section
    assert "AI profile not found" in section


def test_existing_admin_get_route_preserved():
    source = server_source()

    assert (
        '@api.get("/ai/characters")'
        in source
    )


def test_existing_admin_create_route_preserved():
    source = server_source()

    assert (
        '@api.post("/ai/characters")'
        in source
    )


def test_existing_admin_update_route_preserved():
    source = server_source()

    assert (
        '@api.put("/ai/characters/{cid}")'
        in source
    )


def test_existing_admin_delete_route_preserved():
    source = server_source()

    assert (
        '@api.delete("/ai/characters/{cid}")'
        in source
    )


def test_admin_write_guard_still_present():
    source = server_source()

    assert "require_write(" in source


def test_reference_registry_is_not_public_by_default(
    repo,
):
    assert SVC.list_public_profiles() == []

    for reference in REFERENCE_CHARACTERS:
        cid = reference["characterId"]

        assert (
            SVC.get_public_profile(cid)
            is None
        )


@pytest.mark.parametrize(
    "status",
    [
        "draft",
        "paused",
        "archived",
    ],
)
def test_nonpublished_status_fails_closed(
    repo,
    status,
):
    SVC.upsert_character(
        character(
            profileStatus=status,
        )
    )

    assert (
        SVC.get_public_profile(
            "prod-secure-a"
        )
        is None
    )


def test_hidden_profile_fails_closed(
    repo,
):
    SVC.upsert_character(
        character(
            visibility="hidden",
        )
    )

    assert (
        SVC.get_public_profile(
            "prod-secure-a"
        )
        is None
    )


def test_disabled_profile_fails_closed(
    repo,
):
    SVC.upsert_character(
        character(
            enabled=False,
        )
    )

    assert (
        SVC.get_public_profile(
            "prod-secure-a"
        )
        is None
    )


def test_archived_flag_fails_closed(
    repo,
):
    SVC.upsert_character(
        character(
            archived=True,
        )
    )

    assert (
        SVC.get_public_profile(
            "prod-secure-a"
        )
        is None
    )


def test_invalid_status_fails_closed(
    repo,
):
    result = SVC.upsert_character(
        character(
            profileStatus="INVALID",
        )
    )

    assert (
        result["profileStatus"]
        == "draft"
    )

    assert (
        SVC.get_public_profile(
            "prod-secure-a"
        )
        is None
    )


def test_invalid_visibility_fails_closed(
    repo,
):
    result = SVC.upsert_character(
        character(
            visibility="INVALID",
        )
    )

    assert (
        result["visibility"]
        == "hidden"
    )

    assert (
        SVC.get_public_profile(
            "prod-secure-a"
        )
        is None
    )


def test_unknown_capability_removed(
    repo,
):
    result = SVC.upsert_character(
        character(
            capabilities={
                "chat": True,
                "unknownDangerousFeature":
                    True,
            }
        )
    )

    assert (
        "unknownDangerousFeature"
        not in result["capabilities"]
    )


def test_unspecified_capabilities_fail_closed(
    repo,
):
    value = character()

    value.pop(
        "capabilities",
        None,
    )

    result = SVC.upsert_character(
        value
    )

    assert all(
        enabled is False
        for enabled
        in result[
            "capabilities"
        ].values()
    )


def test_invalid_tiers_removed(
    repo,
):
    result = SVC.upsert_character(
        character(
            tierAccess=[
                "casual",
                "root",
                "admin",
                "love",
            ]
        )
    )

    assert (
        result["tierAccess"]
        == [
            "casual",
            "love",
        ]
    )


def test_ai_flag_cannot_be_disabled(
    repo,
):
    result = SVC.upsert_character(
        character(
            isAi=False,
            aiDisclosure=False,
        )
    )

    assert result["isAi"] is True

    assert (
        result["aiDisclosure"]
        is True
    )


def test_public_output_does_not_include_created_by(
    repo,
):
    SVC.upsert_character(
        character(
            createdBy=
                "private-admin@example.com",
        )
    )

    result = SVC.get_public_profile(
        "prod-secure-a"
    )

    assert result is not None
    assert "createdBy" not in result


@pytest.mark.parametrize(
    "field",
    [
        "userId",
        "memoryIdsUsed",
        "relationshipState",
        "adaptationState",
        "activeGoal",
        "activePlan",
        "providerSessionId",
        "scopeToken",
        "signedUrl",
    ],
)
def test_user_or_private_state_never_public(
    repo,
    field,
):
    value = character()

    value[field] = {
        "private": True,
    }

    repo.upsert_character(
        value
    )

    result = SVC.get_public_profile(
        "prod-secure-a"
    )

    assert result is not None
    assert field not in result


def test_public_profile_has_ai_disclosure(
    repo,
):
    SVC.upsert_character(
        character()
    )

    result = SVC.get_public_profile(
        "prod-secure-a"
    )

    assert result is not None
    assert result["isAi"] is True
    assert result["aiDisclosure"] is True


def test_public_profile_keeps_character_id(
    repo,
):
    SVC.upsert_character(
        character()
    )

    result = SVC.get_public_profile(
        "prod-secure-a"
    )

    assert result is not None

    assert (
        result["characterId"]
        == "prod-secure-a"
    )


def test_partial_update_does_not_reset_publication(
    repo,
):
    SVC.upsert_character(
        character()
    )

    SVC.upsert_character(
        {
            "characterId":
                "prod-secure-a",
            "profileBio":
                "Updated biography",
        }
    )

    result = SVC.get_public_profile(
        "prod-secure-a"
    )

    assert result is not None

    assert (
        result["profileStatus"]
        == "published"
    )

    assert (
        result["visibility"]
        == "public"
    )


def test_partial_update_preserves_personality(
    repo,
):
    initial = SVC.upsert_character(
        character()
    )

    before = deepcopy(
        initial["personalityTraits"]
    )

    updated = SVC.upsert_character(
        {
            "characterId":
                "prod-secure-a",
            "profileBio":
                "New biography",
        }
    )

    assert (
        updated["personalityTraits"]
        == before
    )


def test_public_list_excludes_draft_hidden_disabled(
    repo,
):
    SVC.upsert_character(
        character(
            "public-a",
        )
    )

    SVC.upsert_character(
        character(
            "draft-a",
            profileStatus="draft",
        )
    )

    SVC.upsert_character(
        character(
            "hidden-a",
            visibility="hidden",
        )
    )

    SVC.upsert_character(
        character(
            "disabled-a",
            enabled=False,
        )
    )

    ids = {
        item["characterId"]
        for item
        in SVC.list_public_profiles()
    }

    assert ids == {
        "public-a",
    }


def test_featured_sorting_is_deterministic(
    repo,
):
    SVC.upsert_character(
        character(
            "normal-a",
            featured=False,
            sortOrder=1,
        )
    )

    SVC.upsert_character(
        character(
            "featured-b",
            featured=True,
            sortOrder=20,
        )
    )

    SVC.upsert_character(
        character(
            "featured-a",
            featured=True,
            sortOrder=10,
        )
    )

    ids = [
        item["characterId"]
        for item
        in SVC.list_public_profiles()
    ]

    assert ids == [
        "featured-a",
        "featured-b",
        "normal-a",
    ]


def test_normalization_is_defensive_copy():
    source = character()

    original = deepcopy(source)

    PROFILE.normalize_profile(
        source
    )

    assert source == original

from copy import deepcopy
from pathlib import Path

import pytest

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


def profile_character(
    character_id,
    **overrides,
):
    value = deepcopy(
        REFERENCE_CHARACTERS[0]
    )

    value["characterId"] = character_id

    value.update(
        {
            "profileStatus": "published",
            "visibility": "public",
            "capabilities": {
                "chat": True,
                "imageUnderstanding": True,
            },
            "avatarUrl":
                "https://example.invalid/a.jpg",
            "avatarThumbnailUrl":
                "https://example.invalid/a-thumb.jpg",
            "relationshipStyle":
                "warm friendship",
            "featured": False,
            "sortOrder": 10,
        }
    )

    value.update(overrides)

    return value


def test_create_persists_profile_metadata(
    repo,
):
    result = SVC.upsert_character(
        profile_character(
            "prod-a",
        ),
        author="admin@example.com",
    )

    stored = repo.get_character(
        "prod-a"
    )

    assert (
        result["profileStatus"]
        == "published"
    )

    assert (
        stored["visibility"]
        == "public"
    )

    assert (
        stored["capabilities"]["chat"]
        is True
    )

    assert (
        stored["relationshipStyle"]
        == "warm friendship"
    )

    assert (
        stored["createdBy"]
        == "admin@example.com"
    )


def test_partial_update_preserves_identity(
    repo,
):
    SVC.upsert_character(
        profile_character(
            "prod-a",
        )
    )

    before = deepcopy(
        repo.get_character(
            "prod-a"
        )
    )

    result = SVC.upsert_character(
        {
            "characterId": "prod-a",
            "profileBio":
                "Updated production bio",
        }
    )

    assert (
        result["displayName"]
        == before["displayName"]
    )

    assert (
        result["languages"]
        == before["languages"]
    )

    assert (
        result["personalityTraits"]
        == before["personalityTraits"]
    )

    assert (
        result["profileStatus"]
        == "published"
    )

    assert (
        result["visibility"]
        == "public"
    )

    assert (
        result["profileBio"]
        == "Updated production bio"
    )


def test_update_preserves_created_at(
    repo,
):
    first = SVC.upsert_character(
        profile_character(
            "prod-a",
        )
    )

    second = SVC.upsert_character(
        {
            "characterId": "prod-a",
            "profileBio": "Changed",
        }
    )

    assert (
        second["createdAt"]
        == first["createdAt"]
    )


def test_ai_transparency_cannot_be_disabled(
    repo,
):
    result = SVC.upsert_character(
        profile_character(
            "prod-a",
            isAi=False,
            aiDisclosure=False,
        )
    )

    assert result["isAi"] is True
    assert result["aiDisclosure"] is True


def test_public_list_only_returns_public(
    repo,
):
    SVC.upsert_character(
        profile_character(
            "public-a",
        )
    )

    SVC.upsert_character(
        profile_character(
            "draft-a",
            profileStatus="draft",
        )
    )

    SVC.upsert_character(
        profile_character(
            "hidden-a",
            visibility="hidden",
        )
    )

    SVC.upsert_character(
        profile_character(
            "disabled-a",
            enabled=False,
        )
    )

    items = SVC.list_public_profiles()

    ids = {
        item["characterId"]
        for item in items
    }

    assert ids == {
        "public-a",
    }


def test_public_get_returns_profile(
    repo,
):
    SVC.upsert_character(
        profile_character(
            "public-a",
        )
    )

    result = SVC.get_public_profile(
        "public-a"
    )

    assert result is not None

    assert (
        result["characterId"]
        == "public-a"
    )

    assert (
        result["aiDisclosure"]
        is True
    )


def test_hidden_profile_fails_closed(
    repo,
):
    SVC.upsert_character(
        profile_character(
            "hidden-a",
            visibility="hidden",
        )
    )

    result = SVC.get_public_profile(
        "hidden-a"
    )

    assert result is None


def test_reference_characters_not_auto_public(
    repo,
):
    assert (
        SVC.list_public_profiles()
        == []
    )

    assert (
        SVC.get_public_profile(
            "ref_ananya"
        )
        is None
    )


def test_public_profile_excludes_user_state(
    repo,
):
    value = profile_character(
        "public-a"
    )

    value["userId"] = "private-user"

    value["relationshipState"] = {
        "state": "comfortable",
    }

    value["memoryIdsUsed"] = [
        "private-memory",
    ]

    repo.upsert_character(value)

    result = SVC.get_public_profile(
        "public-a"
    )

    assert result is not None

    assert "userId" not in result

    assert (
        "relationshipState"
        not in result
    )

    assert (
        "memoryIdsUsed"
        not in result
    )


def test_featured_profiles_sort_first(
    repo,
):
    SVC.upsert_character(
        profile_character(
            "normal-a",
            displayName="Normal",
            featured=False,
            sortOrder=1,
        )
    )

    SVC.upsert_character(
        profile_character(
            "featured-a",
            displayName="Featured",
            featured=True,
            sortOrder=50,
        )
    )

    items = SVC.list_public_profiles()

    assert (
        items[0]["characterId"]
        == "featured-a"
    )


def test_sort_order_within_group(
    repo,
):
    SVC.upsert_character(
        profile_character(
            "second-a",
            sortOrder=20,
        )
    )

    SVC.upsert_character(
        profile_character(
            "first-a",
            sortOrder=10,
        )
    )

    items = SVC.list_public_profiles()

    ids = [
        item["characterId"]
        for item in items
    ]

    assert ids == [
        "first-a",
        "second-a",
    ]


def test_existing_admin_character_routes_preserved():
    source = Path(
        "server.py"
    ).read_text(
        encoding="utf-8-sig"
    )

    assert (
        '@api.get("/ai/characters")'
        in source
    )

    assert (
        '@api.post("/ai/characters")'
        in source
    )

    assert (
        '@api.put("/ai/characters/{cid}")'
        in source
    )


def test_authenticated_profile_list_route():
    source = Path(
        "server.py"
    ).read_text(
        encoding="utf-8-sig"
    )

    assert (
        '@api.get("/ai/profiles")'
        in source
    )

    start = source.index(
        "async def ai_profiles_list"
    )

    section = source[
        start:
        start + 600
    ]

    assert (
        "Depends(get_current_user)"
        in section
    )

    assert (
        "ai_svc.list_public_profiles"
        in section
    )


def test_authenticated_profile_detail_route():
    source = Path(
        "server.py"
    ).read_text(
        encoding="utf-8-sig"
    )

    assert (
        '@api.get("/ai/profiles/{cid}")'
        in source
    )

    start = source.index(
        "async def ai_profile_get"
    )

    section = source[
        start:
        start + 800
    ]

    assert (
        "Depends(get_current_user)"
        in section
    )

    assert (
        "ai_svc.get_public_profile"
        in section
    )

    assert (
        "status_code=404"
        in section
    )

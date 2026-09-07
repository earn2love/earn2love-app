"""
Production AI profile presentation contract.

This module does NOT replace the AI character schema or intelligence engine.

Global AI identity remains stored in aiCharacters.
User memory, relationship, adaptation, goals, plans and conversations remain
separately scoped by the existing AI engine repositories.

This layer normalizes only production-facing profile presentation metadata.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any


PROFILE_VERSION = 1

VALID_PROFILE_STATUSES = {
    "draft",
    "published",
    "paused",
    "archived",
}

VALID_VISIBILITY = {
    "public",
    "hidden",
}

VALID_TIERS = {
    "casual",
    "friendship",
    "love",
}

CAPABILITY_KEYS = (
    "chat",
    "imageUnderstanding",
    "imageCreation",
    "liveKnowledge",
    "playTogether",
)

DEFAULT_CAPABILITIES = {
    key: False
    for key in CAPABILITY_KEYS
}


def _clean_string(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _clean_string_list(value: Any) -> list[str]:
    if not isinstance(value, (list, tuple)):
        return []

    result = []

    for item in value:
        text = _clean_string(item)

        if text and text not in result:
            result.append(text)

    return result


def normalize_capabilities(
    value: Any,
) -> dict[str, bool]:
    incoming = (
        value
        if isinstance(value, dict)
        else {}
    )

    result = dict(DEFAULT_CAPABILITIES)

    for key in CAPABILITY_KEYS:
        if key in incoming:
            result[key] = bool(
                incoming[key]
            )

    return result


def normalize_tier_access(
    value: Any,
) -> list[str]:
    tiers = _clean_string_list(
        value
    )

    return [
        tier
        for tier in tiers
        if tier in VALID_TIERS
    ]


def normalize_profile(
    character: dict[str, Any],
) -> dict[str, Any]:
    """
    Return a defensive copy of one global AI character plus normalized
    production presentation metadata.

    This function does not persist anything.
    """

    if not isinstance(character, dict):
        raise TypeError(
            "character must be a dict"
        )

    character_id = _clean_string(
        character.get(
            "characterId"
        )
    )

    if not character_id:
        raise ValueError(
            "characterId is required"
        )

    display_name = _clean_string(
        character.get(
            "displayName"
        )
    )

    if not display_name:
        raise ValueError(
            "displayName is required"
        )

    result = deepcopy(
        character
    )

    # AI transparency is authoritative.
    result["isAi"] = True
    result["aiDisclosure"] = True

    result["profileVersion"] = int(
        character.get(
            "profileVersion",
            PROFILE_VERSION,
        )
        or PROFILE_VERSION
    )

    status = _clean_string(
        character.get(
            "profileStatus",
            "draft",
        )
    ).lower()

    if status not in VALID_PROFILE_STATUSES:
        status = "draft"

    result["profileStatus"] = status

    visibility = _clean_string(
        character.get(
            "visibility",
            "hidden",
        )
    ).lower()

    if visibility not in VALID_VISIBILITY:
        visibility = "hidden"

    result["visibility"] = visibility

    result["avatarUrl"] = _clean_string(
        character.get(
            "avatarUrl"
        )
    )

    result["avatarThumbnailUrl"] = _clean_string(
        character.get(
            "avatarThumbnailUrl"
        )
    )

    media = character.get(
        "profileMedia"
    )

    if not isinstance(
        media,
        list,
    ):
        media = []

    result["profileMedia"] = deepcopy(
        media
    )

    result["capabilities"] = (
        normalize_capabilities(
            character.get(
                "capabilities"
            )
        )
    )

    result["tierAccess"] = (
        normalize_tier_access(
            character.get(
                "tierAccess"
            )
        )
    )

    result["relationshipStyle"] = (
        _clean_string(
            character.get(
                "relationshipStyle"
            )
        )
    )

    try:
        sort_order = int(
            character.get(
                "sortOrder",
                0,
            )
            or 0
        )
    except (
        TypeError,
        ValueError,
    ):
        sort_order = 0

    result["sortOrder"] = sort_order

    result["featured"] = bool(
        character.get(
            "featured",
            False,
        )
    )

    result["createdBy"] = _clean_string(
        character.get(
            "createdBy"
        )
    )

    result["publishedAt"] = (
        character.get(
            "publishedAt"
        )
    )

    return result


def is_public_profile(
    character: dict[str, Any],
) -> bool:
    profile = normalize_profile(
        character
    )

    return bool(
        profile.get(
            "enabled",
            False,
        )
        and not profile.get(
            "archived",
            False,
        )
        and profile[
            "profileStatus"
        ]
        == "published"
        and profile[
            "visibility"
        ]
        == "public"
    )


def public_profile(
    character: dict[str, Any],
) -> dict[str, Any] | None:
    """
    Return public-safe profile data.

    User-scoped intelligence state is deliberately absent because it never
    belongs to the global profile document.
    """

    profile = normalize_profile(
        character
    )

    if not is_public_profile(
        profile
    ):
        return None

    allowed = (
        "characterId",
        "displayName",
        "isAi",
        "aiDisclosure",
        "genderPresentation",
        "age",
        "country",
        "city",
        "profession",
        "profileBio",
        "languages",
        "interests",
        "hobbies",
        "personalityTraits",
        "communicationStyle",
        "humorStyle",
        "emojiStyle",
        "greetingStyle",
        "avatarUrl",
        "avatarThumbnailUrl",
        "profileMedia",
        "profileStatus",
        "visibility",
        "capabilities",
        "tierAccess",
        "relationshipStyle",
        "sortOrder",
        "featured",
        "profileVersion",
        "version",
        "publishedAt",
    )

    return {
        key: deepcopy(
            profile.get(
                key
            )
        )
        for key in allowed
        if key in profile
    }

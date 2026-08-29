"""
Earn2Love AI Engine V14 - Image Creation Intelligence.

Pure validation/normalization contract.

This module:
- performs no provider calls
- performs no Firestore writes
- performs no Storage writes
- performs no billing mutations
- performs no user-memory persistence

External image provider communication belongs in provider.py.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Optional, Sequence


V14_IMAGE_CREATION_INTELLIGENCE = True

MAX_IMAGE_PROMPT_LENGTH = 4000
MAX_EDIT_INSTRUCTION_LENGTH = 3000
MAX_EDIT_SOURCE_IMAGES = 4

SUPPORTED_IMAGE_SIZES = frozenset(
    {
        "1024x1024",
        "1536x1024",
        "1024x1536",
    }
)

SUPPORTED_IMAGE_QUALITIES = frozenset(
    {
        "low",
        "medium",
        "high",
    }
)

SUPPORTED_BACKGROUND_MODES = frozenset(
    {
        "auto",
        "opaque",
        "transparent",
    }
)


def _clean_text(
    value: Any,
    *,
    field: str,
    max_length: int,
) -> str:
    if not isinstance(value, str):
        raise ValueError(f"invalid_{field}")

    cleaned = " ".join(value.split()).strip()

    if not cleaned:
        raise ValueError(f"invalid_{field}")

    if len(cleaned) > max_length:
        raise ValueError(f"{field}_too_long")

    return cleaned


def _normalize_choice(
    value: Any,
    *,
    field: str,
    allowed: frozenset[str],
    default: str,
) -> str:
    if value is None:
        return default

    if not isinstance(value, str):
        raise ValueError(f"invalid_{field}")

    cleaned = value.strip().casefold()

    if cleaned not in allowed:
        raise ValueError(f"invalid_{field}")

    return cleaned


def _normalize_source_image_ids(
    values: Optional[Sequence[Any]],
) -> tuple[str, ...]:
    if values is None:
        return ()

    if isinstance(values, (str, bytes)):
        raise ValueError("invalid_source_image_ids")

    if not isinstance(values, (list, tuple)):
        raise ValueError("invalid_source_image_ids")

    if len(values) > MAX_EDIT_SOURCE_IMAGES:
        raise ValueError("too_many_source_images")

    normalized: list[str] = []
    seen: set[str] = set()

    for raw in values:
        if not isinstance(raw, str):
            raise ValueError("invalid_source_image_id")

        # Image IDs are opaque identifiers. Never case-normalize them.
        image_id = raw.strip()

        if not image_id:
            raise ValueError("invalid_source_image_id")

        if image_id in seen:
            raise ValueError("duplicate_source_image_id")

        seen.add(image_id)
        normalized.append(image_id)

    return tuple(normalized)


@dataclass(frozen=True)
class ImageCreationRequest:
    prompt: str
    size: str = "1024x1024"
    quality: str = "medium"
    background: str = "auto"

    @classmethod
    def from_input(
        cls,
        *,
        prompt: Any,
        size: Any = None,
        quality: Any = None,
        background: Any = None,
    ) -> "ImageCreationRequest":
        return cls(
            prompt=_clean_text(
                prompt,
                field="image_prompt",
                max_length=MAX_IMAGE_PROMPT_LENGTH,
            ),
            size=_normalize_choice(
                size,
                field="image_size",
                allowed=SUPPORTED_IMAGE_SIZES,
                default="1024x1024",
            ),
            quality=_normalize_choice(
                quality,
                field="image_quality",
                allowed=SUPPORTED_IMAGE_QUALITIES,
                default="medium",
            ),
            background=_normalize_choice(
                background,
                field="image_background",
                allowed=SUPPORTED_BACKGROUND_MODES,
                default="auto",
            ),
        )


@dataclass(frozen=True)
class ImageEditRequest:
    instruction: str
    source_image_ids: tuple[str, ...]
    size: str = "1024x1024"
    quality: str = "medium"
    background: str = "auto"

    @classmethod
    def from_input(
        cls,
        *,
        instruction: Any,
        source_image_ids: Optional[Sequence[Any]],
        size: Any = None,
        quality: Any = None,
        background: Any = None,
    ) -> "ImageEditRequest":
        sources = _normalize_source_image_ids(
            source_image_ids
        )

        if not sources:
            raise ValueError("source_image_required")

        return cls(
            instruction=_clean_text(
                instruction,
                field="edit_instruction",
                max_length=MAX_EDIT_INSTRUCTION_LENGTH,
            ),
            source_image_ids=sources,
            size=_normalize_choice(
                size,
                field="image_size",
                allowed=SUPPORTED_IMAGE_SIZES,
                default="1024x1024",
            ),
            quality=_normalize_choice(
                quality,
                field="image_quality",
                allowed=SUPPORTED_IMAGE_QUALITIES,
                default="medium",
            ),
            background=_normalize_choice(
                background,
                field="image_background",
                allowed=SUPPORTED_BACKGROUND_MODES,
                default="auto",
            ),
        )


def normalize_creation_result(
    value: Mapping[str, Any],
) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError("invalid_image_creation_result")

    image_bytes = value.get("imageBytes")
    mime_type = value.get("mimeType")

    if not isinstance(image_bytes, (bytes, bytearray)):
        raise ValueError("missing_generated_image")

    if not image_bytes:
        raise ValueError("missing_generated_image")

    if mime_type != "image/png":
        raise ValueError("invalid_generated_image_mime")

    revised_prompt = value.get("revisedPrompt")

    if revised_prompt is not None:
        if not isinstance(revised_prompt, str):
            raise ValueError("invalid_revised_prompt")

        revised_prompt = revised_prompt.strip() or None

    return {
        "imageBytes": bytes(image_bytes),
        "mimeType": "image/png",
        "revisedPrompt": revised_prompt,
    }


def image_creation_policy() -> dict[str, Any]:
    return {
        "version": "V14",
        "providerBoundary": "provider.py",
        "persistentUserMemory": False,
        "providerResultPersistence": False,
        "privateTemporaryStorage": True,
        "billingAuthority": "backend_only",
        "sourceImageIdsOpaque": True,
        "maxEditSourceImages": MAX_EDIT_SOURCE_IMAGES,
        "supportedSizes": sorted(SUPPORTED_IMAGE_SIZES),
        "supportedQualities": sorted(SUPPORTED_IMAGE_QUALITIES),
        "supportedBackgrounds": sorted(SUPPORTED_BACKGROUND_MODES),
    }

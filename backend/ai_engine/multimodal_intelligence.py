"""
V13.1 Multimodal Input Intelligence.

Pure deterministic validation and scope construction for image
understanding.

This layer:
- performs no provider calls;
- performs no Firestore/database writes;
- does not mutate personality, adaptation, goals, plans, relationship,
  or memory;
- does not fetch arbitrary URLs;
- does not store image bytes;
- keeps image context conversation-scoped and ephemeral by default.

Actual external vision-provider communication remains exclusively in
provider.py.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from typing import Any
from urllib.parse import urlparse


MULTIMODAL_VERSION = 13

MAX_IMAGES_PER_TURN = 4
MAX_IMAGE_ID_LENGTH = 128
MAX_IMAGE_URL_LENGTH = 4096
MAX_USER_TEXT_LENGTH = 20000

ALLOWED_DETAILS = frozenset(
    {
        "auto",
        "low",
        "high",
    }
)

ALLOWED_MIME_TYPES = frozenset(
    {
        "image/jpeg",
        "image/jpg",
        "image/png",
        "image/webp",
        "image/gif",
    }
)


@dataclass(
    frozen=True
)
class ImageReference:
    image_id: str
    source_type: str
    image_url: str = ""
    file_id: str = ""
    detail: str = "auto"
    mime_type: str = ""

    def provider_payload(
        self,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "type": "input_image",
            "detail": self.detail,
        }

        if self.source_type == "url":
            payload["image_url"] = self.image_url
        else:
            payload["file_id"] = self.file_id

        return payload

    def safe_dict(
        self,
    ) -> dict[str, Any]:
        """
        Safe observability metadata.

        The actual signed URL / provider file ID is intentionally excluded.
        """
        return {
            "imageId": self.image_id,
            "sourceType": self.source_type,
            "detail": self.detail,
            "mimeType": self.mime_type or None,
        }


@dataclass(
    frozen=True
)
class MultimodalTurnContext:
    ok: bool
    scope_token: str
    user_text: str
    images: tuple[ImageReference, ...]
    error: str | None = None

    @property
    def has_images(
        self,
    ) -> bool:
        return bool(
            self.images
        )

    @property
    def image_count(
        self,
    ) -> int:
        return len(
            self.images
        )

    def provider_images(
        self,
    ) -> list[dict[str, Any]]:
        return [
            image.provider_payload()
            for image in self.images
        ]

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "version": MULTIMODAL_VERSION,
            "ok": self.ok,
            "scopeToken": self.scope_token,
            "hasImages": self.has_images,
            "imageCount": self.image_count,
            "images": [
                image.safe_dict()
                for image in self.images
            ],
            "error": self.error,
            "ephemeralContextOnly": True,
            "persistImageBytes": False,
            "persistVisualAnalysis": False,
        }


def _clean(
    value,
) -> str:
    return " ".join(
        str(
            value
            or ""
        ).strip().split()
    )


def build_scope_token(
    character_id,
    user_id,
    conversation_id,
) -> str:
    """
    Ephemeral scope identity.

    Includes character + user + conversation so two users or two
    conversations can never share a V13 image-context scope token.
    """
    cid = _clean(
        character_id
    )

    uid = _clean(
        user_id
    )

    conversation = _clean(
        conversation_id
    )

    if not cid:
        raise ValueError(
            "character_id_required"
        )

    if not uid:
        raise ValueError(
            "user_id_required"
        )

    if not conversation:
        raise ValueError(
            "conversation_id_required"
        )

    raw = (
        cid
        + "\x00"
        + uid
        + "\x00"
        + conversation
    ).encode(
        "utf-8"
    )

    return hashlib.sha256(
        raw
    ).hexdigest()[:24]


def _validate_https_url(
    value,
) -> str:
    url = str(
        value
        or ""
    ).strip()

    if not url:
        raise ValueError(
            "image_url_required"
        )

    if len(
        url
    ) > MAX_IMAGE_URL_LENGTH:
        raise ValueError(
            "image_url_too_long"
        )

    parsed = urlparse(
        url
    )

    if (
        parsed.scheme.casefold()
        != "https"
    ):
        raise ValueError(
            "image_url_must_use_https"
        )

    if not parsed.hostname:
        raise ValueError(
            "image_url_missing_host"
        )

    if (
        parsed.username
        or parsed.password
    ):
        raise ValueError(
            "image_url_credentials_forbidden"
        )

    return url


def _validate_file_id(
    value,
) -> str:
    file_id = str(
        value
        or ""
    ).strip()

    if not file_id:
        raise ValueError(
            "file_id_required"
        )

    if len(
        file_id
    ) > 256:
        raise ValueError(
            "file_id_too_long"
        )

    if not file_id.startswith(
        "file-"
    ):
        raise ValueError(
            "invalid_provider_file_id"
        )

    return file_id


def normalize_image_reference(
    raw,
) -> ImageReference:
    if not isinstance(
        raw,
        dict,
    ):
        raise ValueError(
            "image_reference_must_be_object"
        )

    image_id = _clean(
        raw.get(
            "imageId"
        )
        or raw.get(
            "image_id"
        )
    )

    if not image_id:
        raise ValueError(
            "image_id_required"
        )

    if len(
        image_id
    ) > MAX_IMAGE_ID_LENGTH:
        raise ValueError(
            "image_id_too_long"
        )

    detail = _clean(
        raw.get(
            "detail",
            "auto",
        )
    ).casefold()

    if detail not in ALLOWED_DETAILS:
        raise ValueError(
            "invalid_image_detail"
        )

    mime_type = _clean(
        raw.get(
            "mimeType"
        )
        or raw.get(
            "mime_type"
        )
    ).casefold()

    if (
        mime_type
        and mime_type
        not in ALLOWED_MIME_TYPES
    ):
        raise ValueError(
            "unsupported_image_mime_type"
        )

    raw_url = (
        raw.get(
            "url"
        )
        or raw.get(
            "imageUrl"
        )
        or raw.get(
            "image_url"
        )
    )

    raw_file_id = (
        raw.get(
            "fileId"
        )
        or raw.get(
            "file_id"
        )
    )

    has_url = bool(
        str(
            raw_url
            or ""
        ).strip()
    )

    has_file = bool(
        str(
            raw_file_id
            or ""
        ).strip()
    )

    if (
        has_url
        and has_file
    ):
        raise ValueError(
            "multiple_image_sources_forbidden"
        )

    if not (
        has_url
        or has_file
    ):
        raise ValueError(
            "image_source_required"
        )

    if has_url:
        return ImageReference(
            image_id=image_id,
            source_type="url",
            image_url=_validate_https_url(
                raw_url
            ),
            detail=detail,
            mime_type=mime_type,
        )

    return ImageReference(
        image_id=image_id,
        source_type="file_id",
        file_id=_validate_file_id(
            raw_file_id
        ),
        detail=detail,
        mime_type=mime_type,
    )


def normalize_image_inputs(
    raw_images,
    *,
    max_images=MAX_IMAGES_PER_TURN,
) -> tuple[ImageReference, ...]:
    if raw_images is None:
        return ()

    if not isinstance(
        raw_images,
        (
            list,
            tuple,
        ),
    ):
        raise ValueError(
            "image_inputs_must_be_list"
        )

    if len(
        raw_images
    ) > int(
        max_images
    ):
        raise ValueError(
            "too_many_images"
        )

    normalized = tuple(
        normalize_image_reference(
            item
        )
        for item in raw_images
    )

    image_ids = [
        image.image_id
        for image in normalized
    ]

    if len(
        image_ids
    ) != len(
        set(
            image_ids
        )
    ):
        raise ValueError(
            "duplicate_image_id"
        )

    return normalized


def build_turn_context(
    character_id,
    user_id,
    conversation_id,
    user_text,
    image_inputs=None,
) -> MultimodalTurnContext:
    try:
        scope_token = build_scope_token(
            character_id,
            user_id,
            conversation_id,
        )

        text = str(
            user_text
            or ""
        ).strip()

        if len(
            text
        ) > MAX_USER_TEXT_LENGTH:
            raise ValueError(
                "user_text_too_long"
            )

        images = normalize_image_inputs(
            image_inputs
        )

        return MultimodalTurnContext(
            ok=True,
            scope_token=scope_token,
            user_text=text,
            images=images,
            error=None,
        )

    except ValueError as exc:
        return MultimodalTurnContext(
            ok=False,
            scope_token="",
            user_text=str(
                user_text
                or ""
            ).strip()[
                :MAX_USER_TEXT_LENGTH
            ],
            images=(),
            error=str(
                exc
            ),
        )


def build_multimodal_directive(
    context: MultimodalTurnContext,
) -> str:
    if not context.ok:
        return (
            "V13 multimodal input is invalid. "
            "Do not claim to have inspected an image."
        )

    if not context.has_images:
        return (
            "No V13 image input is attached to this turn."
        )

    return (
        "V13 multimodal image-understanding context is available for "
        f"{context.image_count} image(s). "
        "Describe only visual details actually supported by the supplied "
        "images. If a visual detail is unclear, say that it is unclear "
        "instead of inventing it. Treat image context as scoped to the "
        "current character, user, and conversation. Do not assume an image "
        "belongs to another conversation. Do not persist raw image bytes or "
        "visual analysis as long-term user memory merely because an image "
        "was supplied. Existing V11 rules remain authoritative for any "
        "explicit durable personal fact."
    )


def multimodal_memory_policy() -> dict[str, bool]:
    return {
        "persistImageBytes": False,
        "persistVisualAnalysis": False,
        "ephemeralContextOnly": True,
        "existingMemoryRulesRemainAuthoritative": True,
    }


MAX_VISUAL_SUMMARY_LENGTH = 6000


def normalize_visual_summary(
    value,
) -> str:
    """
    Normalize provider-derived visual evidence before it reaches the
    CharacterEngine system context.

    The result is ephemeral conversation input, not durable V11 memory.
    """
    summary = str(
        value
        or ""
    ).strip()

    if not summary:
        raise ValueError(
            "empty_visual_summary"
        )

    if len(
        summary
    ) > MAX_VISUAL_SUMMARY_LENGTH:
        summary = summary[
            :MAX_VISUAL_SUMMARY_LENGTH
        ].rstrip()

    return summary


def build_grounded_visual_context(
    visual_summary,
    *,
    image_count,
    scope_token="",
) -> str:
    """
    Produce safe V13 context for CharacterEngine.

    This is observation context only. It must never be represented as
    hidden reasoning or automatically written into user memory.
    """
    summary = normalize_visual_summary(
        visual_summary
    )

    count = int(
        image_count
        or 0
    )

    if count <= 0:
        raise ValueError(
            "visual_image_count_required"
        )

    scope = str(
        scope_token
        or ""
    ).strip()

    parts = [
        "V13 multimodal visual evidence is available for this turn.",
        f"Attached image count: {count}.",
        (
            "The following text is an ephemeral provider-derived visual "
            "observation grounded in the authenticated image input:"
        ),
        summary,
        (
            "Use only visual claims supported by that observation. "
            "Do not invent unseen details."
        ),
        (
            "Do not treat the visual observation itself as a durable "
            "personal memory, preference, relationship fact, goal, or plan."
        ),
        (
            "Do not expose internal provider, storage, signed-URL, scope-token, "
            "or multimodal pipeline details to the user."
        ),
    ]

    if scope:
        parts.append(
            "Image context has already been verified as scoped to the "
            "current character, authenticated user, and conversation."
        )

    return "\n".join(
        parts
    )


# ---------------------------------------------------------------------------
# V13.4 conversation-scoped image continuity
# ---------------------------------------------------------------------------

MAX_CONTINUITY_LOOKBACK_TURNS = 12

_IMAGE_REFERENCE_PHRASES = (
    "same image",
    "same photo",
    "same picture",
    "that image",
    "that photo",
    "that picture",
    "this image",
    "this photo",
    "this picture",
    "the image",
    "the photo",
    "the picture",
    "previous image",
    "previous photo",
    "previous picture",
    "last image",
    "last photo",
    "last picture",
    "uploaded image",
    "uploaded photo",
    "uploaded picture",
    "ee image",
    "ee photo",
    "ee picture",
    "aa image",
    "aa photo",
    "aa picture",
    "ade image",
    "ade photo",
    "ade picture",
)

_VISUAL_FOLLOWUP_PHRASES = (
    "left side",
    "right side",
    "top side",
    "bottom side",
    "background",
    "foreground",
    "behind",
    "in front",
    "what is shown",
    "what do you see",
    "what's shown",
    "whats shown",
    "what is visible",
    "what's visible",
    "whats visible",
    "who is there",
    "what is there",
    "enti",
    "em undi",
    "emundi",
    "em vundi",
    "emvundi",
    "kanipistundi",
    "kanipisthundi",
)


def is_image_followup_reference(
    user_text,
) -> bool:
    """
    Conservative V13.4 image-continuity detector.

    Continuity activates only when the user explicitly refers to an
    image-like object. Generic conversational/deictic phrases such as
    "enti?", "background", "left side", "right side", "that", or
    "same thing" are intentionally insufficient on their own.

    This prevents ordinary conversation from unexpectedly reusing an
    earlier image.
    """
    value = " ".join(
        str(
            user_text
            or ""
        ).strip().casefold().split()
    )

    if not value:
        return False

    # Explicit visual-object nouns are authoritative.
    image_nouns = (
        "image",
        "photo",
        "picture",
        "pic",
        "screenshot",
        "photograph",
    )

    words = {
        token.strip(
            ".,!?;:()[]{}\"'"
        )
        for token in value.split()
    }

    if any(
        noun in words
        for noun in image_nouns
    ):
        return True

    # Common compounds / plural variants that token stripping alone
    # may not represent consistently.
    explicit_phrases = (
        "same image",
        "same photo",
        "same picture",
        "same pic",
        "same screenshot",
        "previous image",
        "previous photo",
        "previous picture",
        "previous pic",
        "previous screenshot",
        "last image",
        "last photo",
        "last picture",
        "last pic",
        "last screenshot",
        "that image",
        "that photo",
        "that picture",
        "that pic",
        "that screenshot",
        "this image",
        "this photo",
        "this picture",
        "this pic",
        "this screenshot",
        "ee image",
        "ee photo",
        "ee picture",
        "ee pic",
        "aa image",
        "aa photo",
        "aa picture",
        "aa pic",
        "uploaded image",
        "uploaded photo",
        "uploaded picture",
        "attached image",
        "attached photo",
        "attached picture",
        "images",
        "photos",
        "pictures",
        "screenshots",
    )

    return any(
        phrase in value
        for phrase in explicit_phrases
    )


def extract_turn_image_ids(
    turns,
    *,
    max_images=MAX_IMAGES_PER_TURN,
):
    """
    Return image IDs from the newest qualifying user turn only.

    Turn ordering is expected oldest -> newest, matching repository
    get_turns(). The IDs remain opaque references; no visual summary
    or URL is accepted here.
    """
    if not isinstance(
        turns,
        (
            list,
            tuple,
        ),
    ):
        return []

    limit = max(
        1,
        min(
            int(
                max_images
                or MAX_IMAGES_PER_TURN
            ),
            MAX_IMAGES_PER_TURN,
        ),
    )

    for turn in reversed(
        list(
            turns
        )
    ):
        if not isinstance(
            turn,
            dict,
        ):
            continue

        sender = str(
            turn.get(
                "sender",
                ""
            )
            or ""
        ).strip().casefold()

        if sender not in {
            "user",
            "human",
        }:
            continue

        raw = turn.get(
            "imageIds"
        )

        if not isinstance(
            raw,
            (
                list,
                tuple,
            ),
        ):
            continue

        cleaned = []

        for value in raw:
            image_id = str(
                value
                or ""
            ).strip()

            if not image_id:
                continue

            if image_id in cleaned:
                continue

            cleaned.append(
                image_id
            )

            if len(
                cleaned
            ) >= limit:
                break

        if cleaned:
            return cleaned

    return []


def continuity_policy():
    return {
        "version": 13,
        "conversationScoped": True,
        "userScoped": True,
        "characterScoped": True,
        "persistImageIdsOnly": True,
        "persistVisualSummary": False,
        "persistSignedUrls": False,
        "persistImageBytes": False,
        "reanalyzeActualImage": True,
        "failClosedIfUnavailable": True,
        "lookbackTurns":
            MAX_CONTINUITY_LOOKBACK_TURNS,
    }

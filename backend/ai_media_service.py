
"""
V13.2 authenticated temporary image-storage service.

Production security properties:
- Firebase-authenticated UID is supplied by server.py, never trusted from
  request form/body data.
- Uploads pass server-side byte, MIME, image-format and dimension checks.
- Client cannot choose the Firebase Storage object path.
- Object paths are scoped by authenticated user + character + conversation.
- Raw character/conversation identifiers are hashed in the Storage path.
- Objects are private temporary media; no public URL is created.
- Signed provider URLs are generated server-side only and are short lived.
- Uploaded image bytes are not Firestore memory.
- No new Firestore collection is created.
"""

from __future__ import annotations
import logging

import asyncio
from datetime import datetime, timedelta, timezone
import hashlib
from io import BytesIO
import os
import re
import uuid
import warnings

from PIL import Image

import firebase_service as fb



logger = logging.getLogger(__name__)
MEDIA_VERSION = 13

MAX_IMAGE_BYTES = int(
    os.environ.get(
        "AI_IMAGE_MAX_BYTES",
        str(
            10
            * 1024
            * 1024
        ),
    )
)

MAX_IMAGE_DIMENSION = int(
    os.environ.get(
        "AI_IMAGE_MAX_DIMENSION",
        "8192",
    )
)

MAX_IMAGE_PIXELS = int(
    os.environ.get(
        "AI_IMAGE_MAX_PIXELS",
        "36000000",
    )
)

TEMP_MEDIA_TTL_SECONDS = int(
    os.environ.get(
        "AI_IMAGE_TEMP_TTL_SECONDS",
        "86400",
    )
)

SIGNED_URL_TTL_SECONDS = int(
    os.environ.get(
        "AI_IMAGE_SIGNED_URL_TTL_SECONDS",
        "300",
    )
)

STORAGE_ROOT = "ai-chat-media"

FORMAT_TO_MIME = {
    "JPEG": "image/jpeg",
    "PNG": "image/png",
    "WEBP": "image/webp",
    "GIF": "image/gif",
}

FORMAT_TO_EXTENSION = {
    "JPEG": ".jpg",
    "PNG": ".png",
    "WEBP": ".webp",
    "GIF": ".gif",
}

_SAFE_IMAGE_ID = re.compile(
    r"^[0-9a-f]{32}\.(?:jpg|png|webp|gif)$"
)


def _now():
    return datetime.now(
        timezone.utc
    )


def _iso(
    value,
):
    return value.astimezone(
        timezone.utc
    ).isoformat()


def _scope_hash(
    value,
):
    normalized = str(
        value
        or ""
    ).strip()

    if not normalized:
        raise ValueError(
            "media_scope_required"
        )

    return hashlib.sha256(
        normalized.encode(
            "utf-8"
        )
    ).hexdigest()[:20]


def _validate_uid(
    user_id,
):
    uid = str(
        user_id
        or ""
    ).strip()

    if not uid:
        raise ValueError(
            "authenticated_user_required"
        )

    if (
        "/" in uid
        or "\\" in uid
        or len(
            uid
        ) > 256
    ):
        raise ValueError(
            "invalid_authenticated_user"
        )

    return uid


def _normalize_conversation_id(
    value,
):
    return str(
        value
        or "default"
    ).strip() or "default"


def _object_prefix(
    user_id,
    character_id,
    conversation_id,
):
    uid = _validate_uid(
        user_id
    )

    return (
        f"{STORAGE_ROOT}/"
        f"{_scope_hash(uid)}/"
        f"{_scope_hash(character_id)}/"
        f"{_scope_hash(_normalize_conversation_id(conversation_id))}"
    )


def _object_name(
    user_id,
    character_id,
    conversation_id,
    image_id,
):
    image_id = str(
        image_id
        or ""
    ).strip().casefold()

    if not _SAFE_IMAGE_ID.fullmatch(
        image_id
    ):
        raise ValueError(
            "invalid_image_id"
        )

    return (
        _object_prefix(
            user_id,
            character_id,
            conversation_id,
        )
        + "/"
        + image_id
    )


def _inspect_image_bytes(
    data,
):
    if not isinstance(
        data,
        bytes,
    ):
        raise ValueError(
            "invalid_image_bytes"
        )

    if not data:
        raise ValueError(
            "empty_image"
        )

    if len(
        data
    ) > MAX_IMAGE_BYTES:
        raise ValueError(
            "image_too_large"
        )

    try:
        with warnings.catch_warnings():
            warnings.simplefilter(
                "error",
                Image.DecompressionBombWarning,
            )

            with Image.open(
                BytesIO(
                    data
                )
            ) as probe:
                detected_format = str(
                    probe.format
                    or ""
                ).upper()

                width, height = (
                    probe.size
                )

                is_animated = bool(
                    getattr(
                        probe,
                        "is_animated",
                        False,
                    )
                )

                frame_count = int(
                    getattr(
                        probe,
                        "n_frames",
                        1,
                    )
                    or 1
                )

                probe.verify()

    except (
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
    ):
        raise ValueError(
            "image_dimensions_unsafe"
        )

    except Exception as exc:
        raise ValueError(
            "invalid_image_content"
        ) from exc

    if (
        detected_format
        not in FORMAT_TO_MIME
    ):
        raise ValueError(
            "unsupported_image_format"
        )

    if (
        width <= 0
        or height <= 0
    ):
        raise ValueError(
            "invalid_image_dimensions"
        )

    if (
        width > MAX_IMAGE_DIMENSION
        or height > MAX_IMAGE_DIMENSION
        or (
            width
            * height
        ) > MAX_IMAGE_PIXELS
    ):
        raise ValueError(
            "image_dimensions_too_large"
        )

    # Animated GIFs are deliberately rejected in V13.
    # They can have disproportionate decode/provider cost and ambiguous
    # frame semantics. Static GIF remains supported.
    if (
        detected_format == "GIF"
        and (
            is_animated
            or frame_count > 1
        )
    ):
        raise ValueError(
            "animated_gif_not_supported"
        )

    return {
        "format": detected_format,
        "mimeType":
            FORMAT_TO_MIME[
                detected_format
            ],
        "extension":
            FORMAT_TO_EXTENSION[
                detected_format
            ],
        "width": int(
            width
        ),
        "height": int(
            height
        ),
        "sizeBytes": len(
            data
        ),
    }


async def _read_upload(
    upload,
):
    if upload is None:
        raise ValueError(
            "image_required"
        )

    data = await upload.read(
        MAX_IMAGE_BYTES
        + 1
    )

    if len(
        data
    ) > MAX_IMAGE_BYTES:
        raise ValueError(
            "image_too_large"
        )

    return data


def _metadata_matches_scope(
    metadata,
    *,
    user_id,
    character_id,
    conversation_id,
):
    metadata = metadata or {}

    return (
        metadata.get(
            "ownerUid"
        )
        == _validate_uid(
            user_id
        )
        and metadata.get(
            "characterScope"
        )
        == _scope_hash(
            character_id
        )
        and metadata.get(
            "conversationScope"
        )
        == _scope_hash(
            _normalize_conversation_id(
                conversation_id
            )
        )
        and metadata.get(
            "temporary"
        )
        == "true"
        and metadata.get(
            "v13Media"
        )
        == "true"
    )


def _parse_created_at(
    metadata,
):
    raw = str(
        (
            metadata
            or {}
        ).get(
            "createdAt",
            "",
        )
        or ""
    ).strip()

    if not raw:
        return None

    try:
        value = datetime.fromisoformat(
            raw.replace(
                "Z",
                "+00:00",
            )
        )

        if value.tzinfo is None:
            value = value.replace(
                tzinfo=timezone.utc
            )

        return value.astimezone(
            timezone.utc
        )

    except Exception:
        return None


def _expired(
    metadata,
    *,
    now=None,
):
    created = _parse_created_at(
        metadata
    )

    if created is None:
        return True

    clock = (
        now
        or _now()
    )

    age = (
        clock
        - created
    ).total_seconds()

    return (
        age < -300
        or age
        > TEMP_MEDIA_TTL_SECONDS
    )


async def cleanup_expired_media(
    *,
    max_objects=250,
):
    """
    Physically delete expired V13 temporary media.

    This is a bounded server-side maintenance operation.
    It never trusts a client-supplied object path and does not
    create persistent user state.
    """
    try:
        limit = int(
            max_objects
        )
    except Exception:
        limit = 250

    limit = max(
        1,
        min(
            limit,
            1000,
        ),
    )

    bucket = fb.get_bucket()

    deleted = 0
    inspected = 0

    def _list():
        return list(
            bucket.list_blobs(
                prefix=
                    f"{STORAGE_ROOT}/",
                max_results=limit,
            )
        )

    blobs = await asyncio.to_thread(
        _list
    )

    for blob in blobs:
        if inspected >= limit:
            break

        inspected += 1

        try:
            await asyncio.to_thread(
                blob.reload
            )

            metadata = (
                blob.metadata
                or {}
            )

            if (
                str(
                    metadata.get(
                        "v13Media",
                        "",
                    )
                ).casefold()
                != "true"
            ):
                continue

            if (
                str(
                    metadata.get(
                        "temporary",
                        "",
                    )
                ).casefold()
                != "true"
            ):
                continue

            if not _expired(
                metadata
            ):
                continue

            await asyncio.to_thread(
                blob.delete
            )

            deleted += 1

        except Exception:
            # Cleanup is maintenance. One malformed/unavailable
            # object must not prevent other expired objects from
            # being inspected.
            continue

    return {
        "ok": True,
        "version": MEDIA_VERSION,
        "inspected": inspected,
        "deleted": deleted,
        "bounded": True,
    }


PHYSICAL_DELETE_AFTER_DAYS = int(
    os.environ.get(
        "AI_MEDIA_PHYSICAL_DELETE_AFTER_DAYS",
        2,
    )
)

if PHYSICAL_DELETE_AFTER_DAYS < 1:
    PHYSICAL_DELETE_AFTER_DAYS = 1


def _is_media_lifecycle_rule(
    rule,
):
    """
    Return True only for the V13 temporary-media delete lifecycle rule.

    Existing unrelated bucket lifecycle rules are never considered
    equivalent and are never removed.
    """
    if not isinstance(
        rule,
        dict,
    ):
        return False

    action = (
        rule.get(
            "action"
        )
        or {}
    )

    condition = (
        rule.get(
            "condition"
        )
        or {}
    )

    if str(
        action.get(
            "type"
        )
        or ""
    ).casefold() != "delete":
        return False

    try:
        age = int(
            condition.get(
                "age"
            )
        )
    except (
        TypeError,
        ValueError,
    ):
        return False

    prefixes = (
        condition.get(
            "matchesPrefix"
        )
        or condition.get(
            "matches_prefix"
        )
        or []
    )

    if isinstance(
        prefixes,
        str,
    ):
        prefixes = [
            prefixes
        ]

    return (
        age
        == PHYSICAL_DELETE_AFTER_DAYS
        and STORAGE_ROOT + "/"
        in {
            str(value)
            for value in prefixes
        }
    )


async def ensure_media_lifecycle_policy():
    """
    Ensure Firebase/GCS has a physical-delete lifecycle rule for
    V13 temporary media.

    This is idempotent and preserves all existing bucket lifecycle
    rules. Uploads fail closed if the lifecycle guarantee cannot be
    verified or configured.
    """
    bucket = fb.get_bucket()

    try:
        await asyncio.to_thread(
            bucket.reload
        )

        rules = list(
            bucket.lifecycle_rules
            or []
        )

        if any(
            _is_media_lifecycle_rule(
                rule
            )
            for rule in rules
        ):
            return {
                "ok": True,
                "configured": True,
                "created": False,
                "physicalDeleteAfterDays":
                    PHYSICAL_DELETE_AFTER_DAYS,
                "prefix":
                    STORAGE_ROOT + "/",
            }

        # google-cloud-storage appends this rule to the existing
        # in-memory lifecycle configuration. No existing rules are
        # removed or replaced.
        bucket.add_lifecycle_delete_rule(
            age=
                PHYSICAL_DELETE_AFTER_DAYS,
            matches_prefix=[
                STORAGE_ROOT + "/"
            ],
        )

        await asyncio.to_thread(
            bucket.patch
        )

        # Verify after persistence rather than assuming patch success.
        await asyncio.to_thread(
            bucket.reload
        )

        verified_rules = list(
            bucket.lifecycle_rules
            or []
        )

        if not any(
            _is_media_lifecycle_rule(
                rule
            )
            for rule in verified_rules
        ):
            raise RuntimeError(
                "media_lifecycle_verification_failed"
            )

        return {
            "ok": True,
            "configured": True,
            "created": True,
            "physicalDeleteAfterDays":
                PHYSICAL_DELETE_AFTER_DAYS,
            "prefix":
                STORAGE_ROOT + "/",
        }

    except RuntimeError:
        raise

    except Exception as exc:
        logger.warning(
            "AI media lifecycle guarantee unavailable: %s: %s",
            type(exc).__name__,
            exc,
        )

        raise RuntimeError(
            "media_lifecycle_unavailable"
        ) from exc

async def upload_image(
    upload,
    *,
    user_id,
    character_id,
    conversation_id="default",
):
    """
    Store one validated private temporary image.

    No public or signed URL is returned to the client.
    """

    # Physical cleanup is a prerequisite for accepting
    # temporary user media. Fail closed if GCS lifecycle
    # cannot be verified/configured.
    await ensure_media_lifecycle_policy()

    uid = _validate_uid(
        user_id
    )

    character_id = str(
        character_id
        or ""
    ).strip()

    if not character_id:
        raise ValueError(
            "character_id_required"
        )

    conversation_id = (
        _normalize_conversation_id(
            conversation_id
        )
    )

    data = await _read_upload(
        upload
    )

    inspected = await asyncio.to_thread(
        _inspect_image_bytes,
        data,
    )

    image_id = (
        uuid.uuid4().hex
        + inspected[
            "extension"
        ]
    )

    object_name = _object_name(
        uid,
        character_id,
        conversation_id,
        image_id,
    )

    bucket = fb.get_bucket()

    blob = bucket.blob(
        object_name
    )

    created_at = _now()

    blob.metadata = {
        "v13Media": "true",
        "temporary": "true",
        "ownerUid": uid,
        "characterScope":
            _scope_hash(
                character_id
            ),
        "conversationScope":
            _scope_hash(
                conversation_id
            ),
        "createdAt":
            _iso(
                created_at
            ),
        "expiresAt":
            _iso(
                created_at
                + timedelta(
                    seconds=
                        TEMP_MEDIA_TTL_SECONDS
                )
            ),
        "detectedMimeType":
            inspected[
                "mimeType"
            ],
        "width":
            str(
                inspected[
                    "width"
                ]
            ),
        "height":
            str(
                inspected[
                    "height"
                ]
            ),
    }

    blob.cache_control = (
        "private, no-store, max-age=0"
    )

    await asyncio.to_thread(
        blob.upload_from_string,
        data,
        content_type=
            inspected[
                "mimeType"
            ],
    )

    return {
        "ok": True,
        "version": MEDIA_VERSION,
        "imageId": image_id,
        "contentType":
            inspected[
                "mimeType"
            ],
        "width":
            inspected[
                "width"
            ],
        "height":
            inspected[
                "height"
            ],
        "sizeBytes":
            inspected[
                "sizeBytes"
            ],
        "temporary": True,
        "expiresAt":
            blob.metadata[
                "expiresAt"
            ],
    }


async def resolve_image_reference(
    image_id,
    *,
    user_id,
    character_id,
    conversation_id="default",
    detail="auto",
):
    """
    Resolve an authenticated user's own temporary image into a
    short-lived HTTPS reference for provider.py.

    Arbitrary client URLs are never accepted here.
    """
    uid = _validate_uid(
        user_id
    )

    conversation_id = (
        _normalize_conversation_id(
            conversation_id
        )
    )

    object_name = _object_name(
        uid,
        character_id,
        conversation_id,
        image_id,
    )

    bucket = fb.get_bucket()

    blob = bucket.blob(
        object_name
    )

    exists = await asyncio.to_thread(
        blob.exists
    )

    if not exists:
        raise ValueError(
            "image_not_found"
        )

    await asyncio.to_thread(
        blob.reload
    )

    if not _metadata_matches_scope(
        blob.metadata,
        user_id=uid,
        character_id=character_id,
        conversation_id=
            conversation_id,
    ):
        raise ValueError(
            "image_scope_mismatch"
        )

    if _expired(
        blob.metadata
    ):
        try:
            await asyncio.to_thread(
                blob.delete
            )
        except Exception:
            pass

        raise ValueError(
            "image_expired"
        )

    content_type = str(
        blob.content_type
        or (
            blob.metadata
            or {}
        ).get(
            "detectedMimeType",
            "",
        )
    ).casefold()

    if (
        content_type
        not in set(
            FORMAT_TO_MIME.values()
        )
    ):
        raise ValueError(
            "stored_image_type_invalid"
        )

    signed_url = await asyncio.to_thread(
        blob.generate_signed_url,
        version="v4",
        expiration=timedelta(
            seconds=
                SIGNED_URL_TTL_SECONDS
        ),
        method="GET",
    )

    if not str(
        signed_url
        or ""
    ).startswith(
        "https://"
    ):
        raise RuntimeError(
            "signed_image_url_invalid"
        )

    return {
        "imageId":
            str(
                image_id
            ),
        "url":
            signed_url,
        "mimeType":
            content_type,
        "detail":
            str(
                detail
                or "auto"
            ).casefold(),
    }


async def delete_image(
    image_id,
    *,
    user_id,
    character_id,
    conversation_id="default",
):
    """
    Delete only an image in the caller's exact user/character/conversation
    scope.
    """
    uid = _validate_uid(
        user_id
    )

    conversation_id = (
        _normalize_conversation_id(
            conversation_id
        )
    )

    object_name = _object_name(
        uid,
        character_id,
        conversation_id,
        image_id,
    )

    bucket = fb.get_bucket()

    blob = bucket.blob(
        object_name
    )

    exists = await asyncio.to_thread(
        blob.exists
    )

    if not exists:
        return {
            "ok": True,
            "deleted": False,
        }

    await asyncio.to_thread(
        blob.reload
    )

    if not _metadata_matches_scope(
        blob.metadata,
        user_id=uid,
        character_id=character_id,
        conversation_id=
            conversation_id,
    ):
        raise ValueError(
            "image_scope_mismatch"
        )

    await asyncio.to_thread(
        blob.delete
    )

    return {
        "ok": True,
        "deleted": True,
    }


def storage_policy():
    return {
        "version": MEDIA_VERSION,
        "authenticatedUploadOnly": True,
        "directClientStorageWrite": False,
        "publicObjects": False,
        "arbitraryClientUrls": False,
        "temporaryMedia": True,
        "physicalCleanupSupported": True,
        "physicalCleanupGuaranteed": True,
        "physicalDeleteAfterDays":
            PHYSICAL_DELETE_AFTER_DAYS,
        "lifecyclePrefix":
            STORAGE_ROOT + "/",
        "hashedUserStorageScope": True,
        "ttlSeconds":
            TEMP_MEDIA_TTL_SECONDS,
        "signedUrlTtlSeconds":
            SIGNED_URL_TTL_SECONDS,
        "newFirestoreCollection": False,
    }

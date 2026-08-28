import asyncio
from datetime import datetime, timedelta, timezone
from io import BytesIO

import pytest
from PIL import Image

import ai_media_service as MEDIA


class FakeUpload:
    def __init__(
        self,
        data,
    ):
        self.data = data

    async def read(
        self,
        size=-1,
    ):
        if size < 0:
            return self.data

        return self.data[
            :size
        ]


class FakeBlob:
    def __init__(
        self,
        name,
    ):
        self.name = name
        self.metadata = {}
        self.cache_control = None
        self.content_type = None
        self.data = None
        self.deleted = False
        self.present = False

    def upload_from_string(
        self,
        data,
        content_type=None,
    ):
        self.data = data
        self.content_type = (
            content_type
        )
        self.present = True

    def exists(
        self,
    ):
        return (
            self.present
            and not self.deleted
        )

    def reload(
        self,
    ):
        return None

    def delete(
        self,
    ):
        self.deleted = True
        self.present = False

    def generate_signed_url(
        self,
        **kwargs,
    ):
        return (
            "https://storage.example.test/"
            + self.name
            + "?signed=1"
        )


class FakeBucket:
    def __init__(
        self,
    ):
        self.blobs = {}
        self.lifecycle_rules = [
            {
                "action": {"type": "Delete"},
                "condition": {
                    "age": MEDIA.PHYSICAL_DELETE_AFTER_DAYS,
                    "matchesPrefix": [MEDIA.STORAGE_ROOT + "/"],
                },
            }
        ]

    def blob(
        self,
        name,
    ):
        if name not in self.blobs:
            self.blobs[name] = (
                FakeBlob(
                    name
                )
            )

        return self.blobs[
            name
        ]

    def reload(self):
        return None

    def add_lifecycle_delete_rule(
        self,
        *,
        age,
        matches_prefix,
    ):
        self.lifecycle_rules.append(
            {
                "action": {
                    "type": "Delete",
                },
                "condition": {
                    "age": age,
                    "matchesPrefix": list(
                        matches_prefix
                    ),
                },
            }
        )

    def patch(self):
        return None


def png_bytes(
    width=100,
    height=80,
):
    out = BytesIO()

    Image.new(
        "RGB",
        (
            width,
            height,
        ),
    ).save(
        out,
        format="PNG",
    )

    return out.getvalue()


def gif_bytes():
    out = BytesIO()

    Image.new(
        "RGB",
        (
            20,
            20,
        ),
    ).save(
        out,
        format="GIF",
    )

    return out.getvalue()


def animated_gif_bytes():
    out = BytesIO()

    frames = [
        Image.new(
            "RGB",
            (
                20,
                20,
            ),
            value,
        )
        for value in (
            "red",
            "blue",
        )
    ]

    frames[0].save(
        out,
        format="GIF",
        save_all=True,
        append_images=
            frames[1:],
        duration=100,
        loop=0,
    )

    return out.getvalue()


def install_bucket(
    monkeypatch,
):
    bucket = FakeBucket()

    monkeypatch.setattr(
        MEDIA.fb,
        "get_bucket",
        lambda: bucket,
    )

    return bucket


def test_storage_policy_is_private_backend_authoritative():
    policy = MEDIA.storage_policy()

    assert (
        policy[
            "authenticatedUploadOnly"
        ]
        is True
    )

    assert (
        policy[
            "directClientStorageWrite"
        ]
        is False
    )

    assert (
        policy[
            "publicObjects"
        ]
        is False
    )

    assert (
        policy[
            "arbitraryClientUrls"
        ]
        is False
    )

    assert (
        policy[
            "newFirestoreCollection"
        ]
        is False
    )


def test_object_scope_changes_between_users():
    a = MEDIA._object_prefix(
        "user-a",
        "character",
        "conversation",
    )

    b = MEDIA._object_prefix(
        "user-b",
        "character",
        "conversation",
    )

    assert a != b


def test_object_scope_changes_between_conversations():
    a = MEDIA._object_prefix(
        "user",
        "character",
        "conversation-a",
    )

    b = MEDIA._object_prefix(
        "user",
        "character",
        "conversation-b",
    )

    assert a != b


def test_raw_character_and_conversation_not_in_path():
    prefix = MEDIA._object_prefix(
        "user",
        "my-secret-character",
        "my-private-conversation",
    )

    assert (
        "my-secret-character"
        not in prefix
    )

    assert (
        "my-private-conversation"
        not in prefix
    )


def test_valid_png_is_inspected():
    result = MEDIA._inspect_image_bytes(
        png_bytes()
    )

    assert (
        result["format"]
        == "PNG"
    )

    assert (
        result["mimeType"]
        == "image/png"
    )

    assert (
        result["width"]
        == 100
    )

    assert (
        result["height"]
        == 80
    )


def test_static_gif_allowed():
    result = MEDIA._inspect_image_bytes(
        gif_bytes()
    )

    assert (
        result["format"]
        == "GIF"
    )


def test_animated_gif_rejected():
    with pytest.raises(
        ValueError,
        match="animated_gif_not_supported",
    ):
        MEDIA._inspect_image_bytes(
            animated_gif_bytes()
        )


def test_invalid_content_rejected():
    with pytest.raises(
        ValueError,
        match="invalid_image_content",
    ):
        MEDIA._inspect_image_bytes(
            b"not-an-image"
        )


def test_empty_content_rejected():
    with pytest.raises(
        ValueError,
        match="empty_image",
    ):
        MEDIA._inspect_image_bytes(
            b""
        )


def test_upload_uses_authenticated_uid_scope(
    monkeypatch,
):
    bucket = install_bucket(
        monkeypatch
    )

    result = asyncio.run(
        MEDIA.upload_image(
            FakeUpload(
                png_bytes()
            ),
            user_id="authenticated-user",
            character_id="character-a",
            conversation_id="conversation-a",
        )
    )

    assert result["ok"] is True
    assert result["temporary"] is True
    assert result["contentType"] == "image/png"

    assert len(
        bucket.blobs
    ) == 1

    blob = next(
        iter(
            bucket.blobs.values()
        )
    )

    assert blob.name.startswith(
        "ai-chat-media/"
        f"{MEDIA._scope_hash('authenticated-user')}/"
    )

    assert (
        "authenticated-user"
        not in blob.name
    )

    assert (
        blob.metadata[
            "ownerUid"
        ]
        == "authenticated-user"
    )

    assert (
        blob.cache_control
        == "private, no-store, max-age=0"
    )


def test_upload_does_not_return_storage_url(
    monkeypatch,
):
    install_bucket(
        monkeypatch
    )

    result = asyncio.run(
        MEDIA.upload_image(
            FakeUpload(
                png_bytes()
            ),
            user_id="user",
            character_id="character",
            conversation_id="conversation",
        )
    )

    serialized = str(
        result
    ).casefold()

    assert "https://" not in serialized
    assert "signed" not in serialized
    assert "objectname" not in serialized
    assert "objectref" not in serialized


def test_resolve_returns_short_lived_provider_reference(
    monkeypatch,
):
    bucket = install_bucket(
        monkeypatch
    )

    uploaded = asyncio.run(
        MEDIA.upload_image(
            FakeUpload(
                png_bytes()
            ),
            user_id="user",
            character_id="character",
            conversation_id="conversation",
        )
    )

    ref = asyncio.run(
        MEDIA.resolve_image_reference(
            uploaded[
                "imageId"
            ],
            user_id="user",
            character_id="character",
            conversation_id="conversation",
            detail="high",
        )
    )

    assert ref[
        "imageId"
    ] == uploaded[
        "imageId"
    ]

    assert ref[
        "url"
    ].startswith(
        "https://"
    )

    assert (
        ref["mimeType"]
        == "image/png"
    )

    assert (
        ref["detail"]
        == "high"
    )


def test_wrong_user_cannot_resolve_other_users_image(
    monkeypatch,
):
    bucket = install_bucket(
        monkeypatch
    )

    uploaded = asyncio.run(
        MEDIA.upload_image(
            FakeUpload(
                png_bytes()
            ),
            user_id="user-a",
            character_id="character",
            conversation_id="conversation",
        )
    )

    with pytest.raises(
        ValueError,
        match="image_not_found",
    ):
        asyncio.run(
            MEDIA.resolve_image_reference(
                uploaded[
                    "imageId"
                ],
                user_id="user-b",
                character_id="character",
                conversation_id="conversation",
            )
        )


def test_wrong_conversation_cannot_resolve_image(
    monkeypatch,
):
    install_bucket(
        monkeypatch
    )

    uploaded = asyncio.run(
        MEDIA.upload_image(
            FakeUpload(
                png_bytes()
            ),
            user_id="user",
            character_id="character",
            conversation_id="conversation-a",
        )
    )

    with pytest.raises(
        ValueError,
        match="image_not_found",
    ):
        asyncio.run(
            MEDIA.resolve_image_reference(
                uploaded[
                    "imageId"
                ],
                user_id="user",
                character_id="character",
                conversation_id="conversation-b",
            )
        )


def test_metadata_scope_mismatch_fails_closed(
    monkeypatch,
):
    bucket = install_bucket(
        monkeypatch
    )

    uploaded = asyncio.run(
        MEDIA.upload_image(
            FakeUpload(
                png_bytes()
            ),
            user_id="user",
            character_id="character",
            conversation_id="conversation",
        )
    )

    blob = next(
        iter(
            bucket.blobs.values()
        )
    )

    blob.metadata[
        "ownerUid"
    ] = "different-user"

    with pytest.raises(
        ValueError,
        match="image_scope_mismatch",
    ):
        asyncio.run(
            MEDIA.resolve_image_reference(
                uploaded[
                    "imageId"
                ],
                user_id="user",
                character_id="character",
                conversation_id="conversation",
            )
        )


def test_expired_image_fails_closed_and_deletes(
    monkeypatch,
):
    bucket = install_bucket(
        monkeypatch
    )

    uploaded = asyncio.run(
        MEDIA.upload_image(
            FakeUpload(
                png_bytes()
            ),
            user_id="user",
            character_id="character",
            conversation_id="conversation",
        )
    )

    blob = next(
        iter(
            bucket.blobs.values()
        )
    )

    old = (
        datetime.now(
            timezone.utc
        )
        - timedelta(
            seconds=
                MEDIA.TEMP_MEDIA_TTL_SECONDS
                + 60
        )
    )

    blob.metadata[
        "createdAt"
    ] = old.isoformat()

    with pytest.raises(
        ValueError,
        match="image_expired",
    ):
        asyncio.run(
            MEDIA.resolve_image_reference(
                uploaded[
                    "imageId"
                ],
                user_id="user",
                character_id="character",
                conversation_id="conversation",
            )
        )

    assert blob.deleted is True


def test_delete_exact_scope(
    monkeypatch,
):
    install_bucket(
        monkeypatch
    )

    uploaded = asyncio.run(
        MEDIA.upload_image(
            FakeUpload(
                png_bytes()
            ),
            user_id="user",
            character_id="character",
            conversation_id="conversation",
        )
    )

    result = asyncio.run(
        MEDIA.delete_image(
            uploaded[
                "imageId"
            ],
            user_id="user",
            character_id="character",
            conversation_id="conversation",
        )
    )

    assert result == {
        "ok": True,
        "deleted": True,
    }


def test_invalid_image_id_blocks_path_manipulation():
    with pytest.raises(
        ValueError,
        match="invalid_image_id",
    ):
        MEDIA._object_name(
            "user",
            "character",
            "conversation",
            "../../secret.jpg",
        )


def test_service_has_no_firestore_collection():
    from pathlib import Path

    source = Path(
        "backend/ai_media_service.py"
    ).read_text(
        encoding="utf-8"
    )

    forbidden = [
        ".collection(",
        "firestore.client",
        "add_memory(",
        "save_structured_memory(",
    ]

    for marker in forbidden:
        assert marker not in source

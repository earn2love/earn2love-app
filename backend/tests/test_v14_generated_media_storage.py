import asyncio
from datetime import datetime, timedelta, timezone
from io import BytesIO

import pytest
from PIL import Image

import ai_media_service as MEDIA


def png_bytes(
    width=64,
    height=48,
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
        self.present = False
        self.deleted = False

    def upload_from_string(
        self,
        data,
        content_type=None,
    ):
        self.data = data
        self.content_type = content_type
        self.present = True

    def exists(self):
        return (
            self.present
            and not self.deleted
        )

    def reload(self):
        return None

    def delete(self):
        self.deleted = True
        self.present = False

    def download_as_bytes(self):
        if not self.exists():
            raise RuntimeError(
                "missing"
            )

        return self.data

    def generate_signed_url(
        self,
        **_kwargs,
    ):
        return (
            "https://storage.example.test/"
            + self.name
            + "?signed=1"
        )


class FakeBucket:
    def __init__(self):
        self.blobs = {}

        self.lifecycle_rules = [
            {
                "action": {
                    "type": "Delete",
                },
                "condition": {
                    "age":
                        MEDIA.PHYSICAL_DELETE_AFTER_DAYS,
                    "matchesPrefix": [
                        MEDIA.STORAGE_ROOT + "/",
                    ],
                },
            },
            {
                "action": {
                    "type": "Delete",
                },
                "condition": {
                    "age":
                        MEDIA.PHYSICAL_DELETE_AFTER_DAYS,
                    "matchesPrefix": [
                        MEDIA.GENERATED_STORAGE_ROOT
                        + "/",
                    ],
                },
            },
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

    def patch(self):
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
                    "matchesPrefix":
                        list(
                            matches_prefix
                        ),
                },
            }
        )

    def list_blobs(
        self,
        prefix=None,
        max_results=None,
    ):
        values = [
            blob
            for name, blob
            in self.blobs.items()
            if (
                prefix is None
                or name.startswith(
                    prefix
                )
            )
        ]

        if max_results is not None:
            values = values[
                :max_results
            ]

        return values


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


def store(
    monkeypatch,
    *,
    user="user-a",
    character="char-a",
    conversation="conv-a",
):
    bucket = install_bucket(
        monkeypatch
    )

    result = asyncio.run(
        MEDIA.store_generated_image(
            png_bytes(),
            user_id=user,
            character_id=character,
            conversation_id=conversation,
        )
    )

    return (
        bucket,
        result,
    )


def test_generated_storage_policy_is_private():
    policy = (
        MEDIA.generated_storage_policy()
    )

    assert policy["version"] == 14
    assert policy["privateObjects"] is True
    assert policy["publicObjects"] is False
    assert (
        policy["arbitraryClientUrls"]
        is False
    )
    assert (
        policy["providerUrlsPersisted"]
        is False
    )
    assert (
        policy["newFirestoreCollection"]
        is False
    )


def test_generated_root_is_separate_from_v13():
    assert (
        MEDIA.GENERATED_STORAGE_ROOT
        != MEDIA.STORAGE_ROOT
    )


def test_generated_scope_is_hashed():
    prefix = (
        MEDIA._generated_object_prefix(
            "private-user",
            "private-character",
            "private-conversation",
        )
    )

    assert prefix.startswith(
        MEDIA.GENERATED_STORAGE_ROOT
        + "/"
    )

    assert "private-user" not in prefix
    assert "private-character" not in prefix
    assert "private-conversation" not in prefix


def test_store_generated_image_private(
    monkeypatch,
):
    bucket, result = store(
        monkeypatch
    )

    assert result["ok"] is True
    assert result["version"] == 14
    assert result["generated"] is True
    assert result["temporary"] is True

    image_id = result["imageId"]

    name = MEDIA._generated_object_name(
        "user-a",
        "char-a",
        "conv-a",
        image_id,
    )

    blob = bucket.blobs[
        name
    ]

    assert blob.present is True
    assert (
        blob.cache_control
        == "private, no-store, max-age=0"
    )

    assert (
        blob.metadata[
            "v14GeneratedMedia"
        ]
        == "true"
    )

    assert (
        blob.metadata[
            "temporary"
        ]
        == "true"
    )

    assert (
        blob.metadata[
            "ownerUid"
        ]
        == "user-a"
    )

    assert "url" not in result
    assert "objectName" not in result
    assert "ownerUid" not in result


def test_generated_image_id_remains_opaque():
    image_id = (
        "ABCDEF0123456789ABCDEF0123456789.png"
    )

    with pytest.raises(
        ValueError,
        match="invalid_image_id",
    ):
        MEDIA._generated_object_name(
            "user",
            "char",
            "conv",
            image_id,
        )

    # Incoming IDs are not silently case-normalized.
    assert (
        image_id
        != image_id.casefold()
    )


def test_generated_reference_resolves_signed_url(
    monkeypatch,
):
    _bucket, stored = store(
        monkeypatch
    )

    result = asyncio.run(
        MEDIA.resolve_generated_image_reference(
            stored["imageId"],
            user_id="user-a",
            character_id="char-a",
            conversation_id="conv-a",
        )
    )

    assert result["imageId"] == (
        stored["imageId"]
    )

    assert result["generated"] is True

    assert result["url"].startswith(
        "https://"
    )


def test_wrong_user_cannot_resolve_generated(
    monkeypatch,
):
    _bucket, stored = store(
        monkeypatch
    )

    with pytest.raises(
        ValueError,
        match="image_not_found",
    ):
        asyncio.run(
            MEDIA.resolve_generated_image_reference(
                stored["imageId"],
                user_id="user-b",
                character_id="char-a",
                conversation_id="conv-a",
            )
        )


def test_wrong_character_cannot_resolve_generated(
    monkeypatch,
):
    _bucket, stored = store(
        monkeypatch
    )

    with pytest.raises(
        ValueError,
        match="image_not_found",
    ):
        asyncio.run(
            MEDIA.resolve_generated_image_reference(
                stored["imageId"],
                user_id="user-a",
                character_id="char-b",
                conversation_id="conv-a",
            )
        )


def test_wrong_conversation_cannot_resolve_generated(
    monkeypatch,
):
    _bucket, stored = store(
        monkeypatch
    )

    with pytest.raises(
        ValueError,
        match="image_not_found",
    ):
        asyncio.run(
            MEDIA.resolve_generated_image_reference(
                stored["imageId"],
                user_id="user-a",
                character_id="char-a",
                conversation_id="conv-b",
            )
        )


def test_expired_generated_image_fails_closed(
    monkeypatch,
):
    bucket, stored = store(
        monkeypatch
    )

    name = MEDIA._generated_object_name(
        "user-a",
        "char-a",
        "conv-a",
        stored["imageId"],
    )

    blob = bucket.blobs[
        name
    ]

    expired = (
        datetime.now(
            timezone.utc
        )
        - timedelta(
            seconds=
                MEDIA.GENERATED_MEDIA_TTL_SECONDS
                + 60
        )
    ).isoformat()

    blob.metadata[
        "createdAt"
    ] = expired

    with pytest.raises(
        ValueError,
        match="image_expired",
    ):
        asyncio.run(
            MEDIA.resolve_generated_image_reference(
                stored["imageId"],
                user_id="user-a",
                character_id="char-a",
                conversation_id="conv-a",
            )
        )

    assert blob.deleted is True


def test_generated_edit_bytes_exact_scope(
    monkeypatch,
):
    _bucket, stored = store(
        monkeypatch
    )

    result = asyncio.run(
        MEDIA.resolve_image_bytes_for_edit(
            stored["imageId"],
            user_id="user-a",
            character_id="char-a",
            conversation_id="conv-a",
        )
    )

    assert (
        result["sourceType"]
        == "generated"
    )

    assert (
        result["imageBytes"]
        == png_bytes()
    )

    assert (
        result["mimeType"]
        == "image/png"
    )

    assert "url" not in result


def test_generated_edit_wrong_scope_denied(
    monkeypatch,
):
    _bucket, stored = store(
        monkeypatch
    )

    with pytest.raises(
        ValueError,
        match="image_not_found",
    ):
        asyncio.run(
            MEDIA.resolve_image_bytes_for_edit(
                stored["imageId"],
                user_id="other-user",
                character_id="char-a",
                conversation_id="conv-a",
            )
        )


def test_v13_uploaded_image_can_be_edit_source(
    monkeypatch,
):
    bucket = install_bucket(
        monkeypatch
    )

    image_id = (
        "0123456789abcdef"
        "0123456789abcdef.png"
    )

    name = MEDIA._object_name(
        "user-a",
        "char-a",
        "conv-a",
        image_id,
    )

    blob = bucket.blob(
        name
    )

    data = png_bytes(
        32,
        24,
    )

    created = datetime.now(
        timezone.utc
    )

    blob.metadata = {
        "v13Media": "true",
        "temporary": "true",
        "ownerUid": "user-a",
        "characterScope":
            MEDIA._scope_hash(
                "char-a"
            ),
        "conversationScope":
            MEDIA._scope_hash(
                "conv-a"
            ),
        "createdAt":
            created.isoformat(),
        "detectedMimeType":
            "image/png",
    }

    blob.upload_from_string(
        data,
        content_type="image/png",
    )

    result = asyncio.run(
        MEDIA.resolve_image_bytes_for_edit(
            image_id,
            user_id="user-a",
            character_id="char-a",
            conversation_id="conv-a",
        )
    )

    assert (
        result["sourceType"]
        == "uploaded"
    )

    assert (
        result["imageBytes"]
        == data
    )


def test_edit_source_rejects_arbitrary_url(
    monkeypatch,
):
    install_bucket(
        monkeypatch
    )

    with pytest.raises(
        ValueError,
        match="invalid_image_id",
    ):
        asyncio.run(
            MEDIA.resolve_image_bytes_for_edit(
                "https://evil.example/image.png",
                user_id="user-a",
                character_id="char-a",
                conversation_id="conv-a",
            )
        )


def test_delete_generated_exact_scope(
    monkeypatch,
):
    bucket, stored = store(
        monkeypatch
    )

    result = asyncio.run(
        MEDIA.delete_generated_image(
            stored["imageId"],
            user_id="user-a",
            character_id="char-a",
            conversation_id="conv-a",
        )
    )

    assert result == {
        "ok": True,
        "deleted": True,
    }

    name = MEDIA._generated_object_name(
        "user-a",
        "char-a",
        "conv-a",
        stored["imageId"],
    )

    assert (
        bucket.blobs[
            name
        ].deleted
        is True
    )


def test_cleanup_generated_is_bounded(
    monkeypatch,
):
    bucket = install_bucket(
        monkeypatch
    )

    image_id = (
        "aaaaaaaaaaaaaaaa"
        "aaaaaaaaaaaaaaaa.png"
    )

    name = MEDIA._generated_object_name(
        "user",
        "char",
        "conv",
        image_id,
    )

    blob = bucket.blob(
        name
    )

    blob.present = True
    blob.content_type = "image/png"

    expired = (
        datetime.now(
            timezone.utc
        )
        - timedelta(
            seconds=
                MEDIA.GENERATED_MEDIA_TTL_SECONDS
                + 100
        )
    ).isoformat()

    blob.metadata = {
        "v14GeneratedMedia": "true",
        "temporary": "true",
        "ownerUid": "user",
        "characterScope":
            MEDIA._scope_hash(
                "char"
            ),
        "conversationScope":
            MEDIA._scope_hash(
                "conv"
            ),
        "createdAt": expired,
    }

    result = asyncio.run(
        MEDIA.cleanup_expired_generated_media(
            max_objects=50000
        )
    )

    assert result["bounded"] is True
    assert result["deleted"] == 1
    assert blob.deleted is True


def test_generated_lifecycle_existing_rule(
    monkeypatch,
):
    bucket = install_bucket(
        monkeypatch
    )

    before = len(
        bucket.lifecycle_rules
    )

    result = asyncio.run(
        MEDIA.ensure_generated_media_lifecycle_policy()
    )

    assert result["ok"] is True
    assert result["created"] is False

    assert len(
        bucket.lifecycle_rules
    ) == before


def test_v13_storage_policy_unchanged_shape():
    policy = MEDIA.storage_policy()

    assert policy["version"] == 13
    assert (
        policy["lifecyclePrefix"]
        == MEDIA.STORAGE_ROOT + "/"
    )

    assert (
        policy["newFirestoreCollection"]
        is False
    )

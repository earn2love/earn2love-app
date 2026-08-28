import asyncio
from datetime import datetime, timedelta, timezone

import ai_media_service as MEDIA


def test_storage_path_does_not_expose_raw_uid():
    uid = "firebase-user-sensitive-123"

    prefix = MEDIA._object_prefix(
        uid,
        "character-a",
        "conversation-a",
    )

    assert uid not in prefix

    parts = prefix.split("/")

    assert parts[0] == MEDIA.STORAGE_ROOT
    assert len(parts) == 4
    assert parts[1] == MEDIA._scope_hash(uid)


def test_storage_scope_is_deterministic_and_isolated():
    first = MEDIA._object_prefix(
        "user-a",
        "character-a",
        "conversation-a",
    )

    same = MEDIA._object_prefix(
        "user-a",
        "character-a",
        "conversation-a",
    )

    other_user = MEDIA._object_prefix(
        "user-b",
        "character-a",
        "conversation-a",
    )

    other_character = MEDIA._object_prefix(
        "user-a",
        "character-b",
        "conversation-a",
    )

    other_conversation = MEDIA._object_prefix(
        "user-a",
        "character-a",
        "conversation-b",
    )

    assert first == same
    assert first != other_user
    assert first != other_character
    assert first != other_conversation


def test_duplicate_image_ids_remain_fail_closed():
    from ai_engine import multimodal_intelligence as MM13

    raw = {
        "imageId": "image-a",
        "url": "https://example.invalid/a.png",
        "mimeType": "image/png",
    }

    try:
        MM13.normalize_image_inputs(
            [
                raw,
                dict(raw),
            ]
        )
    except ValueError as exc:
        assert str(exc) == "duplicate_image_id"
    else:
        raise AssertionError(
            "duplicate image IDs must fail closed"
        )


def test_storage_policy_reports_hardening():
    policy = MEDIA.storage_policy()

    assert policy["temporaryMedia"] is True
    assert policy["physicalCleanupSupported"] is True
    assert policy["hashedUserStorageScope"] is True
    assert policy["publicObjects"] is False
    assert policy["directClientStorageWrite"] is False
    assert policy["newFirestoreCollection"] is False


def test_cleanup_only_deletes_expired_v13_temporary_media(
    monkeypatch,
):
    now = datetime.now(
        timezone.utc
    )

    expired = (
        now
        - timedelta(
            seconds=
                MEDIA.TEMP_MEDIA_TTL_SECONDS
                + 100,
        )
    ).isoformat()

    fresh = now.isoformat()

    class Blob:
        def __init__(
            self,
            name,
            metadata,
        ):
            self.name = name
            self.metadata = metadata
            self.deleted = False

        def reload(self):
            return None

        def delete(self):
            self.deleted = True

    old = Blob(
        "old",
        {
            "v13Media": "true",
            "temporary": "true",
            "createdAt": expired,
        },
    )

    current = Blob(
        "current",
        {
            "v13Media": "true",
            "temporary": "true",
            "createdAt": fresh,
        },
    )

    foreign = Blob(
        "foreign",
        {
            "v13Media": "false",
            "temporary": "true",
            "createdAt": expired,
        },
    )

    class Bucket:
        def list_blobs(
            self,
            prefix=None,
            max_results=None,
        ):
            assert prefix == f"{MEDIA.STORAGE_ROOT}/"
            assert max_results == 250

            return [
                old,
                current,
                foreign,
            ]

    monkeypatch.setattr(
        MEDIA.fb,
        "get_bucket",
        lambda: Bucket(),
    )

    result = asyncio.run(
        MEDIA.cleanup_expired_media()
    )

    assert result["ok"] is True
    assert result["deleted"] == 1

    assert old.deleted is True
    assert current.deleted is False
    assert foreign.deleted is False


def test_cleanup_is_bounded(
    monkeypatch,
):
    calls = []

    class Bucket:
        def list_blobs(
            self,
            prefix=None,
            max_results=None,
        ):
            calls.append(
                (
                    prefix,
                    max_results,
                )
            )
            return []

    monkeypatch.setattr(
        MEDIA.fb,
        "get_bucket",
        lambda: Bucket(),
    )

    result = asyncio.run(
        MEDIA.cleanup_expired_media(
            max_objects=50000
        )
    )

    assert result["bounded"] is True

    assert calls == [
        (
            f"{MEDIA.STORAGE_ROOT}/",
            1000,
        )
    ]

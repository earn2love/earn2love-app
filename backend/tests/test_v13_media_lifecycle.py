from pathlib import Path
import asyncio

import pytest

import ai_media_service as MEDIA


class _FakeBucket:
    def __init__(
        self,
        rules=None,
        *,
        patch_error=None,
    ):
        self.lifecycle_rules = list(
            rules
            or []
        )
        self.patch_error = patch_error
        self.patch_calls = 0
        self.reload_calls = 0

    def reload(self):
        self.reload_calls += 1

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

    def patch(self):
        self.patch_calls += 1

        if self.patch_error:
            raise self.patch_error


def _rule(
    prefix,
    age=None,
):
    return {
        "action": {
            "type": "Delete",
        },
        "condition": {
            "age":
                (
                    MEDIA.PHYSICAL_DELETE_AFTER_DAYS
                    if age is None
                    else age
                ),
            "matchesPrefix": [
                prefix
            ],
        },
    }


def test_media_lifecycle_rule_match_is_exact():
    assert MEDIA._is_media_lifecycle_rule(
        _rule(
            MEDIA.STORAGE_ROOT + "/"
        )
    )

    assert not MEDIA._is_media_lifecycle_rule(
        _rule(
            "other-prefix/"
        )
    )

    assert not MEDIA._is_media_lifecycle_rule(
        _rule(
            MEDIA.STORAGE_ROOT + "/",
            age=
                MEDIA.PHYSICAL_DELETE_AFTER_DAYS
                + 1,
        )
    )


def test_existing_lifecycle_rule_is_idempotent(
    monkeypatch,
):
    existing = _rule(
        MEDIA.STORAGE_ROOT + "/"
    )

    bucket = _FakeBucket(
        [
            existing
        ]
    )

    monkeypatch.setattr(
        MEDIA.fb,
        "get_bucket",
        lambda: bucket,
    )

    result = asyncio.run(
        MEDIA.ensure_media_lifecycle_policy()
    )

    assert result["ok"] is True
    assert result["created"] is False
    assert bucket.patch_calls == 0


def test_lifecycle_add_preserves_existing_rules(
    monkeypatch,
):
    unrelated = {
        "action": {
            "type": "Delete",
        },
        "condition": {
            "age": 30,
            "matchesPrefix": [
                "documents/"
            ],
        },
    }

    bucket = _FakeBucket(
        [
            unrelated
        ]
    )

    monkeypatch.setattr(
        MEDIA.fb,
        "get_bucket",
        lambda: bucket,
    )

    result = asyncio.run(
        MEDIA.ensure_media_lifecycle_policy()
    )

    assert result["ok"] is True
    assert result["created"] is True
    assert bucket.patch_calls == 1

    assert unrelated in bucket.lifecycle_rules

    assert any(
        MEDIA._is_media_lifecycle_rule(
            rule
        )
        for rule in bucket.lifecycle_rules
    )


def test_lifecycle_configuration_failure_fails_closed(
    monkeypatch,
):
    bucket = _FakeBucket(
        patch_error=
            PermissionError(
                "bucket update denied"
            )
    )

    monkeypatch.setattr(
        MEDIA.fb,
        "get_bucket",
        lambda: bucket,
    )

    with pytest.raises(
        RuntimeError,
        match=
            "media_lifecycle_unavailable",
    ):
        asyncio.run(
            MEDIA.ensure_media_lifecycle_policy()
        )


def test_storage_policy_reports_physical_guarantee():
    policy = MEDIA.storage_policy()

    assert (
        policy[
            "physicalCleanupGuaranteed"
        ]
        is True
    )

    assert (
        policy[
            "physicalDeleteAfterDays"
        ]
        == MEDIA.PHYSICAL_DELETE_AFTER_DAYS
    )

    assert (
        policy[
            "lifecyclePrefix"
        ]
        == MEDIA.STORAGE_ROOT + "/"
    )


def test_upload_source_requires_lifecycle_before_storage():
    source = Path(
        "backend/ai_media_service.py"
    ).read_text(
        encoding="utf-8-sig"
    )

    start = source.index(
        "async def upload_image("
    )

    end = source.index(
        "async def resolve_image_reference("
    )

    section = source[
        start:
        end
    ]

    lifecycle = section.index(
        "await ensure_media_lifecycle_policy()"
    )

    upload = section.index(
        "upload_from_string"
    )

    assert lifecycle < upload

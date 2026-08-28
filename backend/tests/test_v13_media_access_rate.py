import ast
from pathlib import Path

from ai_engine import rate_limit as RL


def test_media_rate_limits_use_existing_collection():
    source = Path(
        "backend/ai_engine/rate_limit.py"
    ).read_text(
        encoding="utf-8-sig"
    )

    assert 'COLL = "aiRateLimits"' in source
    assert "def check_and_consume_media_upload(" in source
    assert 'f"media_{uid}"' in source

    # V13.5B must not introduce a second collection.
    assert "aiMediaRateLimits" not in source


def test_media_upload_limits_are_bounded():
    assert RL.MEDIA_UPLOAD_PER_MINUTE > 0
    assert RL.MEDIA_UPLOAD_PER_HOUR >= RL.MEDIA_UPLOAD_PER_MINUTE
    assert RL.MEDIA_UPLOAD_PER_DAY >= RL.MEDIA_UPLOAD_PER_HOUR


def test_media_guard_rejects_missing_uid_without_firestore():
    class ExplodingDB:
        def collection(self, *_args, **_kwargs):
            raise AssertionError(
                "Firestore must not be touched for invalid UID"
            )

    result = RL.check_and_consume_media_upload(
        ExplodingDB(),
        "",
    )

    assert result == {
        "allowed": False,
        "reason": "invalid_user",
        "retryAfter": 0,
    }


def test_media_guard_fails_closed_when_store_unavailable():
    class BrokenDB:
        def collection(self, _name):
            raise RuntimeError(
                "firestore unavailable"
            )

    result = RL.check_and_consume_media_upload(
        BrokenDB(),
        "user-a",
    )

    assert result["allowed"] is False
    assert result["reason"] == "guard_unavailable"
    assert result["retryAfter"] > 0


def test_server_character_gate_exists_before_upload():
    source = Path(
        "backend/server.py"
    ).read_text(
        encoding="utf-8-sig"
    )

    ast.parse(source)

    gate = source.index(
        "_validate_ai_media_character("
    )

    consume = source.index(
        "check_and_consume_media_upload("
    )

    upload = source.index(
        "return await ai_media.upload_image("
    )

    assert gate < upload
    assert consume < upload


def test_server_character_gate_is_availability_only():
    source = Path(
        "backend/server.py"
    ).read_text(
        encoding="utf-8-sig"
    )

    start = source.index(
        "def _validate_ai_media_character("
    )

    end = source.index(
        "\n\n",
        start,
    )

    # Expand through helper return if the first blank line is
    # inside formatting.
    helper = source[
        start:
        source.index(
            "\n\n@",
            start,
        )
        if "\n\n@" in source[start:]
        else start + 3000
    ]

    assert "character_not_found" in helper
    assert "character_unavailable" in helper
    assert '"enabled"' in helper
    assert '"archived"' in helper

    # No invented tier/subscription contract in V13.5B.
    assert "subscriptionPlan" not in helper
    assert "subscriptionStatus" not in helper
    assert "subTier" not in helper
    assert "tierAccess" not in helper


def test_media_endpoint_uses_authenticated_uid_for_guard():
    source = Path(
        "backend/server.py"
    ).read_text(
        encoding="utf-8-sig"
    )

    endpoint = source[
        source.index(
            "async def ai_media_upload("
        ):
        source.index(
            "async def ai_media_delete(",
            source.index(
                "async def ai_media_upload("
            ),
        )
    ]

    assert 'user["uid"]' in endpoint
    assert "check_and_consume_media_upload" in endpoint
    assert "characterId" in endpoint


def test_media_endpoint_maps_rate_and_guard_failures():
    source = Path(
        "backend/server.py"
    ).read_text(
        encoding="utf-8-sig"
    )

    assert "image_upload_rate_limited" in source
    assert "image_upload_guard_unavailable" in source
    assert "status_code=429" in source
    assert "status_code=503" in source

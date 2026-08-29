import asyncio
from pathlib import Path

import pytest

import ai_image_creation_service as SVC
from ai_engine import rate_limit as RL


PNG = (
    b"\x89PNG\r\n\x1a\n"
    b"v14-hardening"
)


def install_character(
    monkeypatch,
):
    async def character(
        character_id,
    ):
        return {
            "id": character_id,
            "enabled": True,
            "archived": False,
        }

    monkeypatch.setattr(
        SVC.ai_service,
        "get_character",
        character,
    )


def install_model(
    monkeypatch,
):
    monkeypatch.setenv(
        "AI_ENGINE_IMAGE_PROVIDER",
        "openai",
    )

    monkeypatch.setenv(
        "AI_ENGINE_IMAGE_MODEL",
        "v14-hardening-test-model",
    )


def allow_guard(
    monkeypatch,
):
    monkeypatch.setattr(
        SVC,
        "_consume_image_creation_slot",
        lambda _uid: {
            "allowed": True,
            "reason": None,
            "retryAfter": 0,
        },
    )


def test_real_edit_provider_kwarg_is_instruction():
    source = Path(
        "backend/ai_image_creation_service.py"
    ).read_text(
        encoding="utf-8-sig"
    )

    assert (
        "instruction=request.instruction"
        in source
    )

    assert (
        "prompt=request.instruction"
        not in source
    )


def test_image_guard_uses_existing_collection():
    source = Path(
        "backend/ai_engine/rate_limit.py"
    ).read_text(
        encoding="utf-8-sig"
    )

    assert 'COLL = "aiRateLimits"' in source

    assert (
        "def check_and_consume_image_creation("
        in source
    )

    assert (
        'f"image_{uid}"'
        in source
    )

    assert (
        '"image_platform_daily"'
        in source
    )


def test_service_denied_before_provider(
    monkeypatch,
):
    install_character(
        monkeypatch
    )

    install_model(
        monkeypatch
    )

    called = {
        "provider": False,
    }

    def deny(
        _uid,
    ):
        raise SVC.ImageCreationServiceError(
            "image_rate_limited",
            status_code=429,
            retry_after=17,
        )

    async def provider(
        **_kwargs,
    ):
        called["provider"] = True

        raise AssertionError(
            "provider must not run after rate denial"
        )

    monkeypatch.setattr(
        SVC,
        "_consume_image_creation_slot",
        deny,
    )

    monkeypatch.setattr(
        SVC.PROV,
        "generate_image",
        provider,
    )

    with pytest.raises(
        SVC.ImageCreationServiceError,
        match="image_rate_limited",
    ) as exc:
        asyncio.run(
            SVC.generate_image(
                user_id="user-a",
                character_id="char-a",
                prompt="create",
            )
        )

    assert exc.value.status_code == 429
    assert exc.value.retry_after == 17
    assert called["provider"] is False


def test_model_failure_occurs_before_rate_consume(
    monkeypatch,
):
    install_character(
        monkeypatch
    )

    monkeypatch.delenv(
        "AI_ENGINE_IMAGE_MODEL",
        raising=False,
    )

    monkeypatch.setattr(
        SVC,
        "DEFAULT_IMAGE_MODEL",
        "",
    )

    called = {
        "guard": False,
    }

    def guard(
        _uid,
    ):
        called["guard"] = True

    monkeypatch.setattr(
        SVC,
        "_consume_image_creation_slot",
        guard,
    )

    with pytest.raises(
        SVC.ImageCreationServiceError,
        match="image_model_not_configured",
    ):
        asyncio.run(
            SVC.generate_image(
                user_id="user-a",
                character_id="char-a",
                prompt="create",
            )
        )

    assert called["guard"] is False


def test_generate_resolve_failure_deletes_orphan(
    monkeypatch,
):
    install_character(
        monkeypatch
    )

    install_model(
        monkeypatch
    )

    allow_guard(
        monkeypatch
    )

    deleted = []

    async def provider(
        **_kwargs,
    ):
        return {
            "imageBytes": PNG,
            "mimeType": "image/png",
        }

    async def store(
        image_bytes,
        **_kwargs,
    ):
        return {
            "imageId":
                "aaaaaaaaaaaaaaaa"
                "aaaaaaaaaaaaaaaa.png",
            "contentType": "image/png",
            "width": 64,
            "height": 64,
            "sizeBytes": len(image_bytes),
            "temporary": True,
            "expiresAt":
                "2099-01-01T00:00:00+00:00",
        }

    async def resolve(
        *_args,
        **_kwargs,
    ):
        raise RuntimeError(
            "signed_url_failure"
        )

    async def delete(
        image_id,
        **kwargs,
    ):
        deleted.append(
            (
                image_id,
                kwargs,
            )
        )

        return {
            "deleted": True,
        }

    monkeypatch.setattr(
        SVC.PROV,
        "generate_image",
        provider,
    )

    monkeypatch.setattr(
        SVC.MEDIA,
        "store_generated_image",
        store,
    )

    monkeypatch.setattr(
        SVC.MEDIA,
        "resolve_generated_image_reference",
        resolve,
    )

    monkeypatch.setattr(
        SVC.MEDIA,
        "delete_generated_image",
        delete,
    )

    with pytest.raises(
        SVC.ImageCreationServiceError,
        match="image_creation_unavailable",
    ):
        asyncio.run(
            SVC.generate_image(
                user_id="user-a",
                character_id="char-a",
                conversation_id="conv-a",
                prompt="create",
            )
        )

    assert len(deleted) == 1

    assert (
        deleted[0][0]
        == "aaaaaaaaaaaaaaaa"
           "aaaaaaaaaaaaaaaa.png"
    )

    assert (
        deleted[0][1]["user_id"]
        == "user-a"
    )

    assert (
        deleted[0][1]["character_id"]
        == "char-a"
    )

    assert (
        deleted[0][1]["conversation_id"]
        == "conv-a"
    )


def test_provider_failure_has_no_delete(
    monkeypatch,
):
    install_character(
        monkeypatch
    )

    install_model(
        monkeypatch
    )

    allow_guard(
        monkeypatch
    )

    deleted = []

    async def provider(
        **_kwargs,
    ):
        raise RuntimeError(
            "provider unavailable"
        )

    async def delete(
        *_args,
        **_kwargs,
    ):
        deleted.append(
            True
        )

        return {
            "deleted": True,
        }

    monkeypatch.setattr(
        SVC.PROV,
        "generate_image",
        provider,
    )

    monkeypatch.setattr(
        SVC.MEDIA,
        "delete_generated_image",
        delete,
    )

    with pytest.raises(
        SVC.ImageCreationServiceError,
        match="image_creation_unavailable",
    ):
        asyncio.run(
            SVC.generate_image(
                user_id="user-a",
                character_id="char-a",
                prompt="create",
            )
        )

    assert deleted == []


def test_cleanup_failure_does_not_leak_internal_error(
    monkeypatch,
):
    install_character(
        monkeypatch
    )

    install_model(
        monkeypatch
    )

    allow_guard(
        monkeypatch
    )

    async def provider(
        **_kwargs,
    ):
        return {
            "imageBytes": PNG,
            "mimeType": "image/png",
        }

    async def store(
        image_bytes,
        **_kwargs,
    ):
        return {
            "imageId":
                "bbbbbbbbbbbbbbbb"
                "bbbbbbbbbbbbbbbb.png",
            "contentType": "image/png",
            "width": 64,
            "height": 64,
            "sizeBytes": len(image_bytes),
            "temporary": True,
            "expiresAt":
                "2099-01-01T00:00:00+00:00",
        }

    async def resolve(
        *_args,
        **_kwargs,
    ):
        raise RuntimeError(
            "secret signed-url internal"
        )

    async def delete(
        *_args,
        **_kwargs,
    ):
        raise RuntimeError(
            "secret storage internal"
        )

    monkeypatch.setattr(
        SVC.PROV,
        "generate_image",
        provider,
    )

    monkeypatch.setattr(
        SVC.MEDIA,
        "store_generated_image",
        store,
    )

    monkeypatch.setattr(
        SVC.MEDIA,
        "resolve_generated_image_reference",
        resolve,
    )

    monkeypatch.setattr(
        SVC.MEDIA,
        "delete_generated_image",
        delete,
    )

    with pytest.raises(
        SVC.ImageCreationServiceError,
        match="image_creation_unavailable",
    ) as exc:
        asyncio.run(
            SVC.generate_image(
                user_id="user-a",
                character_id="char-a",
                prompt="create",
            )
        )

    assert "secret" not in str(
        exc.value
    )


def test_service_policy_hardening():
    policy = (
        SVC.image_creation_service_policy()
    )

    assert (
        policy["imageCreationRateLimit"]
        == "existing_aiRateLimits"
    )

    assert (
        policy["rateLimitFailClosed"]
        is True
    )

    assert (
        policy["platformCostCircuitBreaker"]
        is True
    )

    assert (
        policy["failureCompensatingDelete"]
        is True
    )


def test_no_billing_added():
    combined = (
        Path(
            "backend/ai_image_creation_service.py"
        ).read_text(
            encoding="utf-8-sig"
        )
        +
        Path(
            "backend/ai_engine/rate_limit.py"
        ).read_text(
            encoding="utf-8-sig"
        )
    ).casefold()

    for forbidden in (
        "silverbalance",
        "goldbalance",
        "diamondbalance",
        "charge_user",
        "deduct_balance",
    ):
        assert forbidden not in combined

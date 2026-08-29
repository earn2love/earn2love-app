import asyncio
from pathlib import Path

import pytest

import ai_image_creation_service as SVC


PNG = (
    b"\x89PNG\r\n\x1a\n"
    b"v14-idempotency"
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
        "v14-idem-test-model",
    )


def test_client_request_id_contract():
    assert (
        SVC._normalize_client_request_id(
            "req-123"
        )
        == "req-123"
    )

    assert (
        SVC._normalize_client_request_id(
            None
        )
        is None
    )

    with pytest.raises(
        SVC.ImageCreationServiceError,
        match="invalid_client_request_id",
    ):
        SVC._normalize_client_request_id(
            "https://evil.example/request"
        )


def test_fingerprint_is_deterministic():
    first = SVC._request_fingerprint(
        "generate",
        {
            "prompt": "hello",
            "size": "1024x1024",
        },
    )

    second = SVC._request_fingerprint(
        "generate",
        {
            "size": "1024x1024",
            "prompt": "hello",
        },
    )

    assert first == second
    assert len(first) == 64


def test_same_request_replays_before_rate_and_provider(
    monkeypatch,
):
    install_character(
        monkeypatch
    )

    install_model(
        monkeypatch
    )

    image_id = (
        "aaaaaaaaaaaaaaaa"
        "aaaaaaaaaaaaaaaa.png"
    )

    monkeypatch.setattr(
        SVC,
        "_begin_image_request",
        lambda **_kwargs: {
            "action": "replay",
            "result": {
                "operation": "generate",
                "imageId": image_id,
                "contentType":
                    "image/png",
                "width": 1024,
                "height": 1024,
                "sizeBytes": 100,
                "temporary": True,
                "expiresAt":
                    "2099-01-01T00:00:00+00:00",
            },
        },
    )

    called = {
        "rate": False,
        "provider": False,
    }

    def rate(
        _uid,
    ):
        called["rate"] = True
        raise AssertionError(
            "replay must happen before rate guard"
        )

    async def provider(
        **_kwargs,
    ):
        called["provider"] = True
        raise AssertionError(
            "replay must not call provider"
        )

    async def resolve(
        image_id_arg,
        **_kwargs,
    ):
        assert image_id_arg == image_id

        return {
            "imageId": image_id,
            "url":
                "https://signed.example/replay",
            "mimeType":
                "image/png",
        }

    monkeypatch.setattr(
        SVC,
        "_consume_image_creation_slot",
        rate,
    )

    monkeypatch.setattr(
        SVC.PROV,
        "generate_image",
        provider,
    )

    monkeypatch.setattr(
        SVC.MEDIA,
        "resolve_generated_image_reference",
        resolve,
    )

    result = asyncio.run(
        SVC.generate_image(
            user_id="user-a",
            character_id="char-a",
            conversation_id="conv-a",
            prompt="hello",
            client_request_id="req-123",
        )
    )

    assert result["ok"] is True
    assert result["idempotentReplay"] is True
    assert result["clientRequestId"] == "req-123"
    assert result["imageId"] == image_id
    assert (
        result["url"]
        == "https://signed.example/replay"
    )

    assert called["rate"] is False
    assert called["provider"] is False


def test_idempotency_conflict_fails_before_provider(
    monkeypatch,
):
    install_character(
        monkeypatch
    )

    install_model(
        monkeypatch
    )

    monkeypatch.setattr(
        SVC.ai_service,
        "begin_image_request",
        lambda *_args, **_kwargs: {
            "action": "conflict",
        },
    )

    called = {
        "provider": False,
        "rate": False,
    }

    def rate(
        _uid,
    ):
        called["rate"] = True

    async def provider(
        **_kwargs,
    ):
        called["provider"] = True

    monkeypatch.setattr(
        SVC,
        "_consume_image_creation_slot",
        rate,
    )

    monkeypatch.setattr(
        SVC.PROV,
        "generate_image",
        provider,
    )

    with pytest.raises(
        SVC.ImageCreationServiceError,
        match="image_idempotency_conflict",
    ) as exc:
        asyncio.run(
            SVC.generate_image(
                user_id="user-a",
                character_id="char-a",
                prompt="hello",
                client_request_id="req-123",
            )
        )

    assert exc.value.status_code == 409
    assert called["rate"] is False
    assert called["provider"] is False


def test_pending_request_fails_before_provider(
    monkeypatch,
):
    install_character(
        monkeypatch
    )

    install_model(
        monkeypatch
    )

    monkeypatch.setattr(
        SVC.ai_service,
        "begin_image_request",
        lambda *_args, **_kwargs: {
            "action": "in_progress",
            "retryAfter": 2,
        },
    )

    called = {
        "provider": False,
    }

    async def provider(
        **_kwargs,
    ):
        called["provider"] = True

    monkeypatch.setattr(
        SVC.PROV,
        "generate_image",
        provider,
    )

    with pytest.raises(
        SVC.ImageCreationServiceError,
        match="image_request_in_progress",
    ) as exc:
        asyncio.run(
            SVC.generate_image(
                user_id="user-a",
                character_id="char-a",
                prompt="hello",
                client_request_id="req-123",
            )
        )

    assert exc.value.status_code == 409
    assert exc.value.retry_after == 2
    assert called["provider"] is False


def test_generate_completion_persists_without_signed_url(
    monkeypatch,
):
    install_character(
        monkeypatch
    )

    install_model(
        monkeypatch
    )

    monkeypatch.setattr(
        SVC,
        "_begin_image_request",
        lambda **_kwargs: {
            "action": "new",
        },
    )

    monkeypatch.setattr(
        SVC,
        "_consume_image_creation_slot",
        lambda _uid: {
            "allowed": True,
        },
    )

    captured = {}

    def complete(
        **kwargs,
    ):
        captured.update(
            kwargs
        )
        return True

    monkeypatch.setattr(
        SVC,
        "_complete_image_request",
        complete,
    )

    async def provider(
        **_kwargs,
    ):
        return {
            "imageBytes": PNG,
            "mimeType":
                "image/png",
        }

    async def store(
        image_bytes,
        **_kwargs,
    ):
        return {
            "imageId":
                "bbbbbbbbbbbbbbbb"
                "bbbbbbbbbbbbbbbb.png",
            "contentType":
                "image/png",
            "width": 1024,
            "height": 1024,
            "sizeBytes":
                len(image_bytes),
            "temporary": True,
            "expiresAt":
                "2099-01-01T00:00:00+00:00",
        }

    async def resolve(
        image_id,
        **_kwargs,
    ):
        return {
            "imageId":
                image_id,
            "url":
                "https://signed.example/new",
            "mimeType":
                "image/png",
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

    result = asyncio.run(
        SVC.generate_image(
            user_id="user-a",
            character_id="char-a",
            conversation_id="conv-a",
            prompt="hello",
            client_request_id="req-123",
        )
    )

    assert result["idempotentReplay"] is False
    assert result["clientRequestId"] == "req-123"

    persisted = captured["result"]

    assert "url" not in persisted
    assert (
        persisted["imageId"]
        == result["imageId"]
    )


def test_rate_denial_releases_reservation(
    monkeypatch,
):
    install_character(
        monkeypatch
    )

    install_model(
        monkeypatch
    )

    monkeypatch.setattr(
        SVC,
        "_begin_image_request",
        lambda **_kwargs: {
            "action": "new",
        },
    )

    aborted = []

    def abort(
        **kwargs,
    ):
        aborted.append(
            kwargs
        )
        return True

    monkeypatch.setattr(
        SVC,
        "_abort_image_request",
        abort,
    )

    def denied(
        _uid,
    ):
        raise SVC.ImageCreationServiceError(
            "image_rate_limited",
            status_code=429,
            retry_after=10,
        )

    monkeypatch.setattr(
        SVC,
        "_consume_image_creation_slot",
        denied,
    )

    with pytest.raises(
        SVC.ImageCreationServiceError,
        match="image_rate_limited",
    ):
        asyncio.run(
            SVC.generate_image(
                user_id="user-a",
                character_id="char-a",
                prompt="hello",
                client_request_id="req-123",
            )
        )

    assert len(aborted) == 1
    assert (
        aborted[0]["client_request_id"]
        == "req-123"
    )


def test_edit_invalid_source_does_not_consume_rate(
    monkeypatch,
):
    install_character(
        monkeypatch
    )

    install_model(
        monkeypatch
    )

    monkeypatch.setattr(
        SVC,
        "_begin_image_request",
        lambda **_kwargs: {
            "action": "new",
        },
    )

    rate_called = {
        "value": False,
    }

    def rate(
        _uid,
    ):
        rate_called["value"] = True

    monkeypatch.setattr(
        SVC,
        "_consume_image_creation_slot",
        rate,
    )

    async def source(
        *_args,
        **_kwargs,
    ):
        raise ValueError(
            "image_not_found"
        )

    monkeypatch.setattr(
        SVC.MEDIA,
        "resolve_image_bytes_for_edit",
        source,
    )

    image_id = (
        "cccccccccccccccc"
        "cccccccccccccccc.png"
    )

    with pytest.raises(
        SVC.ImageCreationServiceError,
        match="image_not_found",
    ):
        asyncio.run(
            SVC.edit_image(
                user_id="user-a",
                character_id="char-a",
                prompt="edit",
                source_image_ids=[
                    image_id
                ],
                client_request_id="req-edit-1",
            )
        )

    assert rate_called["value"] is False


def test_service_policy_declares_existing_authority():
    policy = (
        SVC.image_creation_service_policy()
    )

    assert (
        policy["idempotency"]
        == "transactional_clientRequestId"
    )

    assert (
        policy["idempotencyAuthority"]
        == "existing_aiCharacterConversations"
    )

    assert (
        policy["signedUrlPersistence"]
        is False
    )

    assert (
        policy[
            "duplicateProviderCallProtection"
        ]
        is True
    )


def test_server_contract_exposes_client_request_id():
    server = Path(
        "backend/server.py"
    ).read_text(
        encoding="utf-8-sig"
    )

    assert (
        server.count(
            "clientRequestId: str | None = None"
        )
        >= 2
    )

    assert (
        server.count(
            "client_request_id=body.clientRequestId"
        )
        >= 2
    )

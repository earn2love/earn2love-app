import asyncio
import os

import pytest

import ai_image_creation_service as SVC


PNG = (
    b"\x89PNG\r\n\x1a\n"
    b"v14-test-image"
)



@pytest.fixture(autouse=True)
def _v14_allow_image_creation_guard(
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

    monkeypatch.setattr(
        SVC,
        "_begin_image_request",
        lambda **_kwargs: {
            "action": "disabled",
        },
    )

    monkeypatch.setattr(
        SVC,
        "_complete_image_request",
        lambda **_kwargs: True,
    )

    monkeypatch.setattr(
        SVC,
        "_abort_image_request",
        lambda **_kwargs: False,
    )


def install_character(
    monkeypatch,
):
    async def fake_get_character(
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
        fake_get_character,
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
        "v14-test-image-model",
    )


def test_service_policy():
    policy = (
        SVC.image_creation_service_policy()
    )

    assert policy["version"] == 14
    assert policy["privateStorage"] is True
    assert (
        policy["arbitraryClientUrls"]
        is False
    )
    assert (
        policy["newFirestoreCollection"]
        is False
    )
    assert (
        policy["billingMutation"]
        is False
    )


def test_missing_image_model_fails_closed(
    monkeypatch,
):
    monkeypatch.delenv(
        "AI_ENGINE_IMAGE_MODEL",
        raising=False,
    )

    monkeypatch.setattr(
        SVC,
        "DEFAULT_IMAGE_MODEL",
        "",
    )

    with pytest.raises(
        SVC.ImageCreationServiceError,
        match="image_model_not_configured",
    ):
        SVC._resolve_provider_model()


def test_generate_orchestration(
    monkeypatch,
):
    install_character(
        monkeypatch
    )

    install_model(
        monkeypatch
    )

    calls = {}

    async def fake_generate_image(
        **kwargs,
    ):
        calls["provider"] = kwargs

        return {
            "imageBytes": PNG,
            "mimeType": "image/png",
        }

    async def fake_store(
        image_bytes,
        **kwargs,
    ):
        calls["storedBytes"] = (
            image_bytes
        )
        calls["store"] = kwargs

        return {
            "imageId":
                "aaaaaaaaaaaaaaaa"
                "aaaaaaaaaaaaaaaa.png",
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

    async def fake_resolve(
        image_id,
        **kwargs,
    ):
        calls["resolve"] = {
            "imageId":
                image_id,
            **kwargs,
        }

        return {
            "imageId":
                image_id,
            "url":
                "https://signed.example/generated",
            "mimeType":
                "image/png",
            "generated": True,
        }

    monkeypatch.setattr(
        SVC.PROV,
        "generate_image",
        fake_generate_image,
    )

    monkeypatch.setattr(
        SVC.MEDIA,
        "store_generated_image",
        fake_store,
    )

    monkeypatch.setattr(
        SVC.MEDIA,
        "resolve_generated_image_reference",
        fake_resolve,
    )

    result = asyncio.run(
        SVC.generate_image(
            user_id="user-a",
            character_id="char-a",
            conversation_id="conv-a",
            prompt="Create a peaceful lake",
        )
    )

    assert result["ok"] is True
    assert result["operation"] == "generate"

    assert (
        result["imageId"]
        == "aaaaaaaaaaaaaaaa"
           "aaaaaaaaaaaaaaaa.png"
    )

    assert result["url"].startswith(
        "https://"
    )

    assert (
        calls["provider"]["provider"]
        == "openai"
    )

    assert (
        calls["provider"]["model"]
        == "v14-test-image-model"
    )

    assert (
        calls["store"]["user_id"]
        == "user-a"
    )

    assert (
        calls["store"]["character_id"]
        == "char-a"
    )

    assert (
        calls["store"]["conversation_id"]
        == "conv-a"
    )


def test_edit_resolves_source_server_side(
    monkeypatch,
):
    install_character(
        monkeypatch
    )

    install_model(
        monkeypatch
    )

    source_id = (
        "bbbbbbbbbbbbbbbb"
        "bbbbbbbbbbbbbbbb.png"
    )

    calls = {}

    async def fake_source(
        image_id,
        **kwargs,
    ):
        calls["source"] = {
            "imageId": image_id,
            **kwargs,
        }

        return {
            "imageId": image_id,
            "imageBytes": PNG,
            "mimeType": "image/png",
            "width": 64,
            "height": 64,
            "sourceType": "uploaded",
        }

    async def fake_edit_image(
        **kwargs,
    ):
        calls["provider"] = kwargs

        assert len(
            kwargs["image_files"]
        ) == 1

        assert (
            kwargs["image_files"][0].read()
            == PNG
        )

        kwargs[
            "image_files"
        ][0].seek(0)

        return {
            "imageBytes": PNG,
            "mimeType": "image/png",
        }

    async def fake_store(
        image_bytes,
        **kwargs,
    ):
        return {
            "imageId":
                "cccccccccccccccc"
                "cccccccccccccccc.png",
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

    async def fake_resolve(
        image_id,
        **kwargs,
    ):
        return {
            "imageId": image_id,
            "url":
                "https://signed.example/edited",
            "mimeType":
                "image/png",
            "generated": True,
        }

    monkeypatch.setattr(
        SVC.MEDIA,
        "resolve_image_bytes_for_edit",
        fake_source,
    )

    monkeypatch.setattr(
        SVC.PROV,
        "edit_image",
        fake_edit_image,
    )

    monkeypatch.setattr(
        SVC.MEDIA,
        "store_generated_image",
        fake_store,
    )

    monkeypatch.setattr(
        SVC.MEDIA,
        "resolve_generated_image_reference",
        fake_resolve,
    )

    result = asyncio.run(
        SVC.edit_image(
            user_id="user-a",
            character_id="char-a",
            conversation_id="conv-a",
            prompt="Make the sky warmer",
            source_image_ids=[
                source_id
            ],
        )
    )

    assert result["ok"] is True
    assert result["operation"] == "edit"

    assert result[
        "sourceImageIds"
    ] == [
        source_id
    ]

    assert (
        calls["source"]["user_id"]
        == "user-a"
    )

    assert (
        calls["source"]["character_id"]
        == "char-a"
    )

    assert (
        calls["source"]["conversation_id"]
        == "conv-a"
    )


def test_edit_arbitrary_url_rejected_before_media(
    monkeypatch,
):
    install_character(
        monkeypatch
    )

    install_model(
        monkeypatch
    )

    called = {
        "media": False,
    }

    async def fake_source(
        *_args,
        **_kwargs,
    ):
        called["media"] = True
        raise AssertionError(
            "media resolver must not receive arbitrary URL"
        )

    monkeypatch.setattr(
        SVC.MEDIA,
        "resolve_image_bytes_for_edit",
        fake_source,
    )

    with pytest.raises(
        SVC.ImageCreationServiceError,
    ):
        asyncio.run(
            SVC.edit_image(
                user_id="user-a",
                character_id="char-a",
                conversation_id="conv-a",
                prompt="Edit it",
                source_image_ids=[
                    "https://evil.example/a.png"
                ],
            )
        )

    assert called["media"] is False


def test_disabled_character_denied(
    monkeypatch,
):
    install_model(
        monkeypatch
    )

    async def disabled(
        character_id,
    ):
        return {
            "id": character_id,
            "enabled": False,
        }

    monkeypatch.setattr(
        SVC.ai_service,
        "get_character",
        disabled,
    )

    with pytest.raises(
        SVC.ImageCreationServiceError,
        match="character_unavailable",
    ):
        asyncio.run(
            SVC.generate_image(
                user_id="user-a",
                character_id="char-a",
                prompt="hello",
            )
        )


def test_provider_failure_is_safe(
    monkeypatch,
):
    install_character(
        monkeypatch
    )

    install_model(
        monkeypatch
    )

    async def failure(
        **_kwargs,
    ):
        raise RuntimeError(
            "provider secret internal error"
        )

    monkeypatch.setattr(
        SVC.PROV,
        "generate_image",
        failure,
    )

    with pytest.raises(
        SVC.ImageCreationServiceError,
        match="image_creation_unavailable",
    ) as exc:
        asyncio.run(
            SVC.generate_image(
                user_id="user-a",
                character_id="char-a",
                prompt="hello",
            )
        )

    assert (
        "provider secret"
        not in str(
            exc.value
        )
    )


def test_service_uses_v14_contract_validation():
    from pathlib import Path

    service_source = Path(
        "backend/ai_image_creation_service.py"
    ).read_text(
        encoding="utf-8-sig"
    )

    assert (
        "ImageCreationRequest.from_input("
        in service_source
    )

    assert (
        "ImageEditRequest.from_input("
        in service_source
    )

    assert (
        "instruction=prompt"
        in service_source
    )

    assert (
        "instruction=request.instruction"
        in service_source
    )

    assert (
        "prompt=request.instruction"
        not in service_source
    )


def test_generate_invalid_size_rejected_before_provider(
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

    async def provider(
        **_kwargs,
    ):
        called["provider"] = True
        raise AssertionError(
            "provider must not run for invalid request"
        )

    monkeypatch.setattr(
        SVC.PROV,
        "generate_image",
        provider,
    )

    with pytest.raises(
        SVC.ImageCreationServiceError,
        match="invalid_image_size",
    ):
        asyncio.run(
            SVC.generate_image(
                user_id="user-a",
                character_id="char-a",
                prompt="test",
                size="999x999",
            )
        )

    assert called["provider"] is False


def test_edit_duplicate_source_ids_rejected_before_media(
    monkeypatch,
):
    install_character(
        monkeypatch
    )

    install_model(
        monkeypatch
    )

    image_id = (
        "dddddddddddddddd"
        "dddddddddddddddd.png"
    )

    called = {
        "media": False,
    }

    async def resolver(
        *_args,
        **_kwargs,
    ):
        called["media"] = True
        raise AssertionError(
            "media must not run for duplicate IDs"
        )

    monkeypatch.setattr(
        SVC.MEDIA,
        "resolve_image_bytes_for_edit",
        resolver,
    )

    with pytest.raises(
        SVC.ImageCreationServiceError,
        match="duplicate_source_image_id",
    ):
        asyncio.run(
            SVC.edit_image(
                user_id="user-a",
                character_id="char-a",
                prompt="edit",
                source_image_ids=[
                    image_id,
                    image_id,
                ],
            )
        )

    assert called["media"] is False


def test_edit_path_like_source_rejected_before_media(
    monkeypatch,
):
    install_character(
        monkeypatch
    )

    install_model(
        monkeypatch
    )

    called = {
        "media": False,
    }

    async def fake_source(
        *_args,
        **_kwargs,
    ):
        called["media"] = True
        raise AssertionError(
            "media resolver must not receive path input"
        )

    monkeypatch.setattr(
        SVC.MEDIA,
        "resolve_image_bytes_for_edit",
        fake_source,
    )

    with pytest.raises(
        SVC.ImageCreationServiceError,
        match="invalid_image_id",
    ):
        asyncio.run(
            SVC.edit_image(
                user_id="user-a",
                character_id="char-a",
                conversation_id="conv-a",
                prompt="Edit it",
                source_image_ids=[
                    "../../secret.png"
                ],
            )
        )

    assert called["media"] is False


def test_edit_uppercase_opaque_id_not_normalized(
    monkeypatch,
):
    install_character(
        monkeypatch
    )

    install_model(
        monkeypatch
    )

    image_id = (
        "AAAAAAAAAAAAAAAA"
        "AAAAAAAAAAAAAAAA.png"
    )

    called = {
        "media": False,
    }

    async def fake_source(
        *_args,
        **_kwargs,
    ):
        called["media"] = True
        raise AssertionError(
            "invalid uppercase ID must fail before media"
        )

    monkeypatch.setattr(
        SVC.MEDIA,
        "resolve_image_bytes_for_edit",
        fake_source,
    )

    with pytest.raises(
        SVC.ImageCreationServiceError,
        match="invalid_image_id",
    ):
        asyncio.run(
            SVC.edit_image(
                user_id="user-a",
                character_id="char-a",
                conversation_id="conv-a",
                prompt="Edit it",
                source_image_ids=[
                    image_id
                ],
            )
        )

    assert called["media"] is False


def test_edit_valid_opaque_id_passes_security_gate():
    image_id = (
        "abcdef0123456789"
        "abcdef0123456789.webp"
    )

    result = (
        SVC._validate_edit_source_image_ids(
            (
                image_id,
            )
        )
    )

    assert result == (
        image_id,
    )

import asyncio
from contextlib import asynccontextmanager

import pytest

import ai_service as AI


class _FakeCollection:
    def document(self, _document_id):
        return _FakeDocument()


class _FakeDocument:
    pass


class _FakeDB:
    def collection(self, _name):
        return _FakeCollection()


class _FakeRepo:
    def __init__(self):
        self.db = _FakeDB()


@asynccontextmanager
async def _fake_lock(*_args, **_kwargs):
    yield


class _ExplodingEngine:
    async def respond(self, *_args, **_kwargs):
        raise AssertionError(
            "normal generation must not run"
        )


def _install_base_chat_guards(monkeypatch):
    monkeypatch.setattr(
        AI.RL,
        "check_and_consume",
        lambda *_a, **_k: {
            "allowed": True,
            "reason": None,
            "retryAfter": 0,
        },
    )

    monkeypatch.setattr(
        AI,
        "_live_flags",
        lambda: {
            "aiCharactersEnabled": True,
        },
    )

    fake_repo = _FakeRepo()

    monkeypatch.setattr(
        AI,
        "prod_repo",
        lambda: fake_repo,
    )

    monkeypatch.setattr(
        AI,
        "_chat_lock",
        _fake_lock,
    )

    monkeypatch.setattr(
        AI,
        "prod_engine",
        lambda: _ExplodingEngine(),
    )


def test_explicit_followup_without_history_fails_closed(
    monkeypatch,
):
    _install_base_chat_guards(monkeypatch)

    async def no_refs(*_args, **_kwargs):
        return []

    monkeypatch.setattr(
        AI,
        "_resolve_continuity_image_ids",
        no_refs,
    )

    result = asyncio.run(
        AI.chat(
            "character-a",
            "user-a",
            "same image lo left side enti?",
            conversation_id="conversation-a",
        )
    )

    assert result["ok"] is False
    assert (
        result["error"]
        == "referenced_image_unavailable"
    )
    assert result["needsImageReupload"] is True
    assert result["usage"]["provider"] == "guard"


@pytest.mark.parametrize(
    "storage_error",
    [
        "image_not_found",
        "image_expired",
        "image_scope_mismatch",
    ],
)
def test_stale_continuity_reference_fails_closed(
    monkeypatch,
    storage_error,
):
    _install_base_chat_guards(monkeypatch)

    async def refs(*_args, **_kwargs):
        return [
            "abcdef0123456789abcdef0123456789.png"
        ]

    async def unavailable(*_args, **_kwargs):
        raise ValueError(storage_error)

    monkeypatch.setattr(
        AI,
        "_resolve_continuity_image_ids",
        refs,
    )

    monkeypatch.setattr(
        AI,
        "_prepare_multimodal_context",
        unavailable,
    )

    result = asyncio.run(
        AI.chat(
            "character-a",
            "user-a",
            "same image lo background enti?",
            conversation_id="conversation-a",
        )
    )

    assert result["ok"] is False
    assert (
        result["error"]
        == "referenced_image_unavailable"
    )
    assert result["needsImageReupload"] is True
    assert storage_error not in result["responseText"]


def test_explicit_new_image_error_is_not_rewritten(
    monkeypatch,
):
    _install_base_chat_guards(monkeypatch)

    async def invalid(*_args, **_kwargs):
        raise ValueError("image_not_found")

    monkeypatch.setattr(
        AI,
        "_prepare_multimodal_context",
        invalid,
    )

    result = asyncio.run(
        AI.chat(
            "character-a",
            "user-a",
            "check this image",
            conversation_id="conversation-a",
            image_ids=[
                "abcdef0123456789abcdef0123456789.png"
            ],
        )
    )

    assert result["ok"] is False
    assert result["error"] == "image_not_found"


def test_duplicate_ids_fail_before_storage_resolution(
    monkeypatch,
):
    calls = []

    async def should_not_resolve(*_args, **_kwargs):
        calls.append(True)
        raise AssertionError(
            "storage must not run for duplicate IDs"
        )

    monkeypatch.setattr(
        AI.ai_media,
        "resolve_image_reference",
        should_not_resolve,
    )

    image_id = (
        "abcdef0123456789abcdef0123456789.png"
    )

    with pytest.raises(
        ValueError,
        match="duplicate_image_id",
    ):
        asyncio.run(
            AI._prepare_multimodal_context(
                "character-a",
                "user-a",
                "conversation-a",
                "look",
                [image_id, image_id],
            )
        )

    assert calls == []


def test_unavailable_mapping_is_narrow():
    for value in (
        "image_not_found",
        "image_expired",
        "image_scope_mismatch",
    ):
        assert (
            AI._is_referenced_image_unavailable_error(
                value
            )
            is True
        )

    for value in (
        "stored_image_type_invalid",
        "duplicate_image_id",
        "signed_image_url_invalid",
        "multimodal_provider_failed",
        "",
    ):
        assert (
            AI._is_referenced_image_unavailable_error(
                value
            )
            is False
        )

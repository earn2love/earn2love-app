import asyncio
from pathlib import Path

import ai_service as AI
from ai_engine import multimodal_intelligence as MM13


def test_explicit_image_followup_detection():
    values = [
        "same image lo left side enti?",
        "what is on the left side of that photo?",
        "ee image lo em undi?",
        "what is visible in the previous picture?",
        "who is there in that image?",
        "ee photo lo background enti?",
    ]

    for value in values:
        assert MM13.is_image_followup_reference(
            value
        )


def test_normal_text_does_not_force_continuity():
    values = [
        "hello",
        "how are you",
        "tell me a joke",
        "what did I say yesterday",
        "I like coffee",
    ]

    for value in values:
        assert not MM13.is_image_followup_reference(
            value
        )


def test_extracts_newest_user_image_turn():
    first = "a" * 32 + ".png"
    latest = "b" * 32 + ".jpg"

    turns = [
        {
            "sender": "user",
            "text": "first",
            "imageIds": [first],
        },
        {
            "sender": "character",
            "text": "reply",
        },
        {
            "sender": "user",
            "text": "second",
            "imageIds": [latest],
        },
        {
            "sender": "character",
            "text": "reply",
        },
    ]

    assert MM13.extract_turn_image_ids(
        turns
    ) == [latest]


def test_character_turn_cannot_authorize_image_reuse():
    image_id = "c" * 32 + ".webp"

    assert MM13.extract_turn_image_ids(
        [
            {
                "sender": "character",
                "imageIds": [image_id],
            }
        ]
    ) == []


def test_visual_summary_cannot_authorize_image_reuse():
    assert MM13.extract_turn_image_ids(
        [
            {
                "sender": "user",
                "visualSummary":
                    "old generated description",
            }
        ]
    ) == []


def test_continuity_policy():
    policy = MM13.continuity_policy()

    assert policy["conversationScoped"]
    assert policy["userScoped"]
    assert policy["characterScoped"]
    assert policy["persistImageIdsOnly"]

    assert not policy["persistVisualSummary"]
    assert not policy["persistSignedUrls"]
    assert not policy["persistImageBytes"]

    assert policy["reanalyzeActualImage"]
    assert policy["failClosedIfUnavailable"]


def test_exact_scope_repository_lookup(
    monkeypatch,
):
    calls = []

    image_id = "d" * 32 + ".png"

    class FakeRepo:
        def get_turns(
            self,
            character_id,
            user_id,
            limit=None,
            conversation_id="default",
        ):
            calls.append(
                (
                    character_id,
                    user_id,
                    limit,
                    conversation_id,
                )
            )

            return [
                {
                    "sender": "user",
                    "imageIds": [image_id],
                }
            ]

    monkeypatch.setattr(
        AI,
        "prod_repo",
        lambda: FakeRepo(),
    )

    result = asyncio.run(
        AI._resolve_continuity_image_ids(
            "character-a",
            "user-a",
            "conversation-a",
            "same image lo enti?",
        )
    )

    assert result == [image_id]

    assert calls == [
        (
            "character-a",
            "user-a",
            MM13.MAX_CONTINUITY_LOOKBACK_TURNS,
            "conversation-a",
        )
    ]


def test_normal_message_does_not_query_repository(
    monkeypatch,
):
    class FakeRepo:
        def get_turns(
            self,
            *args,
            **kwargs,
        ):
            raise AssertionError(
                "must not query history"
            )

    monkeypatch.setattr(
        AI,
        "prod_repo",
        lambda: FakeRepo(),
    )

    result = asyncio.run(
        AI._resolve_continuity_image_ids(
            "character",
            "user",
            "conversation",
            "hello how are you",
        )
    )

    assert result == []


def test_followup_reuses_actual_image_pipeline():
    source = Path(
        "backend/ai_service.py"
    ).read_text(
        encoding="utf-8-sig"
    )

    assert "effective_image_ids" in source
    assert "await _prepare_multimodal_context(" in source

    section = source.split(
        "async def _resolve_continuity_image_ids(",
        1,
    )[1].split(
        "async def _prepare_multimodal_context(",
        1,
    )[0]

    assert "visualSummary" not in section


def test_user_turn_only_persists_opaque_ids():
    source = Path(
        "backend/ai_engine/engine.py"
    ).read_text(
        encoding="utf-8-sig"
    )

    marker = (
        "# V13.4 persist opaque image references on the user turn only."
    )

    assert marker in source

    pos = source.index(
        marker
    )

    section = source[
        pos:
        pos + 1000
    ]

    assert 'user_turn["imageIds"]' in section

    for forbidden in (
        "visualSummary",
        "signedUrl",
        "image_url",
        "imageBytes",
    ):
        assert forbidden not in section


def test_no_firestore_collection_in_multimodal_module():
    source = Path(
        "backend/ai_engine/multimodal_intelligence.py"
    ).read_text(
        encoding="utf-8-sig"
    )

    assert ".collection(" not in source


def test_no_provider_boundary_in_continuity_module():
    source = Path(
        "backend/ai_engine/multimodal_intelligence.py"
    ).read_text(
        encoding="utf-8-sig"
    )

    assert "AsyncOpenAI" not in source
    assert "responses.create" not in source
    assert "litellm." not in source

import asyncio
from pathlib import Path

import pytest

import ai_service as AI
from ai_engine import multimodal_intelligence as MM13


def test_visual_context_is_ephemeral():
    value = MM13.build_grounded_visual_context(
        "A blue cup is visible.",
        image_count=1,
        scope_token="scope",
    )

    lower = value.casefold()

    assert "blue cup" in lower
    assert "ephemeral" in lower
    assert "durable personal memory" in lower


def test_empty_summary_rejected():
    with pytest.raises(
        ValueError,
        match="empty_visual_summary",
    ):
        MM13.build_grounded_visual_context(
            "",
            image_count=1,
        )


def test_zero_images_rejected():
    with pytest.raises(
        ValueError,
        match="visual_image_count_required",
    ):
        MM13.build_grounded_visual_context(
            "visible object",
            image_count=0,
        )


def test_visual_summary_is_bounded():
    value = MM13.normalize_visual_summary(
        "x"
        * (
            MM13.MAX_VISUAL_SUMMARY_LENGTH
            + 500
        )
    )

    assert len(
        value
    ) == MM13.MAX_VISUAL_SUMMARY_LENGTH


def test_prepare_uses_exact_authenticated_scope(
    monkeypatch,
):
    calls = []

    async def fake_resolve(
        image_id,
        *,
        user_id,
        character_id,
        conversation_id,
        detail,
    ):
        calls.append(
            (
                image_id,
                user_id,
                character_id,
                conversation_id,
                detail,
            )
        )

        return {
            "imageId": image_id,
            "url":
                "https://example.test/image.png",
            "mimeType": "image/png",
            "detail": detail,
        }

    async def fake_analyze(
        system_message,
        user_prompt,
        image_inputs,
        *,
        provider,
        model,
        **kwargs,
    ):
        assert (
            image_inputs[0]["type"]
            == "input_image"
        )

        return {
            "ok": True,
            "text":
                "A red bicycle is visible.",
            "provider":
                provider,
            "model":
                model,
            "latencyMs":
                10,
        }

    monkeypatch.setattr(
        AI.ai_media,
        "resolve_image_reference",
        fake_resolve,
    )

    monkeypatch.setattr(
        AI.PROV,
        "analyze_images",
        fake_analyze,
    )

    image_id = (
        "a"
        * 32
        + ".png"
    )

    result = asyncio.run(
        AI._prepare_multimodal_context(
            "character-a",
            "user-a",
            "conversation-a",
            "What is shown?",
            [
                image_id
            ],
        )
    )

    assert (
        result["visualSummary"]
        == "A red bicycle is visible."
    )

    assert result["imageCount"] == 1

    assert calls == [
        (
            image_id,
            "user-a",
            "character-a",
            "conversation-a",
            "auto",
        )
    ]


def test_prepare_rejects_too_many_images():
    with pytest.raises(
        ValueError,
        match="too_many_images",
    ):
        asyncio.run(
            AI._prepare_multimodal_context(
                "c",
                "u",
                "conversation",
                "look",
                [
                    f"{i:032x}.png"
                    for i in range(
                        5
                    )
                ],
            )
        )


def test_provider_failure_fails_closed(
    monkeypatch,
):
    async def fake_resolve(
        image_id,
        **kwargs,
    ):
        return {
            "imageId": image_id,
            "url":
                "https://example.test/image.png",
            "mimeType": "image/png",
            "detail": "auto",
        }

    async def fake_analyze(
        *args,
        **kwargs,
    ):
        return {
            "ok": False,
            "text": "",
            "provider": "openai",
            "model": "vision",
            "error":
                "provider_timeout",
        }

    monkeypatch.setattr(
        AI.ai_media,
        "resolve_image_reference",
        fake_resolve,
    )

    monkeypatch.setattr(
        AI.PROV,
        "analyze_images",
        fake_analyze,
    )

    with pytest.raises(
        RuntimeError,
        match="multimodal_provider_failed",
    ):
        asyncio.run(
            AI._prepare_multimodal_context(
                "c",
                "u",
                "conversation",
                "look",
                [
                    "0" * 32
                    + ".png"
                ],
            )
        )


def test_engine_context_is_system_only():
    source = Path(
        "backend/ai_engine/engine.py"
    ).read_text(
        encoding="utf-8-sig"
    )

    grounding_start = source.find(
        "# V13.3 ephemeral multimodal grounding."
    )

    prompt_build = source.find(
        "        sys = build_system_prompt("
    )

    visual_append = source.find(
        "V13_MULTIMODAL_INTELLIGENCE:"
    )

    generation = source.find(
        "        result, quality, attempts = await self._generate_guarded("
    )

    assert grounding_start >= 0
    assert prompt_build > grounding_start
    assert visual_append > prompt_build
    assert generation > visual_append

    grounding_section = source[
        grounding_start:
        prompt_build
    ]

    assert (
        "MM13.build_grounded_visual_context"
        in grounding_section
    )

    # V13 visual processing itself must not mutate durable
    # memory/adaptation/goal/plan/turn state.
    forbidden = [
        "add_memory(",
        "save_structured_memory(",
        "reinforce_memory(",
        "revise_memories(",
        "advance_adaptation(",
        "advance_goal_state(",
        "advance_plan_state(",
        "append_turn(",
    ]

    for marker in forbidden:
        assert marker not in grounding_section

    append_section = source[
        prompt_build:
        generation
    ]

    assert (
        "V13_MULTIMODAL_INTELLIGENCE"
        in append_section
    )

    assert (
        "v13_multimodal_context"
        in append_section
    )


def test_generate_guarded_not_extended_for_multimodal():
    import ast

    tree = ast.parse(
        Path(
            "backend/ai_engine/engine.py"
        ).read_text(
            encoding="utf-8-sig"
        )
    )

    target = None

    for node in ast.walk(
        tree
    ):
        if (
            isinstance(
                node,
                ast.AsyncFunctionDef,
            )
            and node.name
            == "_generate_guarded"
        ):
            target = node
            break

    assert target is not None

    names = [
        arg.arg
        for arg in (
            target.args.args
            + target.args.kwonlyargs
        )
    ]

    assert (
        "multimodal_context"
        not in names
    )

    assert (
        "image_inputs"
        not in names
    )


def test_chat_api_accepts_ids_not_urls():
    source = Path(
        "backend/server.py"
    ).read_text(
        encoding="utf-8-sig"
    )

    body = source.split(
        "class AiChatBody(BaseModel):",
        1,
    )[1].split(
        "def client_ip",
        1,
    )[0]

    assert (
        "imageIds: list[str] | None = None"
        in body
    )

    assert "imageUrls" not in body
    assert "signedUrl" not in body


def test_response_metadata_does_not_expose_visual_summary():
    source = Path(
        "backend/ai_service.py"
    ).read_text(
        encoding="utf-8-sig"
    )

    section = source.split(
        'r["multimodal"] = {',
        1,
    )[1].split(
        "if client_message_id:",
        1,
    )[0]

    assert (
        "visualSummary"
        not in section
    )

    assert (
        "signed"
        not in section.casefold()
    )


def test_multimodal_preparation_has_no_firestore_state_write():
    source = Path(
        "backend/ai_service.py"
    ).read_text(
        encoding="utf-8-sig"
    )

    section = source.split(
        "async def _prepare_multimodal_context(",
        1,
    )[1].split(
        "_prod_engine = None",
        1,
    )[0]

    for marker in (
        ".collection(",
        "add_memory(",
        "save_structured_memory(",
        "advance_adaptation(",
        "advance_goal_state(",
        "append_turn(",
    ):
        assert marker not in section


def test_multimodal_context_is_appended_after_base_system_prompt():
    source = Path(
        "backend/ai_engine/engine.py"
    ).read_text(
        encoding="utf-8-sig"
    )

    build_pos = source.find(
        "        sys = build_system_prompt("
    )

    visual_pos = source.find(
        "V13_MULTIMODAL_INTELLIGENCE:"
    )

    assert build_pos >= 0
    assert visual_pos >= 0

    # Critical V13.3 regression guard:
    # visual grounding must survive base prompt construction.
    assert visual_pos > build_pos

    assert source.count(
        "V13_MULTIMODAL_INTELLIGENCE:"
    ) == 1


def test_multimodal_context_not_added_to_user_prompt():
    source = Path(
        "backend/ai_engine/engine.py"
    ).read_text(
        encoding="utf-8-sig"
    )

    visual_pos = source.find(
        "V13_MULTIMODAL_INTELLIGENCE:"
    )

    prompt_pos = source.find(
        'prompt = (f"Recent conversation:'
    )

    assert visual_pos >= 0
    assert prompt_pos >= 0

    visual_section = source[
        visual_pos:
        prompt_pos
    ]

    assert (
        "Latest message from the person"
        not in visual_section
    )


def test_v13_visual_context_remains_outside_v11_memory():
    source = Path(
        "backend/ai_engine/engine.py"
    ).read_text(
        encoding="utf-8-sig"
    )

    start = source.find(
        "# V13.3 ephemeral multimodal grounding."
    )

    end = source.find(
        "# 6. build prompt + transcript.",
        start,
    )

    assert start >= 0
    assert end > start

    section = source[
        start:end
    ]

    for forbidden in (
        "add_memory(",
        "save_structured_memory(",
        "reinforce_memory(",
        "revise_memories(",
        "advance_adaptation(",
        "advance_goal_state(",
        "advance_plan_state(",
        "append_turn(",
    ):
        assert forbidden not in section

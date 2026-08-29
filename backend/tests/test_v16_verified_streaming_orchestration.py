import asyncio
import inspect
import pytest

from ai_engine import buffered_streaming_generation as BSG
from ai_engine import verified_streaming_orchestration as VSO


class CaptureEngine:
    def __init__(self):
        self.calls = []

    async def respond(
        self,
        character_id,
        user_id,
        user_text,
        *,
        sandbox=False,
        language_override=None,
        relationship_override=None,
        history_fixture=None,
        feature_flags=None,
        conversation_id="default",
        multimodal_context=None,
        _generation_callable=None,
    ):
        self.calls.append({
            "character_id": character_id,
            "user_id": user_id,
            "user_text": user_text,
            "sandbox": sandbox,
            "language_override": language_override,
            "relationship_override": relationship_override,
            "history_fixture": history_fixture,
            "feature_flags": feature_flags,
            "conversation_id": conversation_id,
            "multimodal_context": multimodal_context,
            "generation_callable": _generation_callable,
        })

        return {
            "ok": True,
            "text": "verified final response",
        }


def test_marker():
    assert VSO.V16_2_VERIFIED_STREAMING_ORCHESTRATION is True


def test_buffered_callable_injected():
    engine = CaptureEngine()

    async def execute():
        return await VSO.respond_with_buffered_stream(
            engine,
            "character-A",
            "user-A",
            "hello",
            conversation_id="conversation-A",
        )

    result = asyncio.run(execute())

    assert result["ok"] is True
    assert len(engine.calls) == 1
    assert (
        engine.calls[0]["generation_callable"]
        is BSG.generate_buffered_stream
    )


def test_scope_forwarding():
    engine = CaptureEngine()

    history = [{"sender": "user", "text": "earlier"}]
    flags = {"advancedMemoryEnabled": True}
    multimodal = {"opaque": "context"}

    async def execute():
        await VSO.respond_with_buffered_stream(
            engine,
            "character-X",
            "user-Y",
            "message-Z",
            sandbox=True,
            language_override="te",
            relationship_override="trusted",
            history_fixture=history,
            feature_flags=flags,
            conversation_id="conversation-Q",
            multimodal_context=multimodal,
        )

    asyncio.run(execute())

    call = engine.calls[0]

    assert call["character_id"] == "character-X"
    assert call["user_id"] == "user-Y"
    assert call["conversation_id"] == "conversation-Q"
    assert call["sandbox"] is True
    assert call["history_fixture"] is history
    assert call["feature_flags"] is flags
    assert call["multimodal_context"] is multimodal


def test_engine_required():
    async def execute():
        await VSO.respond_with_buffered_stream(
            None, "character", "user", "hello"
        )

    with pytest.raises(ValueError, match="engine_required"):
        asyncio.run(execute())


def test_engine_respond_required():
    async def execute():
        await VSO.respond_with_buffered_stream(
            object(), "character", "user", "hello"
        )

    with pytest.raises(ValueError, match="engine_respond_required"):
        asyncio.run(execute())


def test_no_direct_provider_boundary():
    source = inspect.getsource(VSO)

    assert "PROV.generate(" not in source
    assert "PROV.generate_stream(" not in source
    assert "BSG16.generate_buffered_stream" in source

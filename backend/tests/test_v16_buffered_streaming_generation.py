import asyncio
import inspect
from types import SimpleNamespace

import pytest

from ai_engine import provider as PROV
from ai_engine import engine as ENGINE
from ai_engine import buffered_streaming_generation as BSG
from ai_engine.engine import CharacterEngine


def make_event(
    kind,
    *,
    text="",
    ok=True,
    provider="router-provider",
    model="router-model",
    latency=3,
    usage=None,
    error=None,
):
    return PROV.ProviderResult(
        ok=ok,
        event=kind,
        text=text,
        provider=provider,
        model=model,
        latencyMs=latency,
        usage=usage or {},
        finishReason=(
            "stop"
            if kind == "completed"
            else None
        ),
        error=error,
    )


def install_guards(monkeypatch):
    monkeypatch.setattr(
        ENGINE.G,
        "repetition_check",
        lambda text, recent: (
            True,
            "ok",
            None,
        ),
    )

    monkeypatch.setattr(
        ENGINE.G,
        "consistency_check",
        lambda text, character, recent: (
            True,
            "ok",
        ),
    )

    monkeypatch.setattr(
        ENGINE.G,
        "safety_check",
        lambda text: (
            True,
            "ok",
            None,
        ),
    )

    monkeypatch.setattr(
        ENGINE.G,
        "quality_penalty",
        lambda text: 0,
    )

    monkeypatch.setattr(
        ENGINE.CI,
        "response_quality_check",
        lambda text, guidance, recent: (
            True,
            "ok",
        ),
    )

    monkeypatch.setattr(
        ENGINE.RI,
        "relationship_response_safety",
        lambda text: (
            True,
            "ok",
        ),
    )

    monkeypatch.setattr(
        ENGINE.RL10,
        "decide_reliability",
        lambda **kwargs: SimpleNamespace(
            action="accept",
            confidence=1.0,
        ),
    )


def guarded_kwargs():
    return {
        "sys": "system",
        "prompt": "prompt",
        "c": {},
        "recent_ai": [],
        "plan": {
            "targetLength": "short",
        },
        "session_id": "opaque-session",
        "routing": {
            "provider": "router-provider",
            "model": "router-model",
        },
        "conversation_guidance": None,
        "relationship_guidance": None,
        "personality_fingerprint": None,
        "adaptation_guidance": None,
        "orchestration_guidance": None,
    }


def test_marker():
    assert BSG.V16_2_BUFFERED_STREAMING_GENERATION is True


def test_signature_matches_engine_seam():
    sig = inspect.signature(
        BSG.generate_buffered_stream
    )

    for name in (
        "system_message",
        "user_prompt",
        "session_id",
        "provider",
        "model",
    ):
        assert name in sig.parameters


def test_buffers_provider_deltas(monkeypatch):

    async def fake_stream(*args, **kwargs):
        yield make_event(
            "delta",
            text="Hello ",
            latency=2,
        )

        yield make_event(
            "delta",
            text="there",
            latency=4,
        )

        yield make_event(
            "completed",
            latency=8,
            usage={
                "total_tokens": 7,
            },
        )

    monkeypatch.setattr(
        PROV,
        "generate_stream",
        fake_stream,
    )

    async def execute():
        return await BSG.generate_buffered_stream(
            "system",
            "prompt",
            session_id="session-1",
            provider="router-provider",
            model="router-model",
        )

    result = asyncio.run(execute())

    assert result["ok"] is True
    assert result["text"] == "Hello there"
    assert result["provider"] == "router-provider"
    assert result["model"] == "router-model"
    assert result["latencyMs"] == 8

    assert result["usage"] == {
        "total_tokens": 7,
    }


def test_completion_only_text(monkeypatch):

    async def fake_stream(*args, **kwargs):
        yield make_event(
            "completed",
            text="Final only",
            latency=5,
        )

    monkeypatch.setattr(
        PROV,
        "generate_stream",
        fake_stream,
    )

    async def execute():
        return await BSG.generate_buffered_stream(
            "system",
            "prompt",
            session_id="session-2",
            provider="router-provider",
            model="router-model",
        )

    result = asyncio.run(execute())

    assert result["ok"] is True
    assert result["text"] == "Final only"


def test_error_discards_partial_output(monkeypatch):

    async def fake_stream(*args, **kwargs):
        yield make_event(
            "delta",
            text="partial",
        )

        yield make_event(
            "error",
            ok=False,
            error="provider_stream_timeout",
        )

    monkeypatch.setattr(
        PROV,
        "generate_stream",
        fake_stream,
    )

    async def execute():
        return await BSG.generate_buffered_stream(
            "system",
            "prompt",
            session_id="session-3",
            provider="router-provider",
            model="router-model",
        )

    result = asyncio.run(execute())

    assert result["ok"] is False
    assert result["text"] == ""
    assert result["error"] == "provider_stream_timeout"


def test_incomplete_stream_fails_closed(monkeypatch):

    async def fake_stream(*args, **kwargs):
        yield make_event(
            "delta",
            text="unfinished",
        )

    monkeypatch.setattr(
        PROV,
        "generate_stream",
        fake_stream,
    )

    async def execute():
        return await BSG.generate_buffered_stream(
            "system",
            "prompt",
            session_id="session-4",
            provider="router-provider",
            model="router-model",
        )

    result = asyncio.run(execute())

    assert result["ok"] is False
    assert result["text"] == ""
    assert result["error"] == "provider_stream_incomplete"


def test_unknown_event_fails_closed(monkeypatch):

    async def fake_stream(*args, **kwargs):
        yield make_event(
            "mystery",
            text="bad",
        )

    monkeypatch.setattr(
        PROV,
        "generate_stream",
        fake_stream,
    )

    async def execute():
        return await BSG.generate_buffered_stream(
            "system",
            "prompt",
            session_id="session-5",
            provider="router-provider",
            model="router-model",
        )

    result = asyncio.run(execute())

    assert result["ok"] is False

    assert result["error"] == (
        "provider_stream_protocol_error:"
        "unknown_event"
    )


def test_requires_explicit_provider_model_session():

    async def missing_provider():
        return await BSG.generate_buffered_stream(
            "system",
            "prompt",
            session_id="session",
            provider="",
            model="model",
        )

    async def missing_model():
        return await BSG.generate_buffered_stream(
            "system",
            "prompt",
            session_id="session",
            provider="provider",
            model="",
        )

    async def missing_session():
        return await BSG.generate_buffered_stream(
            "system",
            "prompt",
            session_id="",
            provider="provider",
            model="model",
        )

    a = asyncio.run(missing_provider())
    b = asyncio.run(missing_model())
    c = asyncio.run(missing_session())

    assert a["error"] == "stream_provider_required"
    assert b["error"] == "stream_model_required"
    assert c["error"] == "stream_session_required"


def test_cancellation_propagates(monkeypatch):

    async def fake_stream(*args, **kwargs):
        raise asyncio.CancelledError()

        if False:
            yield None

    monkeypatch.setattr(
        PROV,
        "generate_stream",
        fake_stream,
    )

    async def execute():
        return await BSG.generate_buffered_stream(
            "system",
            "prompt",
            session_id="session-6",
            provider="router-provider",
            model="router-model",
        )

    with pytest.raises(asyncio.CancelledError):
        asyncio.run(execute())


def test_adapter_runs_through_existing_engine_guards(
    monkeypatch,
):
    install_guards(monkeypatch)

    observed = {}

    async def fake_stream(
        system_message,
        user_prompt,
        *,
        session_id,
        provider,
        model,
        timeout_seconds=None,
    ):
        observed.update(
            {
                "system": system_message,
                "prompt": user_prompt,
                "session": session_id,
                "provider": provider,
                "model": model,
            }
        )

        yield make_event(
            "delta",
            text="Engine ",
            provider=provider,
            model=model,
        )

        yield make_event(
            "delta",
            text="verified",
            provider=provider,
            model=model,
        )

        yield make_event(
            "completed",
            provider=provider,
            model=model,
            latency=9,
        )

    monkeypatch.setattr(
        PROV,
        "generate_stream",
        fake_stream,
    )

    engine = CharacterEngine(object())

    async def execute():
        return await engine._generate_guarded(
            **guarded_kwargs(),
            generation_callable=(
                BSG.generate_buffered_stream
            ),
        )

    result, quality, attempts = asyncio.run(execute())

    assert result["ok"] is True
    assert result["text"] == "Engine verified"
    assert attempts == 1
    assert quality["safetyPassed"] is True

    assert observed == {
        "system": "system",
        "prompt": "prompt",
        "session": "opaque-session",
        "provider": "router-provider",
        "model": "router-model",
    }


def test_no_persistence_transport_or_voice():
    source = inspect.getsource(
        BSG
    ).casefold()

    forbidden = (
        ".collection(",
        "firestore",
        "append_turn(",
        "advance_goal_state(",
        "advance_plan_state(",
        "advance_adaptation(",
        "r.advance(",
        "streamingresponse(",
        "eventsourceresponse(",
        "text/event-stream",
        "websocket(",
        "agora",
        "tts",
        "stt",
    )

    for token in forbidden:
        assert token not in source

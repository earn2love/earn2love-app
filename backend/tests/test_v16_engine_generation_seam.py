import asyncio
import inspect
from types import SimpleNamespace

from ai_engine.engine import CharacterEngine
from ai_engine import engine as ENGINE
from ai_engine import provider as PROV


def install_passing_guards(monkeypatch):
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


def make_result(
    text,
    provider,
    model,
    latency=5,
):
    return PROV.ProviderResult(
        ok=True,
        text=text,
        provider=provider,
        model=model,
        latencyMs=latency,
        usage={},
        error=None,
    )


def test_private_respond_generation_parameter_exists():
    sig = inspect.signature(
        CharacterEngine.respond
    )

    assert "_generation_callable" in sig.parameters

    assert (
        sig.parameters[
            "_generation_callable"
        ].default
        is None
    )


def test_guarded_generation_parameter_exists():
    sig = inspect.signature(
        CharacterEngine._generate_guarded
    )

    assert "generation_callable" in sig.parameters

    assert (
        sig.parameters[
            "generation_callable"
        ].default
        is None
    )


def test_normal_provider_boundary_literal_preserved():
    source = inspect.getsource(
        ENGINE
    )

    assert "PROV.generate(" in source


def test_default_guarded_path_uses_prov_generate(
    monkeypatch,
):
    install_passing_guards(
        monkeypatch
    )

    calls = []

    async def fake_generate(
        system_message,
        user_prompt,
        session_id="char",
        provider=None,
        model=None,
    ):
        calls.append(
            {
                "system": system_message,
                "prompt": user_prompt,
                "session": session_id,
                "provider": provider,
                "model": model,
            }
        )

        return make_result(
            "normal",
            provider,
            model,
            4,
        )

    monkeypatch.setattr(
        PROV,
        "generate",
        fake_generate,
    )

    engine = CharacterEngine(
        object()
    )

    async def execute():
        return await engine._generate_guarded(
            **guarded_kwargs()
        )

    result, quality, attempts = asyncio.run(
        execute()
    )

    assert result["ok"] is True
    assert result["text"] == "normal"
    assert attempts == 1

    assert calls == [
        {
            "system": "system",
            "prompt": "prompt",
            "session": "opaque-session",
            "provider": "router-provider",
            "model": "router-model",
        }
    ]

    assert quality[
        "safetyPassed"
    ] is True


def test_injected_path_does_not_call_prov_generate(
    monkeypatch,
):
    install_passing_guards(
        monkeypatch
    )

    async def forbidden_generate(
        *args,
        **kwargs,
    ):
        raise AssertionError(
            "PROV.generate must not be called "
            "when injection is explicit"
        )

    monkeypatch.setattr(
        PROV,
        "generate",
        forbidden_generate,
    )

    observed = []

    async def injected(
        system_message,
        user_prompt,
        session_id="char",
        provider=None,
        model=None,
    ):
        observed.append(
            (
                session_id,
                provider,
                model,
            )
        )

        return make_result(
            "injected",
            provider,
            model,
            6,
        )

    engine = CharacterEngine(
        object()
    )

    async def execute():
        return await engine._generate_guarded(
            **guarded_kwargs(),
            generation_callable=injected,
        )

    result, _, attempts = asyncio.run(
        execute()
    )

    assert result["ok"] is True
    assert result["text"] == "injected"
    assert attempts == 1

    assert observed == [
        (
            "opaque-session",
            "router-provider",
            "router-model",
        )
    ]


def test_injected_generation_still_runs_repair_loop(
    monkeypatch,
):
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
            False,
            "blocked",
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
            action="repair",
            confidence=0.5,
        ),
    )

    calls = []

    async def injected(
        system_message,
        user_prompt,
        session_id="char",
        provider=None,
        model=None,
    ):
        calls.append(
            {
                "system": system_message,
                "provider": provider,
                "model": model,
            }
        )

        return make_result(
            "candidate",
            provider,
            model,
        )

    engine = CharacterEngine(
        object()
    )

    async def execute():
        return await engine._generate_guarded(
            **guarded_kwargs(),
            generation_callable=injected,
        )

    result, quality, attempts = asyncio.run(
        execute()
    )

    assert result["ok"] is True
    assert attempts == 2
    assert len(calls) == 2

    assert quality[
        "safetyPassed"
    ] is False

    # Existing repair prompt must be added.
    assert calls[1]["system"] != "system"


def test_normal_respond_dispatch_preserves_old_guarded_signature():
    source = inspect.getsource(
        CharacterEngine.respond
    )

    assert "if _generation_callable is None:" in source

    normal_branch = source.split(
        "if _generation_callable is None:",
        1,
    )[1].split(
        "else:",
        1,
    )[0]

    assert (
        "generation_callable="
        not in normal_branch
    )


def test_engine_has_no_stream_transport():
    source = inspect.getsource(
        ENGINE
    )

    forbidden = (
        "StreamingResponse(",
        "EventSourceResponse(",
        "text/event-stream",
        "WebSocket(",
    )

    for token in forbidden:
        assert token not in source

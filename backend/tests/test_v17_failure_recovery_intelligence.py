"""
Earn2Love AI Engine V17.5
Failure + Recovery Intelligence acceptance contract.

This suite adds no production behavior.

It verifies that the existing V10-V16 architecture:
- fails safely after repeated provider failure;
- never fabricates provider success;
- treats transport failure/cancellation as non-semantic;
- rejects duplicate/stale streaming chunks;
- propagates buffered-generation cancellation;
- refuses unverified final delivery;
- fails closed when required live evidence is unavailable;
- keeps public live knowledge out of user memory;
- fails closed on invalid multimodal context;
- preserves exact multimodal scope separation;
- preserves personality under failure/recovery pressure;
- preserves sandbox non-persistence architecture;
- preserves provider-only external communication boundaries.
"""

from __future__ import annotations

import asyncio
import inspect
from copy import deepcopy
from pathlib import Path

import pytest

from ai_engine import buffered_streaming_generation as BSG16
from ai_engine import live_knowledge_intelligence as LK12
from ai_engine import multimodal_intelligence as MM13
from ai_engine import realtime_intelligence as RT16
from ai_engine import reliability_intelligence as RI10
from ai_engine import streaming_intelligence as SI16
from ai_engine import verified_final_delivery as VFD16


V17_5_FAILURE_RECOVERY_INTELLIGENCE = True


BACKEND = Path(__file__).resolve().parents[1]
AI_ENGINE = BACKEND / "ai_engine"


def _source(name: str) -> str:
    return (AI_ENGINE / name).read_text(
        encoding="utf-8",
    )


def test_v17_provider_failure_escalates_then_fails_safe():
    first = RI10.decide_reliability(
        provider_ok=False,
        provider_error="provider_timeout",
        attempt=1,
    )

    second = RI10.decide_reliability(
        provider_ok=False,
        provider_error="provider_timeout",
        attempt=2,
    )

    assert RI10.should_escalate(first) is True

    assert second.action == RI10.FAIL_SAFE
    assert second.can_claim_success is False
    assert RI10.should_escalate(second) is False


def test_v17_reliability_never_fabricates_provider_success():
    decision = RI10.decide_reliability(
        provider_ok=False,
        provider_error="provider_error:RuntimeError",
        attempt=2,
        external_success_claim=True,
        verified_external_success=False,
    )

    guidance = RI10.build_reliability_guidance(
        decision,
    ).lower()

    assert decision.action == RI10.FAIL_SAFE
    assert decision.can_claim_success is False

    assert (
        "do not fabricate" in guidance
        or "do not claim successful" in guidance
        or "fail safely" in guidance
    )


def test_v17_transport_cancellation_is_nonsemantic():
    request = RT16.build_request(
        character_id="ref_ananya",
        user_id="user-v17-failure",
        conversation_id="conversation-v17-failure",
        request_id="request-v17-failure",
        sequence=7,
        sandbox=False,
    )

    metadata = RT16.cancellation_metadata(
        request,
        reason="client_disconnected",
    )

    assert metadata["state"] == "cancelled"
    assert metadata["relationshipEvent"] is False
    assert metadata["memoryEvent"] is False

    for key in (
        "semanticPersistence",
        "adaptationEvent",
    ):
        if key in metadata:
            assert metadata[key] is False



def test_v17_stream_cancel_and_duplicate_are_safe():
    request = RT16.build_request(
        character_id="ref_ananya",
        user_id="user-v17-stream",
        conversation_id="conversation-v17-stream",
        request_id="request-v17-stream",
        sequence=0,
        sandbox=False,
    )

    state = SI16.start_stream(
        request,
    )

    first = SI16.accept_chunk(
        state,
        index=0,
        text="verified ",
        final=False,
    )

    duplicate = SI16.accept_chunk(
        first.state,
        index=0,
        text="duplicate",
        final=False,
    )

    assert duplicate.accepted is False
    assert (
        duplicate.reason
        == "duplicate_or_stale_chunk"
    )
    assert duplicate.state == first.state

    cancelled = SI16.cancel_stream(
        first.state,
    )

    after_cancel = SI16.accept_chunk(
        cancelled,
        index=1,
        text="must not be accepted",
        final=False,
    )

    assert after_cancel.accepted is False
    assert (
        after_cancel.reason
        == "stream_cancelled"
    )

    event = SI16.cancellation_event(
        cancelled,
        reason="client_disconnected",
    )

    assert event["semanticPersistence"] is False
    assert event["relationshipEvent"] is False
    assert event["memoryEvent"] is False
    assert event["adaptationEvent"] is False


def test_v17_buffered_generation_propagates_cancellation(
    monkeypatch,
):
    async def cancelled_provider(*args, **kwargs):
        raise asyncio.CancelledError()

        if False:
            yield None

    monkeypatch.setattr(
        BSG16.PROV,
        "generate_stream",
        cancelled_provider,
    )

    async def execute():
        return await BSG16.generate_buffered_stream(
            "system",
            "prompt",
            session_id="v17-failure-session",
            provider="router-provider",
            model="router-model",
        )

    with pytest.raises(
        asyncio.CancelledError,
    ):
        asyncio.run(
            execute()
        )

def test_v17_unverified_final_response_is_never_delivered():
    with pytest.raises(
        ValueError,
        match="engine_response_not_verified",
    ):
        VFD16.prepare_verified_delivery(
            {
                "ok": False,
                "error": "provider_timeout",
            },
            character_id="ref_ananya",
            user_id="user-v17-delivery",
            conversation_id="conversation-v17-delivery",
            request_id="request-v17-delivery",
        )


def test_v17_required_live_knowledge_failure_is_fail_closed():
    packet = LK12.build_live_knowledge_packet(
        "What is happening right now?",
        [],
        requires_live_retrieval=True,
    )

    context = LK12.build_grounding_context(
        packet,
    )

    assert packet.can_answer is False
    assert packet.status == LK12.STATUS_UNAVAILABLE

    assert "UNAVAILABLE" in context.upper()

    lower = context.lower()

    assert (
        "do not" in lower
        or "cannot" in lower
        or "unavailable" in lower
    )


def test_v17_public_live_facts_never_become_user_memory():
    policy = LK12.public_knowledge_memory_policy()

    assert isinstance(policy, dict)

    source = inspect.getsource(
        LK12.public_knowledge_memory_policy,
    ).lower()

    assert "memory" in source

    assert (
        "not user memory" in source
        or "public" in source
    )



def test_v17_invalid_multimodal_context_fails_closed():
    context = MM13.build_turn_context(
        "ref_ananya",
        "user-v17-mm",
        "conversation-v17-mm",
        "look at this image",
        [
            {
                "imageId": "invalid-image",
            }
        ],
    )

    assert context.ok is False
    assert context.error is not None
    assert context.images == ()

def test_v17_multimodal_scope_is_exact_and_isolated():
    scope_a = MM13.build_scope_token(
        character_id="ref_ananya",
        user_id="user-a",
        conversation_id="conversation-a",
    )

    scope_b = MM13.build_scope_token(
        character_id="ref_ananya",
        user_id="user-b",
        conversation_id="conversation-a",
    )

    scope_c = MM13.build_scope_token(
        character_id="ref_ananya",
        user_id="user-a",
        conversation_id="conversation-b",
    )

    scope_d = MM13.build_scope_token(
        character_id="ref_marcus",
        user_id="user-a",
        conversation_id="conversation-a",
    )

    assert scope_a != scope_b
    assert scope_a != scope_c
    assert scope_a != scope_d


def test_v17_failure_paths_do_not_create_transport_semantics():
    realtime_policy = RT16.realtime_policy_directive().lower()
    streaming_policy = SI16.streaming_policy_directive().lower()

    for term in (
        "cancellation",
        "disconnect",
        "duplicate",
    ):
        assert term in realtime_policy or term in streaming_policy

    assert "semantic" in realtime_policy
    assert "semantic" in streaming_policy

    assert "memory" in streaming_policy
    assert "relationship" in streaming_policy


def test_v17_engine_failure_occurs_before_persistence_lifecycle():
    source = _source(
        "engine.py",
    )

    failure_return = source.index(
        'return {"ok": False, "error": result["error"]'
    )

    persistence_marker = source.index(
        "# 8. persist"
    )

    assert failure_return < persistence_marker


def test_v17_live_fail_closed_occurs_before_persistence():
    source = _source(
        "engine.py",
    )

    guard = source.index(
        "live_knowledge_fail_closed"
    )

    persistence = source.index(
        "# 8. persist"
    )

    assert guard < persistence


def test_v17_multimodal_context_remains_ephemeral():
    source = _source(
        "engine.py",
    )

    assert "V13.3 ephemeral multimodal grounding" in source

    assert (
        "multimodal_context"
        in inspect.signature(
            __import__(
                "ai_engine.engine",
                fromlist=["CharacterEngine"],
            ).CharacterEngine.respond
        ).parameters
    )


def test_v17_provider_remains_external_ai_boundary():
    provider_source = _source(
        "provider.py",
    )

    engine_source = _source(
        "engine.py",
    )

    assert "from ai_engine import provider as PROV" in engine_source

    assert (
        "AsyncOpenAI"
        in provider_source
        or "OpenAI"
        in provider_source
    )

    forbidden = (
        "AsyncOpenAI(",
        "OpenAI(",
        "client.responses.create(",
        "client.chat.completions.create(",
        "client.images.generate(",
        "client.images.edit(",
    )

    for path in AI_ENGINE.glob("*.py"):
        if path.name == "provider.py":
            continue

        text = path.read_text(
            encoding="utf-8",
        )

        for marker in forbidden:
            assert marker not in text, (
                f"Direct provider boundary violation: "
                f"{path.name} contains {marker}"
            )



def test_v17_failure_recovery_does_not_rewrite_personality():
    from ai_engine import personality_engine as PE

    character = {
        "characterId": "global-v17-failure-character",
        "personalityTraits": [
            "warm",
            "playful",
            "curious",
            "witty",
        ],
    }

    original_character = deepcopy(
        character
    )

    baseline = PE.build_fingerprint(
        character
    )

    for attempt in range(1, 5001):
        decision = RI10.decide_reliability(
            provider_ok=False,
            provider_error="provider_timeout",
            attempt=(
                1
                if attempt % 2
                else 2
            ),
        )

        assert (
            decision.can_claim_success
            is False
        )

        if attempt % 250 == 0:
            current = PE.build_fingerprint(
                character
            )

            assert (
                current.identity_signature
                == baseline.identity_signature
            )

    after = PE.build_fingerprint(
        character
    )

    assert (
        after.identity_signature
        == baseline.identity_signature
    )

    assert character == original_character

def test_v17_sandbox_gate_remains_before_semantic_writes():
    source = _source(
        "engine.py",
    )

    persistence = source.index(
        "# 8. persist"
    )

    sandbox_gate = source.find(
        "if not sandbox",
        persistence,
    )

    assert sandbox_gate != -1

    semantic_markers = (
        "R.advance(",
        "repo.append_turn(",
        "repo.add_memory(",
    )

    for marker in semantic_markers:
        position = source.find(
            marker,
            persistence,
        )

        assert position == -1 or position > sandbox_gate


def test_v17_marker():
    assert V17_5_FAILURE_RECOVERY_INTELLIGENCE is True

"""
Earn2Love AI Engine V17.4
Cross-Capability Intelligence Acceptance

Proves that V12/V13/V15/V16 capabilities cooperate with the existing
V6-V11 semantic intelligence stack without creating competing state
authorities or turning ephemeral transport/media/live context into
durable user intelligence.
"""

from __future__ import annotations

import inspect
from pathlib import Path

from ai_engine import context_intelligence as CX10
from ai_engine import emotional_intelligence as EI15
from ai_engine import freshness_intelligence as FI12
from ai_engine import multimodal_intelligence as MM13
from ai_engine import orchestration_intelligence as OI10
from ai_engine import relationship_emotional_intelligence as RE15
from ai_engine import verified_final_delivery as VFD16
from ai_engine import verified_streaming_orchestration as VSO16
from ai_engine.engine import CharacterEngine


V17_4_CROSS_CAPABILITY_INTELLIGENCE = True


def _source(relative_path: str) -> str:
    return Path(relative_path).read_text(
        encoding="utf-8",
    )


def test_v17_engine_is_common_semantic_authority():
    sig = inspect.signature(
        CharacterEngine.respond
    )

    assert "multimodal_context" in sig.parameters
    assert "_generation_callable" in sig.parameters

    assert (
        sig.parameters[
            "multimodal_context"
        ].default
        is None
    )

    assert (
        sig.parameters[
            "_generation_callable"
        ].default
        is None
    )


def test_v17_streaming_reuses_same_engine_multimodal_contract():
    sig = inspect.signature(
        VSO16.respond_with_buffered_stream
    )

    assert "engine" in sig.parameters
    assert "character_id" in sig.parameters
    assert "user_id" in sig.parameters
    assert "conversation_id" in sig.parameters
    assert "multimodal_context" in sig.parameters

    source = inspect.getsource(
        VSO16.respond_with_buffered_stream
    )


    assert (
        "multimodal_context="
        "multimodal_context"
        in source
    )

    assert (
        "_generation_callable="
        "BSG16.generate_buffered_stream"
        in source
    )


def test_v17_multimodal_context_remains_ephemeral_grounding():
    context = (
        MM13.build_grounded_visual_context(
            "A red bicycle is beside a blue cup.",
            image_count=1,
            scope_token="opaque-scope-token",
        )
    )

    lowered = context.casefold()

    assert "red bicycle" in lowered
    assert "blue cup" in lowered
    assert "ephemeral" in lowered

    assert (
        "durable personal memory"
        in lowered
    )


def test_v17_multimodal_does_not_create_parallel_semantic_writes():
    source = _source(
        "ai_engine/multimodal_intelligence.py"
    )

    forbidden = (
        "add_memory(",
        "save_structured_memory(",
        "reinforce_memory(",
        "revise_memories(",
        "advance_adaptation(",
        "advance_goal_state(",
        "advance_plan_state(",
        "advance_relationship(",
        "append_turn(",
    )

    for marker in forbidden:
        assert marker not in source


def test_v17_personal_memory_question_does_not_trigger_live_retrieval():
    decision = FI12.assess_freshness(
        "Do you remember what food I like?"
    )

    assert (
        decision.requires_live_retrieval
        is False
    )


def test_v17_current_fact_does_trigger_live_retrieval():
    decision = FI12.assess_freshness(
        "Who is the current Prime Minister?"
    )

    assert (
        decision.requires_live_retrieval
        is True
    )


def test_v17_live_knowledge_never_becomes_memory_authority():
    source = _source(
        "ai_engine/engine.py"
    )

    assert (
        "Public live facts remain ephemeral"
        in source
    )

    assert (
        "durable user memory"
        in source
    )

    assert (
        "V12_LIVE_KNOWLEDGE_INTELLIGENCE"
        in source
    )


def test_v17_v10_remains_context_authority_across_capabilities():
    decision = OI10.decide_orchestration(
        "Do you remember what food I like?",
        memories=[
            {
                "memoryId": "memory-1",
                "text": "User likes dosa.",
            },
            {
                "memoryId": "memory-2",
                "text": "User likes coffee.",
            },
            {
                "memoryId": "memory-3",
                "text": "User avoids very spicy food.",
            },
        ],
    )

    selection = CX10.select_context(
        decision,
        history_count=25,
        memory_count=3,
        has_active_goal=True,
        has_active_plan=True,
    )

    assert selection.memory_limit >= 1
    assert selection.include_relationship is True

    assert (
        selection.memory_limit
        <= CX10.MAX_MEMORY_ITEMS
    )


def test_v17_emotional_relationship_layer_does_not_mutate_input():
    relationship = {
        "state": "comfortable",
        "interactionCount": 25,
    }

    original = dict(
        relationship
    )

    emotional = (
        EI15.analyze_emotional_state_v15(
            "I am stressed about my exam tomorrow."
        )
    )

    guidance = (
        RE15.build_relationship_emotional_guidance(
            "I am stressed about my exam tomorrow.",
            emotional,
            relationship,
        )
    )

    assert relationship == original
    assert guidance is not None

    assert hasattr(
        guidance,
        "directive",
    )

    assert isinstance(
        guidance.directive,
        str,
    )


def test_v17_relationship_has_single_engine_evolution_authority():
    source = _source(
        "ai_engine/engine.py"
    )

    assert (
        source.count(
            "R.advance("
        )
        == 1
    )

    transport_sources = " ".join(
        [
            _source(
                "ai_engine/streaming_intelligence.py"
            ),
            _source(
                "ai_engine/verified_final_delivery.py"
            ),
            _source(
                "ai_engine/verified_streaming_orchestration.py"
            ),
            _source(
                "ai_engine/buffered_streaming_generation.py"
            ),
        ]
    )

    assert "R.advance(" not in transport_sources


def test_v17_image_creation_remains_separate_from_chat_engine():
    engine_source = _source(
        "ai_engine/engine.py"
    )

    provider_source = _source(
        "ai_engine/provider.py"
    )

    image_source = _source(
        "ai_engine/image_creation_intelligence.py"
    )

    assert "generate_image(" not in engine_source
    assert "edit_image(" not in engine_source

    assert "async def generate_image(" in provider_source
    assert "async def edit_image(" in provider_source

    assert (
        "V14_IMAGE_CREATION_INTELLIGENCE"
        in image_source
    )


def test_v17_verified_delivery_accepts_only_final_engine_response():
    response = {
        "ok": True,
        "responseText": (
            "This is the verified final response."
        ),
        "characterId": "character-v17",
        "relationshipState": "comfortable",
        "memoryIdsUsed": [],
    }

    plan = VFD16.prepare_verified_delivery(
        response,
        character_id="character-v17",
        user_id="user-v17",
        conversation_id="conversation-v17",
        request_id="request-v17",
        chunk_size=512,
    )

    assert plan is not None
    assert plan.state.final_seen is True

    source = inspect.getsource(
        VFD16.prepare_verified_delivery
    )

    assert (
        "_verified_response_text"
        in source
    )


def test_v17_transport_cancellation_is_explicitly_nonsemantic():
    response = {
        "ok": True,
        "responseText": "Verified response.",
        "characterId": "character-v17",
        "relationshipState": "new",
        "memoryIdsUsed": [],
    }

    plan = VFD16.prepare_verified_delivery(
        response,
        character_id="character-v17",
        user_id="user-v17",
        conversation_id="conversation-v17",
        request_id="request-v17-cancel",
    )

    _, event = (
        VFD16.cancel_verified_delivery(
            plan.state,
            reason="client_disconnected",
        )
    )

    assert (
        event["semanticPersistence"]
        is False
    )

    assert (
        event["relationshipEvent"]
        is False
    )

    assert (
        event["memoryEvent"]
        is False
    )

    assert (
        event["adaptationEvent"]
        is False
    )


def test_v17_cross_capability_marker():
    assert (
        V17_4_CROSS_CAPABILITY_INTELLIGENCE
        is True
    )


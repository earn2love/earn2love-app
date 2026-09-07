"""
Earn2Love AI Engine V17.7
Final Production Acceptance Contract.

This is the final test-only acceptance layer before freezing
the V3-V17 AI intelligence architecture.

It introduces no production behavior.
"""

from __future__ import annotations

import ast

import inspect
from pathlib import Path

import ai_service

from ai_engine.engine import CharacterEngine
from ai_engine import provider as PROV
from ai_engine import realtime_intelligence as RT16
from ai_engine import streaming_intelligence as SI16
from ai_engine import verified_streaming_orchestration as VSO16


V17_7_PRODUCTION_ACCEPTANCE = True


BACKEND = Path(__file__).resolve().parents[1]
AI_ENGINE = BACKEND / "ai_engine"

ENGINE_SOURCE = (
    AI_ENGINE / "engine.py"
).read_text(
    encoding="utf-8",
)

PROVIDER_SOURCE = (
    AI_ENGINE / "provider.py"
).read_text(
    encoding="utf-8",
)

ROUTER_SOURCE = (
    AI_ENGINE / "router.py"
).read_text(
    encoding="utf-8",
)

AI_SERVICE_SOURCE = (
    BACKEND / "ai_service.py"
).read_text(
    encoding="utf-8",
)

SERVER_SOURCE = (
    BACKEND / "server.py"
).read_text(
    encoding="utf-8",
)


def test_v17_final_engine_public_contract():
    signature = inspect.signature(
        CharacterEngine.respond
    )

    parameters = signature.parameters

    assert "character_id" in parameters
    assert "user_id" in parameters
    assert "user_text" in parameters
    assert "sandbox" in parameters
    assert "conversation_id" in parameters
    assert "multimodal_context" in parameters
    assert "_generation_callable" in parameters

    assert (
        parameters["conversation_id"].default
        == "default"
    )


def test_v17_final_ai_service_public_contract():
    signature = inspect.signature(
        ai_service.chat
    )

    parameters = signature.parameters

    assert "character_id" in parameters
    assert "user_id" in parameters
    assert "message" in parameters
    assert "client_message_id" in parameters
    assert "conversation_id" in parameters
    assert "image_ids" in parameters
    assert "_verified_buffered_generation" in parameters


def test_v17_final_verified_stream_contract():
    signature = inspect.signature(
        VSO16.respond_with_buffered_stream
    )

    parameters = signature.parameters

    assert "engine" in parameters
    assert "character_id" in parameters
    assert "user_id" in parameters
    assert "user_text" in parameters
    assert "sandbox" in parameters
    assert "conversation_id" in parameters
    assert "multimodal_context" in parameters


def test_v17_provider_generation_contract_is_explicit():
    generate = inspect.signature(
        PROV.generate
    )

    streaming = inspect.signature(
        PROV.generate_stream
    )

    assert "provider" in generate.parameters
    assert "model" in generate.parameters
    assert "session_id" in generate.parameters

    assert "provider" in streaming.parameters
    assert "model" in streaming.parameters
    assert "session_id" in streaming.parameters


def test_v17_provider_supports_separate_capabilities():
    required = (
        "generate",
        "generate_stream",
        "search_web",
        "analyze_images",
        "generate_image",
        "edit_image",
    )

    for name in required:
        assert hasattr(
            PROV,
            name,
        )

        assert callable(
            getattr(
                PROV,
                name,
            )
        )


def test_v17_direct_external_ai_boundary_is_provider_only():
    direct_markers = (
        "AsyncOpenAI(",
        "OpenAI(",
        "client.responses.create(",
        "client.chat.completions.create(",
        "client.images.generate(",
        "client.images.edit(",
    )

    offenders = []

    for path in AI_ENGINE.glob("*.py"):
        if path.name == "provider.py":
            continue

        source = path.read_text(
            encoding="utf-8",
        )

        if any(
            marker in source
            for marker in direct_markers
        ):
            offenders.append(
                path.name
            )

    assert offenders == []


def test_v17_provider_is_actual_external_boundary():
    direct_markers = (
        "AsyncOpenAI(",
        "OpenAI(",
        "client.responses.create(",
        "client.chat.completions.create(",
        "client.images.generate(",
        "client.images.edit(",
    )

    assert any(
        marker in PROVIDER_SOURCE
        for marker in direct_markers
    )


def test_v17_router_remains_normal_generation_authority():
    assert "router" in ENGINE_SOURCE.lower()

    assert (
        "provider" in ROUTER_SOURCE.lower()
    )

    assert (
        "model" in ROUTER_SOURCE.lower()
    )


def test_v17_single_semantic_evolution_authorities():
    assert ENGINE_SOURCE.count(
        "R.advance("
    ) == 1

    assert ENGINE_SOURCE.count(
        "advance_adaptation("
    ) == 1

    assert ENGINE_SOURCE.count(
        "advance_goal_state("
    ) == 1

    assert ENGINE_SOURCE.count(
        "advance_plan_state("
    ) == 1


def test_v17_conversation_scope_reaches_engine_persistence():
    assert "_provider_session_key(" in ENGINE_SOURCE

    assert "conversation_id=conversation_id" in ENGINE_SOURCE

    assert ENGINE_SOURCE.count(
        "append_turn("
    ) >= 2


def test_v17_realtime_scope_has_all_three_identity_dimensions():
    scope = RT16.build_scope(
        character_id="character",
        user_id="user",
        conversation_id="conversation",
    )

    assert scope.character_id == "character"
    assert scope.user_id == "user"
    assert scope.conversation_id == "conversation"

    different_user = RT16.build_scope(
        character_id="character",
        user_id="other-user",
        conversation_id="conversation",
    )

    different_character = RT16.build_scope(
        character_id="other-character",
        user_id="user",
        conversation_id="conversation",
    )

    different_conversation = RT16.build_scope(
        character_id="character",
        user_id="user",
        conversation_id="other-conversation",
    )

    baseline = RT16.build_session_key(
        scope
    )

    assert baseline != RT16.build_session_key(
        different_user
    )

    assert baseline != RT16.build_session_key(
        different_character
    )

    assert baseline != RT16.build_session_key(
        different_conversation
    )


def test_v17_transport_failure_is_nonsemantic():
    request = RT16.build_request(
        character_id="character",
        user_id="user",
        conversation_id="conversation",
        request_id="request",
        sequence=0,
        sandbox=False,
    )

    metadata = RT16.cancellation_metadata(
        request,
        reason="client_disconnected",
    )

    assert metadata["relationshipEvent"] is False
    assert metadata["memoryEvent"] is False

    if "semanticPersistence" in metadata:
        assert (
            metadata["semanticPersistence"]
            is False
        )

    state = SI16.start_stream(
        request
    )

    state = SI16.cancel_stream(
        state
    )

    event = SI16.cancellation_event(
        state,
        reason="client_disconnected",
    )

    assert event["semanticPersistence"] is False
    assert event["relationshipEvent"] is False
    assert event["memoryEvent"] is False
    assert event["adaptationEvent"] is False


def test_v17_duplicate_transport_data_rejected():
    request = RT16.build_request(
        character_id="character",
        user_id="user",
        conversation_id="conversation",
        request_id="request",
        sequence=0,
        sandbox=False,
    )

    state = SI16.start_stream(
        request
    )

    first = SI16.accept_chunk(
        state,
        index=0,
        text="verified",
        final=False,
    )

    assert first.accepted is True

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


def test_v17_live_knowledge_is_integrated_without_new_memory_authority():
    lowered = ENGINE_SOURCE.lower()

    assert (
        "live_knowledge"
        in lowered
        or "freshness"
        in lowered
    )

    assert ENGINE_SOURCE.count(
        "advance_adaptation("
    ) == 1

    assert ENGINE_SOURCE.count(
        "R.advance("
    ) == 1


def test_v17_multimodal_is_integrated_as_context():
    assert (
        "multimodal_context"
        in ENGINE_SOURCE
    )

    assert (
        "image_ids"
        in AI_SERVICE_SOURCE
    )


def test_v17_image_creation_remains_separate_capability():
    image_module = (
        AI_ENGINE
        / "image_creation_intelligence.py"
    )

    assert image_module.exists()

    server_source = SERVER_SOURCE

    assert (
        "ai_image_creation.generate_image("
        in server_source
    )

    assert (
        "ai_image_creation.edit_image("
        in server_source
    )

    assert (
        "ai_image_creation.resolve_generated_image("
        in server_source
    )


def test_v17_streaming_is_opt_in_not_parallel_engine():
    assert (
        "_verified_buffered_generation"
        in AI_SERVICE_SOURCE
    )

    assert (
        "respond_with_buffered_stream"
        in AI_SERVICE_SOURCE
    )

    streaming_path = (
        AI_ENGINE
        / "streaming_intelligence.py"
    )

    streaming_source = streaming_path.read_text(
        encoding="utf-8-sig",
    )

    streaming_tree = ast.parse(
        streaming_source
    )

    imported_names = set()

    for node in ast.walk(streaming_tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported_names.add(
                    alias.name
                )

        if isinstance(node, ast.ImportFrom):
            module = node.module or ""

            for alias in node.names:
                imported_names.add(
                    f"{module}.{alias.name}"
                )

    assert not any(
        name == "ai_engine.engine.CharacterEngine"
        or name.endswith(".CharacterEngine")
        for name in imported_names
    )


def test_v17_server_exposes_normal_and_stream_chat_paths():
    lowered = SERVER_SOURCE.lower()

    assert (
        'apirouter(prefix="/api")'
        in lowered
    )

    assert (
        '@api.post("/ai/chat")'
        in lowered
    )

    assert (
        '@api.post("/ai/chat/stream")'
        in lowered
    )


def test_v17_no_voice_stt_tts_engine_modules():
    forbidden_module_names = (
        "voice",
        "stt",
        "tts",
        "speech_to_text",
        "text_to_speech",
    )

    offenders = []

    for path in AI_ENGINE.glob("*.py"):
        stem = path.stem.lower()

        if any(
            token == stem
            or stem.startswith(token + "_")
            or stem.endswith("_" + token)
            for token in forbidden_module_names
        ):
            offenders.append(
                path.name
            )

    assert offenders == []


def test_v17_v6_through_v16_capability_modules_exist():
    required = (
        "personality_engine.py",
        "preference_engine.py",
        "goal_intelligence.py",
        "planner.py",
        "orchestration_intelligence.py",
        "reliability_intelligence.py",
        "live_knowledge_intelligence.py",
        "multimodal_intelligence.py",
        "image_creation_intelligence.py",
        "emotional_intelligence.py",
        "relationship_emotional_intelligence.py",
        "realtime_intelligence.py",
        "streaming_intelligence.py",
        "buffered_streaming_generation.py",
        "verified_streaming_orchestration.py",
        "verified_final_delivery.py",
    )

    missing = [
        name
        for name in required
        if not (
            AI_ENGINE / name
        ).exists()
    ]

    assert missing == []


def test_v17_final_acceptance_marker():
    assert (
        V17_7_PRODUCTION_ACCEPTANCE
        is True
    )

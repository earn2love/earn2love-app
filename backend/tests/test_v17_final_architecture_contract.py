from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
AI = ROOT / "ai_engine"

ENGINE = AI / "engine.py"
SERVICE = ROOT / "ai_service.py"
SERVER = ROOT / "server.py"
PROVIDER = AI / "provider.py"

V17_1_FINAL_ARCHITECTURE_CONTRACT = True


def read(path):
    return path.read_text(encoding="utf-8")


def test_v17_core_files_exist():
    required = [
        AI / "personality_engine.py",
        AI / "adaptive_intelligence.py",
        AI / "goal_intelligence.py",
        AI / "reasoning_intelligence.py",
        AI / "plan_intelligence.py",
        AI / "execution_intelligence.py",
        AI / "verification_intelligence.py",
        AI / "orchestration_intelligence.py",
        AI / "routing_intelligence.py",
        AI / "context_intelligence.py",
        AI / "reliability_intelligence.py",
        AI / "memory_retrieval_intelligence.py",
        AI / "conversation_continuity_intelligence.py",
        AI / "preference_learning_intelligence.py",
        AI / "memory_integrity_intelligence.py",
        AI / "freshness_intelligence.py",
        AI / "live_knowledge_intelligence.py",
        AI / "engagement_intelligence.py",
        AI / "multimodal_intelligence.py",
        AI / "image_creation_intelligence.py",
        AI / "emotional_intelligence.py",
        AI / "relationship_emotional_intelligence.py",
        AI / "realtime_intelligence.py",
        AI / "streaming_intelligence.py",
        AI / "buffered_streaming_generation.py",
        AI / "verified_streaming_orchestration.py",
        AI / "verified_final_delivery.py",
    ]

    missing = [
        str(path.relative_to(ROOT))
        for path in required
        if not path.exists()
    ]

    assert not missing, "Missing AI modules: " + ", ".join(missing)


def test_v17_engine_wires_intelligence_stack():
    text = read(ENGINE)

    required_imports = [
        "personality_engine",
        "adaptive_intelligence",
        "goal_intelligence",
        "reasoning_intelligence",
        "plan_intelligence",
        "execution_intelligence",
        "verification_intelligence",
        "orchestration_intelligence",
        "routing_intelligence",
        "context_intelligence",
        "reliability_intelligence",
        "memory_retrieval_intelligence",
        "conversation_continuity_intelligence",
        "preference_learning_intelligence",
        "memory_integrity_intelligence",
        "freshness_intelligence",
        "live_knowledge_intelligence",
        "engagement_intelligence",
        "multimodal_intelligence",
        "emotional_intelligence",
        "relationship_emotional_intelligence",
    ]

    missing = [
        name for name in required_imports
        if name not in text
    ]

    assert not missing, (
        "Engine intelligence imports disconnected: "
        + ", ".join(missing)
    )


def test_v17_v16_verified_streaming_remains_service_opt_in():
    text = read(SERVICE)

    assert "verified_streaming_orchestration" in text
    assert "_verified_buffered_generation=False" in text
    assert "respond_with_buffered_stream" in text
    assert "prod_engine().respond" in text


def test_v17_multimodal_remains_ephemeral_engine_context():
    text = read(ENGINE)

    assert "multimodal_context=None" in text
    assert "V13_MULTIMODAL_INTELLIGENCE" in text

    service = read(SERVICE)

    assert "_prepare_multimodal_context" in service
    assert "resolve_image_reference" in service
    assert "analyze_images" in service


def test_v17_image_creation_capability_exists_without_engine_duplication():
    service = read(SERVICE)

    assert (AI / "image_creation_intelligence.py").exists()

    assert "begin_image_request" in service
    assert "complete_image_request" in service
    assert "abort_image_request" in service


def test_v17_provider_is_only_direct_llm_boundary():
    forbidden_patterns = [
        re.compile(r"\bAsyncOpenAI\b"),
        re.compile(r"\bOpenAI\s*\("),
        re.compile(r"\blitellm\.acompletion\s*\("),
        re.compile(r"(?<![\w.])acompletion\s*\("),
    ]

    violations = []

    for path in AI.glob("*.py"):
        if path.name == "provider.py":
            continue

        text = read(path)

        for pattern in forbidden_patterns:
            if pattern.search(text):
                violations.append(
                    f"{path.name}: {pattern.pattern}"
                )

    assert not violations, (
        "Direct provider boundary violation: "
        + ", ".join(violations)
    )


def test_v17_provider_streaming_boundary_exists():
    text = read(PROVIDER)

    assert "V16_2_PROVIDER_STREAMING = True" in text
    assert "generate_stream" in text


def test_v17_realtime_transport_is_nonsemantic():
    realtime = read(AI / "realtime_intelligence.py")
    streaming = read(AI / "streaming_intelligence.py")

    assert "V16_1_REALTIME_SESSION_INTELLIGENCE = True" in realtime
    assert "V16_2_STREAMING_RESPONSE_INTELLIGENCE = True" in streaming

    assert "existing AI engine" in realtime
    assert "delivery timing only" in streaming


def test_v17_verified_final_delivery_exists():
    text = read(AI / "verified_final_delivery.py")

    assert "V16_2_VERIFIED_FINAL_RESPONSE_DELIVERY = True" in text


def test_v17_verified_streaming_uses_engine_generation_seam():
    text = read(AI / "verified_streaming_orchestration.py")

    assert "buffered_streaming_generation" in text
    assert "_generation_callable=" in text


def test_v17_production_chat_is_persistent_and_lab_is_separate():
    text = read(SERVICE)

    assert "FirestoreCharacterRepository" in text
    assert "InMemoryCharacterRepository" in text
    assert "def prod_engine" in text
    assert "async def chat" in text
    assert "def lab_start" in text


def test_v17_no_voice_implementation_added_to_ai_engine():
    filenames = {
        path.name.lower()
        for path in AI.glob("*.py")
    }

    forbidden = {
        "voice_intelligence.py",
        "speech_intelligence.py",
        "tts_intelligence.py",
        "stt_intelligence.py",
        "audio_intelligence.py",
    }

    assert filenames.isdisjoint(forbidden)


def test_v17_server_keeps_normal_and_stream_chat_paths():
    text = read(SERVER)

    assert "/ai/chat" in text
    assert "/ai/chat/stream" in text


def test_v17_engine_keeps_scoped_provider_session():
    text = read(ENGINE)

    assert "_provider_session_key" in text
    assert "character_id" in text
    assert "user_id" in text
    assert "conversation_id" in text


def test_v17_architecture_marker():
    assert V17_1_FINAL_ARCHITECTURE_CONTRACT is True

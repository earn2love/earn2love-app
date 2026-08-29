from pathlib import Path
import ast


ROOT = Path(__file__).resolve().parents[1]
SERVER = ROOT / "server.py"


def _source():
    return SERVER.read_text(encoding="utf-8")


def _tree():
    return ast.parse(_source())


def _function(name):
    for node in _tree().body:
        if isinstance(node, ast.AsyncFunctionDef) and node.name == name:
            return node
    raise AssertionError(f"{name} not found")


def _segment(name):
    node = _function(name)
    return ast.get_source_segment(_source(), node)


def _decorator_paths(node):
    values = []

    for decorator in node.decorator_list:
        if not isinstance(decorator, ast.Call):
            continue

        if not decorator.args:
            continue

        arg = decorator.args[0]

        if isinstance(arg, ast.Constant):
            values.append(arg.value)

    return values


def _calls(node):
    result = []

    for item in ast.walk(node):
        if not isinstance(item, ast.Call):
            continue

        fn = item.func

        if isinstance(fn, ast.Name):
            result.append(fn.id)
            continue

        if isinstance(fn, ast.Attribute):
            parts = []
            current = fn

            while isinstance(current, ast.Attribute):
                parts.append(current.attr)
                current = current.value

            if isinstance(current, ast.Name):
                parts.append(current.id)

            result.append(".".join(reversed(parts)))

    return result


def test_existing_chat_route_still_exists():
    node = _function("ai_chat")
    assert "/ai/chat" in _decorator_paths(node)


def test_existing_chat_does_not_opt_into_streaming():
    source = _segment("ai_chat")
    assert "_verified_buffered_generation" not in source


def test_stream_route_exists():
    node = _function("ai_chat_stream")
    assert "/ai/chat/stream" in _decorator_paths(node)


def test_stream_route_uses_existing_body_model():
    node = _function("ai_chat_stream")

    body = node.args.args[0]

    assert body.arg == "body"
    assert isinstance(body.annotation, ast.Name)
    assert body.annotation.id == "AiChatBody"


def test_stream_route_requires_authenticated_user():
    source = _segment("ai_chat_stream")

    assert "Depends(get_current_user)" in source
    assert 'user["uid"]' in source


def test_stream_route_preserves_message_validation():
    source = _segment("ai_chat_stream")

    assert '"message is required"' in source
    assert '"message too long (max 2000 characters)"' in source


def test_stream_route_uses_ai_service_once():
    calls = _calls(_function("ai_chat_stream"))
    assert calls.count("ai_svc.chat") == 1


def test_stream_route_opts_into_verified_buffered_generation():
    source = _segment("ai_chat_stream")

    assert "_verified_buffered_generation=True" in source


def test_stream_route_passes_existing_chat_contract():
    source = _segment("ai_chat_stream")

    required = (
        "body.characterId",
        'user["uid"]',
        "body.message",
        "body.language",
        "body.clientMessageId",
        'body.conversationId or "default"',
        "body.imageIds",
    )

    for token in required:
        assert token in source


def test_stream_route_uses_verified_final_delivery():
    calls = _calls(_function("ai_chat_stream"))

    assert "VFD16.prepare_verified_delivery" in calls


def test_stream_route_does_not_deliver_provider_deltas():
    source = _segment("ai_chat_stream")

    forbidden = (
        "generate_stream(",
        "provider.generate",
        "PROV.generate",
        "PROV.generate_stream",
        "prod_engine(",
    )

    for token in forbidden:
        assert token not in source


def test_stream_transport_is_sse():
    source = _segment("ai_chat_stream")

    assert 'media_type="text/event-stream"' in source
    assert "V16StreamingResponse(" in source


def test_stream_disconnect_is_delivery_only():
    source = _segment("ai_chat_stream")

    assert "await request.is_disconnected()" in source
    assert "VFD16.cancel_verified_delivery(" in source
    assert 'reason="client_disconnected"' in source


def test_stream_route_has_no_persistence_boundary():
    source = _segment("ai_chat_stream").lower()

    forbidden = (
        ".collection(",
        ".document(",
        ".set(",
        ".update(",
        ".add(",
        "advance_goal_state(",
        "advance_plan_state(",
        "advance_adaptation(",
        "r.advance(",
    )

    for token in forbidden:
        assert token not in source


def test_stream_route_has_no_voice():
    source = _segment("ai_chat_stream").lower()

    forbidden = (
        "agora",
        "speech_to_text",
        "text_to_speech",
        "transcription",
        "audio_stream",
    )

    for token in forbidden:
        assert token not in source


def test_no_websocket_transport_added():
    source = _source().lower()

    assert '@api.websocket("/ai/chat/stream")' not in source
    assert "eventsourceresponse" not in source


def test_sse_frame_helper_is_present():
    source = _source()

    assert "def _v16_sse_frame(event):" in source
    assert 'f"event: {event_type}\\n"' in source
    assert 'f"data: {payload}\\n\\n"' in source


def test_verified_delivery_import_is_present():
    source = _source()

    assert "verified_final_delivery as VFD16" in source


def test_streaming_response_import_is_present():
    source = _source()

    assert "StreamingResponse as V16StreamingResponse" in source


def test_only_one_normal_chat_route():
    source = _source()

    assert source.count('@api.post("/ai/chat")') == 1


def test_only_one_stream_chat_route():
    source = _source()

    assert source.count('@api.post("/ai/chat/stream")') == 1

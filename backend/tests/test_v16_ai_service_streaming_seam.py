"""
V16.2C5A production ai_service buffered-generation seam.

The production chat lifecycle remains the single authority for:
- rate limiting;
- feature flags;
- idempotency;
- exact conversation locking;
- multimodal preparation;
- generation metadata;
- idempotency persistence.

Only generation acquisition is selectable internally.
"""

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SERVICE = ROOT / "ai_service.py"


def _source():
    return SERVICE.read_text(encoding="utf-8")


def _tree():
    return ast.parse(_source())


def _chat_node():
    for node in ast.walk(_tree()):
        if (
            isinstance(node, ast.AsyncFunctionDef)
            and node.name == "chat"
        ):
            return node
    raise AssertionError("chat function not found")


def _call_names(node):
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
            cur = fn

            while isinstance(cur, ast.Attribute):
                parts.append(cur.attr)
                cur = cur.value

            if isinstance(cur, ast.Name):
                parts.append(cur.id)

            result.append(
                ".".join(reversed(parts))
            )

    return result


def test_v16_c5a_import_present():
    source = _source()

    assert (
        "verified_streaming_orchestration as VSO16"
        in source
    )


def test_chat_has_private_keyword_only_switch():
    node = _chat_node()

    kwonly = [
        arg.arg
        for arg in node.args.kwonlyargs
    ]

    assert (
        "_verified_buffered_generation"
        in kwonly
    )


def test_switch_defaults_false():
    node = _chat_node()

    names = [
        arg.arg
        for arg in node.args.kwonlyargs
    ]

    idx = names.index(
        "_verified_buffered_generation"
    )

    default = node.args.kw_defaults[idx]

    assert isinstance(default, ast.Constant)
    assert default.value is False


def test_existing_positional_contract_preserved():
    node = _chat_node()

    positional = [
        arg.arg
        for arg in node.args.args
    ]

    assert positional == [
        "character_id",
        "user_id",
        "message",
        "language",
        "client_message_id",
        "conversation_id",
        "image_ids",
    ]


def test_chat_keeps_normal_engine_path():
    calls = _call_names(
        _chat_node()
    )

    assert (
        "prod_engine.respond"
        in calls
        or "prod_engine" in calls
    )

    source = ast.get_source_segment(
        _source(),
        _chat_node(),
    )

    assert (
        "await prod_engine().respond("
        in source
    )


def test_chat_has_verified_buffered_path():
    calls = _call_names(
        _chat_node()
    )

    assert (
        "VSO16.respond_with_buffered_stream"
        in calls
    )


def test_buffered_path_is_opt_in_only():
    source = ast.get_source_segment(
        _source(),
        _chat_node(),
    )

    assert (
        "if _verified_buffered_generation:"
        in source
    )

    assert (
        "else:\n"
        "            r = await prod_engine().respond("
        in source
    )


def test_single_rate_limit_lifecycle():
    source = ast.get_source_segment(
        _source(),
        _chat_node(),
    )

    assert (
        source.count(
            "RL.check_and_consume("
        )
        == 1
    )


def test_single_chat_lock_lifecycle():
    source = ast.get_source_segment(
        _source(),
        _chat_node(),
    )

    assert (
        source.count(
            "async with _chat_lock("
        )
        == 1
    )


def test_single_generation_id_lifecycle():
    source = ast.get_source_segment(
        _source(),
        _chat_node(),
    )

    assert (
        source.count(
            "generation_id = uuid.uuid4().hex"
        )
        == 1
    )


def test_idempotency_replay_preserved():
    source = ast.get_source_segment(
        _source(),
        _chat_node(),
    )

    assert (
        'd.get("lastClientMessageId")'
        in source
    )

    assert (
        '"idempotentReplay": True'
        in source
    )


def test_multimodal_preparation_preserved():
    source = ast.get_source_segment(
        _source(),
        _chat_node(),
    )

    assert (
        "_prepare_multimodal_context("
        in source
    )

    assert (
        "_resolve_continuity_image_ids("
        in source
    )


def test_existing_idempotency_write_preserved_once():
    source = ast.get_source_segment(
        _source(),
        _chat_node(),
    )

    assert (
        source.count(
            'conv.set({"lastClientMessageId"'
        )
        == 1
    )


def test_no_transport_added_to_service():
    source = _source().lower()

    forbidden = (
        "streamingresponse(",
        "eventsourceresponse(",
        "text/event-stream",
        "websocket(",
    )

    for token in forbidden:
        assert token not in source


def test_no_voice_added():
    source = _source().lower()

    forbidden = (
        "agora",
        "text_to_speech",
        "speech_to_text",
        "transcription",
    )

    for token in forbidden:
        assert token not in source

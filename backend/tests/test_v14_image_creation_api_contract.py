from pathlib import Path
import ast


SERVER = Path(
    "backend/server.py"
).read_text(
    encoding="utf-8-sig"
)


def test_v14_routes_exist():
    assert (
        '"/ai/images/generate"'
        in SERVER
    )

    assert (
        '"/ai/images/edit"'
        in SERVER
    )

    assert (
        '"/ai/images/{image_id}"'
        in SERVER
    )


def test_v14_routes_use_service_boundary():
    assert (
        "ai_image_creation.generate_image("
        in SERVER
    )

    assert (
        "ai_image_creation.edit_image("
        in SERVER
    )

    assert (
        "ai_image_creation.resolve_generated_image("
        in SERVER
    )

    assert (
        "ai_image_creation.delete_generated_image("
        in SERVER
    )


def test_server_does_not_call_openai_image_api():
    assert ".images.generate(" not in SERVER
    assert ".images.edit(" not in SERVER
    assert "AsyncOpenAI(" not in SERVER


def test_server_has_no_v14_storage_write():
    marker = SERVER.index(
        "# V14 IMAGE CREATION API"
    )

    v14 = SERVER[
        marker:
    ]

    assert "upload_from_string(" not in v14
    assert "get_bucket(" not in v14
    assert ".collection(" not in v14


def test_v14_server_parses():
    ast.parse(
        SERVER
    )


def test_v14_rate_limit_retry_after_contract():
    assert (
        '"Retry-After"'
        in SERVER
    )

    assert (
        'getattr(\n            exc,\n            "retry_after"'
        in SERVER
    )

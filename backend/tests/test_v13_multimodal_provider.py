import asyncio
from pathlib import Path
import sys
import types

from ai_engine import provider as PROV


class FakeUsage:
    def model_dump(
        self,
    ):
        return {
            "input_tokens": 10,
            "output_tokens": 5,
            "total_tokens": 15,
        }


class FakeResponse:
    output_text = "I can see a cat."
    output = []
    usage = FakeUsage()


def install_fake_openai(
    monkeypatch,
    captured,
):
    class FakeResponses:
        async def create(
            self,
            **kwargs,
        ):
            captured.update(
                kwargs
            )

            return FakeResponse()

    class FakeClient:
        def __init__(
            self,
            api_key,
        ):
            captured[
                "api_key"
            ] = api_key

            self.responses = (
                FakeResponses()
            )

    module = types.ModuleType(
        "openai"
    )

    module.AsyncOpenAI = FakeClient

    monkeypatch.setitem(
        sys.modules,
        "openai",
        module,
    )


def test_requires_openai_provider():
    result = asyncio.run(
        PROV.analyze_images(
            "system",
            "look",
            [
                {
                    "type": "input_image",
                    "detail": "auto",
                    "image_url":
                        "https://example.com/a.jpg",
                }
            ],
            provider="other",
            model="vision-model",
        )
    )

    assert result["ok"] is False

    assert (
        result["error"]
        == "unsupported_multimodal_provider"
    )


def test_requires_model():
    result = asyncio.run(
        PROV.analyze_images(
            "system",
            "look",
            [
                {
                    "type": "input_image",
                    "detail": "auto",
                    "image_url":
                        "https://example.com/a.jpg",
                }
            ],
            provider="openai",
            model="",
        )
    )

    assert result["ok"] is False

    assert (
        result["error"]
        == "multimodal_model_required"
    )


def test_requires_image():
    result = asyncio.run(
        PROV.analyze_images(
            "system",
            "look",
            [],
            provider="openai",
            model="vision-model",
        )
    )

    assert result["ok"] is False

    assert (
        result["error"]
        == "multimodal_image_required"
    )


def test_missing_api_key_fails_closed(
    monkeypatch,
):
    monkeypatch.delenv(
        "OPENAI_API_KEY",
        raising=False,
    )

    result = asyncio.run(
        PROV.analyze_images(
            "system",
            "look",
            [
                {
                    "type": "input_image",
                    "detail": "auto",
                    "image_url":
                        "https://example.com/a.jpg",
                }
            ],
            provider="openai",
            model="vision-model",
        )
    )

    assert result["ok"] is False

    assert (
        result["error"]
        == "missing_openai_api_key"
    )


def test_url_image_uses_responses_input_image(
    monkeypatch,
):
    captured = {}

    install_fake_openai(
        monkeypatch,
        captured,
    )

    monkeypatch.setenv(
        "OPENAI_API_KEY",
        "test-key",
    )

    result = asyncio.run(
        PROV.analyze_images(
            "SYSTEM",
            "What is in this image?",
            [
                {
                    "type": "input_image",
                    "detail": "high",
                    "image_url":
                        "https://example.com/a.jpg",
                }
            ],
            provider="openai",
            model="gpt-5.6-sol",
            timeout_seconds=5,
            max_output_tokens=500,
        )
    )

    assert result["ok"] is True
    assert result["text"] == "I can see a cat."

    assert captured["model"] == "gpt-5.6-sol"
    assert captured["instructions"] == "SYSTEM"

    assert (
        captured["store"]
        is False
    )

    content = (
        captured["input"][0][
            "content"
        ]
    )

    assert content[0] == {
        "type": "input_text",
        "text": "What is in this image?",
    }

    assert content[1] == {
        "type": "input_image",
        "detail": "high",
        "image_url":
            "https://example.com/a.jpg",
    }


def test_file_id_image_supported(
    monkeypatch,
):
    captured = {}

    install_fake_openai(
        monkeypatch,
        captured,
    )

    monkeypatch.setenv(
        "OPENAI_API_KEY",
        "test-key",
    )

    result = asyncio.run(
        PROV.analyze_images(
            "SYSTEM",
            "look",
            [
                {
                    "type": "input_image",
                    "detail": "auto",
                    "file_id": "file-123",
                }
            ],
            provider="openai",
            model="gpt-5.6-sol",
        )
    )

    assert result["ok"] is True

    content = (
        captured["input"][0][
            "content"
        ]
    )

    assert content[1] == {
        "type": "input_image",
        "detail": "auto",
        "file_id": "file-123",
    }


def test_provider_rejects_two_sources():
    result = asyncio.run(
        PROV.analyze_images(
            "system",
            "look",
            [
                {
                    "type": "input_image",
                    "detail": "auto",
                    "image_url":
                        "https://example.com/a.jpg",
                    "file_id": "file-123",
                }
            ],
            provider="openai",
            model="vision-model",
        )
    )

    assert result["ok"] is False

    assert (
        result["error"]
        == "invalid_multimodal_image_source"
    )


def test_provider_boundary_has_store_false():
    source = Path(
        "backend/ai_engine/provider.py"
    ).read_text(
        encoding="utf-8"
    )

    marker = (
        "# V13 MULTIMODAL VISION "
        "PROVIDER BOUNDARY"
    )

    section = source.split(
        marker,
        1,
    )[1]

    assert "store=False" in section


def test_no_other_v13_module_imports_openai():
    import ast

    root = Path(
        "backend/ai_engine"
    )

    violations = []

    for path in root.glob(
        "*.py"
    ):
        if path.name == "provider.py":
            continue

        tree = ast.parse(
            path.read_text(
                encoding="utf-8-sig"
            )
        )

        for node in ast.walk(
            tree
        ):
            if isinstance(
                node,
                ast.Import,
            ):
                if any(
                    alias.name == "openai"
                    or alias.name.startswith(
                        "openai."
                    )
                    for alias
                    in node.names
                ):
                    violations.append(
                        str(
                            path
                        )
                    )

            if isinstance(
                node,
                ast.ImportFrom,
            ):
                if (
                    node.module == "openai"
                    or (
                        node.module
                        and node.module.startswith(
                            "openai."
                        )
                    )
                ):
                    violations.append(
                        str(
                            path
                        )
                    )

    assert violations == []

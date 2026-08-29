import ast
import asyncio
import base64
from pathlib import Path
from types import SimpleNamespace

import pytest
import openai

from ai_engine import provider as PROV


class _FakeImages:
    def __init__(self):
        self.generate_kwargs = None
        self.edit_kwargs = None

    async def generate(self, **kwargs):
        self.generate_kwargs = kwargs

        return SimpleNamespace(
            data=[
                SimpleNamespace(
                    b64_json=base64.b64encode(
                        b"generated"
                    ).decode("ascii"),
                    revised_prompt="clean prompt",
                )
            ]
        )

    async def edit(self, **kwargs):
        self.edit_kwargs = kwargs

        return SimpleNamespace(
            data=[
                SimpleNamespace(
                    b64_json=base64.b64encode(
                        b"edited"
                    ).decode("ascii"),
                    revised_prompt=None,
                )
            ]
        )


class _FakeClient:
    last = None

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.images = _FakeImages()
        _FakeClient.last = self


def test_generate_image_uses_provider_boundary(
    monkeypatch,
):
    monkeypatch.setattr(
        openai,
        "AsyncOpenAI",
        _FakeClient,
    )

    result = asyncio.run(
        PROV.generate_image(
            prompt="a peaceful lake",
            model="gpt-image-test",
            size="1024x1024",
            quality="medium",
            background="auto",
        )
    )

    assert result["imageBytes"] == b"generated"
    assert result["mimeType"] == "image/png"
    assert result["revisedPrompt"] == "clean prompt"

    kwargs = (
        _FakeClient
        .last
        .images
        .generate_kwargs
    )

    assert kwargs["model"] == "gpt-image-test"
    assert kwargs["prompt"] == "a peaceful lake"
    assert kwargs["size"] == "1024x1024"
    assert kwargs["quality"] == "medium"
    assert kwargs["background"] == "auto"
    assert kwargs["n"] == 1
    assert kwargs["response_format"] == "b64_json"


def test_edit_image_uses_provider_boundary(
    monkeypatch,
):
    monkeypatch.setattr(
        openai,
        "AsyncOpenAI",
        _FakeClient,
    )

    source = object()

    result = asyncio.run(
        PROV.edit_image(
            instruction="make background blue",
            image_files=[source],
            model="gpt-image-test",
        )
    )

    assert result["imageBytes"] == b"edited"
    assert result["mimeType"] == "image/png"
    assert result["revisedPrompt"] is None

    kwargs = (
        _FakeClient
        .last
        .images
        .edit_kwargs
    )

    assert kwargs["model"] == "gpt-image-test"
    assert kwargs["image"] is source
    assert kwargs["prompt"] == "make background blue"
    assert kwargs["n"] == 1
    assert kwargs["response_format"] == "b64_json"


def test_generation_rejects_other_provider():
    with pytest.raises(
        ValueError,
        match="unsupported_image_provider",
    ):
        asyncio.run(
            PROV.generate_image(
                prompt="test",
                model="model",
                provider="other",
            )
        )


def test_edit_requires_source():
    with pytest.raises(
        ValueError,
        match="source_image_required",
    ):
        asyncio.run(
            PROV.edit_image(
                instruction="edit",
                image_files=[],
                model="model",
            )
        )


def test_provider_remains_only_openai_boundary():
    hits = []

    for path in Path(
        "backend/ai_engine"
    ).glob("*.py"):

        if path.name == "provider.py":
            continue

        source = path.read_text(
            encoding="utf-8-sig",
            errors="ignore",
        )

        if (
            "AsyncOpenAI(" in source
            or "OpenAI(" in source
            or ".images.generate(" in source
            or ".images.edit(" in source
            or ".responses.create(" in source
        ):
            hits.append(
                str(path)
            )

    assert hits == []


def test_provider_parses():
    source = Path(
        "backend/ai_engine/provider.py"
    ).read_text(
        encoding="utf-8-sig"
    )

    ast.parse(source)

    assert (
        "V14 IMAGE CREATION PROVIDER BOUNDARY"
        in source
    )

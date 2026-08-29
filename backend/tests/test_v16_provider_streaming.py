import asyncio
import functools
import sys
import types

import pytest

from ai_engine import provider as PROV




def run_async_test(func):
    """
    Run an async pytest test using the standard library event loop.

    This keeps the V16 test suite independent of pytest-asyncio and
    does not alter production dependencies.
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        return asyncio.run(
            func(*args, **kwargs)
        )

    return wrapper

class Delta:
    def __init__(self, content):
        self.content = content


class Choice:
    def __init__(
        self,
        content=None,
        finish_reason=None,
    ):
        self.delta = Delta(content)
        self.finish_reason = finish_reason


class Usage:
    def __init__(
        self,
        prompt_tokens=2,
        completion_tokens=3,
        total_tokens=5,
    ):
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens
        self.total_tokens = total_tokens

    def model_dump(self):
        return {
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
        }


class Chunk:
    def __init__(
        self,
        content=None,
        finish_reason=None,
        usage=None,
    ):
        self.choices = [
            Choice(
                content=content,
                finish_reason=finish_reason,
            )
        ]
        self.usage = usage


class FakeStream:
    def __init__(
        self,
        chunks,
        *,
        delay=0,
    ):
        self._chunks = list(chunks)
        self._index = 0
        self.delay = delay
        self.closed = False

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self.delay:
            await asyncio.sleep(
                self.delay
            )

        if self._index >= len(
            self._chunks
        ):
            raise StopAsyncIteration

        value = self._chunks[
            self._index
        ]

        self._index += 1

        return value

    async def aclose(self):
        self.closed = True


async def collect(**kwargs):
    output = []

    async for event in PROV.generate_stream(
        **kwargs
    ):
        output.append(event)

    return output


def install_fake_litellm(
    monkeypatch,
    func,
):
    fake_module = types.ModuleType(
        "litellm"
    )

    fake_module.acompletion = func

    monkeypatch.setitem(
        sys.modules,
        "litellm",
        fake_module,
    )


def base_kwargs():
    return {
        "system_message": "system",
        "user_prompt": "hello",
        "session_id": "opaque-session",
        "provider": "openai",
        "model": "model-test",
        "timeout_seconds": 1,
    }


def test_marker():
    assert PROV.V16_2_PROVIDER_STREAMING is True


def test_delta_text_object():
    chunk = Chunk(
        content="Hello"
    )

    assert (
        PROV._v16_stream_delta_text(
            chunk
        )
        == "Hello"
    )


def test_delta_text_dict():
    chunk = {
        "choices": [
            {
                "delta": {
                    "content": "Hello"
                }
            }
        ]
    }

    assert (
        PROV._v16_stream_delta_text(
            chunk
        )
        == "Hello"
    )


def test_content_list_normalization():
    content = [
        {"text": "Hel"},
        {"text": "lo"},
    ]

    assert (
        PROV._v16_stream_content_text(
            content
        )
        == "Hello"
    )


def test_finish_reason():
    chunk = Chunk(
        content="",
        finish_reason="stop",
    )

    assert (
        PROV._v16_stream_finish_reason(
            chunk
        )
        == "stop"
    )


def test_usage_normalization():
    chunk = Chunk(
        usage=Usage()
    )

    result = PROV._v16_stream_usage(
        chunk
    )

    assert result["prompt_tokens"] == 2
    assert result["completion_tokens"] == 3
    assert result["total_tokens"] == 5


@run_async_test
async def test_provider_and_model_required():
    events = await collect(
        system_message="system",
        user_prompt="hello",
        session_id="session",
        provider="",
        model="model",
        timeout_seconds=1,
    )

    assert len(events) == 1
    assert (
        events[0]["error"]
        == "stream_provider_required"
    )

    events = await collect(
        system_message="system",
        user_prompt="hello",
        session_id="session",
        provider="openai",
        model="",
        timeout_seconds=1,
    )

    assert len(events) == 1
    assert (
        events[0]["error"]
        == "stream_model_required"
    )


@run_async_test
async def test_stream_uses_explicit_router_values(
    monkeypatch,
):
    captured = {}

    stream = FakeStream([
        Chunk("Hello"),
        Chunk(
            "",
            finish_reason="stop",
            usage=Usage(),
        ),
    ])

    async def fake_acompletion(
        **kwargs
    ):
        captured.update(kwargs)
        return stream

    install_fake_litellm(
        monkeypatch,
        fake_acompletion,
    )

    events = await collect(
        **base_kwargs()
    )

    assert (
        captured["model"]
        == "openai/model-test"
    )

    assert captured["stream"] is True

    assert (
        captured["messages"][0]["role"]
        == "system"
    )

    assert (
        captured["messages"][1]["role"]
        == "user"
    )

    assert [
        event["event"]
        for event in events
    ] == [
        "delta",
        "completed",
    ]


@run_async_test
async def test_stream_delta_order(
    monkeypatch,
):
    async def fake_acompletion(
        **kwargs
    ):
        return FakeStream([
            Chunk("Earn"),
            Chunk("2"),
            Chunk("Love"),
            Chunk(
                "",
                finish_reason="stop",
            ),
        ])

    install_fake_litellm(
        monkeypatch,
        fake_acompletion,
    )

    events = await collect(
        **base_kwargs()
    )

    deltas = [
        event["text"]
        for event in events
        if event["event"] == "delta"
    ]

    assert deltas == [
        "Earn",
        "2",
        "Love",
    ]


@run_async_test
async def test_empty_chunks_not_emitted_as_delta(
    monkeypatch,
):
    async def fake_acompletion(
        **kwargs
    ):
        return FakeStream([
            Chunk(""),
            Chunk(None),
            Chunk("Hello"),
        ])

    install_fake_litellm(
        monkeypatch,
        fake_acompletion,
    )

    events = await collect(
        **base_kwargs()
    )

    deltas = [
        event
        for event in events
        if event["event"] == "delta"
    ]

    assert len(deltas) == 1
    assert deltas[0]["text"] == "Hello"


@run_async_test
async def test_completed_event_has_usage(
    monkeypatch,
):
    async def fake_acompletion(
        **kwargs
    ):
        return FakeStream([
            Chunk("Hello"),
            Chunk(
                "",
                finish_reason="stop",
                usage=Usage(
                    prompt_tokens=10,
                    completion_tokens=4,
                    total_tokens=14,
                ),
            ),
        ])

    install_fake_litellm(
        monkeypatch,
        fake_acompletion,
    )

    events = await collect(
        **base_kwargs()
    )

    completed = events[-1]

    assert completed["event"] == "completed"
    assert completed["finishReason"] == "stop"
    assert completed["usage"][
        "total_tokens"
    ] == 14


@run_async_test
async def test_stream_is_closed(
    monkeypatch,
):
    stream = FakeStream([
        Chunk("Hello")
    ])

    async def fake_acompletion(
        **kwargs
    ):
        return stream

    install_fake_litellm(
        monkeypatch,
        fake_acompletion,
    )

    await collect(
        **base_kwargs()
    )

    assert stream.closed is True


@run_async_test
async def test_creation_timeout(
    monkeypatch,
):
    async def fake_acompletion(
        **kwargs
    ):
        await asyncio.sleep(0.1)
        return FakeStream([])

    install_fake_litellm(
        monkeypatch,
        fake_acompletion,
    )

    kwargs = base_kwargs()
    kwargs["timeout_seconds"] = 0.01

    events = await collect(
        **kwargs
    )

    assert len(events) == 1
    assert (
        events[0]["error"]
        == "stream_provider_timeout"
    )


@run_async_test
async def test_iteration_timeout(
    monkeypatch,
):
    stream = FakeStream(
        [Chunk("late")],
        delay=0.1,
    )

    async def fake_acompletion(
        **kwargs
    ):
        return stream

    install_fake_litellm(
        monkeypatch,
        fake_acompletion,
    )

    kwargs = base_kwargs()
    kwargs["timeout_seconds"] = 0.01

    events = await collect(
        **kwargs
    )

    assert len(events) == 1
    assert (
        events[0]["error"]
        == "stream_provider_timeout"
    )

    assert stream.closed is True


@run_async_test
async def test_provider_exception_normalized(
    monkeypatch,
):
    async def fake_acompletion(
        **kwargs
    ):
        raise RuntimeError(
            "provider unavailable"
        )

    install_fake_litellm(
        monkeypatch,
        fake_acompletion,
    )

    events = await collect(
        **base_kwargs()
    )

    assert len(events) == 1

    assert (
        events[0]["error"]
        == "stream_provider_error:RuntimeError"
    )


@run_async_test
async def test_invalid_timeout_fails_closed():
    kwargs = base_kwargs()
    kwargs["timeout_seconds"] = 0

    events = await collect(
        **kwargs
    )

    assert len(events) == 1

    assert (
        events[0]["error"]
        == "stream_timeout_invalid"
    )


@run_async_test
async def test_no_provider_object_leaks(
    monkeypatch,
):
    async def fake_acompletion(
        **kwargs
    ):
        return FakeStream([
            Chunk("Hello"),
        ])

    install_fake_litellm(
        monkeypatch,
        fake_acompletion,
    )

    events = await collect(
        **base_kwargs()
    )

    for event in events:
        assert isinstance(
            event,
            dict,
        )

        assert "choices" not in event
        assert "delta" not in event


@run_async_test
async def test_session_id_not_sent_as_model_or_message(
    monkeypatch,
):
    captured = {}

    async def fake_acompletion(
        **kwargs
    ):
        captured.update(kwargs)
        return FakeStream([])

    install_fake_litellm(
        monkeypatch,
        fake_acompletion,
    )

    kwargs = base_kwargs()
    kwargs["session_id"] = (
        "private-session-value"
    )

    await collect(
        **kwargs
    )

    assert (
        "private-session-value"
        not in str(captured)
    )


@run_async_test
async def test_cancellation_propagates(
    monkeypatch,
):
    started = asyncio.Event()

    class BlockingStream:
        def __aiter__(self):
            return self

        async def __anext__(self):
            started.set()
            await asyncio.sleep(100)
            raise StopAsyncIteration

        async def aclose(self):
            return None

    async def fake_acompletion(
        **kwargs
    ):
        return BlockingStream()

    install_fake_litellm(
        monkeypatch,
        fake_acompletion,
    )

    async def consume():
        async for _ in PROV.generate_stream(
            **base_kwargs()
        ):
            pass

    task = asyncio.create_task(
        consume()
    )

    await started.wait()

    task.cancel()

    with pytest.raises(
        asyncio.CancelledError
    ):
        await task


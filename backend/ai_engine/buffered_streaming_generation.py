"""
V16.2C2 buffered provider-stream generation adapter.

Raw provider deltas stay internal.

The complete candidate is returned to CharacterEngine as a normal
ProviderResult so the existing semantic guard and repair lifecycle
remains authoritative before anything becomes deliverable.

No persistence.
No server transport.
No Flutter/client transport.
No voice.
"""

import asyncio

from . import provider as PROV
from . import streaming_intelligence as SI16


V16_2_BUFFERED_STREAMING_GENERATION = True


def _result(
    *,
    ok,
    text,
    provider,
    model,
    latency_ms=0,
    usage=None,
    error=None,
):
    return PROV.ProviderResult(
        ok=bool(ok),
        text=str(text or ""),
        provider=str(provider or ""),
        model=str(model or ""),
        latencyMs=max(
            0,
            int(latency_ms or 0),
        ),
        usage=(
            dict(usage)
            if isinstance(usage, dict)
            else {}
        ),
        error=error,
    )


def _event_error(event, fallback):
    value = ""

    if isinstance(event, dict):
        value = str(
            event.get("error")
            or ""
        ).strip()

    return value or fallback


async def generate_buffered_stream(
    system_message,
    user_prompt,
    *,
    session_id,
    provider,
    model,
    timeout_seconds=None,
):
    provider_name = str(
        provider or ""
    ).strip()

    model_name = str(
        model or ""
    ).strip()

    session_value = str(
        session_id or ""
    ).strip()

    if not provider_name:
        return _result(
            ok=False,
            text="",
            provider="",
            model=model_name,
            error="stream_provider_required",
        )

    if not model_name:
        return _result(
            ok=False,
            text="",
            provider=provider_name,
            model="",
            error="stream_model_required",
        )

    if not session_value:
        return _result(
            ok=False,
            text="",
            provider=provider_name,
            model=model_name,
            error="stream_session_required",
        )

    chunks = []
    total_chars = 0
    completed = False
    latency_ms = 0
    usage = {}

    try:
        stream = PROV.generate_stream(
            system_message,
            user_prompt,
            session_id=session_value,
            provider=provider_name,
            model=model_name,
            timeout_seconds=timeout_seconds,
        )

        async for event in stream:

            if not isinstance(event, dict):
                return _result(
                    ok=False,
                    text="",
                    provider=provider_name,
                    model=model_name,
                    latency_ms=latency_ms,
                    usage=usage,
                    error=(
                        "provider_stream_protocol_error:"
                        "non_mapping_event"
                    ),
                )

            event_type = str(
                event.get("event")
                or ""
            ).strip().casefold()

            try:
                latency_ms = max(
                    latency_ms,
                    int(
                        event.get("latencyMs")
                        or 0
                    ),
                )
            except (TypeError, ValueError):
                pass

            event_usage = event.get("usage")

            if (
                isinstance(event_usage, dict)
                and event_usage
            ):
                usage = dict(event_usage)

            if event_type == "delta":

                if not event.get("ok", False):
                    return _result(
                        ok=False,
                        text="",
                        provider=provider_name,
                        model=model_name,
                        latency_ms=latency_ms,
                        usage=usage,
                        error=_event_error(
                            event,
                            "provider_stream_delta_error",
                        ),
                    )

                piece = str(
                    event.get("text")
                    or ""
                )

                if not piece:
                    continue

                if len(piece) > SI16.MAX_CHUNK_CHARS:
                    return _result(
                        ok=False,
                        text="",
                        provider=provider_name,
                        model=model_name,
                        latency_ms=latency_ms,
                        usage=usage,
                        error="provider_stream_chunk_too_large",
                    )

                total_chars += len(piece)

                if total_chars > SI16.MAX_STREAM_CHARS:
                    return _result(
                        ok=False,
                        text="",
                        provider=provider_name,
                        model=model_name,
                        latency_ms=latency_ms,
                        usage=usage,
                        error="provider_stream_too_large",
                    )

                chunks.append(piece)
                continue

            if event_type == "completed":

                if not event.get("ok", False):
                    return _result(
                        ok=False,
                        text="",
                        provider=provider_name,
                        model=model_name,
                        latency_ms=latency_ms,
                        usage=usage,
                        error=_event_error(
                            event,
                            "provider_stream_completion_error",
                        ),
                    )

                if not chunks:
                    final_text = str(
                        event.get("text")
                        or ""
                    )

                    if len(final_text) > SI16.MAX_STREAM_CHARS:
                        return _result(
                            ok=False,
                            text="",
                            provider=provider_name,
                            model=model_name,
                            latency_ms=latency_ms,
                            usage=usage,
                            error="provider_stream_too_large",
                        )

                    if final_text:
                        chunks.append(final_text)

                completed = True
                break

            if event_type == "error":
                return _result(
                    ok=False,
                    text="",
                    provider=provider_name,
                    model=model_name,
                    latency_ms=latency_ms,
                    usage=usage,
                    error=_event_error(
                        event,
                        "provider_stream_error",
                    ),
                )

            return _result(
                ok=False,
                text="",
                provider=provider_name,
                model=model_name,
                latency_ms=latency_ms,
                usage=usage,
                error=(
                    "provider_stream_protocol_error:"
                    "unknown_event"
                ),
            )

        if not completed:
            return _result(
                ok=False,
                text="",
                provider=provider_name,
                model=model_name,
                latency_ms=latency_ms,
                usage=usage,
                error="provider_stream_incomplete",
            )

        return _result(
            ok=True,
            text="".join(chunks).strip(),
            provider=provider_name,
            model=model_name,
            latency_ms=latency_ms,
            usage=usage,
            error=None,
        )

    except asyncio.CancelledError:
        raise

    except Exception as exc:
        return _result(
            ok=False,
            text="",
            provider=provider_name,
            model=model_name,
            latency_ms=latency_ms,
            usage=usage,
            error=(
                "buffered_stream_error:"
                + type(exc).__name__
            ),
        )

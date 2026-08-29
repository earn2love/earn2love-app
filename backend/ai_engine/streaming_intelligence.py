"""
Earn2Love AI Engine V16.2
Streaming Response Intelligence.

Pure deterministic coordination for incremental response delivery.

This module owns:
- chunk sequencing;
- duplicate/stale chunk rejection;
- bounded chunk validation;
- finalization semantics;
- cancellation semantics;
- safe transport metadata.

This module does not:
- call an AI provider;
- choose a provider or model;
- write Firestore;
- create HTTP/SSE/WebSocket transport;
- mutate memory, relationship, goals or adaptation;
- implement voice/audio behavior.

The existing CharacterEngine remains semantic intelligence authority.
"""

from dataclasses import asdict, dataclass
from typing import Any, Dict, Iterable, List, Optional, Tuple

from ai_engine import realtime_intelligence as RT16


V16_2_STREAMING_RESPONSE_INTELLIGENCE = True

MAX_CHUNK_CHARS = 16384
MAX_STREAM_CHARS = 262144


@dataclass(frozen=True)
class StreamChunk:
    request_id: str
    session_key: str
    index: int
    text: str
    final: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class StreamState:
    request_id: str
    session_key: str
    next_index: int = 0
    accepted_chars: int = 0
    final_seen: bool = False
    cancelled: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class StreamDecision:
    accepted: bool
    reason: str
    state: StreamState
    chunk: Optional[StreamChunk]

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        return data


def start_stream(
    request: RT16.RealtimeRequest,
) -> StreamState:
    return StreamState(
        request_id=request.request_id,
        session_key=request.session_key,
    )


def _normalize_chunk_text(value: Any) -> str:
    if value is None:
        return ""

    text = str(value)

    if len(text) > MAX_CHUNK_CHARS:
        raise ValueError("stream_chunk_too_large")

    return text


def accept_chunk(
    state: StreamState,
    *,
    index: int,
    text: Any,
    final: bool = False,
) -> StreamDecision:
    index_value = int(index)

    if index_value < 0:
        raise ValueError("stream_chunk_index_invalid")

    if state.cancelled:
        return StreamDecision(
            accepted=False,
            reason="stream_cancelled",
            state=state,
            chunk=None,
        )

    if state.final_seen:
        return StreamDecision(
            accepted=False,
            reason="stream_already_final",
            state=state,
            chunk=None,
        )

    if index_value < state.next_index:
        return StreamDecision(
            accepted=False,
            reason="duplicate_or_stale_chunk",
            state=state,
            chunk=None,
        )

    if index_value > state.next_index:
        return StreamDecision(
            accepted=False,
            reason="out_of_order_chunk",
            state=state,
            chunk=None,
        )

    chunk_text = _normalize_chunk_text(text)

    if not chunk_text and not final:
        return StreamDecision(
            accepted=False,
            reason="empty_nonfinal_chunk",
            state=state,
            chunk=None,
        )

    new_total = state.accepted_chars + len(chunk_text)

    if new_total > MAX_STREAM_CHARS:
        return StreamDecision(
            accepted=False,
            reason="stream_size_limit",
            state=state,
            chunk=None,
        )

    chunk = StreamChunk(
        request_id=state.request_id,
        session_key=state.session_key,
        index=index_value,
        text=chunk_text,
        final=bool(final),
    )

    new_state = StreamState(
        request_id=state.request_id,
        session_key=state.session_key,
        next_index=index_value + 1,
        accepted_chars=new_total,
        final_seen=bool(final),
        cancelled=False,
    )

    return StreamDecision(
        accepted=True,
        reason="accepted",
        state=new_state,
        chunk=chunk,
    )


def cancel_stream(
    state: StreamState,
) -> StreamState:
    if state.final_seen:
        return state

    return StreamState(
        request_id=state.request_id,
        session_key=state.session_key,
        next_index=state.next_index,
        accepted_chars=state.accepted_chars,
        final_seen=False,
        cancelled=True,
    )


def delivery_event(
    chunk: StreamChunk,
) -> Dict[str, Any]:
    return {
        "version": "16.2",
        "type": (
            "response.completed"
            if chunk.final
            else "response.delta"
        ),
        "requestId": chunk.request_id,
        "sessionKey": chunk.session_key,
        "chunkIndex": chunk.index,
        "delta": chunk.text,
        "final": chunk.final,
    }


def cancellation_event(
    state: StreamState,
    *,
    reason: str = "client_cancelled",
) -> Dict[str, Any]:
    clean_reason = str(
        reason or "client_cancelled"
    ).strip()

    if not clean_reason or len(clean_reason) > 128:
        clean_reason = "client_cancelled"

    return {
        "version": "16.2",
        "type": "response.cancelled",
        "requestId": state.request_id,
        "sessionKey": state.session_key,
        "final": True,
        "reason": clean_reason,
        "semanticPersistence": False,
        "relationshipEvent": False,
        "memoryEvent": False,
        "adaptationEvent": False,
    }


def error_event(
    state: StreamState,
    *,
    code: str,
) -> Dict[str, Any]:
    clean_code = str(code or "stream_error").strip()

    if not clean_code or len(clean_code) > 128:
        clean_code = "stream_error"

    return {
        "version": "16.2",
        "type": "response.error",
        "requestId": state.request_id,
        "sessionKey": state.session_key,
        "final": True,
        "code": clean_code,
    }


def collect_text(
    chunks: Iterable[StreamChunk],
) -> str:
    ordered: List[Tuple[int, str]] = []

    for chunk in chunks:
        ordered.append(
            (
                int(chunk.index),
                str(chunk.text),
            )
        )

    ordered.sort(key=lambda item: item[0])

    return "".join(
        text
        for _, text in ordered
    )


def streaming_policy_directive() -> str:
    return (
        "Streaming changes delivery timing only. The existing CharacterEngine "
        "remains semantic intelligence authority. Partial delivery, client "
        "disconnect, cancellation, retry, duplicate chunks and transport "
        "failure are transport events and must not independently create "
        "memory, relationship, emotional, goal or adaptation evidence. "
        "Provider and model selection remain controlled by the existing "
        "router/provider architecture. Sandbox and evaluation sessions must "
        "not persist semantic user state."
    )

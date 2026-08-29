"""
V16.2C4 verified final-response delivery intelligence.

This layer receives only the final CharacterEngine response after the
existing generation, verification, repair and semantic lifecycle have
completed.

Provider stream deltas never enter this delivery layer.
"""

from dataclasses import dataclass
from typing import Any, Dict, Tuple

from . import realtime_intelligence as RT16
from . import streaming_intelligence as SI16


V16_2_VERIFIED_FINAL_RESPONSE_DELIVERY = True

DEFAULT_DELIVERY_CHUNK_CHARS = 512


@dataclass(frozen=True)
class VerifiedDeliveryPlan:
    request: RT16.RealtimeRequest
    state: SI16.StreamState
    events: Tuple[Dict[str, Any], ...]
    response_text: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request": self.request.to_dict(),
            "state": self.state.to_dict(),
            "events": [dict(event) for event in self.events],
            "responseText": self.response_text,
        }


def _clean_chunk_size(value: Any) -> int:
    try:
        size = int(value)
    except (TypeError, ValueError):
        raise ValueError("delivery_chunk_size_invalid")

    if size <= 0:
        raise ValueError("delivery_chunk_size_invalid")

    if size > SI16.MAX_CHUNK_CHARS:
        raise ValueError("delivery_chunk_size_too_large")

    return size


def _verified_response_text(
    engine_response: Dict[str, Any],
) -> str:
    if not isinstance(engine_response, dict):
        raise ValueError("engine_response_invalid")

    if engine_response.get("ok") is not True:
        raise ValueError("engine_response_not_verified")

    if "responseText" not in engine_response:
        raise ValueError("verified_response_text_missing")

    text = engine_response.get("responseText")

    if not isinstance(text, str):
        raise ValueError("verified_response_text_invalid")

    if len(text) > SI16.MAX_STREAM_CHARS:
        raise ValueError("verified_response_too_large")

    return text


def prepare_verified_delivery(
    engine_response: Dict[str, Any],
    *,
    character_id: str,
    user_id: str,
    conversation_id: str = "default",
    request_id: str,
    sequence: int = 0,
    sandbox: bool = False,
    chunk_size: int = DEFAULT_DELIVERY_CHUNK_CHARS,
) -> VerifiedDeliveryPlan:
    """
    Convert an already verified final engine response into deterministic
    delivery events.

    No generation occurs here.
    """

    text = _verified_response_text(engine_response)
    size = _clean_chunk_size(chunk_size)

    request = RT16.build_request(
        character_id=character_id,
        user_id=user_id,
        conversation_id=conversation_id,
        request_id=request_id,
        sequence=sequence,
        sandbox=sandbox,
    )

    state = SI16.start_stream(request)
    events = []

    if not text:
        decision = SI16.accept_chunk(
            state,
            index=0,
            text="",
            final=True,
        )

        if not decision.accepted or decision.chunk is None:
            raise RuntimeError(
                f"verified_delivery_rejected:{decision.reason}"
            )

        state = decision.state
        events.append(
            SI16.delivery_event(decision.chunk)
        )

        return VerifiedDeliveryPlan(
            request=request,
            state=state,
            events=tuple(events),
            response_text=text,
        )

    index = 0
    offset = 0

    while offset < len(text):
        end = min(
            offset + size,
            len(text),
        )

        piece = text[offset:end]
        final = end >= len(text)

        decision = SI16.accept_chunk(
            state,
            index=index,
            text=piece,
            final=final,
        )

        if not decision.accepted or decision.chunk is None:
            raise RuntimeError(
                f"verified_delivery_rejected:{decision.reason}"
            )

        state = decision.state

        events.append(
            SI16.delivery_event(
                decision.chunk
            )
        )

        offset = end
        index += 1

    return VerifiedDeliveryPlan(
        request=request,
        state=state,
        events=tuple(events),
        response_text=text,
    )


def cancel_verified_delivery(
    state: SI16.StreamState,
    *,
    reason: str = "client_cancelled",
):
    """
    Cancel delivery only.

    This does not create or modify semantic evidence.
    """

    cancelled_state = SI16.cancel_stream(
        state
    )

    return (
        cancelled_state,
        SI16.cancellation_event(
            cancelled_state,
            reason=reason,
        ),
    )


def verified_delivery_error(
    state: SI16.StreamState,
    *,
    code: str,
):
    """
    Normalize a delivery-layer transport failure.
    """

    return SI16.error_event(
        state,
        code=code,
    )


def delivered_text(
    plan: VerifiedDeliveryPlan,
) -> str:
    chunks = []

    for event in plan.events:
        chunks.append(
            SI16.StreamChunk(
                request_id=event["requestId"],
                session_key=event["sessionKey"],
                index=event["chunkIndex"],
                text=event["delta"],
                final=event["final"],
            )
        )

    return SI16.collect_text(chunks)

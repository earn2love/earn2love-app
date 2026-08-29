"""
Earn2Love AI Engine V16.1
Real-Time Session Intelligence.

Pure deterministic coordination layer.

Responsibilities:
- define authenticated realtime session scope;
- protect character/user/conversation isolation;
- coordinate lifecycle state;
- define safe cancellation/interruption semantics;
- define delivery sequencing metadata;
- preserve existing engine as semantic intelligence authority.

This module does NOT:
- call an external AI provider;
- write Firestore;
- create WebSockets/SSE transport;
- persist user state;
- mutate global character personality;
- mutate relationship/memory/goal/adaptation state;
- create billing/subscription policy;
- create voice or audio behavior.
"""

from dataclasses import asdict, dataclass
from enum import Enum
import hashlib
import re
from typing import Any, Dict, Optional


V16_1_REALTIME_SESSION_INTELLIGENCE = True


_MAX_ID_LENGTH = 256
_MAX_REQUEST_ID_LENGTH = 128
_SAFE_ID_RE = re.compile(r"^[A-Za-z0-9._:@+\-]+$")


class RealtimeSessionState(str, Enum):
    CREATED = "created"
    ACTIVE = "active"
    GENERATING = "generating"
    DELIVERING = "delivering"
    CANCELLED = "cancelled"
    COMPLETED = "completed"
    FAILED = "failed"
    CLOSED = "closed"


_TERMINAL_STATES = frozenset({
    RealtimeSessionState.CANCELLED,
    RealtimeSessionState.COMPLETED,
    RealtimeSessionState.FAILED,
    RealtimeSessionState.CLOSED,
})


_ALLOWED_TRANSITIONS = {
    RealtimeSessionState.CREATED: frozenset({
        RealtimeSessionState.ACTIVE,
        RealtimeSessionState.CANCELLED,
        RealtimeSessionState.FAILED,
        RealtimeSessionState.CLOSED,
    }),
    RealtimeSessionState.ACTIVE: frozenset({
        RealtimeSessionState.GENERATING,
        RealtimeSessionState.CANCELLED,
        RealtimeSessionState.FAILED,
        RealtimeSessionState.CLOSED,
    }),
    RealtimeSessionState.GENERATING: frozenset({
        RealtimeSessionState.DELIVERING,
        RealtimeSessionState.CANCELLED,
        RealtimeSessionState.FAILED,
    }),
    RealtimeSessionState.DELIVERING: frozenset({
        RealtimeSessionState.COMPLETED,
        RealtimeSessionState.CANCELLED,
        RealtimeSessionState.FAILED,
    }),
    RealtimeSessionState.CANCELLED: frozenset({
        RealtimeSessionState.CLOSED,
    }),
    RealtimeSessionState.COMPLETED: frozenset({
        RealtimeSessionState.CLOSED,
    }),
    RealtimeSessionState.FAILED: frozenset({
        RealtimeSessionState.CLOSED,
    }),
    RealtimeSessionState.CLOSED: frozenset(),
}


@dataclass(frozen=True)
class RealtimeScope:
    character_id: str
    user_id: str
    conversation_id: str

    def to_dict(self) -> Dict[str, str]:
        return asdict(self)


@dataclass(frozen=True)
class RealtimeRequest:
    scope: RealtimeScope
    request_id: str
    session_key: str
    sequence: int
    cancellable: bool
    persist_semantic_state: bool

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RealtimeTransition:
    previous_state: str
    next_state: str
    allowed: bool
    terminal: bool
    reason: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _clean_required_id(
    value: Optional[str],
    *,
    name: str,
    max_length: int = _MAX_ID_LENGTH,
) -> str:
    cleaned = str(value or "").strip()

    if not cleaned:
        raise ValueError(f"{name}_required")

    if len(cleaned) > max_length:
        raise ValueError(f"{name}_too_long")

    if not _SAFE_ID_RE.fullmatch(cleaned):
        raise ValueError(f"{name}_invalid")

    return cleaned


def build_scope(
    *,
    character_id: str,
    user_id: str,
    conversation_id: str = "default",
) -> RealtimeScope:
    return RealtimeScope(
        character_id=_clean_required_id(
            character_id,
            name="character_id",
        ),
        user_id=_clean_required_id(
            user_id,
            name="user_id",
        ),
        conversation_id=_clean_required_id(
            conversation_id or "default",
            name="conversation_id",
        ),
    )


def scope_fingerprint(
    scope: RealtimeScope,
) -> str:
    """
    Stable opaque scope fingerprint.

    Prevents raw user/character identifiers from being reused as
    transport/provider-side session identifiers.
    """

    raw = (
        f"{scope.character_id}\x1f"
        f"{scope.user_id}\x1f"
        f"{scope.conversation_id}"
    ).encode("utf-8")

    return hashlib.sha256(raw).hexdigest()


def build_session_key(
    scope: RealtimeScope,
) -> str:
    return f"rt16:{scope_fingerprint(scope)}"


def build_request(
    *,
    character_id: str,
    user_id: str,
    conversation_id: str = "default",
    request_id: str,
    sequence: int = 0,
    sandbox: bool = False,
) -> RealtimeRequest:
    scope = build_scope(
        character_id=character_id,
        user_id=user_id,
        conversation_id=conversation_id,
    )

    cleaned_request_id = _clean_required_id(
        request_id,
        name="request_id",
        max_length=_MAX_REQUEST_ID_LENGTH,
    )

    sequence_value = int(sequence)

    if sequence_value < 0:
        raise ValueError("sequence_invalid")

    return RealtimeRequest(
        scope=scope,
        request_id=cleaned_request_id,
        session_key=build_session_key(scope),
        sequence=sequence_value,
        cancellable=True,
        persist_semantic_state=not bool(sandbox),
    )


def can_transition(
    previous_state: RealtimeSessionState,
    next_state: RealtimeSessionState,
) -> bool:
    if previous_state == next_state:
        return False

    return next_state in _ALLOWED_TRANSITIONS.get(
        previous_state,
        frozenset(),
    )


def transition(
    previous_state: RealtimeSessionState,
    next_state: RealtimeSessionState,
) -> RealtimeTransition:
    allowed = can_transition(
        previous_state,
        next_state,
    )

    if allowed:
        reason = "allowed"
    elif previous_state == next_state:
        reason = "duplicate_transition"
    elif previous_state in _TERMINAL_STATES:
        reason = "terminal_state"
    else:
        reason = "invalid_transition"

    return RealtimeTransition(
        previous_state=previous_state.value,
        next_state=next_state.value,
        allowed=allowed,
        terminal=next_state in _TERMINAL_STATES,
        reason=reason,
    )


def is_terminal(
    state: RealtimeSessionState,
) -> bool:
    return state in _TERMINAL_STATES


def delivery_metadata(
    request: RealtimeRequest,
    *,
    state: RealtimeSessionState,
    chunk_index: int = 0,
    final: bool = False,
) -> Dict[str, Any]:
    chunk_value = int(chunk_index)

    if chunk_value < 0:
        raise ValueError("chunk_index_invalid")

    return {
        "version": "16.1",
        "requestId": request.request_id,
        "sessionKey": request.session_key,
        "sequence": request.sequence,
        "chunkIndex": chunk_value,
        "state": state.value,
        "final": bool(final),
    }


def cancellation_metadata(
    request: RealtimeRequest,
    *,
    reason: str = "client_cancelled",
) -> Dict[str, Any]:
    clean_reason = str(reason or "client_cancelled").strip()

    if len(clean_reason) > 128:
        clean_reason = "client_cancelled"

    return {
        "version": "16.1",
        "requestId": request.request_id,
        "sessionKey": request.session_key,
        "state": RealtimeSessionState.CANCELLED.value,
        "reason": clean_reason,
        "relationshipEvent": False,
        "memoryEvent": False,
        "emotionalEvent": False,
    }


def realtime_policy_directive() -> str:
    return (
        "V16 realtime transport must preserve the existing AI engine as "
        "semantic intelligence authority. Transport cancellation, reconnects, "
        "partial delivery, client disconnects and duplicate requests must not "
        "be interpreted as relationship conflict, emotional rejection, user "
        "preference, memory evidence, goal completion or adaptation evidence. "
        "All realtime work must remain isolated by authenticated character, "
        "user and conversation scope. Sandbox and evaluation sessions must not "
        "persist semantic user state. Global character personality remains "
        "immutable."
    )


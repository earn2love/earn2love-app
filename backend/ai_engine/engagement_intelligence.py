from __future__ import annotations

"""
V12 Conversation Engagement Intelligence.

Stateless generation-policy layer.

Responsibilities:
- reduce conversational dead ends;
- allow useful continuation without forcing questions;
- preserve V4 question-count authority;
- encourage compact callbacks only when authorized memory exists;
- respect disengagement;
- adapt warmth to relationship context without mutating personality;
- preserve multilingual/code-switched conversation naturally.

This module:
- performs no provider calls;
- performs no repository/Firestore writes;
- stores no user state;
- does not mutate V4/V6/V7/V11 objects.
"""

from dataclasses import dataclass
import re
from typing import Any, Iterable


ENGAGEMENT_VERSION = 12

DEPTH_MINIMAL = "minimal"
DEPTH_NATURAL = "natural"
DEPTH_EXPANDED = "expanded"

CONTINUATION_NONE = "none"
CONTINUATION_STATEMENT = "statement"
CONTINUATION_OPTIONAL_QUESTION = "optional_question"

_ACKNOWLEDGEMENTS = {
    "ok",
    "okay",
    "k",
    "kk",
    "fine",
    "alright",
    "right",
    "sure",
    "yeah",
    "yes",
    "yep",
    "hmm",
    "hm",
    "sare",
    "sarle",
    "avunu",
    "haa",
    "ha",
}

_DISENGAGEMENT_PHRASES = (
    "leave it",
    "leave me alone",
    "stop",
    "don't want to talk",
    "do not want to talk",
    "not now",
    "bye",
    "goodbye",
    "later",
    "vaddule",
    "vaddu",
    "oddu",
    "inka vaddu",
)

_POSITIVE_SOCIAL_PHRASES = (
    "i'm fine",
    "i am fine",
    "i'm good",
    "i am good",
    "doing good",
    "doing well",
    "bagunna",
    "baagunna",
    "bagunnanu",
    "baagunnanu",
)

_MEMORY_HINT_KEYS = (
    "summary",
    "text",
    "value",
    "object",
    "content",
)


def _norm(value: Any) -> str:
    text = str(value or "").strip().casefold()
    text = re.sub(r"\s+", " ", text)
    return text


def _tokens(value: Any) -> list[str]:
    return re.findall(
        r"[a-zA-Z0-9\u0080-\uffff']+",
        _norm(value),
    )


def _ends_with_question(value: Any) -> bool:
    return str(value or "").strip().endswith("?")


def _is_disengaging(user_text: Any) -> bool:
    text = _norm(user_text)

    if not text:
        return False

    return any(
        phrase == text
        or text.startswith(phrase + " ")
        for phrase in _DISENGAGEMENT_PHRASES
    )


def _is_acknowledgement(user_text: Any) -> bool:
    text = _norm(user_text).strip(" .,!")

    return text in _ACKNOWLEDGEMENTS


def _is_positive_social_reply(user_text: Any) -> bool:
    text = _norm(user_text).strip(" .,!")

    return any(
        phrase == text
        or text.startswith(phrase + " ")
        for phrase in _POSITIVE_SOCIAL_PHRASES
    )


def _memory_text(memory: Any) -> str:
    if not isinstance(memory, dict):
        return ""

    for key in _MEMORY_HINT_KEYS:
        value = memory.get(key)

        if isinstance(value, str) and value.strip():
            return value.strip()

    predicate = str(
        memory.get("predicate")
        or ""
    ).strip()

    value = str(
        memory.get("value")
        or memory.get("object")
        or ""
    ).strip()

    if predicate and value:
        return f"{predicate}: {value}"

    return value


def _usable_memory_count(
    selected_memories: Iterable[Any] | None,
) -> int:
    count = 0

    for memory in list(selected_memories or []):
        if not isinstance(memory, dict):
            continue

        status = _norm(
            memory.get(
                "status",
                "active",
            )
        )

        if status not in {
            "",
            "active",
            "confirmed",
            "current",
        }:
            continue

        if _memory_text(memory):
            count += 1

    return count


def _relationship_warmth(
    relationship: dict[str, Any] | None,
) -> str:
    relationship = dict(
        relationship
        or {}
    )

    state = _norm(
        relationship.get("state")
        or relationship.get("relationshipState")
        or relationship.get("tier")
        or ""
    )

    if state in {
        "love",
        "romantic",
        "close",
        "intimate",
        "deep",
    }:
        return "warm"

    if state in {
        "friendship",
        "friend",
        "comfortable",
        "familiar",
        "trusted",
    }:
        return "friendly_warm"

    return "friendly"


@dataclass(frozen=True)
class EngagementGuidance:
    version: int
    reply_depth: str
    continuation_mode: str
    allow_question: bool
    max_questions: int
    allow_memory_callback: bool
    memory_candidates: int
    warmth: str
    disengaging: bool
    acknowledgement: bool
    directive: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "replyDepth": self.reply_depth,
            "continuationMode": self.continuation_mode,
            "allowQuestion": self.allow_question,
            "maxQuestions": self.max_questions,
            "allowMemoryCallback": self.allow_memory_callback,
            "memoryCandidates": self.memory_candidates,
            "warmth": self.warmth,
            "disengaging": self.disengaging,
            "acknowledgement": self.acknowledgement,
        }


def analyze_engagement(
    user_text: str,
    conversation_guidance: Any,
    *,
    selected_memories: Iterable[Any] | None = None,
    relationship: dict[str, Any] | None = None,
    history: Iterable[Any] | None = None,
) -> EngagementGuidance:
    """
    Build stateless engagement guidance.

    V4 remains the hard authority for whether/how many questions are allowed.
    V12 may choose not to use an allowed question, but can never increase
    V4's question allowance.
    """

    text = str(
        user_text
        or ""
    ).strip()

    tokens = _tokens(
        text
    )

    disengaging = _is_disengaging(
        text
    )

    acknowledgement = _is_acknowledgement(
        text
    )

    positive_social = _is_positive_social_reply(
        text
    )

    v4_max_questions = int(
        getattr(
            conversation_guidance,
            "max_questions",
            0,
        )
        or 0
    )

    v4_should_followup = bool(
        getattr(
            conversation_guidance,
            "should_ask_followup",
            False,
        )
    )

    allow_question = (
        not disengaging
        and v4_should_followup
        and v4_max_questions > 0
        and not _ends_with_question(text)
    )

    max_questions = (
        min(
            1,
            max(
                0,
                v4_max_questions,
            ),
        )
        if allow_question
        else 0
    )

    memory_candidates = _usable_memory_count(
        selected_memories
    )

    allow_memory_callback = (
        not disengaging
        and memory_candidates > 0
    )

    warmth = _relationship_warmth(
        relationship
    )

    if disengaging:
        reply_depth = DEPTH_MINIMAL
        continuation_mode = CONTINUATION_NONE

    elif acknowledgement:
        reply_depth = DEPTH_NATURAL
        continuation_mode = CONTINUATION_STATEMENT

    elif positive_social:
        reply_depth = DEPTH_NATURAL

        continuation_mode = (
            CONTINUATION_OPTIONAL_QUESTION
            if allow_question
            else CONTINUATION_STATEMENT
        )

    elif len(tokens) <= 3:
        reply_depth = DEPTH_NATURAL

        continuation_mode = (
            CONTINUATION_OPTIONAL_QUESTION
            if allow_question
            else CONTINUATION_STATEMENT
        )

    elif len(tokens) >= 30:
        reply_depth = DEPTH_EXPANDED

        continuation_mode = (
            CONTINUATION_OPTIONAL_QUESTION
            if allow_question
            else CONTINUATION_STATEMENT
        )

    else:
        reply_depth = DEPTH_NATURAL

        continuation_mode = (
            CONTINUATION_OPTIONAL_QUESTION
            if allow_question
            else CONTINUATION_STATEMENT
        )

    parts = [
        "Treat this as one turn in an ongoing human-style conversation, not an isolated chatbot exchange.",
        "Answer the person's actual message first.",
        "Match the person's conversational language, code-switching, energy and level of formality naturally.",
        "Short input does not require a dead-end one-line reply: when useful, give roughly 1-3 natural conversational sentences, but never pad, lecture or become repetitive.",
        "Do not manufacture enthusiasm, intimacy or familiarity.",
        "Do not end every response with a question.",
        "V4 conversation intelligence remains the hard authority for question count.",
    ]

    if disengaging:
        parts.extend(
            [
                "The person appears to be disengaging. Respect that immediately.",
                "Keep the response brief and do not chase the conversation.",
                "Do not ask a follow-up question.",
            ]
        )

    elif acknowledgement:
        parts.extend(
            [
                "This is a short acknowledgement. Avoid replying with an equally empty conversational dead end when a natural continuation is available.",
                "Continue with a brief relevant statement, transition, reaction or conversational cue.",
                "Do not force a question because V4 has not authorized one.",
            ]
        )

    elif allow_question:
        parts.extend(
            [
                "At most one genuinely useful follow-up question is allowed.",
                "A question is optional, not mandatory. Prefer a natural statement when that flows better.",
            ]
        )

    else:
        parts.extend(
            [
                "Do not add a follow-up question on this turn.",
                "If conversational continuation is useful, use a natural statement, reaction, observation or transition instead.",
            ]
        )

    if allow_memory_callback:
        parts.extend(
            [
                "Relevant V11-selected memory is available. You may make one compact natural callback only when it clearly fits the current topic.",
                "Use only memory actually supplied in context; never invent a remembered fact or imply familiarity that is not supported.",
                "Do not dump memory, list remembered facts, or mention memory systems/storage.",
            ]
        )

    else:
        parts.append(
            "Do not invent a memory callback or claim the person told you something earlier unless supplied context supports it."
        )

    if warmth == "warm":
        parts.append(
            "The relationship context permits a warmer conversational delivery, while preserving boundaries and the locked global character personality."
        )

    elif warmth == "friendly_warm":
        parts.append(
            "Use a naturally friendly, familiar warmth where appropriate, without changing the locked global character personality."
        )

    else:
        parts.append(
            "Keep the delivery naturally friendly without manufacturing closeness."
        )

    if reply_depth == DEPTH_EXPANDED:
        parts.append(
            "The turn can support a somewhat fuller response, but remain conversational rather than essay-like."
        )

    elif reply_depth == DEPTH_MINIMAL:
        parts.append(
            "Prefer a minimal response for this turn."
        )

    else:
        parts.append(
            "Prefer natural conversational depth rather than either a dead-end fragment or unnecessary verbosity."
        )

    return EngagementGuidance(
        version=ENGAGEMENT_VERSION,
        reply_depth=reply_depth,
        continuation_mode=continuation_mode,
        allow_question=allow_question,
        max_questions=max_questions,
        allow_memory_callback=allow_memory_callback,
        memory_candidates=memory_candidates,
        warmth=warmth,
        disengaging=disengaging,
        acknowledgement=acknowledgement,
        directive="\n".join(
            f"- {part}"
            for part in parts
        ),
    )


def build_engagement_guidance(
    user_text: str,
    conversation_guidance: Any,
    *,
    selected_memories: Iterable[Any] | None = None,
    relationship: dict[str, Any] | None = None,
    history: Iterable[Any] | None = None,
) -> EngagementGuidance:
    return analyze_engagement(
        user_text,
        conversation_guidance,
        selected_memories=selected_memories,
        relationship=relationship,
        history=history,
    )

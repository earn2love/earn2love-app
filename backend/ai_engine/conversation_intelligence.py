"""
Earn2Love AI Engine V4
Conversation Intelligence Controller.

Pure deterministic conversation analysis.
No provider calls.
No global mutable per-user state.
No Firestore writes.

The controller consumes the current message + already isolated conversation
history and returns generation guidance for CharacterEngine.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, asdict
from typing import Any, Iterable


_ACKS = {
    "ok",
    "okay",
    "k",
    "kk",
    "hmm",
    "hm",
    "hmmm",
    "yeah",
    "yep",
    "yes",
    "no",
    "nope",
    "right",
    "true",
    "fine",
    "sure",
    "cool",
    "nice",
    "alright",
    "acha",
    "accha",
    "haa",
    "ha",
    "avunu",
    "sare",
    "okay ra",
    "ok ra",
}

_CONTINUATION_WORDS = {
    "why",
    "how",
    "then",
    "and",
    "but",
    "really",
    "seriously",
    "what",
    "when",
    "where",
    "who",
    "which",
    "because",
}

_CORRECTION_PREFIXES = (
    "no i mean",
    "no, i mean",
    "i mean",
    "actually",
    "not that",
    "that's not",
    "thats not",
    "you misunderstood",
    "what i meant",
)

_RETURN_PATTERNS = (
    "back to",
    "coming back to",
    "about what we were",
    "earlier you said",
    "you said earlier",
    "we were talking about",
    "as i said before",
    "like i told you",
    "remember when",
)

_EXIT_PATTERNS = (
    "anyway",
    "leave it",
    "forget it",
    "never mind",
    "nevermind",
    "skip that",
    "change topic",
    "something else",
)

_QUESTION_OPENERS = (
    "what",
    "why",
    "how",
    "when",
    "where",
    "who",
    "which",
    "can",
    "could",
    "would",
    "should",
    "do",
    "does",
    "did",
    "is",
    "are",
    "am",
    "will",
    "have",
    "has",
)

_STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "if", "then", "than",
    "to", "of", "for", "from", "in", "on", "at", "with", "about",
    "this", "that", "these", "those", "it", "its", "i", "me", "my",
    "mine", "you", "your", "yours", "we", "our", "ours", "they",
    "their", "he", "she", "is", "am", "are", "was", "were", "be",
    "been", "being", "do", "does", "did", "have", "has", "had",
    "can", "could", "would", "should", "will", "just", "really",
    "very", "so", "like", "okay", "ok", "yeah", "yes", "no",
}


@dataclass(frozen=True)
class ConversationGuidance:
    message_kind: str
    continuity_mode: str
    current_topic: str | None
    previous_topic: str | None
    should_ask_followup: bool
    should_answer_directly: bool
    should_acknowledge_first: bool
    should_reference_context: bool
    should_avoid_new_topic: bool
    user_is_correcting: bool
    user_is_returning: bool
    user_is_disengaging: bool
    short_reply: bool
    question: bool
    pacing: str
    max_questions: int
    anti_repetition: bool
    guidance_text: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _text(turn: Any) -> str:
    if isinstance(turn, str):
        return turn.strip()

    if isinstance(turn, dict):
        return str(turn.get("text") or "").strip()

    return ""


def _sender(turn: Any) -> str:
    if isinstance(turn, dict):
        return str(turn.get("sender") or "").lower().strip()
    return ""


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "").strip())


def _lower(text: str) -> str:
    return _normalize(text).casefold()


def _tokens(text: str) -> list[str]:
    return re.findall(
        r"[a-zA-ZÀ-ÿ\u0C00-\u0C7F\u0900-\u097F']+",
        _lower(text),
    )


def _keywords(text: str, limit: int = 5) -> list[str]:
    result = []

    for token in _tokens(text):
        if len(token) < 3:
            continue

        if token in _STOPWORDS:
            continue

        if token not in result:
            result.append(token)

        if len(result) >= limit:
            break

    return result


def _topic(text: str) -> str | None:
    words = _keywords(text, limit=4)

    if not words:
        return None

    return " ".join(words[:3])


def _is_question(text: str) -> bool:
    value = _lower(text)

    if not value:
        return False

    if "?" in value:
        return True

    first = value.split(" ", 1)[0]

    return first in _QUESTION_OPENERS


def _is_acknowledgement(text: str) -> bool:
    value = _lower(text).strip(" .!?,")

    if value in _ACKS:
        return True

    tokens = value.split()

    return len(tokens) <= 2 and value in _ACKS


def _is_short(text: str) -> bool:
    return len(_tokens(text)) <= 4


def _starts_with_any(value: str, patterns: Iterable[str]) -> bool:
    return any(
        value.startswith(pattern)
        or pattern in value
        for pattern in patterns
    )


def _recent_user_messages(history: list[Any]) -> list[str]:
    messages = []

    for turn in history:
        if _sender(turn) == "user":
            text = _text(turn)
            if text:
                messages.append(text)

    return messages


def _recent_ai_messages(history: list[Any]) -> list[str]:
    messages = []

    for turn in history:
        if _sender(turn) in {"assistant", "character", "ai"}:
            text = _text(turn)
            if text:
                messages.append(text)

    return messages


def _previous_topic(history: list[Any]) -> str | None:
    for turn in reversed(history):
        if _sender(turn) != "user":
            continue

        candidate = _topic(_text(turn))

        if candidate:
            return candidate

    return None


def repeated_ai_openings(history: list[Any], limit: int = 6) -> list[str]:
    openings = []

    for text in _recent_ai_messages(history)[-limit:]:
        cleaned = re.sub(r"[^a-zA-Z0-9\s']", " ", text.casefold())
        words = cleaned.split()

        if not words:
            continue

        opening = " ".join(words[:4])

        if opening:
            openings.append(opening)

    duplicates = []

    for opening in openings:
        if openings.count(opening) > 1 and opening not in duplicates:
            duplicates.append(opening)

    return duplicates


def analyze(
    user_text: str,
    history: list[Any] | None = None,
    *,
    relationship_state: str | None = None,
) -> ConversationGuidance:
    history = list(history or [])
    raw = _normalize(user_text)
    value = _lower(raw)

    tokens = _tokens(raw)
    short_reply = _is_short(raw)
    question = _is_question(raw)
    acknowledgement = _is_acknowledgement(raw)

    correcting = _starts_with_any(
        value,
        _CORRECTION_PREFIXES,
    )

    returning = _starts_with_any(
        value,
        _RETURN_PATTERNS,
    )

    disengaging = _starts_with_any(
        value,
        _EXIT_PATTERNS,
    )

    first = value.split(" ", 1)[0] if value else ""

    continuation = (
        acknowledgement
        or first in _CONTINUATION_WORDS
        or (short_reply and bool(history))
    )

    previous_topic = _previous_topic(history)

    current_topic = _topic(raw)

    if acknowledgement and previous_topic:
        current_topic = previous_topic

    if returning:
        continuity_mode = "return"
    elif correcting:
        continuity_mode = "repair"
    elif disengaging:
        continuity_mode = "topic_exit"
    elif continuation:
        continuity_mode = "continue"
    elif previous_topic and current_topic == previous_topic:
        continuity_mode = "continue"
    elif previous_topic and current_topic:
        continuity_mode = "switch"
    else:
        continuity_mode = "new"

    if correcting:
        message_kind = "correction"
    elif returning:
        message_kind = "topic_return"
    elif disengaging:
        message_kind = "topic_exit"
    elif acknowledgement:
        message_kind = "acknowledgement"
    elif question:
        message_kind = "question"
    elif short_reply:
        message_kind = "short_reply"
    else:
        message_kind = "statement"

    should_answer_directly = (
        question
        or correcting
        or returning
        or first in {"why", "how", "what", "when", "where", "who"}
    )

    should_acknowledge_first = (
        correcting
        or disengaging
        or relationship_state in {"comfortable", "established"}
    )

    should_reference_context = bool(
        history
        and (
            continuation
            or correcting
            or returning
        )
    )

    should_avoid_new_topic = (
        acknowledgement
        or correcting
        or returning
        or question
    )

    # Avoid the classic chatbot habit of ending every message with a question.
    should_ask_followup = (
        not question
        and not correcting
        and not disengaging
        and not acknowledgement
        and len(tokens) >= 5
    )

    if relationship_state in {"comfortable", "established"}:
        pacing = "natural_familiar"
    elif acknowledgement or short_reply:
        pacing = "brief"
    else:
        pacing = "natural"

    max_questions = 1 if should_ask_followup else 0

    duplicate_openings = repeated_ai_openings(history)

    guidance_parts = [
        f"Conversation mode: {continuity_mode}.",
        f"Message type: {message_kind}.",
    ]

    if should_answer_directly:
        guidance_parts.append(
            "Answer the user's actual point first; do not delay the answer with filler."
        )

    if acknowledgement:
        guidance_parts.append(
            "This is a brief acknowledgement. Continue naturally from the immediate context instead of restarting the conversation."
        )

    if correcting:
        guidance_parts.append(
            "The user is correcting or clarifying. Accept the correction naturally and use the corrected meaning immediately."
        )

    if returning:
        guidance_parts.append(
            "The user is returning to an earlier thread. Reconnect to that thread naturally without pretending it is a new topic."
        )

    if disengaging:
        guidance_parts.append(
            "The user wants to leave the current topic. Do not drag them back into it."
        )

    if should_avoid_new_topic:
        guidance_parts.append(
            "Do not introduce an unrelated topic."
        )

    if max_questions == 0:
        guidance_parts.append(
            "Do not force a follow-up question at the end."
        )
    else:
        guidance_parts.append(
            "At most one genuinely useful follow-up question is allowed."
        )

    guidance_parts.append(
        "Do not repeat facts, advice, greetings, sympathy phrases, or questions that were already clear from the recent conversation."
    )

    guidance_parts.append(
        "Keep conversational momentum: respond as if this is one continuous real conversation, not independent chatbot turns."
    )

    if duplicate_openings:
        guidance_parts.append(
            "Recent AI openings were repetitive; deliberately vary the next opening and sentence structure."
        )

    if previous_topic:
        guidance_parts.append(
            f"Recent conversation topic signal: {previous_topic}."
        )

    return ConversationGuidance(
        message_kind=message_kind,
        continuity_mode=continuity_mode,
        current_topic=current_topic,
        previous_topic=previous_topic,
        should_ask_followup=should_ask_followup,
        should_answer_directly=should_answer_directly,
        should_acknowledge_first=should_acknowledge_first,
        should_reference_context=should_reference_context,
        should_avoid_new_topic=should_avoid_new_topic,
        user_is_correcting=correcting,
        user_is_returning=returning,
        user_is_disengaging=disengaging,
        short_reply=short_reply,
        question=question,
        pacing=pacing,
        max_questions=max_questions,
        anti_repetition=True,
        guidance_text=" ".join(guidance_parts),
    )


def prompt_guidance(
    user_text: str,
    history: list[Any] | None = None,
    *,
    relationship_state: str | None = None,
) -> str:
    return analyze(
        user_text,
        history,
        relationship_state=relationship_state,
    ).guidance_text


# ============================================================================
# V4.2 — HUMAN CONVERSATION BEHAVIOUR
# ============================================================================


def _first_words(text: str, count: int = 5) -> str:
    cleaned = re.sub(
        r"[^a-zA-Z0-9À-ÿ\u0C00-\u0C7F\u0900-\u097F\s']",
        " ",
        str(text or "").casefold(),
    )

    return " ".join(cleaned.split()[:count])


def _ends_with_question(text: str) -> bool:
    value = str(text or "").rstrip()
    return value.endswith("?")


def _question_count(text: str) -> int:
    return str(text or "").count("?")


def recent_topics(
    history: list[Any] | None,
    *,
    limit: int = 6,
) -> list[str]:
    """
    Return compact topic signals from recent user turns.

    This never shares state between users. It analyses only the history
    supplied to this invocation.
    """
    result: list[str] = []

    for turn in reversed(list(history or [])):
        if _sender(turn) != "user":
            continue

        topic = _topic(_text(turn))

        if topic and topic not in result:
            result.append(topic)

        if len(result) >= limit:
            break

    result.reverse()

    return result


def unresolved_thread(
    history: list[Any] | None,
) -> dict[str, Any] | None:
    """
    Detect a lightweight open conversational thread.

    Examples:
      AI asked something and the user only replied "hmm".
      User was discussing one subject and returns to it.
    """
    history = list(history or [])

    if not history:
        return None

    last_ai = None
    last_user_before_ai = None

    for index in range(len(history) - 1, -1, -1):
        turn = history[index]

        if last_ai is None and _sender(turn) in {
            "character",
            "assistant",
            "ai",
        }:
            last_ai = _text(turn)

            for earlier in range(index - 1, -1, -1):
                candidate = history[earlier]

                if _sender(candidate) == "user":
                    last_user_before_ai = _text(candidate)
                    break

            break

    if not last_ai:
        return None

    topic = _topic(last_user_before_ai or last_ai)

    return {
        "topic": topic,
        "aiAskedQuestion": _ends_with_question(last_ai),
        "lastAiText": last_ai,
    }


def human_conversation_guidance(
    guidance: ConversationGuidance,
    history: list[Any] | None,
) -> str:
    parts: list[str] = []

    parts.append(
        "Sound like one continuing conversation, not a sequence of independent assistant answers."
    )

    parts.append(
        "Do not routinely begin with validation phrases such as "
        "'I understand', 'That makes sense', 'Absolutely', "
        "'That's a great question', or the person's name."
    )

    parts.append(
        "Do not restate the person's message unless clarification genuinely requires it."
    )

    parts.append(
        "Vary openings, rhythm, sentence length and conversational structure."
    )

    parts.append(
        "Never manufacture a question merely to keep the conversation alive."
    )

    parts.append(
        "Do not repeatedly offer generic help such as "
        "'I'm here if you need anything' or 'let me know if you want to talk'."
    )

    if guidance.pacing == "brief":
        parts.append(
            "The person's message is brief; usually respond briefly and naturally rather than sending a mini-essay."
        )

    if guidance.continuity_mode == "continue":
        parts.append(
            "Continue the immediate thread without greeting again or re-explaining established context."
        )

    elif guidance.continuity_mode == "switch":
        parts.append(
            "The person appears to have shifted topic. Follow the new topic naturally without awkwardly forcing the previous one back in."
        )

    elif guidance.continuity_mode == "repair":
        parts.append(
            "Treat the correction as authoritative. Update your interpretation immediately and do not defend the earlier misunderstanding."
        )

    elif guidance.continuity_mode == "return":
        parts.append(
            "Reconnect naturally to the earlier subject and use relevant context already known."
        )

    elif guidance.continuity_mode == "topic_exit":
        parts.append(
            "Let the previous subject end. Do not pressure the person to continue discussing it."
        )

    thread = unresolved_thread(history)

    if (
        thread
        and thread.get("aiAskedQuestion")
        and guidance.message_kind == "acknowledgement"
    ):
        parts.append(
            "Your previous turn contained a question and the person only acknowledged it. "
            "Do not repeat that same question mechanically; infer whether to continue, clarify briefly, or allow the thread to rest."
        )

    topics = recent_topics(history)

    if topics:
        parts.append(
            "Recent thread signals: "
            + " | ".join(topics[-4:])
            + "."
        )

    return " ".join(parts)


# ============================================================================
# V4.3 — PERSONALITY + MULTILINGUAL CONTINUITY
# ============================================================================


def _character_values(
    character: dict[str, Any] | None,
) -> list[str]:
    character = character or {}

    values: list[str] = []

    for key in (
        "personalityTraits",
        "communicationStyle",
        "speakingStyle",
        "tone",
        "humorStyle",
        "interests",
    ):
        value = character.get(key)

        if isinstance(value, list):
            values.extend(
                str(x).strip()
                for x in value
                if str(x).strip()
            )

        elif value:
            values.append(str(value).strip())

    return values


def personality_guidance(
    character: dict[str, Any] | None,
    relationship: dict[str, Any] | None,
) -> str:
    """
    Character guidance that makes profiles remain distinguishable without
    inventing attributes absent from their global character definition.
    """
    character = character or {}
    relationship = relationship or {}

    traits = _character_values(character)

    parts = [
        "Preserve this character's individual voice across every turn.",
        "Do not drift into a generic assistant personality.",
        "Never invent personality traits merely to sound interesting.",
    ]

    if traits:
        parts.append(
            "Character style anchors: "
            + ", ".join(traits[:10])
            + "."
        )

    state = str(
        relationship.get("state") or "new"
    ).strip()

    if state == "new":
        parts.append(
            "The relationship is new: be natural but do not behave as though deep familiarity already exists."
        )

    elif state == "familiar":
        parts.append(
            "There is some familiarity: conversational callbacks are appropriate when genuinely relevant."
        )

    elif state == "comfortable":
        parts.append(
            "The relationship is comfortable: use a relaxed familiar rhythm without becoming possessive or over-attached."
        )

    elif state == "established":
        parts.append(
            "The relationship is established: familiarity and shared-context callbacks may feel natural, but remain independent and non-manipulative."
        )

    return " ".join(parts)


def _script_signal(text: str) -> str:
    text = str(text or "")

    telugu = sum(
        1
        for char in text
        if "\u0C00" <= char <= "\u0C7F"
    )

    devanagari = sum(
        1
        for char in text
        if "\u0900" <= char <= "\u097F"
    )

    latin = sum(
        1
        for char in text
        if (
            "a" <= char.casefold() <= "z"
            and char.isalpha()
        )
    )

    counts = {
        "telugu": telugu,
        "devanagari": devanagari,
        "latin": latin,
    }

    script, count = max(
        counts.items(),
        key=lambda item: item[1],
    )

    if count == 0:
        return "unknown"

    return script


def recent_user_script(
    history: list[Any] | None,
) -> str:
    for turn in reversed(list(history or [])):
        if _sender(turn) != "user":
            continue

        signal = _script_signal(_text(turn))

        if signal != "unknown":
            return signal

    return "unknown"


def multilingual_guidance(
    user_text: str,
    history: list[Any] | None,
    language: Any = None,
) -> str:
    current_script = _script_signal(user_text)
    previous_script = recent_user_script(history)

    parts = [
        "Match the person's conversational language naturally.",
        "Do not switch languages merely to demonstrate multilingual ability.",
        "If the person code-switches naturally, you may code-switch naturally too.",
        "Keep names, technical terms and common borrowed words natural instead of awkwardly translating everything.",
    ]

    if (
        previous_script != "unknown"
        and current_script == previous_script
    ):
        parts.append(
            f"The person's recent script remains {current_script}; maintain language continuity unless they clearly switch."
        )

    elif (
        previous_script != "unknown"
        and current_script != "unknown"
        and current_script != previous_script
    ):
        parts.append(
            f"The person appears to have changed writing script from {previous_script} to {current_script}; follow the current message rather than forcing the old language."
        )

    if isinstance(language, dict):
        code = (
            language.get("languageCode")
            or language.get("code")
            or language.get("language")
        )

        if code:
            parts.append(
                f"Resolved language-style signal: {code}."
            )

    return " ".join(parts)


# ============================================================================
# V4.4 — LONG-CONVERSATION INTELLIGENCE
# ============================================================================


def long_conversation_guidance(
    history: list[Any] | None,
) -> str:
    history = list(history or [])

    parts = [
        "Use older context only when it helps the present turn.",
        "Do not dump remembered history into the response.",
        "Do not mention that you are consulting memory, history, summaries or stored context.",
    ]

    if len(history) >= 12:
        parts.append(
            "This is an established multi-turn conversation. Preserve continuity across topic changes without recapping the whole chat."
        )

    if len(history) >= 24:
        parts.append(
            "For this longer conversation, prefer compact callbacks to relevant earlier events rather than repeating their full details."
        )

    topics = recent_topics(
        history,
        limit=6,
    )

    if len(topics) >= 3:
        parts.append(
            "Several subjects have appeared recently. Follow the person's current subject and retain the others only as background threads."
        )

    return " ".join(parts)


def build_generation_directive(
    guidance: ConversationGuidance,
    *,
    character: dict[str, Any] | None = None,
    relationship: dict[str, Any] | None = None,
    language: Any = None,
    history: list[Any] | None = None,
    user_text: str = "",
) -> str:
    """
    One compact V4 generation directive used by CharacterEngine.
    """
    sections = [
        guidance.guidance_text,
        human_conversation_guidance(
            guidance,
            history,
        ),
        personality_guidance(
            character,
            relationship,
        ),
        multilingual_guidance(
            user_text,
            history,
            language,
        ),
        long_conversation_guidance(
            history,
        ),
    ]

    return "\n".join(
        section.strip()
        for section in sections
        if section and section.strip()
    )


def response_quality_check(
    text: str,
    guidance: ConversationGuidance | None,
    recent_ai: list[str] | None = None,
) -> tuple[bool, str]:
    """
    V4 conversational quality guard.

    Conservative by design. It rejects only high-confidence chatbot-like
    failures so legitimate creative conversation remains possible.
    """
    if guidance is None:
        return True, "no_guidance"

    text = str(text or "").strip()

    if not text:
        return False, "empty_response"

    lower = text.casefold()

    robotic_openings = (
        "that's a great question",
        "that is a great question",
        "great question",
        "i'm glad you asked",
        "i am glad you asked",
    )

    if (
        guidance.should_answer_directly
        and any(
            lower.startswith(opening)
            for opening in robotic_openings
        )
    ):
        return False, "delayed_direct_answer"

    if (
        guidance.max_questions == 0
        and _ends_with_question(text)
    ):
        return False, "forced_followup_question"

    if guidance.max_questions >= 0:
        if _question_count(text) > max(
            1,
            guidance.max_questions,
        ):
            return False, "too_many_questions"

    opening = _first_words(
        text,
        5,
    )

    if opening:
        for previous in list(recent_ai or [])[-6:]:
            previous_opening = _first_words(
                previous,
                5,
            )

            if (
                previous_opening
                and opening == previous_opening
            ):
                return False, "repeated_opening"

    generic_closers = (
        "let me know if you want to talk",
        "i'm here if you need anything",
        "i am here if you need anything",
        "feel free to ask anything",
    )

    if (
        len(text.split()) < 35
        and any(
            closer in lower
            for closer in generic_closers
        )
    ):
        return False, "generic_assistant_closer"

    return True, "ok"

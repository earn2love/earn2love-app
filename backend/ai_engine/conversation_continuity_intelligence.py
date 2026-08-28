"""
Earn2Love AI Engine V11.3
Conversational Continuity Intelligence.

Pure deterministic continuity policy for recognizing unresolved topics,
resumable threads, commitments, interruptions and topic returns.

This module intentionally does NOT:
- persist continuity state
- replace V4 conversation intelligence
- write memories
- call providers
- call Firestore
- mutate personality/adaptation/goals/plans
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import re
from typing import Any, Mapping, Sequence


CONTINUITY_VERSION = 11


MODE_NEW = "new"
MODE_CONTINUE = "continue"
MODE_RESUME = "resume"
MODE_RETURN = "return"
MODE_COMPLETE = "complete"
MODE_ABANDON = "abandon"

VALID_MODES = frozenset(
    {
        MODE_NEW,
        MODE_CONTINUE,
        MODE_RESUME,
        MODE_RETURN,
        MODE_COMPLETE,
        MODE_ABANDON,
    }
)


@dataclass(frozen=True)
class ContinuityThread:
    thread_id: str
    topic: str
    summary: str
    status: str
    unresolved: bool
    commitment: str
    turn_count: int
    last_turn_index: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ContinuityAnalysis:
    mode: str
    active_thread_id: str
    selected_thread_id: str
    topic: str
    explicit_return: bool
    explicit_resume: bool
    completion_signal: bool
    abandon_signal: bool
    confidence: float
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


_RETURN_PATTERNS = (
    "back to",
    "going back to",
    "about what we discussed",
    "what we discussed earlier",
    "earlier we discussed",
    "we talked about",
    "coming back to",
)

_RESUME_PATTERNS = (
    "continue",
    "continue from",
    "where were we",
    "pick up",
    "carry on",
    "resume",
    "let's continue",
    "lets continue",
)

_COMPLETE_PATTERNS = (
    "done",
    "finished",
    "completed",
    "that's complete",
    "thats complete",
    "we are done",
    "we're done",
    "solved",
    "fixed now",
)

_ABANDON_PATTERNS = (
    "forget this topic",
    "leave this",
    "drop this",
    "stop this",
    "don't continue",
    "do not continue",
    "cancel this",
)

_UNRESOLVED_PATTERNS = (
    "need to",
    "still need",
    "pending",
    "not finished",
    "not done",
    "next step",
    "we need",
    "have to",
    "remaining",
    "issue",
    "problem",
    "blocked",
)

_COMMITMENT_PATTERNS = (
    r"\bi will\b",
    r"\bi'll\b",
    r"\bwe will\b",
    r"\bwe'll\b",
    r"\bneed to\b",
    r"\bhave to\b",
    r"\bmust\b",
)


def _text(
    value: Any,
) -> str:
    return str(
        value
        or ""
    ).strip()


def _lower(
    value: Any,
) -> str:
    return _text(
        value
    ).casefold()


def _clamp(
    value: float,
) -> float:
    return max(
        0.0,
        min(
            1.0,
            float(value),
        ),
    )


def _contains_any(
    text: str,
    patterns: Sequence[str],
) -> bool:
    lowered = _lower(
        text
    )

    return any(
        pattern in lowered
        for pattern in patterns
    )


def detect_explicit_return(
    user_text: str,
) -> bool:
    return _contains_any(
        user_text,
        _RETURN_PATTERNS,
    )


def detect_explicit_resume(
    user_text: str,
) -> bool:
    return _contains_any(
        user_text,
        _RESUME_PATTERNS,
    )


def detect_completion(
    user_text: str,
) -> bool:
    lowered = _lower(
        user_text
    )

    if not lowered:
        return False

    negated = (
        "not done",
        "not finished",
        "not completed",
        "not complete",
        "is not done",
        "isn't done",
        "isnt done",
        "is not finished",
        "isn't finished",
        "isnt finished",
        "is not fixed",
        "not fixed",
        "isn't fixed",
        "isnt fixed",
        "still broken",
        "still not working",
        "still unresolved",
    )

    if any(
        phrase in lowered
        for phrase in negated
    ):
        return False

    completed = (
        "that's done",
        "that is done",
        "it's done",
        "it is done",
        "we're done",
        "we are done",
        "finished now",
        "completed now",
        "that's complete",
        "that is complete",
        "fixed now",
        "solved now",
        "resolved now",
    )

    return any(
        phrase in lowered
        for phrase in completed
    )




def detect_abandon(
    user_text: str,
) -> bool:
    lowered = _lower(
        user_text
    )

    if not lowered:
        return False

    negated = (
        "don't stop this",
        "do not stop this",
        "don't drop this",
        "do not drop this",
        "don't leave this",
        "do not leave this",
        "don't abandon this",
        "do not abandon this",
        "don't cancel this",
        "do not cancel this",
    )

    if any(
        phrase in lowered
        for phrase in negated
    ):
        return False

    abandon = (
        "stop this issue",
        "stop this topic",
        "drop this issue",
        "drop this topic",
        "leave this issue",
        "leave this topic",
        "abandon this issue",
        "abandon this topic",
        "cancel this issue",
        "cancel this topic",
        "forget this issue",
        "forget this topic",
        "don't continue this",
        "do not continue this",
    )

    return any(
        phrase in lowered
        for phrase in abandon
    )




def detect_unresolved(
    text: str,
) -> bool:
    lowered = _lower(
        text
    )

    if not lowered:
        return False

    if detect_completion(
        lowered
    ):
        return False

    return any(
        pattern in lowered
        for pattern in _UNRESOLVED_PATTERNS
    )


def extract_commitment(
    text: str,
) -> str:
    lowered = _lower(
        text
    )

    if not lowered:
        return ""

    for pattern in _COMMITMENT_PATTERNS:
        if re.search(
            pattern,
            lowered,
        ):
            return _text(
                text
            )

    return ""


def normalize_thread(
    thread: Mapping[str, Any],
) -> ContinuityThread:
    thread_id = _text(
        thread.get(
            "threadId"
        )
        or thread.get(
            "thread_id"
        )
    )

    topic = _text(
        thread.get(
            "topic"
        )
    )

    summary = _text(
        thread.get(
            "summary"
        )
    )

    status = _lower(
        thread.get(
            "status",
            "active",
        )
    )

    unresolved_raw = thread.get(
        "unresolved"
    )

    if isinstance(
        unresolved_raw,
        bool,
    ):
        unresolved = unresolved_raw
    else:
        unresolved = detect_unresolved(
            summary
        )

    commitment = _text(
        thread.get(
            "commitment"
        )
    )

    try:
        turn_count = max(
            0,
            int(
                thread.get(
                    "turnCount",
                    thread.get(
                        "turn_count",
                        0,
                    ),
                )
            ),
        )
    except (
        TypeError,
        ValueError,
    ):
        turn_count = 0

    try:
        last_turn_index = max(
            0,
            int(
                thread.get(
                    "lastTurnIndex",
                    thread.get(
                        "last_turn_index",
                        0,
                    ),
                )
            ),
        )
    except (
        TypeError,
        ValueError,
    ):
        last_turn_index = 0

    return ContinuityThread(
        thread_id=thread_id,
        topic=topic,
        summary=summary,
        status=status,
        unresolved=unresolved,
        commitment=commitment,
        turn_count=turn_count,
        last_turn_index=last_turn_index,
    )


def topic_similarity(
    user_text: str,
    topic: str,
    summary: str = "",
) -> float:
    """
    Score how strongly the current user message matches a continuity
    thread.

    Direct matches against the thread's explicit topic receive priority
    over incidental/generic matches that occur only inside its summary.
    This prevents words such as "fix", "issue" or "need" in an unrelated
    thread summary from beating the thread whose actual topic was named
    by the user.
    """

    stop = {
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "for",
        "from",
        "i",
        "in",
        "is",
        "it",
        "me",
        "my",
        "of",
        "on",
        "the",
        "this",
        "to",
        "we",
        "what",
        "you",
        "your",
    }

    def tokens(
        value: str,
    ) -> set[str]:
        return {
            token
            for token in re.findall(
                r"[A-Za-z0-9']+",
                _lower(
                    value
                ),
            )
            if token not in stop
            and len(token) > 1
        }

    query_tokens = tokens(
        user_text
    )

    topic_tokens = tokens(
        topic
    )

    summary_tokens = tokens(
        summary
    )

    if not query_tokens:
        return 0.0

    # --------------------------------------------------------
    # Explicit topic-name matches have priority.
    #
    # Example:
    # user: "Let's fix Firebase"
    #
    # checkout summary may contain generic "fix",
    # but topic "firebase" is explicitly present in the query.
    # The Firebase thread therefore must rank higher.
    # --------------------------------------------------------

    direct_overlap = query_tokens.intersection(
        topic_tokens
    )

    if direct_overlap:

        topic_coverage = (
            len(
                direct_overlap
            )
            / max(
                1,
                len(
                    topic_tokens
                ),
            )
        )

        query_coverage = (
            len(
                direct_overlap
            )
            / max(
                1,
                len(
                    query_tokens
                ),
            )
        )

        return _clamp(
            0.75
            + (
                0.15
                * topic_coverage
            )
            + (
                0.10
                * query_coverage
            )
        )

    # --------------------------------------------------------
    # Summary matches remain useful for natural continuation,
    # but cannot receive the strong direct-topic priority.
    # --------------------------------------------------------

    if not summary_tokens:
        return 0.0

    summary_overlap = query_tokens.intersection(
        summary_tokens
    )

    if not summary_overlap:
        return 0.0

    query_coverage = (
        len(
            summary_overlap
        )
        / max(
            1,
            len(
                query_tokens
            ),
        )
    )

    summary_coverage = (
        len(
            summary_overlap
        )
        / max(
            1,
            len(
                summary_tokens
            ),
        )
    )

    return _clamp(
        min(
            0.70,
            (
                0.70
                * query_coverage
            )
            + (
                0.30
                * summary_coverage
            ),
        )
    )


def choose_thread(
    user_text: str,
    threads: Sequence[Mapping[str, Any]],
    *,
    active_thread_id: str = "",
) -> ContinuityThread | None:
    normalized = [
        normalize_thread(
            thread
        )
        for thread in threads
    ]

    candidates = [
        thread
        for thread in normalized
        if thread.status
        not in {
            "completed",
            "abandoned",
        }
    ]

    if not candidates:
        return None

    explicit_resume = detect_explicit_resume(
        user_text
    )

    if explicit_resume and active_thread_id:
        for thread in candidates:
            if thread.thread_id == active_thread_id:
                return thread

    ranked = sorted(
        candidates,
        key=lambda thread: (
            topic_similarity(
                user_text,
                thread.topic,
                thread.summary,
            ),
            thread.unresolved,
            bool(thread.commitment),
            thread.last_turn_index,
            thread.turn_count,
        ),
        reverse=True,
    )

    if ranked:
        best = ranked[0]

        similarity = topic_similarity(
            user_text,
            best.topic,
            best.summary,
        )

        if similarity > 0:
            return best

    if explicit_resume and candidates:
        return sorted(
            candidates,
            key=lambda thread: (
                thread.last_turn_index,
                thread.turn_count,
            ),
            reverse=True,
        )[0]

    return None


def analyze_continuity(
    user_text: str,
    threads: Sequence[Mapping[str, Any]],
    *,
    active_thread_id: str = "",
    current_topic: str = "",
) -> ContinuityAnalysis:
    explicit_return = detect_explicit_return(
        user_text
    )

    explicit_resume = detect_explicit_resume(
        user_text
    )

    completion = detect_completion(
        user_text
    )

    abandon = detect_abandon(
        user_text
    )

    selected = choose_thread(
        user_text,
        threads,
        active_thread_id=
            active_thread_id,
    )

    active = None

    for raw in threads:
        thread = normalize_thread(
            raw
        )

        if (
            active_thread_id
            and thread.thread_id
            == active_thread_id
        ):
            active = thread
            break

    if abandon:
        mode = MODE_ABANDON
        selected_thread_id = (
            active.thread_id
            if active
            else (
                selected.thread_id
                if selected
                else ""
            )
        )
        topic = (
            active.topic
            if active
            else (
                selected.topic
                if selected
                else current_topic
            )
        )
        confidence = 0.98
        reason = "explicit_abandon"

    elif completion:
        mode = MODE_COMPLETE
        selected_thread_id = (
            active.thread_id
            if active
            else (
                selected.thread_id
                if selected
                else ""
            )
        )
        topic = (
            active.topic
            if active
            else (
                selected.topic
                if selected
                else current_topic
            )
        )
        confidence = 0.96
        reason = "explicit_completion"

    elif explicit_resume:
        mode = MODE_RESUME
        selected_thread_id = (
            selected.thread_id
            if selected
            else active_thread_id
        )
        topic = (
            selected.topic
            if selected
            else current_topic
        )
        confidence = (
            0.95
            if selected
            else 0.70
        )
        reason = (
            "explicit_resume_match"
            if selected
            else "explicit_resume_without_match"
        )

    elif explicit_return and selected:
        mode = MODE_RETURN
        selected_thread_id = selected.thread_id
        topic = selected.topic
        confidence = 0.94
        reason = "explicit_topic_return"

    elif selected:
        selected_thread_id = selected.thread_id
        topic = selected.topic

        if (
            active_thread_id
            and selected.thread_id
            == active_thread_id
        ):
            mode = MODE_CONTINUE
            confidence = 0.86
            reason = "active_thread_match"
        else:
            mode = MODE_RETURN
            confidence = 0.78
            reason = "prior_thread_match"

    else:
        mode = MODE_NEW
        selected_thread_id = ""
        topic = current_topic
        confidence = 0.72
        reason = "no_matching_thread"

    return ContinuityAnalysis(
        mode=mode,
        active_thread_id=active_thread_id,
        selected_thread_id=
            selected_thread_id,
        topic=topic,
        explicit_return=explicit_return,
        explicit_resume=explicit_resume,
        completion_signal=completion,
        abandon_signal=abandon,
        confidence=_clamp(
            confidence
        ),
        reason=reason,
    )


def build_thread_candidate(
    *,
    thread_id: str,
    topic: str,
    summary: str,
    turn_count: int,
    last_turn_index: int,
    status: str = "active",
) -> ContinuityThread:
    unresolved = detect_unresolved(
        summary
    )

    commitment = extract_commitment(
        summary
    )

    return ContinuityThread(
        thread_id=_text(
            thread_id
        ),
        topic=_text(
            topic
        ),
        summary=_text(
            summary
        ),
        status=_lower(
            status
        )
        or "active",
        unresolved=unresolved,
        commitment=commitment,
        turn_count=max(
            0,
            int(
                turn_count
            ),
        ),
        last_turn_index=max(
            0,
            int(
                last_turn_index
            ),
        ),
    )


def safe_continuity_copy(
    analysis: ContinuityAnalysis,
) -> dict[str, Any]:
    return analysis.to_dict()


# ------------------------------------------------------------
# V11 resume-negation hardening.
# ------------------------------------------------------------

_v11_base_detect_explicit_resume = detect_explicit_resume


def detect_explicit_resume(
    user_text: str,
) -> bool:
    lowered = _lower(
        user_text
    )

    negated = (
        "don't continue",
        "do not continue",
        "don't resume",
        "do not resume",
        "don't carry on",
        "do not carry on",
    )

    if any(
        phrase in lowered
        for phrase in negated
    ):
        return False

    return _v11_base_detect_explicit_resume(
        user_text
    )


def _v11_safe_int(
    value,
    default=0,
):
    try:
        return int(
            value
        )
    except (
        TypeError,
        ValueError,
    ):
        return int(
            default
        )

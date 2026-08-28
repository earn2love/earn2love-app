"""
Earn2Love AI Engine V9.1
Structured Reasoning Intelligence.

This module is intentionally pure:
- no provider calls
- no Firestore access
- no mutable global user state
- no hidden chain-of-thought persistence

It produces safe structured reasoning metadata only:
facts, assumptions, unknowns, constraints, dependencies,
blockers, contradictions, verification needs and guidance.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass
import re
from typing import Any


REASONING_VERSION = 9

REASONING_MODES = (
    "direct",
    "analysis",
    "planning",
    "decision",
    "troubleshooting",
    "verification",
)

_MAX_ITEMS = 12


@dataclass(frozen=True)
class ReasoningAnalysis:
    mode: str
    requires_multi_step: bool
    facts: tuple[str, ...]
    assumptions: tuple[str, ...]
    unknowns: tuple[str, ...]
    constraints: tuple[str, ...]
    dependencies: tuple[str, ...]
    blockers: tuple[str, ...]
    contradictions: tuple[str, ...]
    should_verify: bool
    confidence: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ReasoningGuidance:
    analysis: ReasoningAnalysis
    directive: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "analysis": self.analysis.to_dict(),
            "directive": self.directive,
        }


_PLANNING = (
    "plan",
    "steps",
    "roadmap",
    "how do i build",
    "how can i build",
    "how do we build",
    "how can we build",
    "setup",
    "set up",
    "implement",
    "create",
    "launch",
)

_DECISION = (
    " vs ",
    " versus ",
    "which should",
    "which one",
    "choose between",
    "better option",
    "or should i",
    "or should we",
)

_TROUBLESHOOTING = (
    "error",
    "failed",
    "failing",
    "not working",
    "doesn't work",
    "does not work",
    "broken",
    "bug",
    "issue",
    "problem",
    "crash",
    "blocked",
    "unable",
    "can't",
    "cannot",
)

_VERIFICATION = (
    "verify",
    "check whether",
    "check if",
    "confirm",
    "validate",
    "audit",
    "make sure",
)

_CONSTRAINT_MARKERS = (
    "must",
    "must not",
    "can't",
    "cannot",
    "without",
    "only",
    "at least",
    "at most",
    "before",
    "after",
    "within",
    "under",
    "no more than",
    "do not",
    "don't",
    "need to",
    "needs to",
    "required",
    "requirement",
)

_DEPENDENCY_MARKERS = (
    "before",
    "after",
    "depends on",
    "dependent on",
    "requires",
    "require ",
    "prerequisite",
    "first ",
    "then ",
    "once ",
    "until ",
)

_BLOCKER_MARKERS = (
    "blocked",
    "can't",
    "cannot",
    "unable",
    "missing",
    "waiting for",
    "not working",
    "failed",
    "failure",
    "error",
    "doesn't work",
    "does not work",
)

_UNKNOWN_MARKERS = (
    "not sure",
    "don't know",
    "do not know",
    "unknown",
    "unclear",
    "not certain",
    "need to find out",
    "need to check",
)

_ASSUMPTION_MARKERS = (
    "assume",
    "assuming",
    "probably",
    "likely",
    "maybe",
    "perhaps",
    "i think",
    "we think",
)

_CONTRADICTION_MARKERS = (
    " but ",
    " however ",
    " although ",
    " instead ",
    " despite ",
    " even though ",
    " on the other hand ",
)


def _norm(value: Any) -> str:
    return re.sub(
        r"\s+",
        " ",
        str(value or "").strip().lower(),
    )


def _clean(value: str) -> str:
    return re.sub(
        r"\s+",
        " ",
        str(value or "").strip(),
    )


def _contains_any(
    text: str,
    signals: tuple[str, ...],
) -> bool:
    return any(
        signal in text
        for signal in signals
    )


def _clauses(text: str) -> list[str]:
    parts = re.split(
        r"(?<=[.!?;])\s+|\s+(?:and then|then)\s+",
        _clean(text),
        flags=re.IGNORECASE,
    )

    return [
        part.strip(" ,.;")
        for part in parts
        if part.strip(" ,.;")
    ][:_MAX_ITEMS]


def _matching_clauses(
    text: str,
    markers: tuple[str, ...],
) -> tuple[str, ...]:
    matches: list[str] = []

    for clause in _clauses(text):
        normalized = _norm(clause)

        if _contains_any(
            normalized,
            markers,
        ):
            matches.append(clause)

    return tuple(
        matches[:_MAX_ITEMS]
    )


def _extract_facts(
    user_text: str,
) -> tuple[str, ...]:
    facts: list[str] = []

    for clause in _clauses(user_text):
        normalized = _norm(clause)

        if (
            "?" in clause
            or _contains_any(
                normalized,
                _ASSUMPTION_MARKERS,
            )
            or _contains_any(
                normalized,
                _UNKNOWN_MARKERS,
            )
        ):
            continue

        factual_pattern = bool(
            re.search(
                r"\b(?:is|are|was|were|has|have|had|uses?|works?|runs?|contains?|includes?)\b",
                normalized,
            )
        )

        if factual_pattern:
            facts.append(clause)

    return tuple(
        facts[:_MAX_ITEMS]
    )


def _extract_unknowns(
    user_text: str,
) -> tuple[str, ...]:
    unknowns = list(
        _matching_clauses(
            user_text,
            _UNKNOWN_MARKERS,
        )
    )

    for clause in _clauses(user_text):
        if (
            "?" in clause
            and clause not in unknowns
        ):
            unknowns.append(clause)

    return tuple(
        unknowns[:_MAX_ITEMS]
    )


def _extract_contradictions(
    user_text: str,
) -> tuple[str, ...]:
    normalized = _norm(user_text)

    contradictions: list[str] = []

    if _contains_any(
        f" {normalized} ",
        _CONTRADICTION_MARKERS,
    ):
        contradictions.append(
            _clean(user_text)
        )

    if re.search(
        r"\bnot\b.+\bbut\b",
        normalized,
    ):
        value = _clean(user_text)

        if value not in contradictions:
            contradictions.append(value)

    return tuple(
        contradictions[:_MAX_ITEMS]
    )


def _reasoning_mode(
    normalized: str,
) -> str:
    if _contains_any(
        normalized,
        _TROUBLESHOOTING,
    ):
        return "troubleshooting"

    # Explicit planning intent outranks verification words
    # that may merely describe one step inside the plan.
    if _contains_any(
        normalized,
        _PLANNING,
    ):
        return "planning"

    if _contains_any(
        normalized,
        _VERIFICATION,
    ):
        return "verification"

    if _contains_any(
        f" {normalized} ",
        _DECISION,
    ):
        return "decision"

    token_count = len(
        normalized.split()
    )

    if (
        token_count <= 8
        and "?" not in normalized
    ):
        return "direct"

    return "analysis"


def analyze_reasoning(
    user_text: str,
) -> ReasoningAnalysis:
    raw = _clean(user_text)
    normalized = _norm(raw)

    facts = _extract_facts(raw)

    assumptions = _matching_clauses(
        raw,
        _ASSUMPTION_MARKERS,
    )

    unknowns = _extract_unknowns(
        raw
    )

    constraints = _matching_clauses(
        raw,
        _CONSTRAINT_MARKERS,
    )

    dependencies = _matching_clauses(
        raw,
        _DEPENDENCY_MARKERS,
    )

    blockers = _matching_clauses(
        raw,
        _BLOCKER_MARKERS,
    )

    contradictions = _extract_contradictions(
        raw
    )

    mode = _reasoning_mode(
        normalized
    )

    sequence_signals = sum(
        1
        for marker in (
            " first ",
            " then ",
            " after ",
            " before ",
            " once ",
            " step ",
            " steps ",
        )
        if marker in f" {normalized} "
    )

    requires_multi_step = bool(
        mode in {
            "planning",
            "troubleshooting",
        }
        and (
            sequence_signals > 0
            or len(dependencies) > 0
            or len(constraints) > 1
            or len(_clauses(raw)) > 1
        )
    )

    should_verify = bool(
        mode == "verification"
        or unknowns
        or contradictions
        or (
            mode == "troubleshooting"
            and blockers
        )
    )

    signal_count = sum(
        bool(value)
        for value in (
            facts,
            assumptions,
            unknowns,
            constraints,
            dependencies,
            blockers,
            contradictions,
        )
    )

    confidence = min(
        0.99,
        0.55
        + (0.05 * signal_count)
        + (
            0.08
            if mode != "analysis"
            else 0.0
        ),
    )

    return ReasoningAnalysis(
        mode=mode,
        requires_multi_step=requires_multi_step,
        facts=facts,
        assumptions=assumptions,
        unknowns=unknowns,
        constraints=constraints,
        dependencies=dependencies,
        blockers=blockers,
        contradictions=contradictions,
        should_verify=should_verify,
        confidence=round(
            confidence,
            3,
        ),
    )


def build_reasoning_guidance(
    user_text: str,
) -> ReasoningGuidance:
    analysis = analyze_reasoning(
        user_text
    )

    parts = [
        "V9 structured reasoning guidance.",
        f"Reasoning mode: {analysis.mode}.",
        (
            "Use multi-step reasoning internally and present only the useful conclusion or concise rationale."
            if analysis.requires_multi_step
            else
            "Do not overcomplicate the response when a direct answer is sufficient."
        ),
    ]

    if analysis.constraints:
        parts.append(
            "Respect the user's stated constraints before proposing an answer or plan."
        )

    if analysis.dependencies:
        parts.append(
            "Respect real dependencies and ordering; do not recommend a later step before its prerequisite."
        )

    if analysis.blockers:
        parts.append(
            "Address the active blocker before pretending progress can continue."
        )

    if analysis.unknowns:
        parts.append(
            "Do not invent missing facts. Ask only when the missing information is genuinely necessary; otherwise make the safest explicit assumption."
        )

    if analysis.assumptions:
        parts.append(
            "Keep assumptions distinct from known facts."
        )

    if analysis.contradictions:
        parts.append(
            "Resolve or acknowledge material contradictions before relying on the conflicting information."
        )

    if analysis.should_verify:
        parts.append(
            "Verify material uncertainty when verification is available and relevant."
        )

    parts.extend(
        [
            "Never expose or persist private chain-of-thought.",
            "Never manufacture facts, constraints, dependencies, blockers or requirements.",
            "Do not modify V6 global personality.",
            "Do not modify V7 adaptation.",
            "Do not modify V8 goal state.",
        ]
    )

    return ReasoningGuidance(
        analysis=analysis,
        directive=" ".join(parts),
    )


def safe_reasoning_copy(
    value: Any,
) -> Any:
    return deepcopy(value)

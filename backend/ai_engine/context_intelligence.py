"""Earn2Love V10 context-budget intelligence.

Pure deterministic layer deciding how much existing conversation context
is materially useful for a turn.

It never loads Firestore itself, never calls an LLM provider, never writes
memory/goal/plan state, and never exposes hidden reasoning.
"""

from dataclasses import dataclass
from typing import Any, Iterable, Sequence

from ai_engine import orchestration_intelligence as OI


CONTEXT_VERSION = 10

MAX_RECENT_TURNS = 16
MAX_MEMORY_ITEMS = 8
MAX_SUMMARY_CHARS = 5000


@dataclass(frozen=True)
class ContextSelection:
    recent_turn_limit: int
    memory_limit: int
    include_summary: bool
    include_goal: bool
    include_plan: bool
    include_relationship: bool
    include_adaptation: bool
    include_verification: bool
    reason: str

    def to_dict(self):
        return {
            "recentTurnLimit": self.recent_turn_limit,
            "memoryLimit": self.memory_limit,
            "includeSummary": self.include_summary,
            "includeGoal": self.include_goal,
            "includePlan": self.include_plan,
            "includeRelationship": self.include_relationship,
            "includeAdaptation": self.include_adaptation,
            "includeVerification": self.include_verification,
            "reason": self.reason,
            "contextVersion": CONTEXT_VERSION,
        }


def _mode(orchestration: Any) -> str:
    if orchestration is None:
        return OI.DIRECT

    if hasattr(orchestration, "decision"):
        orchestration = orchestration.decision

    if isinstance(orchestration, dict):
        return str(
            orchestration.get(
                "mode",
                orchestration.get(
                    "decision",
                    {},
                ).get(
                    "mode",
                    OI.DIRECT,
                )
                if isinstance(
                    orchestration.get(
                        "decision",
                        {},
                    ),
                    dict,
                )
                else OI.DIRECT,
            )
            or OI.DIRECT
        ).upper()

    return str(
        getattr(
            orchestration,
            "mode",
            OI.DIRECT,
        )
        or OI.DIRECT
    ).upper()


def select_context(
    orchestration,
    *,
    history_count=0,
    memory_count=0,
    has_active_goal=False,
    has_active_plan=False,
):
    mode = _mode(orchestration)

    history_count = max(
        0,
        int(
            history_count or 0
        ),
    )

    memory_count = max(
        0,
        int(
            memory_count or 0
        ),
    )

    if mode == OI.MEMORY:
        return ContextSelection(
            recent_turn_limit=min(
                max(
                    history_count,
                    8,
                ),
                12,
            ),
            memory_limit=min(
                max(
                    memory_count,
                    1,
                ),
                MAX_MEMORY_ITEMS,
            ),
            include_summary=history_count > 12,
            include_goal=bool(
                has_active_goal
            ),
            include_plan=bool(
                has_active_plan
            ),
            include_relationship=True,
            include_adaptation=True,
            include_verification=False,
            reason="memory-rich continuation",
        )

    if mode in (
        OI.PLAN,
        OI.EXECUTE,
        OI.RECOVER,
    ):
        return ContextSelection(
            recent_turn_limit=min(
                max(
                    history_count,
                    6,
                ),
                10,
            ),
            memory_limit=min(
                memory_count,
                4,
            ),
            include_summary=history_count > 10,
            include_goal=True,
            include_plan=True,
            include_relationship=True,
            include_adaptation=True,
            include_verification=(
                mode == OI.RECOVER
            ),
            reason="active structured work",
        )

    if mode in (
        OI.REASON,
        OI.VERIFY,
    ):
        return ContextSelection(
            recent_turn_limit=min(
                max(
                    history_count,
                    6,
                ),
                8,
            ),
            memory_limit=min(
                memory_count,
                4,
            ),
            include_summary=history_count > 8,
            include_goal=bool(
                has_active_goal
            ),
            include_plan=bool(
                has_active_plan
            ),
            include_relationship=True,
            include_adaptation=True,
            include_verification=(
                mode == OI.VERIFY
            ),
            reason="reasoning context",
        )

    if mode == OI.CONVERSATIONAL:
        return ContextSelection(
            recent_turn_limit=min(
                max(
                    history_count,
                    4,
                ),
                8,
            ),
            memory_limit=min(
                memory_count,
                2,
            ),
            include_summary=history_count > 16,
            include_goal=False,
            include_plan=False,
            include_relationship=True,
            include_adaptation=True,
            include_verification=False,
            reason="natural conversation",
        )

    return ContextSelection(
        recent_turn_limit=min(
            max(
                history_count,
                2,
            ),
            6,
        ),
        memory_limit=min(
            memory_count,
            2,
        ),
        include_summary=False,
        include_goal=False,
        include_plan=False,
        include_relationship=True,
        include_adaptation=True,
        include_verification=False,
        reason="minimum direct-answer context",
    )


def select_recent_turns(
    history: Sequence[dict] | None,
    selection: ContextSelection,
):
    items = list(
        history or []
    )

    limit = max(
        0,
        min(
            selection.recent_turn_limit,
            MAX_RECENT_TURNS,
        ),
    )

    if limit == 0:
        return []

    return items[-limit:]


def select_memories(
    memories: Iterable[dict] | None,
    selection: ContextSelection,
):
    items = list(
        memories or []
    )

    limit = max(
        0,
        min(
            selection.memory_limit,
            MAX_MEMORY_ITEMS,
        ),
    )

    if limit == 0:
        return []

    return items[:limit]


def bound_summary(summary: str | None) -> str:
    value = str(
        summary or ""
    ).strip()

    if len(value) <= MAX_SUMMARY_CHARS:
        return value

    return value[
        :MAX_SUMMARY_CHARS
    ].rstrip()


def build_context_guidance(
    orchestration,
    *,
    history_count=0,
    memory_count=0,
    has_active_goal=False,
    has_active_plan=False,
):
    selection = select_context(
        orchestration,
        history_count=history_count,
        memory_count=memory_count,
        has_active_goal=has_active_goal,
        has_active_plan=has_active_plan,
    )

    return (
        "V10 context budget: "
        f"use up to {selection.recent_turn_limit} recent turns and "
        f"{selection.memory_limit} relevant memory items. "
        f"Reason: {selection.reason}. "
        "Use only context materially needed for the current turn. "
        "Never include another user's memory or conversation context."
    )

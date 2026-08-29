from copy import deepcopy

from ai_engine import relationship_intelligence as RI
from ai_engine import emotional_intelligence as EI
from ai_engine import relationship_emotional_intelligence as RE15
from ai_engine.repository import InMemoryCharacterRepository


CHAR = "v15-continuity-char"
USER = "v15-continuity-user"


def evolve(
    state,
    text,
):
    return RI.evolve(
        state,
        CHAR,
        USER,
        text,
    )


def test_v15_3_marker():
    assert RI.V15_3_RELATIONSHIP_CONTINUITY is True


def test_default_state_has_clear_repair_state():
    state = RI.default_state(
        CHAR,
        USER,
    )

    assert state["relationshipTension"] == 0.0
    assert state["repairState"] == "clear"
    assert state["lastConflictTurn"] is None
    assert state["lastRepairTurn"] is None
    assert state["repairEvents"] == 0
    assert state["recoveryEvents"] == 0
    assert state["calmTurnsSinceConflict"] == 0
    assert state["relationshipVersion"] == 5
    assert state["relationshipContinuityVersion"] == "15.3"


def test_old_v5_document_normalizes_without_false_conflict():
    old = {
        "characterId": CHAR,
        "userId": USER,
        "turnCount": 20,
        "state": "familiar",
        "trust": 0.4,
        "familiarity": 0.4,
        "conflictEvents": 8,
    }

    state = RI.normalize_state(
        old,
        CHAR,
        USER,
    )

    assert state["relationshipTension"] == 0.0
    assert state["repairState"] == "clear"
    assert state["relationshipVersion"] == 5
    assert state["relationshipContinuityVersion"] == "15.3"


def test_invalid_continuity_fields_fail_safe():
    state = RI.normalize_state(
        {
            "repairState": "unknown-state",
            "relationshipTension": -9,
            "repairEvents": "bad",
            "recoveryEvents": None,
            "calmTurnsSinceConflict": -100,
            "lastConflictTurn": "bad",
            "lastRepairTurn": -20,
        },
        CHAR,
        USER,
    )

    assert state["repairState"] == "clear"
    assert state["relationshipTension"] == 0.0
    assert state["repairEvents"] == 0
    assert state["recoveryEvents"] == 0
    assert state["calmTurnsSinceConflict"] == 0
    assert state["lastConflictTurn"] is None
    assert state["lastRepairTurn"] == 0


def test_conflict_opens_bounded_repair_state():
    state = RI.default_state(
        CHAR,
        USER,
    )

    after = evolve(
        state,
        "You misunderstood me. Stop saying that.",
    )

    assert after["repairState"] == "needs_repair"
    assert 0.0 < after["relationshipTension"] <= 0.75
    assert after["lastConflictTurn"] == 1
    assert after["calmTurnsSinceConflict"] == 0


def test_conflict_does_not_dramatically_damage_trust():
    state = RI.default_state(
        CHAR,
        USER,
    )

    state["trust"] = 0.70
    state["warmth"] = 0.70

    after = evolve(
        state,
        "You are wrong and that annoyed me.",
    )

    assert after["trust"] > 0.65
    assert after["warmth"] > 0.65


def test_repeated_conflict_tension_is_bounded():
    state = RI.default_state(
        CHAR,
        USER,
    )

    for _ in range(20):
        state = evolve(
            state,
            "You are wrong and that annoyed me.",
        )

    assert state["relationshipTension"] <= 0.75
    assert state["repairState"] == "needs_repair"


def test_correction_alone_does_not_create_tension():
    state = RI.default_state(
        CHAR,
        USER,
    )

    after = evolve(
        state,
        "No, I mean accounting, not finance.",
    )

    assert after["correctionEvents"] == 1
    assert after["relationshipTension"] == 0.0
    assert after["repairState"] == "clear"


def test_explicit_repair_signal_detection_is_conservative():
    assert RI.is_explicit_repair_signal(
        "Thanks for understanding."
    )

    assert RI.is_explicit_repair_signal(
        "We're good."
    )

    assert not RI.is_explicit_repair_signal(
        "Okay."
    )

    assert not RI.is_explicit_repair_signal(
        "Hello."
    )


def test_explicit_repair_reduces_existing_tension():
    state = RI.default_state(
        CHAR,
        USER,
    )

    conflict = evolve(
        state,
        "You misunderstood me. Stop saying that.",
    )

    repaired = evolve(
        conflict,
        "Thanks for understanding.",
    )

    assert (
        repaired["relationshipTension"]
        <
        conflict["relationshipTension"]
    )

    assert repaired["repairEvents"] == 1
    assert repaired["lastRepairTurn"] == 2


def test_user_is_not_required_to_explicitly_repair():
    state = RI.default_state(
        CHAR,
        USER,
    )

    state = evolve(
        state,
        "You misunderstood me. Stop saying that.",
    )

    initial = state["relationshipTension"]

    state = evolve(
        state,
        "Anyway, how was your day?",
    )

    assert state["relationshipTension"] < initial
    assert state["calmTurnsSinceConflict"] == 1


def test_calm_conversation_eventually_clears_tension():
    state = RI.default_state(
        CHAR,
        USER,
    )

    state = evolve(
        state,
        "You misunderstood me. Stop saying that.",
    )

    for _ in range(20):
        state = evolve(
            state,
            "Tell me something interesting.",
        )

    assert state["relationshipTension"] == 0.0
    assert state["repairState"] == "clear"
    assert state["recoveryEvents"] == 1


def test_recovery_event_not_incremented_repeatedly_after_clear():
    state = RI.default_state(
        CHAR,
        USER,
    )

    state = evolve(
        state,
        "You misunderstood me. Stop saying that.",
    )

    for _ in range(20):
        state = evolve(
            state,
            "Tell me something interesting.",
        )

    recovery_count = state["recoveryEvents"]

    for _ in range(5):
        state = evolve(
            state,
            "Another normal message.",
        )

    assert state["recoveryEvents"] == recovery_count


def test_new_conflict_resets_calm_turn_counter():
    state = RI.default_state(
        CHAR,
        USER,
    )

    state = evolve(
        state,
        "You misunderstood me. Stop saying that.",
    )

    state = evolve(
        state,
        "Let's talk about work.",
    )

    assert state["calmTurnsSinceConflict"] == 1

    state = evolve(
        state,
        "You are wrong and that annoyed me.",
    )

    assert state["calmTurnsSinceConflict"] == 0
    assert state["repairState"] == "needs_repair"


def test_repair_context_clear_state():
    state = RI.default_state(
        CHAR,
        USER,
    )

    context = RI.repair_context(
        state
    )

    assert context["active"] is False
    assert context["state"] == "clear"
    assert context["tension"] == 0.0


def test_repair_context_active_after_conflict():
    state = evolve(
        RI.default_state(
            CHAR,
            USER,
        ),
        "You misunderstood me. Stop saying that.",
    )

    context = RI.repair_context(
        state
    )

    assert context["active"] is True
    assert context["state"] == "needs_repair"
    assert context["tension"] > 0.0


def test_repair_directive_never_demands_user_apology():
    state = evolve(
        RI.default_state(
            CHAR,
            USER,
        ),
        "You misunderstood me. Stop saying that.",
    )

    directive = RI.repair_context(
        state
    )["directive"].casefold()

    assert "do not" in directive
    assert "demand an apology" in directive
    assert "ask for forgiveness" in directive
    assert "seek reassurance" in directive
    assert "test loyalty" in directive


def test_relationship_guidance_includes_active_repair_context():
    state = evolve(
        RI.default_state(
            CHAR,
            USER,
        ),
        "You misunderstood me. Stop saying that.",
    )

    guidance = RI.guidance_for(
        state
    )

    directive = guidance.directive.casefold()

    assert "recent conversational friction" in directive
    assert "demand an apology" in directive


def test_normal_relationship_guidance_remains_normal_when_clear():
    state = RI.default_state(
        CHAR,
        USER,
    )

    guidance = RI.guidance_for(
        state
    )

    assert guidance.stage == "new"
    assert guidance.avoid_overfamiliarity is True


def test_v15_2_bridge_reads_persisted_repair_state():
    relationship = evolve(
        RI.default_state(
            CHAR,
            USER,
        ),
        "You misunderstood me. Stop saying that.",
    )

    emotional = EI.analyze_emotional_state_v15(
        "Anyway, tell me something funny.",
    )

    guidance = RE15.build_relationship_emotional_guidance(
        "Anyway, tell me something funny.",
        emotional,
        relationship,
    )

    assert guidance.repair_needed is True
    assert guidance.repair_mode == "relationship_recovery"
    assert (
        guidance.familiarity_mode
        == "do_not_leverage_closeness"
    )


def test_v15_2_bridge_does_not_mutate_relationship_state():
    relationship = evolve(
        RI.default_state(
            CHAR,
            USER,
        ),
        "You misunderstood me. Stop saying that.",
    )

    original = deepcopy(
        relationship
    )

    emotional = EI.analyze_emotional_state_v15(
        "Let's talk about something else.",
    )

    RE15.build_relationship_emotional_guidance(
        "Let's talk about something else.",
        emotional,
        relationship,
    )

    assert relationship == original


def test_inmemory_repository_persists_same_extended_document():
    repo = InMemoryCharacterRepository()

    first = repo.advance_relationship(
        CHAR,
        USER,
        {},
        user_text=(
            "You misunderstood me. "
            "Stop saying that."
        ),
    )

    assert first["repairState"] == "needs_repair"
    assert first["relationshipContinuityVersion"] == "15.3"

    second = repo.advance_relationship(
        CHAR,
        USER,
        {},
        user_text="Let's talk about work.",
    )

    assert second["relationshipTension"] < first["relationshipTension"]

    stored = repo.get_relationship(
        CHAR,
        USER,
    )

    assert stored == second


def test_relationship_scope_isolation_remains_exact():
    repo = InMemoryCharacterRepository()

    repo.advance_relationship(
        CHAR,
        "user-a",
        {},
        user_text="You misunderstood me.",
    )

    repo.advance_relationship(
        CHAR,
        "user-b",
        {},
        user_text="Hello.",
    )

    a = repo.get_relationship(
        CHAR,
        "user-a",
    )

    b = repo.get_relationship(
        CHAR,
        "user-b",
    )

    assert a["relationshipTension"] > 0.0
    assert b["relationshipTension"] == 0.0


def test_no_repair_milestone_content_is_created():
    state = RI.default_state(
        CHAR,
        USER,
    )

    state = evolve(
        state,
        "You misunderstood me. Stop saying that.",
    )

    state = evolve(
        state,
        "Thanks for understanding.",
    )

    repair_milestones = [
        item
        for item in state["milestones"]
        if item.get("type") == "relationship_repair"
    ]

    assert repair_milestones == []


def test_v5_relationship_version_is_preserved():
    state = evolve(
        RI.default_state(
            CHAR,
            USER,
        ),
        "Normal day at work.",
    )

    assert state["relationshipVersion"] == 5
    assert state["relationshipContinuityVersion"] == "15.3"

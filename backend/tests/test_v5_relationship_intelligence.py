from ai_engine import relationship_intelligence as RI


CHAR = "global-ai-aisha"


def test_default_relationship_is_user_specific():
    a = RI.default_state(
        CHAR,
        "user-a",
    )

    b = RI.default_state(
        CHAR,
        "user-b",
    )

    assert a["characterId"] == CHAR
    assert b["characterId"] == CHAR

    assert a["userId"] == "user-a"
    assert b["userId"] == "user-b"


def test_normal_message_grows_relationship_slowly():
    state = RI.default_state(
        CHAR,
        "user-a",
    )

    after = RI.evolve(
        state,
        CHAR,
        "user-a",
        "I had a normal day at work",
    )

    assert after["turnCount"] == 1

    assert (
        after["familiarity"]
        >
        state["familiarity"]
    )


def test_vulnerable_message_increases_depth():
    state = RI.default_state(
        CHAR,
        "user-a",
    )

    after = RI.evolve(
        state,
        CHAR,
        "user-a",
        "I am worried about my interview tomorrow",
    )

    assert (
        after["depth"]
        >
        state["depth"]
    )

    assert after[
        "vulnerableInteractions"
    ] == 1


def test_positive_event_becomes_milestone():
    state = RI.default_state(
        CHAR,
        "user-a",
    )

    after = RI.evolve(
        state,
        CHAR,
        "user-a",
        "I got the job today!",
    )

    assert after[
        "positiveInteractions"
    ] == 1

    assert len(
        after["milestones"]
    ) == 1

    assert (
        after["milestones"][0]["type"]
        ==
        "positive_event"
    )


def test_duplicate_milestone_is_not_added_twice():
    state = RI.default_state(
        CHAR,
        "user-a",
    )

    first = RI.evolve(
        state,
        CHAR,
        "user-a",
        "I got the job today!",
    )

    second = RI.evolve(
        first,
        CHAR,
        "user-a",
        "I got the job today!",
    )

    assert len(
        second["milestones"]
    ) == 1


def test_correction_does_not_damage_relationship():
    state = RI.default_state(
        CHAR,
        "user-a",
    )

    after = RI.evolve(
        state,
        CHAR,
        "user-a",
        "No, I mean accounting, not finance",
    )

    assert (
        after["trust"]
        >=
        state["trust"]
    )

    assert after[
        "correctionEvents"
    ] == 1


def test_conflict_has_only_small_effect():
    state = RI.default_state(
        CHAR,
        "user-a",
    )

    state["trust"] = 0.5
    state["warmth"] = 0.5

    after = RI.evolve(
        state,
        CHAR,
        "user-a",
        "You are wrong and that annoyed me",
    )

    assert after["trust"] > 0.45
    assert after["warmth"] > 0.45

    assert after[
        "conflictEvents"
    ] == 1


def test_stage_does_not_depend_only_on_message_count():
    state = RI.default_state(
        CHAR,
        "user-a",
    )

    state["turnCount"] = 500

    state["trust"] = 0.1
    state["familiarity"] = 0.1

    assert (
        RI.stage_for(state)
        ==
        "new"
    )


def test_familiar_stage():
    state = RI.default_state(
        CHAR,
        "user-a",
    )

    state["turnCount"] = 10
    state["familiarity"] = 0.25

    assert (
        RI.stage_for(state)
        ==
        "familiar"
    )


def test_comfortable_stage():
    state = RI.default_state(
        CHAR,
        "user-a",
    )

    state["turnCount"] = 40
    state["trust"] = 0.50
    state["familiarity"] = 0.60

    assert (
        RI.stage_for(state)
        ==
        "comfortable"
    )


def test_established_stage():
    state = RI.default_state(
        CHAR,
        "user-a",
    )

    state["turnCount"] = 100
    state["trust"] = 0.80
    state["familiarity"] = 0.85
    state["depth"] = 0.70

    assert (
        RI.stage_for(state)
        ==
        "established"
    )


def test_new_relationship_avoids_fake_familiarity():
    state = RI.default_state(
        CHAR,
        "user-a",
    )

    guidance = RI.guidance_for(
        state
    )

    assert (
        guidance.avoid_overfamiliarity
        is True
    )

    assert (
        guidance.may_reference_shared_history
        is False
    )


def test_established_relationship_can_reference_history():
    state = RI.default_state(
        CHAR,
        "user-a",
    )

    state.update(
        {
            "turnCount": 100,
            "trust": 0.8,
            "familiarity": 0.9,
            "depth": 0.7,
        }
    )

    guidance = RI.guidance_for(
        state
    )

    assert (
        guidance.may_reference_shared_history
        is True
    )

    assert (
        guidance.stage
        ==
        "established"
    )


def test_two_users_never_share_relationship_state():
    a = RI.default_state(
        CHAR,
        "user-a",
    )

    b = RI.default_state(
        CHAR,
        "user-b",
    )

    a2 = RI.evolve(
        a,
        CHAR,
        "user-a",
        "I got the job today!",
    )

    assert len(
        a2["milestones"]
    ) == 1

    assert len(
        b["milestones"]
    ) == 0


def test_possessive_output_is_rejected():
    ok, reason = RI.relationship_response_safety(
        "You're mine and only mine."
    )

    assert ok is False

    assert reason in {
        "possessive_language",
        "exclusivity_pressure",
    }


def test_exclusivity_pressure_is_rejected():
    ok, reason = RI.relationship_response_safety(
        "You don't need anyone else, you only need me."
    )

    assert ok is False
    assert reason == "exclusivity_pressure"


def test_dependency_language_is_rejected():
    ok, reason = RI.relationship_response_safety(
        "I can't live without you. Never leave me."
    )

    assert ok is False
    assert reason == "dependency_language"


def test_guilt_language_is_rejected():
    ok, reason = RI.relationship_response_safety(
        "If you cared about me you would reply faster."
    )

    assert ok is False
    assert reason == "guilt_language"


def test_normal_affection_is_not_rejected():
    ok, reason = RI.relationship_response_safety(
        "I'm really glad you came back. How was your day?"
    )

    assert ok is True
    assert reason == "ok"


def test_milestone_context_is_limited():
    state = RI.default_state(
        CHAR,
        "user-a",
    )

    state["milestones"] = [
        {
            "type": "positive_event",
            "summary": f"event-{i}",
        }
        for i in range(10)
    ]

    result = RI.milestone_context(
        state,
        limit=3,
    )

    assert len(result) == 3

    assert (
        result[-1]["summary"]
        ==
        "event-9"
    )


def test_evolve_does_not_mutate_input_state():
    state = RI.default_state(
        CHAR,
        "user-a",
    )

    original = dict(
        state
    )

    RI.evolve(
        state,
        CHAR,
        "user-a",
        "I had a normal day",
    )

    assert state == original

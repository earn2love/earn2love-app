from ai_engine import execution_intelligence as EI
from ai_engine import plan_intelligence as PI


CID = "aisha"
UID = "user-1"


def make_plan():
    return PI.evolve_plan_state(
        None,
        CID,
        UID,
        "First configure auth, then test auth, finally deploy.",
        {
            "characterId": CID,
            "userId": UID,
            "activeGoal": "Ship authentication",
            "activeGoalStatus": "active",
            "goalHistory": [],
            "goalTurnCount": 0,
            "goalEvents": 0,
            "lastIntent": "planning",
            "goalVersion": 8,
        },
    )


def test_idle_without_plan():
    result = EI.analyze_execution(
        "continue",
        None,
        CID,
        UID,
    )

    assert result.mode == "idle"
    assert result.has_active_plan is False


def test_execute_active_plan():
    state = make_plan()

    result = EI.analyze_execution(
        "I'm working on it",
        state,
        CID,
        UID,
    )

    assert result.mode == "execute"


def test_resume():
    state = make_plan()

    result = EI.analyze_execution(
        "continue",
        state,
        CID,
        UID,
    )

    assert result.mode == "resume"


def test_failure_detected():
    state = make_plan()

    result = EI.analyze_execution(
        "Authentication failed with an error",
        state,
        CID,
        UID,
    )

    assert result.mode == "recover"
    assert result.has_blocker is True


def test_retry_same_step():
    state = make_plan()

    result = EI.analyze_execution(
        "It failed, retry the same step",
        state,
        CID,
        UID,
    )

    assert result.should_retry_same_step is True
    assert result.should_replan is False


def test_explicit_replan():
    state = make_plan()

    result = EI.analyze_execution(
        "This failed, use a different approach",
        state,
        CID,
        UID,
    )

    assert result.should_replan is True
    assert result.mode == "replan"


def test_repeated_failure_replan():
    state = make_plan()

    result = EI.analyze_execution(
        "It is still not working again",
        state,
        CID,
        UID,
    )

    assert result.should_replan is True


def test_completion_advances():
    state = make_plan()

    result = EI.analyze_execution(
        "Done, that worked",
        state,
        CID,
        UID,
    )

    assert result.should_advance is True


def test_stop_detected():
    state = make_plan()

    result = EI.analyze_execution(
        "Stop this",
        state,
        CID,
        UID,
    )

    assert result.should_stop is True


def test_current_step_exposed_safely():
    state = make_plan()

    result = EI.analyze_execution(
        "continue",
        state,
        CID,
        UID,
    )

    assert result.current_step_id == "step-1"
    assert result.current_step_text


def test_guidance_blocks_fake_success():
    state = make_plan()

    directive = EI.build_execution_guidance(
        "continue",
        state,
        CID,
        UID,
    ).directive.lower()

    assert "never fabricate successful execution" in directive


def test_guidance_protects_chain_of_thought():
    directive = EI.build_execution_guidance(
        "continue",
        make_plan(),
        CID,
        UID,
    ).directive.lower()

    assert "chain-of-thought" in directive


def test_guidance_protects_v6_v7_v8():
    directive = EI.build_execution_guidance(
        "continue",
        make_plan(),
        CID,
        UID,
    ).directive

    assert "V6" in directive
    assert "V7" in directive
    assert "V8" in directive


def test_version():
    assert EI.EXECUTION_VERSION == 9

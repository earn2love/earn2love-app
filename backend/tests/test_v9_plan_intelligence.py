from copy import deepcopy

from ai_engine import plan_intelligence as PI


CID = "aisha"
UID = "user-1"


def goal_state(
    goal="Build production chat",
):
    return {
        "characterId": CID,
        "userId": UID,
        "activeGoal": goal,
        "activeGoalStatus": "active",
        "goalHistory": [],
        "goalTurnCount": 0,
        "goalEvents": 0,
        "lastIntent": "planning",
        "goalVersion": 8,
    }


def test_default_state_identity():
    state = PI.default_plan_state(
        CID,
        UID,
    )

    assert state["characterId"] == CID
    assert state["userId"] == UID
    assert state["planVersion"] == 9


def test_normalization_forces_identity():
    state = PI.normalize_plan_state(
        {
            "characterId": "wrong",
            "userId": "wrong",
        },
        CID,
        UID,
    )

    assert state["characterId"] == CID
    assert state["userId"] == UID


def test_blueprint_uses_v8_goal():
    blueprint = PI.derive_plan_blueprint(
        "Create a plan",
        goal_state(),
    )

    assert (
        blueprint.goal
        == "Build production chat"
    )


def test_explicit_sequence_is_parsed():
    blueprint = PI.derive_plan_blueprint(
        "First test backend, then verify Firestore, finally deploy."
    )

    assert len(
        blueprint.steps
    ) >= 3

    assert (
        blueprint.source
        == "explicit_sequence"
    )


def test_non_plan_does_not_invent_steps():
    blueprint = PI.derive_plan_blueprint(
        "I had coffee today"
    )

    assert blueprint.steps == tuple()


def test_start_plan():
    state = PI.evolve_plan_state(
        None,
        CID,
        UID,
        "First test backend, then verify Firestore.",
        goal_state(),
    )

    assert PI.has_active_plan(
        state
    )

    assert (
        state["currentStepId"]
        == "step-1"
    )

    assert (
        state["steps"][0]["status"]
        == "active"
    )


def test_step_dependencies_are_ordered():
    state = PI.evolve_plan_state(
        None,
        CID,
        UID,
        "First test backend, then verify Firestore, finally deploy.",
        goal_state(),
    )

    assert (
        state["steps"][1]["dependsOn"]
        == ["step-1"]
    )

    assert (
        state["steps"][2]["dependsOn"]
        == ["step-2"]
    )


def test_complete_current_step_advances():
    state = PI.evolve_plan_state(
        None,
        CID,
        UID,
        "First test backend, then verify Firestore.",
        goal_state(),
    )

    state = PI.evolve_plan_state(
        state,
        CID,
        UID,
        "Done, that worked.",
        goal_state(),
    )

    assert "step-1" in state[
        "completedStepIds"
    ]

    assert (
        state["currentStepId"]
        == "step-2"
    )


def test_final_step_completes_plan():
    state = PI.evolve_plan_state(
        None,
        CID,
        UID,
        "Create a plan",
        goal_state(),
    )

    state = PI.evolve_plan_state(
        state,
        CID,
        UID,
        "Done",
        goal_state(),
    )

    assert (
        state["activePlanStatus"]
        == "completed"
    )

    assert (
        state["currentStepId"]
        is None
    )


def test_blocker_marks_current_step():
    state = PI.evolve_plan_state(
        None,
        CID,
        UID,
        "Create a plan",
        goal_state(),
    )

    state = PI.evolve_plan_state(
        state,
        CID,
        UID,
        "Blocked because Firebase auth is not working",
        goal_state(),
    )

    assert state["blockers"]

    assert (
        state["steps"][0]["status"]
        == "blocked"
    )


def test_resume_reactivates_blocked_step():
    state = PI.evolve_plan_state(
        None,
        CID,
        UID,
        "Create a plan",
        goal_state(),
    )

    state = PI.evolve_plan_state(
        state,
        CID,
        UID,
        "Blocked because auth failed",
        goal_state(),
    )

    state = PI.evolve_plan_state(
        state,
        CID,
        UID,
        "Continue",
        goal_state(),
    )

    assert (
        state["steps"][0]["status"]
        == "active"
    )

    assert (
        state["lastPlanEvent"]
        == "resumed"
    )


def test_abandon_plan():
    state = PI.evolve_plan_state(
        None,
        CID,
        UID,
        "Create a plan",
        goal_state(),
    )

    state = PI.evolve_plan_state(
        state,
        CID,
        UID,
        "Stop this plan",
        goal_state(),
    )

    assert (
        state["activePlanStatus"]
        == "abandoned"
    )

    assert state["planHistory"]


def test_replace_plan_archives_old():
    state = PI.evolve_plan_state(
        None,
        CID,
        UID,
        "First test backend, then deploy.",
        goal_state(
            "Old goal"
        ),
    )

    state = PI.evolve_plan_state(
        state,
        CID,
        UID,
        "New plan: first verify auth, then verify payments.",
        goal_state(
            "New goal"
        ),
    )

    assert state["planHistory"]

    assert (
        state["planHistory"][-1]["status"]
        == "replaced"
    )


def test_turn_count_increments():
    state = PI.evolve_plan_state(
        None,
        CID,
        UID,
        "Create a plan",
        goal_state(),
    )

    before = state[
        "planTurnCount"
    ]

    state = PI.evolve_plan_state(
        state,
        CID,
        UID,
        "Keep going with the same work",
        goal_state(),
    )

    assert (
        state["planTurnCount"]
        == before + 1
    )


def test_state_evolution_does_not_mutate_input():
    original = PI.evolve_plan_state(
        None,
        CID,
        UID,
        "Create a plan",
        goal_state(),
    )

    snapshot = deepcopy(
        original
    )

    PI.evolve_plan_state(
        original,
        CID,
        UID,
        "Done",
        goal_state(),
    )

    assert original == snapshot


def test_plan_history_bounded():
    state = PI.default_plan_state(
        CID,
        UID,
    )

    state["planHistory"] = [
        {
            "plan": index
        }
        for index in range(
            100
        )
    ]

    normalized = PI.normalize_plan_state(
        state,
        CID,
        UID,
    )

    assert len(
        normalized["planHistory"]
    ) <= 20


def test_blockers_bounded():
    state = PI.default_plan_state(
        CID,
        UID,
    )

    state["blockers"] = [
        f"blocker-{index}"
        for index in range(
            100
        )
    ]

    normalized = PI.normalize_plan_state(
        state,
        CID,
        UID,
    )

    assert len(
        normalized["blockers"]
    ) <= 10


def test_step_count_bounded():
    state = PI.default_plan_state(
        CID,
        UID,
    )

    state["steps"] = [
        {
            "stepId": f"s-{index}",
            "text": str(index),
            "status": "pending",
        }
        for index in range(
            100
        )
    ]

    normalized = PI.normalize_plan_state(
        state,
        CID,
        UID,
    )

    assert len(
        normalized["steps"]
    ) <= 20


def test_guidance_uses_existing_plan():
    state = PI.evolve_plan_state(
        None,
        CID,
        UID,
        "Create a plan",
        goal_state(),
    )

    guidance = PI.build_plan_guidance(
        "Continue",
        state,
        CID,
        UID,
        goal_state(),
    )

    assert (
        "Continue the existing plan"
        in guidance.directive
    )


def test_guidance_does_not_invent_plan():
    guidance = PI.build_plan_guidance(
        "Nice weather today",
        None,
        CID,
        UID,
    )

    assert (
        "Do not invent a persistent plan"
        in guidance.directive
    )


def test_guidance_protects_private_reasoning():
    directive = PI.build_plan_guidance(
        "Create a plan",
        None,
        CID,
        UID,
        goal_state(),
    ).directive.lower()

    assert "chain-of-thought" in directive


def test_guidance_protects_previous_layers():
    directive = PI.build_plan_guidance(
        "Create a plan",
        None,
        CID,
        UID,
        goal_state(),
    ).directive

    assert "V6" in directive
    assert "V7" in directive
    assert "V8" in directive


def test_safe_copy_is_deep():
    original = {
        "nested": {
            "x": 1
        }
    }

    copied = PI.safe_plan_copy(
        original
    )

    copied["nested"]["x"] = 2

    assert original["nested"]["x"] == 1


def test_version():
    assert PI.PLAN_VERSION == 9

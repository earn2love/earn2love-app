from copy import deepcopy

from ai_engine import goal_intelligence as GI


CHAR = "global-aisha"


def test_default_goal_state():
    state = GI.default_goal_state(
        CHAR,
        "user-a",
    )

    assert state["characterId"] == CHAR
    assert state["userId"] == "user-a"
    assert state["goalVersion"] == 8
    assert state["activeGoal"] is None


def test_question_intent():
    result = GI.analyze_intent(
        "How does Firebase authentication work?"
    )

    assert result.primary_intent in {
        "learning",
        "question",
    }

    assert result.wants_answer is True


def test_problem_solving_intent():
    result = GI.analyze_intent(
        "My Flutter app has an error, help me fix it"
    )

    assert (
        result.primary_intent
        ==
        "problem_solving"
    )

    assert result.wants_action is True


def test_planning_intent():
    result = GI.analyze_intent(
        "Give me a plan and next steps for launching the app"
    )

    assert (
        result.primary_intent
        ==
        "planning"
    )

    assert result.wants_plan is True


def test_decision_intent():
    result = GI.analyze_intent(
        "Which is better, Firebase or Supabase? Help me decide"
    )

    assert (
        result.primary_intent
        ==
        "decision"
    )

    assert (
        result.wants_decision_support
        is True
    )


def test_venting_intent():
    result = GI.analyze_intent(
        "I'm really frustrated and stressed today"
    )

    assert (
        result.primary_intent
        ==
        "venting"
    )

    assert (
        result.wants_emotional_support
        is True
    )


def test_correction_intent():
    result = GI.analyze_intent(
        "No I mean the backend, not the Flutter UI"
    )

    assert result.is_correction is True


def test_completion_intent():
    result = GI.analyze_intent(
        "Done, it works now"
    )

    assert (
        result.is_goal_completion
        is True
    )


def test_abandonment_intent():
    result = GI.analyze_intent(
        "Forget it, drop this"
    )

    assert (
        result.is_goal_abandonment
        is True
    )


def test_new_goal_created():
    state = GI.default_goal_state(
        CHAR,
        "user-a",
    )

    after = GI.evolve_goal_state(
        state,
        CHAR,
        "user-a",
        "Help me build a launch plan",
    )

    assert (
        after["activeGoal"]
        is not None
    )

    assert (
        after["activeGoalStatus"]
        ==
        "active"
    )


def test_goal_state_is_pure():
    state = GI.default_goal_state(
        CHAR,
        "user-a",
    )

    before = deepcopy(
        state
    )

    GI.evolve_goal_state(
        state,
        CHAR,
        "user-a",
        "Help me build a launch plan",
    )

    assert state == before


def test_goal_continues_on_neutral_turn():
    state = GI.default_goal_state(
        CHAR,
        "user-a",
    )

    state = GI.evolve_goal_state(
        state,
        CHAR,
        "user-a",
        "Help me build a launch plan",
    )

    count = state[
        "goalTurnCount"
    ]

    state = GI.evolve_goal_state(
        state,
        CHAR,
        "user-a",
        "Okay",
    )

    assert (
        state["goalTurnCount"]
        ==
        count + 1
    )


def test_goal_completion_moves_to_history():
    state = GI.default_goal_state(
        CHAR,
        "user-a",
    )

    state = GI.evolve_goal_state(
        state,
        CHAR,
        "user-a",
        "Help me build a launch plan",
    )

    state = GI.evolve_goal_state(
        state,
        CHAR,
        "user-a",
        "Done, completed",
    )

    assert state["activeGoal"] is None

    assert (
        state["goalHistory"][-1]["status"]
        ==
        "completed"
    )


def test_goal_abandonment_moves_to_history():
    state = GI.default_goal_state(
        CHAR,
        "user-a",
    )

    state = GI.evolve_goal_state(
        state,
        CHAR,
        "user-a",
        "Help me build this feature",
    )

    state = GI.evolve_goal_state(
        state,
        CHAR,
        "user-a",
        "Forget it, drop this",
    )

    assert state["activeGoal"] is None

    assert (
        state["goalHistory"][-1]["status"]
        ==
        "abandoned"
    )


def test_new_goal_replaces_old_goal():
    state = GI.default_goal_state(
        CHAR,
        "user-a",
    )

    state = GI.evolve_goal_state(
        state,
        CHAR,
        "user-a",
        "Help me build the backend",
    )

    first = state[
        "activeGoal"
    ]

    state = GI.evolve_goal_state(
        state,
        CHAR,
        "user-a",
        "Give me a plan for launching the app",
    )

    assert (
        state["activeGoal"]
        !=
        first
    )

    assert (
        state["goalHistory"][-1]["status"]
        ==
        "replaced"
    )


def test_two_users_do_not_share_goals():
    a = GI.default_goal_state(
        CHAR,
        "user-a",
    )

    b = GI.default_goal_state(
        CHAR,
        "user-b",
    )

    a = GI.evolve_goal_state(
        a,
        CHAR,
        "user-a",
        "Help me build the backend",
    )

    b = GI.evolve_goal_state(
        b,
        CHAR,
        "user-b",
        "Help me plan a launch",
    )

    assert (
        a["activeGoal"]
        !=
        b["activeGoal"]
    )

    assert a["userId"] == "user-a"
    assert b["userId"] == "user-b"


def test_same_user_different_characters_have_separate_goals():
    a = GI.default_goal_state(
        "global-aisha",
        "same-user",
    )

    m = GI.default_goal_state(
        "global-meera",
        "same-user",
    )

    a = GI.evolve_goal_state(
        a,
        "global-aisha",
        "same-user",
        "Help me build an app",
    )

    m = GI.evolve_goal_state(
        m,
        "global-meera",
        "same-user",
        "Help me make a decision",
    )

    assert (
        a["characterId"]
        !=
        m["characterId"]
    )

    assert (
        a["activeGoal"]
        !=
        m["activeGoal"]
    )


def test_normalization_forces_identity():
    state = {
        "characterId": "wrong",
        "userId": "wrong",
        "activeGoal": "x",
    }

    normalized = GI.normalize_goal_state(
        state,
        CHAR,
        "real-user",
    )

    assert (
        normalized["characterId"]
        ==
        CHAR
    )

    assert (
        normalized["userId"]
        ==
        "real-user"
    )


def test_goal_history_is_bounded():
    state = GI.default_goal_state(
        CHAR,
        "user-a",
    )

    state["goalHistory"] = [
        {
            "goal": str(i),
            "status": "completed",
        }
        for i in range(100)
    ]

    normalized = GI.normalize_goal_state(
        state,
        CHAR,
        "user-a",
    )

    assert (
        len(
            normalized["goalHistory"]
        )
        ==
        25
    )


def test_active_goal_helper():
    state = GI.default_goal_state(
        CHAR,
        "user-a",
    )

    state = GI.evolve_goal_state(
        state,
        CHAR,
        "user-a",
        "Help me build the backend",
    )

    assert (
        GI.has_active_goal(
            state
        )
        is True
    )

    assert (
        GI.active_goal(
            state
        )
        is not None
    )


def test_goal_guidance_contains_active_goal():
    state = GI.default_goal_state(
        CHAR,
        "user-a",
    )

    state = GI.evolve_goal_state(
        state,
        CHAR,
        "user-a",
        "Help me build the backend",
    )

    guidance = GI.build_goal_guidance(
        "continue",
        state,
    )

    assert (
        "Current active user goal:"
        in guidance.directive
    )


def test_guidance_protects_global_personality():
    state = GI.default_goal_state(
        CHAR,
        "user-a",
    )

    guidance = GI.build_goal_guidance(
        "hello",
        state,
    )

    assert (
        "Do not modify the global V6 character personality."
        in guidance.directive
    )


def test_guidance_protects_v7_preferences():
    state = GI.default_goal_state(
        CHAR,
        "user-a",
    )

    guidance = GI.build_goal_guidance(
        "hello",
        state,
    )

    assert (
        "Do not modify V7 communication preferences"
        in guidance.directive
    )


def test_goal_state_has_no_global_personality_fields():
    state = GI.default_goal_state(
        CHAR,
        "user-a",
    )

    forbidden = {
        "personality",
        "personalitySignature",
        "personalityFingerprint",
    }

    assert not (
        forbidden
        &
        set(
            state.keys()
        )
    )


def test_1000_users_keep_unique_identity():
    states = []

    for number in range(1000):

        user = f"user-{number}"

        state = GI.default_goal_state(
            CHAR,
            user,
        )

        state = GI.evolve_goal_state(
            state,
            CHAR,
            user,
            f"Help me build feature {number}",
        )

        states.append(
            (
                state["characterId"],
                state["userId"],
                state["activeGoal"],
            )
        )

    assert (
        len(
            {
                item[1]
                for item in states
            }
        )
        ==
        1000
    )

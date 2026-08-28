from copy import deepcopy

from ai_engine import proactive_intelligence as PI


def test_explicit_next_step_requests_proactivity():
    result = PI.analyze_proactivity(
        "What should I do next?"
    )

    assert result.should_be_proactive is True
    assert result.should_offer_next_step is True
    assert result.intensity == "high"


def test_user_can_disable_proactivity():
    result = PI.analyze_proactivity(
        "Just answer. Don't suggest anything else."
    )

    assert result.should_be_proactive is False
    assert result.should_offer_next_step is False
    assert result.should_ask_question is False


def test_active_goal_allows_low_proactivity():
    result = PI.analyze_proactivity(
        "Okay",
        has_active_goal=True,
    )

    assert result.should_be_proactive is True
    assert result.intensity == "low"


def test_repeated_proactivity_is_suppressed():
    result = PI.analyze_proactivity(
        "Okay",
        has_active_goal=True,
        prior_proactive_turns=2,
    )

    assert result.should_offer_next_step is False


def test_production_risk_is_surfaceable():
    result = PI.analyze_proactivity(
        "I am deploying this to production"
    )

    assert result.should_surface_risk is True
    assert result.should_be_proactive is True


def test_normal_small_talk_is_not_forced_proactive():
    result = PI.analyze_proactivity(
        "I had coffee today"
    )

    assert result.should_be_proactive is False


def test_decision_detection():
    result = PI.analyze_decision(
        "Which is better, Firebase or Supabase?"
    )

    assert result.is_decision is True


def test_decision_extracts_two_options():
    result = PI.analyze_decision(
        "Should I choose Firebase or Supabase?"
    )

    assert result.is_decision is True
    assert len(result.options) >= 2


def test_vs_options():
    result = PI.analyze_decision(
        "Firebase vs Supabase?"
    )

    assert result.is_decision is True
    assert len(result.options) == 2


def test_decision_constraints():
    result = PI.analyze_decision(
        "Should I use Firebase or Supabase? I need something secure and fast."
    )

    assert result.is_decision is True
    assert result.constraints


def test_decision_priorities():
    result = PI.analyze_decision(
        "Firebase or Supabase? Performance is most important."
    )

    assert result.is_decision is True
    assert result.priorities


def test_non_decision_message():
    result = PI.analyze_decision(
        "I deployed the app today."
    )

    assert result.is_decision is False


def test_guidance_contains_decision_support():
    guidance = PI.build_intelligence_guidance(
        "Which is better, Firebase or Supabase?"
    )

    assert (
        "Treat this as a decision-support request."
        in guidance.directive
    )


def test_guidance_avoids_generic_pros_cons():
    guidance = PI.build_intelligence_guidance(
        "Firebase or Supabase? Help me decide."
    )

    assert (
        "Do not hide behind generic pros-and-cons"
        in guidance.directive
    )


def test_guidance_respects_autonomy():
    guidance = PI.build_intelligence_guidance(
        "What should I do next?"
    )

    assert (
        "Preserve user autonomy"
        in guidance.directive
    )


def test_guidance_no_forced_questions():
    guidance = PI.build_intelligence_guidance(
        "Help me with the next step"
    )

    assert (
        "Do not ask a follow-up question"
        in guidance.directive
    )


def test_guidance_protects_v6():
    guidance = PI.build_intelligence_guidance(
        "hello"
    )

    assert (
        "Do not modify the global V6 personality."
        in guidance.directive
    )


def test_guidance_protects_v7():
    guidance = PI.build_intelligence_guidance(
        "hello"
    )

    assert (
        "Do not modify V7 communication adaptation."
        in guidance.directive
    )


def test_guidance_protects_v8_goal_state():
    guidance = PI.build_intelligence_guidance(
        "hello"
    )

    assert (
        "Do not alter V8 goal state"
        in guidance.directive
    )


def test_state_copy_is_deep():
    state = {
        "x": {
            "y": 1
        }
    }

    copied = PI.safe_state_copy(
        state
    )

    copied["x"]["y"] = 999

    assert state["x"]["y"] == 1


def test_input_state_is_not_mutated():
    state = {
        "goal": "launch app",
        "history": [
            "one",
            "two",
        ],
    }

    before = deepcopy(
        state
    )

    PI.safe_state_copy(
        state
    )

    assert state == before


def test_1000_users_do_not_create_global_state():
    results = []

    for i in range(1000):

        result = PI.analyze_proactivity(
            f"What should I do next for feature {i}?",
            has_active_goal=True,
        )

        results.append(
            result
        )

    assert len(results) == 1000

    assert all(
        item.should_be_proactive
        for item in results
    )


def test_same_input_is_deterministic():
    a = PI.analyze_decision(
        "Firebase or Supabase?"
    )

    b = PI.analyze_decision(
        "Firebase or Supabase?"
    )

    assert a == b


def test_no_global_mutable_state():
    forbidden = (
        "GLOBAL_STATE",
        "USER_STATE",
        "SESSION_STATE",
        "CACHE",
    )

    for name in forbidden:
        assert not hasattr(
            PI,
            name,
        )


def test_direct_request_does_not_force_question():
    result = PI.analyze_proactivity(
        "Give me the next step"
    )

    assert result.should_ask_question is False

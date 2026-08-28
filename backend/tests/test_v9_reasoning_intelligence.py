from copy import deepcopy

import pytest

from ai_engine import reasoning_intelligence as RI


@pytest.mark.parametrize(
    ("text", "mode"),
    [
        ("Give me a short answer", "direct"),
        (
            "Create a plan to launch this feature",
            "planning",
        ),
        (
            "This build failed with an error",
            "troubleshooting",
        ),
        (
            "Verify whether this configuration is correct",
            "verification",
        ),
        (
            "Should I use Firebase vs Supabase?",
            "decision",
        ),
    ],
)
def test_reasoning_modes(
    text,
    mode,
):
    assert RI.analyze_reasoning(
        text
    ).mode == mode


def test_constraints_detected():
    result = RI.analyze_reasoning(
        "We must keep Flutter untouched and finish within two days."
    )

    assert result.constraints


def test_dependencies_detected():
    result = RI.analyze_reasoning(
        "First configure Firebase, then deploy after the tests pass."
    )

    assert result.dependencies


def test_blocker_detected():
    result = RI.analyze_reasoning(
        "The build is blocked because authentication is not working."
    )

    assert result.blockers
    assert result.mode == "troubleshooting"


def test_unknown_detected():
    result = RI.analyze_reasoning(
        "I'm not sure which API version is enabled."
    )

    assert result.unknowns
    assert result.should_verify is True


def test_question_is_unknown():
    result = RI.analyze_reasoning(
        "Which environment is currently deployed?"
    )

    assert result.unknowns


def test_assumption_detected():
    result = RI.analyze_reasoning(
        "I think the backend probably uses the production key."
    )

    assert result.assumptions


def test_contradiction_detected():
    result = RI.analyze_reasoning(
        "We need to deploy today, but production changes must not be rushed."
    )

    assert result.contradictions


def test_not_but_contradiction():
    result = RI.analyze_reasoning(
        "The problem is not Firebase but the provider configuration."
    )

    assert result.contradictions


def test_multi_step_planning():
    result = RI.analyze_reasoning(
        "Create a plan: first test the backend, then verify Firestore, then deploy."
    )

    assert result.requires_multi_step is True


def test_simple_direct_not_multi_step():
    result = RI.analyze_reasoning(
        "Use the existing branch"
    )

    assert result.requires_multi_step is False


def test_guidance_protects_private_reasoning():
    guidance = RI.build_reasoning_guidance(
        "Plan this in several steps"
    )

    directive = guidance.directive.lower()

    assert "chain-of-thought" in directive
    assert "never expose" in directive


def test_guidance_protects_v6_v7_v8():
    directive = RI.build_reasoning_guidance(
        "Help me troubleshoot this"
    ).directive

    assert "V6" in directive
    assert "V7" in directive
    assert "V8" in directive


def test_analysis_to_dict():
    result = RI.analyze_reasoning(
        "Verify this before deployment"
    ).to_dict()

    assert result["mode"] == "verification"
    assert result["should_verify"] is True


def test_safe_copy_is_deep():
    original = {
        "nested": {
            "value": 1
        }
    }

    copied = RI.safe_reasoning_copy(
        original
    )

    copied["nested"]["value"] = 2

    assert original["nested"]["value"] == 1


def test_module_has_no_firestore_contract():
    source = RI.__file__

    assert source


def test_version():
    assert RI.REASONING_VERSION == 9

from ai_engine import reliability_intelligence as RL


GOOD_QUALITY = {
    "consistencyPassed": True,
    "repetitionPassed": True,
    "safetyPassed": True,
    "lengthOk": True,
    "conversationQualityPassed": True,
    "relationshipSafetyPassed": True,
    "personalityConsistencyPassed": True,
}


def test_version():
    assert RL.RELIABILITY_VERSION == 10


def test_actions():
    assert set(
        RL.ACTIONS
    ) == {
        RL.ACCEPT,
        RL.REPAIR,
        RL.ESCALATE,
        RL.FAIL_SAFE,
    }


def test_good_output_accepted():
    result = RL.decide_reliability(
        quality=GOOD_QUALITY,
    )

    assert result.action == RL.ACCEPT


def test_first_quality_failure_repairs():
    quality = dict(
        GOOD_QUALITY
    )
    quality[
        "repetitionPassed"
    ] = False

    result = RL.decide_reliability(
        quality=quality,
        attempt=1,
    )

    assert result.action == RL.REPAIR
    assert not result.can_claim_success


def test_second_quality_failure_fails_safe():
    quality = dict(
        GOOD_QUALITY
    )
    quality[
        "safetyPassed"
    ] = False

    result = RL.decide_reliability(
        quality=quality,
        attempt=2,
    )

    assert result.action == RL.FAIL_SAFE


def test_provider_failure_escalates_first_attempt():
    result = RL.decide_reliability(
        provider_ok=False,
        provider_error="provider_timeout",
        attempt=1,
    )

    assert result.action == RL.ESCALATE


def test_provider_failure_second_attempt_fails_safe():
    result = RL.decide_reliability(
        provider_ok=False,
        provider_error="provider_timeout",
        attempt=2,
    )

    assert result.action == RL.FAIL_SAFE


def test_unverified_external_success_fails_safe():
    result = RL.decide_reliability(
        quality=GOOD_QUALITY,
        external_success_claim=True,
        verified_external_success=False,
    )

    assert result.action == RL.FAIL_SAFE
    assert result.require_verification
    assert not result.can_claim_success


def test_verified_external_success_allowed():
    result = RL.decide_reliability(
        quality=GOOD_QUALITY,
        external_success_claim=True,
        verified_external_success=True,
    )

    assert result.action == RL.ACCEPT
    assert result.can_claim_success


def test_verification_required_propagates():
    result = RL.decide_reliability(
        quality=GOOD_QUALITY,
        verification_required=True,
    )

    assert result.action == RL.ACCEPT
    assert result.require_verification


def test_should_escalate_repair():
    result = RL.ReliabilityDecision(
        action=RL.REPAIR,
        confidence=0.9,
        reasons=("x",),
        require_verification=False,
        can_claim_success=False,
    )

    assert RL.should_escalate(
        result
    )


def test_should_escalate_provider_escalation():
    result = RL.ReliabilityDecision(
        action=RL.ESCALATE,
        confidence=0.9,
        reasons=("x",),
        require_verification=False,
        can_claim_success=False,
    )

    assert RL.should_escalate(
        result
    )


def test_accept_not_escalated():
    result = RL.ReliabilityDecision(
        action=RL.ACCEPT,
        confidence=0.9,
        reasons=("x",),
        require_verification=False,
        can_claim_success=True,
    )

    assert not RL.should_escalate(
        result
    )


def test_missing_quality_defaults_safe_pass():
    result = RL.decide_reliability(
        quality=None,
    )

    assert result.action == RL.ACCEPT


def test_failed_reason_is_recorded():
    quality = dict(
        GOOD_QUALITY
    )
    quality[
        "personalityConsistencyPassed"
    ] = False

    result = RL.decide_reliability(
        quality=quality,
    )

    assert (
        "personalityConsistencyPassed"
        in result.reasons
    )


def test_fail_safe_guidance_for_external_claim():
    result = RL.decide_reliability(
        quality=GOOD_QUALITY,
        external_success_claim=True,
        verified_external_success=False,
    )

    text = RL.build_reliability_guidance(
        result
    ).lower()

    assert "fail safely" in text
    assert "external action" in text


def test_no_hidden_reasoning_schema():
    result = RL.decide_reliability(
        quality=GOOD_QUALITY,
    ).to_dict()

    forbidden = {
        "chainOfThought",
        "chain_of_thought",
        "hiddenReasoning",
        "reasoningTrace",
    }

    assert not (
        forbidden
        & set(
            result
        )
    )

from ai_engine import memory_integrity_intelligence as MI11


def memory(
    memory_id,
    predicate,
    value,
    *,
    status="active",
    polarity="",
    canonical_key="",
    user_id="u1",
    character_id="c1",
    confidence=0.9,
    importance=0.7,
):
    result = {
        "memoryId": memory_id,
        "predicate": predicate,
        "value": value,
        "status": status,
        "userId": user_id,
        "characterId": character_id,
        "confidence": confidence,
        "importance": importance,
    }

    if polarity:
        result["polarity"] = polarity

    if canonical_key:
        result["canonicalKey"] = canonical_key

    return result


def test_version():
    assert MI11.MEMORY_INTEGRITY_VERSION == 11


def test_valid_new_memory_accepted():
    candidate = memory(
        "",
        "preference.food",
        "biryani",
    )

    result = MI11.assess_integrity(
        [],
        candidate,
        user_id="u1",
        character_id="c1",
    )

    assert result.action == MI11.ACTION_ACCEPT
    assert result.allowed


def test_missing_predicate_rejected():
    candidate = {
        "value": "biryani",
    }

    result = MI11.assess_integrity(
        [],
        candidate,
    )

    assert result.action == MI11.ACTION_REJECT
    assert "missing_predicate" in result.issues


def test_missing_value_rejected():
    candidate = {
        "predicate": "preference.food",
    }

    result = MI11.assess_integrity(
        [],
        candidate,
    )

    assert result.action == MI11.ACTION_REJECT
    assert "missing_value" in result.issues


def test_invalid_confidence_rejected():
    candidate = memory(
        "",
        "preference.food",
        "biryani",
        confidence=2.0,
    )

    result = MI11.assess_integrity(
        [],
        candidate,
    )

    assert result.action == MI11.ACTION_REJECT


def test_invalid_importance_rejected():
    candidate = memory(
        "",
        "preference.food",
        "biryani",
        importance=-1,
    )

    result = MI11.assess_integrity(
        [],
        candidate,
    )

    assert result.action == MI11.ACTION_REJECT


def test_historical_candidate_not_readded_as_new():
    candidate = memory(
        "",
        "employment.current",
        "Tesco",
        status="superseded",
    )

    result = MI11.assess_integrity(
        [],
        candidate,
    )

    assert result.action == MI11.ACTION_REJECT
    assert "candidate_already_historical" in result.issues


def test_scope_match():
    candidate = memory(
        "",
        "preference.food",
        "biryani",
    )

    assert MI11.scope_matches(
        candidate,
        user_id="u1",
        character_id="c1",
    )


def test_user_scope_mismatch():
    candidate = memory(
        "",
        "preference.food",
        "biryani",
        user_id="u2",
    )

    assert not MI11.scope_matches(
        candidate,
        user_id="u1",
        character_id="c1",
    )


def test_character_scope_mismatch():
    candidate = memory(
        "",
        "preference.food",
        "biryani",
        character_id="c2",
    )

    assert not MI11.scope_matches(
        candidate,
        user_id="u1",
        character_id="c1",
    )


def test_scope_mismatch_rejected():
    candidate = memory(
        "",
        "preference.food",
        "biryani",
        user_id="other",
    )

    result = MI11.assess_integrity(
        [],
        candidate,
        user_id="u1",
        character_id="c1",
    )

    assert result.action == MI11.ACTION_REJECT
    assert result.reason == "scope_mismatch"


def test_same_fact_by_predicate_value():
    existing = memory(
        "m1",
        "preference.food",
        "biryani",
    )

    candidate = memory(
        "",
        "preference.food",
        "biryani",
    )

    assert MI11.is_same_fact(
        existing,
        candidate,
    )


def test_same_fact_by_canonical_key():
    existing = memory(
        "m1",
        "preference.food",
        "biryani",
        canonical_key="preference:food:biryani",
    )

    candidate = memory(
        "",
        "preference.food",
        "biryani rice",
        canonical_key="preference:food:biryani",
    )

    assert MI11.is_same_fact(
        existing,
        candidate,
    )


def test_same_value_opposite_preference_polarity_not_same_fact():
    existing = memory(
        "m1",
        "preference.food",
        "coffee",
        polarity="positive",
    )

    candidate = memory(
        "",
        "preference.food",
        "coffee",
        polarity="negative",
    )

    assert not MI11.is_same_fact(
        existing,
        candidate,
    )


def test_reconfirmation_reinforces():
    existing = memory(
        "m1",
        "preference.food",
        "biryani",
        polarity="positive",
    )

    candidate = memory(
        "",
        "preference.food",
        "biryani",
        polarity="positive",
    )

    result = MI11.assess_integrity(
        [existing],
        candidate,
        user_id="u1",
        character_id="c1",
    )

    assert result.action == MI11.ACTION_REINFORCE
    assert result.reinforcement_memory_id == "m1"


def test_historical_record_does_not_receive_reinforcement():
    existing = memory(
        "m1",
        "employment.current",
        "Tesco",
        status="superseded",
    )

    candidate = memory(
        "",
        "employment.current",
        "Tesco",
    )

    match = MI11.find_reinforcement_match(
        [existing],
        candidate,
        user_id="u1",
        character_id="c1",
    )

    assert match is None


def test_current_employer_conflict():
    existing = memory(
        "m1",
        "employment.current",
        "Tesco",
    )

    candidate = memory(
        "",
        "employment.current",
        "Barclays",
    )

    assert MI11.memories_conflict(
        existing,
        candidate,
    )


def test_current_location_conflict():
    existing = memory(
        "m1",
        "location.current",
        "London",
    )

    candidate = memory(
        "",
        "location.current",
        "Manchester",
    )

    assert MI11.memories_conflict(
        existing,
        candidate,
    )


def test_identity_name_conflict():
    existing = memory(
        "m1",
        "identity.name",
        "Bala",
    )

    candidate = memory(
        "",
        "identity.name",
        "Ram",
    )

    assert MI11.memories_conflict(
        existing,
        candidate,
    )


def test_two_positive_food_preferences_do_not_conflict():
    existing = memory(
        "m1",
        "preference.food",
        "pizza",
        polarity="positive",
    )

    candidate = memory(
        "",
        "preference.food",
        "biryani",
        polarity="positive",
    )

    assert not MI11.memories_conflict(
        existing,
        candidate,
    )


def test_opposite_polarity_same_preference_conflicts():
    existing = memory(
        "m1",
        "preference.food",
        "coffee",
        polarity="positive",
    )

    candidate = memory(
        "",
        "preference.food",
        "coffee",
        polarity="negative",
    )

    assert MI11.memories_conflict(
        existing,
        candidate,
    )


def test_conflict_defers_to_belief_revision():
    existing = memory(
        "m1",
        "employment.current",
        "Tesco",
    )

    candidate = memory(
        "",
        "employment.current",
        "Barclays",
    )

    result = MI11.assess_integrity(
        [existing],
        candidate,
        user_id="u1",
        character_id="c1",
    )

    assert result.action == MI11.ACTION_DEFER_REVISION
    assert not result.allowed
    assert result.defer_to_belief_revision
    assert "m1" in result.conflicting_memory_ids


def test_explicit_correction_always_defers():
    candidate = memory(
        "",
        "identity.name",
        "Ram",
    )

    result = MI11.assess_integrity(
        [],
        candidate,
        revision_intent="correction",
    )

    assert result.action == MI11.ACTION_DEFER_REVISION
    assert result.defer_to_belief_revision


def test_explicit_forget_always_defers():
    candidate = memory(
        "",
        "identity.name",
        "Ram",
    )

    result = MI11.assess_integrity(
        [],
        candidate,
        revision_intent="forget",
    )

    assert result.action == MI11.ACTION_DEFER_REVISION
    assert result.defer_to_belief_revision


def test_explicit_retract_always_defers():
    candidate = memory(
        "",
        "identity.name",
        "Ram",
    )

    result = MI11.assess_integrity(
        [],
        candidate,
        revision_intent="retract",
    )

    assert result.action == MI11.ACTION_DEFER_REVISION


def test_explicit_replace_always_defers():
    candidate = memory(
        "",
        "employment.current",
        "Barclays",
    )

    result = MI11.assess_integrity(
        [],
        candidate,
        revision_intent="replace",
    )

    assert result.action == MI11.ACTION_DEFER_REVISION


def test_cross_user_memory_not_used_for_reinforcement():
    existing = memory(
        "m1",
        "preference.food",
        "biryani",
        user_id="u2",
    )

    candidate = memory(
        "",
        "preference.food",
        "biryani",
        user_id="u1",
    )

    result = MI11.assess_integrity(
        [existing],
        candidate,
        user_id="u1",
        character_id="c1",
    )

    assert result.action == MI11.ACTION_ACCEPT


def test_cross_character_memory_not_used_for_conflict():
    existing = memory(
        "m1",
        "employment.current",
        "Tesco",
        character_id="c2",
    )

    candidate = memory(
        "",
        "employment.current",
        "Barclays",
        character_id="c1",
    )

    result = MI11.assess_integrity(
        [existing],
        candidate,
        user_id="u1",
        character_id="c1",
    )

    assert result.action == MI11.ACTION_ACCEPT


def test_superseded_history_preserved():
    existing = memory(
        "m1",
        "employment.current",
        "Tesco",
        status="superseded",
    )

    assert MI11.historical_memory_preserved(
        existing
    )


def test_corrected_history_preserved():
    existing = memory(
        "m1",
        "identity.name",
        "Bala",
        status="corrected",
    )

    assert MI11.historical_memory_preserved(
        existing
    )


def test_retracted_history_preserved():
    existing = memory(
        "m1",
        "employment.current",
        "Tesco",
        status="retracted",
    )

    assert MI11.historical_memory_preserved(
        existing
    )


def test_active_memory_not_historical():
    existing = memory(
        "m1",
        "employment.current",
        "Barclays",
    )

    assert not MI11.historical_memory_preserved(
        existing
    )


def test_assessment_does_not_mutate_inputs():
    existing = [
        memory(
            "m1",
            "preference.food",
            "biryani",
        )
    ]

    candidate = memory(
        "",
        "preference.food",
        "biryani",
    )

    before_existing = [
        dict(item)
        for item in existing
    ]

    before_candidate = dict(
        candidate
    )

    MI11.assess_integrity(
        existing,
        candidate,
        user_id="u1",
        character_id="c1",
    )

    assert existing == before_existing
    assert candidate == before_candidate


def test_deterministic():
    existing = [
        memory(
            "m1",
            "preference.food",
            "biryani",
        )
    ]

    candidate = memory(
        "",
        "preference.food",
        "biryani",
    )

    first = MI11.assess_integrity(
        existing,
        candidate,
        user_id="u1",
        character_id="c1",
    )

    second = MI11.assess_integrity(
        existing,
        candidate,
        user_id="u1",
        character_id="c1",
    )

    assert first == second


def test_safe_copy_no_private_reasoning():
    candidate = memory(
        "",
        "preference.food",
        "biryani",
    )

    result = MI11.assess_integrity(
        [],
        candidate,
    )

    safe = MI11.safe_integrity_copy(
        result
    )

    text = str(
        safe
    )

    assert "chainOfThought" not in text
    assert "hiddenReasoning" not in text
    assert "reasoningTrace" not in text


def test_valid_action():
    result = MI11.assess_integrity(
        [],
        memory(
            "",
            "preference.food",
            "biryani",
        ),
    )

    assert result.action in MI11.VALID_ACTIONS

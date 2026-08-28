from datetime import datetime, timedelta, timezone

from ai_engine import memory_lifecycle_intelligence as ML11


NOW = datetime(
    2026,
    8,
    28,
    tzinfo=timezone.utc,
)


def memory(
    **overrides,
):
    value = {
        "memoryId": "m1",
        "predicate": "employment.current",
        "value": "Barclays",
        "canonicalKey":
            "user:employment.current:barclays",
        "type": "semantic",
        "status": "active",
        "confidence": 0.90,
        "importance": 0.70,
        "createdAt": (
            NOW
            - timedelta(
                days=30
            )
        ).isoformat(),
    }

    value.update(
        overrides
    )

    return value


def test_version():
    assert ML11.MEMORY_LIFECYCLE_VERSION == 11


def test_identity_is_stable():
    result = ML11.classify_durability(
        memory(
            predicate="identity.name",
            value="Ram",
        )
    )

    assert result == ML11.DURABILITY_STABLE


def test_preference_is_evolving():
    assert (
        ML11.classify_durability(
            memory(
                predicate="preference.language",
                value="Telugu",
            )
        )
        == ML11.DURABILITY_EVOLVING
    )


def test_employment_is_evolving():
    assert (
        ML11.classify_durability(
            memory(
                predicate="employment.current"
            )
        )
        == ML11.DURABILITY_EVOLVING
    )


def test_location_is_evolving():
    assert (
        ML11.classify_durability(
            memory(
                predicate="location.current"
            )
        )
        == ML11.DURABILITY_EVOLVING
    )


def test_explicit_temporary_is_temporary():
    assert (
        ML11.classify_durability(
            memory(
                durability="temporary"
            )
        )
        == ML11.DURABILITY_TEMPORARY
    )


def test_temporary_type_is_temporary():
    assert (
        ML11.classify_durability(
            memory(
                predicate="misc.note",
                type="temporary",
            )
        )
        == ML11.DURABILITY_TEMPORARY
    )


def test_high_importance_unknown_memory_becomes_stable():
    assert (
        ML11.classify_durability(
            memory(
                predicate="misc.fact",
                importance=0.95,
            )
        )
        == ML11.DURABILITY_STABLE
    )


def test_low_importance_unknown_memory_becomes_temporary():
    assert (
        ML11.classify_durability(
            memory(
                predicate="misc.fact",
                importance=0.10,
            )
        )
        == ML11.DURABILITY_TEMPORARY
    )


def test_reinforcement_increments_count():
    result = ML11.reinforcement_update(
        memory(
            reinforcementCount=2,
            reinforcementScore=0.3,
        )
    )

    assert result.reinforcement_count == 3
    assert result.reinforcement_score > 0.3
    assert result.strengthened


def test_reinforcement_is_bounded():
    current = memory(
        reinforcementCount=20,
        reinforcementScore=0.999,
    )

    result = current

    for _ in range(100):
        result = {
            **current,
            **ML11.reinforcement_update(
                current
            ).to_dict(),
        }

        current = result

    assert result["reinforcement_count"] <= 20
    assert result["reinforcement_score"] <= 1.0


def test_zero_confirmation_does_not_strengthen():
    result = ML11.reinforcement_update(
        memory(
            reinforcementCount=3,
            reinforcementScore=0.4,
        ),
        confirmation_strength=0.0,
    )

    assert result.reinforcement_count == 3
    assert result.reinforcement_score == 0.4
    assert not result.strengthened


def test_recent_memory_age():
    result = ML11.age_days(
        memory(
            createdAt=(
                NOW
                - timedelta(
                    days=10
                )
            ).isoformat()
        ),
        now=NOW,
    )

    assert 9.99 <= result <= 10.01


def test_last_reinforced_at_controls_age():
    result = ML11.age_days(
        memory(
            createdAt=(
                NOW
                - timedelta(
                    days=500
                )
            ).isoformat(),
            lastReinforcedAt=(
                NOW
                - timedelta(
                    days=5
                )
            ).isoformat(),
        ),
        now=NOW,
    )

    assert 4.99 <= result <= 5.01


def test_stable_memories_decay_slowly():
    factor = ML11.decay_factor(
        ML11.DURABILITY_STABLE,
        365,
        0.0,
    )

    assert factor > 0.90


def test_temporary_memories_decay_faster():
    temporary = ML11.decay_factor(
        ML11.DURABILITY_TEMPORARY,
        180,
        0.0,
    )

    evolving = ML11.decay_factor(
        ML11.DURABILITY_EVOLVING,
        180,
        0.0,
    )

    assert temporary < evolving


def test_reinforcement_slows_decay():
    weak = ML11.decay_factor(
        ML11.DURABILITY_EVOLVING,
        400,
        0.0,
    )

    reinforced = ML11.decay_factor(
        ML11.DURABILITY_EVOLVING,
        400,
        1.0,
    )

    assert reinforced > weak


def test_active_evolving_memory_retrievable():
    result = ML11.assess_memory(
        memory(),
        now=NOW,
    )

    assert result.retrieval_eligible
    assert not result.protected_history


def test_old_low_value_temporary_memory_can_decay_out():
    result = ML11.assess_memory(
        memory(
            predicate="temporary.note",
            type="temporary",
            confidence=0.35,
            importance=0.10,
            createdAt=(
                NOW
                - timedelta(
                    days=365
                )
            ).isoformat(),
        ),
        now=NOW,
    )

    assert result.decay_eligible
    assert not result.retrieval_eligible
    assert (
        result.reason
        == "temporary_memory_decayed"
    )


def test_important_temporary_memory_is_not_decay_eligible():
    result = ML11.assess_memory(
        memory(
            predicate="temporary.note",
            type="temporary",
            importance=0.95,
            createdAt=(
                NOW
                - timedelta(
                    days=365
                )
            ).isoformat(),
        ),
        now=NOW,
    )

    assert not result.decay_eligible


def test_superseded_history_is_preserved_but_not_normal_retrieval():
    result = ML11.assess_memory(
        memory(
            status="superseded",
            value="Tesco",
        ),
        now=NOW,
    )

    assert result.protected_history
    assert not result.retrieval_eligible
    assert (
        result.reason
        == "historical_state_preserved"
    )


def test_corrected_history_is_preserved():
    result = ML11.assess_memory(
        memory(
            status="corrected",
        ),
        now=NOW,
    )

    assert result.protected_history


def test_retracted_history_is_preserved():
    result = ML11.assess_memory(
        memory(
            status="retracted",
        ),
        now=NOW,
    )

    assert result.protected_history


def test_same_canonical_key_reinforces():
    existing = memory()

    candidate = memory(
        memoryId="m2"
    )

    assert ML11.should_reinforce(
        existing,
        candidate,
    )


def test_same_predicate_and_value_reinforces_without_key():
    existing = memory(
        canonicalKey=None,
    )

    candidate = memory(
        memoryId="m2",
        canonicalKey=None,
        value="BARCLAYS",
    )

    assert ML11.should_reinforce(
        existing,
        candidate,
    )


def test_different_value_does_not_reinforce():
    existing = memory()

    candidate = memory(
        memoryId="m2",
        canonicalKey=
            "user:employment.current:hsbc",
        value="HSBC",
    )

    assert not ML11.should_reinforce(
        existing,
        candidate,
    )


def test_superseded_memory_does_not_reinforce():
    existing = memory(
        status="superseded"
    )

    candidate = memory()

    assert not ML11.should_reinforce(
        existing,
        candidate,
    )


def test_safe_copy_contains_no_private_reasoning():
    result = ML11.safe_lifecycle_copy(
        ML11.assess_memory(
            memory(),
            now=NOW,
        )
    )

    assert "chainOfThought" not in result
    assert "hiddenReasoning" not in result
    assert "reasoningTrace" not in result


def test_assessment_is_deterministic():
    item = memory(
        reinforcementCount=4,
        reinforcementScore=0.6,
    )

    first = ML11.assess_memory(
        item,
        now=NOW,
    )

    second = ML11.assess_memory(
        item,
        now=NOW,
    )

    assert first == second


def test_assessment_does_not_mutate_input():
    item = memory()
    before = dict(item)

    ML11.assess_memory(
        item,
        now=NOW,
    )

    assert item == before


def test_reinforcement_does_not_mutate_input():
    item = memory()
    before = dict(item)

    ML11.reinforcement_update(
        item
    )

    assert item == before


def test_invalid_numeric_values_safe():
    result = ML11.assess_memory(
        memory(
            confidence="bad",
            importance=None,
            reinforcementScore="oops",
            reinforcementCount="bad",
        ),
        now=NOW,
    )

    assert 0.0 <= result.effective_strength <= 1.0


def test_missing_timestamp_safe():
    item = memory()
    item.pop(
        "createdAt"
    )

    result = ML11.assess_memory(
        item,
        now=NOW,
    )

    assert result.age_days == 0.0


def test_explicit_stable_override_respected():
    result = ML11.classify_durability(
        memory(
            predicate="temporary.note",
            durability="stable",
        )
    )

    assert result == ML11.DURABILITY_STABLE


def test_explicit_evolving_override_respected():
    result = ML11.classify_durability(
        memory(
            predicate="identity.name",
            durability="evolving",
        )
    )

    assert result == ML11.DURABILITY_EVOLVING


def test_effective_strength_is_bounded():
    result = ML11.assess_memory(
        memory(
            confidence=9.0,
            importance=9.0,
            reinforcementScore=9.0,
        ),
        now=NOW,
    )

    assert 0.0 <= result.effective_strength <= 1.0


def test_preference_is_evolving_not_stable():
    memory = {
        "predicate": "preference.food",
        "value": "biryani",
        "status": "active",
    }

    assert (
        ML11.classify_durability(
            memory
        )
        == ML11.DURABILITY_EVOLVING
    )


def test_reinforcement_persistence_round_trip():
    state = {
        "reinforcementCount": 2,
        "reinforcementScore": 0.25,
    }

    first = ML11.reinforcement_update(
        state
    )

    first_saved = (
        ML11.reinforcement_persistence_dict(
            first
        )
    )

    second = ML11.reinforcement_update(
        first_saved
    )

    second_saved = (
        ML11.reinforcement_persistence_dict(
            second
        )
    )

    assert (
        second_saved[
            "reinforcementCount"
        ]
        >
        first_saved[
            "reinforcementCount"
        ]
    )

    assert (
        second_saved[
            "reinforcementScore"
        ]
        >=
        first_saved[
            "reinforcementScore"
        ]
    )

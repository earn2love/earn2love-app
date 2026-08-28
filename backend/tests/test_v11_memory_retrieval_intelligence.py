from datetime import datetime, timedelta, timezone

from ai_engine import memory_retrieval_intelligence as MR11


NOW = datetime(
    2026,
    8,
    28,
    tzinfo=timezone.utc,
)


def item(
    memory_id,
    predicate,
    value,
    *,
    status="active",
    confidence=0.9,
    importance=0.7,
    days=10,
    topics=None,
    memory_type="semantic",
    **extra,
):
    result = {
        "memoryId": memory_id,
        "predicate": predicate,
        "value": value,
        "text": f"I told you {value}",
        "canonicalKey":
            f"user:{predicate}:{str(value).casefold()}",
        "status": status,
        "confidence": confidence,
        "importance": importance,
        "type": memory_type,
        "createdAt": (
            NOW
            - timedelta(
                days=days
            )
        ).isoformat(),
        "topics": topics or [],
    }

    result.update(
        extra
    )

    return result


def test_version():
    assert MR11.MEMORY_RETRIEVAL_VERSION == 11


def test_detect_explicit_recall():
    assert MR11.is_explicit_recall(
        "Do you remember where I work?"
    )


def test_detect_non_recall():
    assert not MR11.is_explicit_recall(
        "Where do I work?"
    )


def test_detect_historical_recall():
    assert MR11.is_historical_recall(
        "Where did I work before?"
    )


def test_current_query_not_historical():
    assert not MR11.is_historical_recall(
        "Where do I work?"
    )


def test_lexical_match():
    memory = item(
        "m1",
        "employment.current",
        "Barclays",
    )

    score = MR11.lexical_relevance(
        memory,
        "Do I still work at Barclays?"
    )

    assert score > 0


def test_unrelated_lexical_is_zero():
    memory = item(
        "m1",
        "employment.current",
        "Barclays",
    )

    score = MR11.lexical_relevance(
        memory,
        "What food do I like?"
    )

    assert score == 0


def test_topic_match():
    memory = item(
        "m1",
        "employment.current",
        "Barclays",
        topics=["work"],
    )

    assert (
        MR11.topic_relevance(
            memory,
            ["work"],
        )
        == 1.0
    )


def test_predicate_topic_match():
    memory = item(
        "m1",
        "employment.current",
        "Barclays",
    )

    assert (
        MR11.topic_relevance(
            memory,
            ["employment"],
        )
        == 1.0
    )


def test_relationship_memory_boost():
    memory = item(
        "m1",
        "relationship.boundary",
        "likes supportive replies",
    )

    score = MR11.relationship_relevance(
        memory,
        relationship_relevant=True,
    )

    assert score == 1.0


def test_relationship_boost_not_applied_when_not_needed():
    memory = item(
        "m1",
        "relationship.boundary",
        "likes supportive replies",
    )

    score = MR11.relationship_relevance(
        memory,
        relationship_relevant=False,
    )

    assert score == 0.0


def test_active_memory_is_eligible():
    candidate = MR11.score_memory(
        item(
            "m1",
            "employment.current",
            "Barclays",
        ),
        "Where do I work?",
        topics=["employment"],
        now=NOW,
    )

    assert candidate.retrieval_eligible


def test_superseded_memory_excluded_for_current_query():
    candidate = MR11.score_memory(
        item(
            "m1",
            "employment.current",
            "Tesco",
            status="superseded",
        ),
        "Where do I work?",
        topics=["employment"],
        now=NOW,
    )

    assert not candidate.retrieval_eligible
    assert candidate.score == 0.0


def test_superseded_memory_allowed_for_history_query():
    candidate = MR11.score_memory(
        item(
            "m1",
            "employment.current",
            "Tesco",
            status="superseded",
        ),
        "Where did I work before?",
        topics=["employment"],
        now=NOW,
    )

    assert candidate.retrieval_eligible
    assert candidate.historical_bonus > 0


def test_retracted_memory_requires_explicit_revision_history():
    vague = MR11.score_memory(
        item(
            "m1",
            "employment.current",
            "Tesco",
            status="retracted",
        ),
        "What did I tell you before about Tesco?",
        topics=["employment"],
        now=NOW,
    )

    assert not vague.retrieval_eligible

    explicit = MR11.score_memory(
        item(
            "m1",
            "employment.current",
            "Tesco",
            status="retracted",
        ),
        "What did I retract about Tesco?",
        topics=["employment"],
        now=NOW,
    )

    assert explicit.retrieval_eligible


def test_explicit_recall_receives_bonus():
    normal = MR11.score_memory(
        item(
            "m1",
            "employment.current",
            "Barclays",
        ),
        "Where do I work?",
        now=NOW,
    )

    explicit = MR11.score_memory(
        item(
            "m1",
            "employment.current",
            "Barclays",
        ),
        "Do you remember where I work at Barclays?",
        now=NOW,
    )

    assert (
        explicit.explicit_recall_bonus
        > normal.explicit_recall_bonus
    )


def test_stronger_relevant_memory_ranks_first():
    memories = [
        item(
            "m1",
            "preference.food",
            "pizza",
            confidence=0.3,
            importance=0.2,
            days=300,
        ),
        item(
            "m2",
            "preference.food",
            "biryani",
            confidence=0.95,
            importance=0.9,
            days=3,
        ),
    ]

    ranked = MR11.rank_memories(
        memories,
        "What food do I like?",
        topics=["food"],
        now=NOW,
    )

    assert ranked[0].memory_id == "m2"


def test_unrelated_memory_does_not_beat_relevant_memory():
    memories = [
        item(
            "m1",
            "location.current",
            "London",
            importance=0.95,
        ),
        item(
            "m2",
            "preference.food",
            "biryani",
            importance=0.7,
            topics=["food"],
        ),
    ]

    ranked = MR11.rank_memories(
        memories,
        "What food do I like?",
        topics=["food"],
        now=NOW,
    )

    assert ranked[0].memory_id == "m2"


def test_selection_respects_limit():
    memories = [
        item(
            f"m{x}",
            "preference.food",
            f"food-{x}",
            topics=["food"],
        )
        for x in range(10)
    ]

    result = MR11.select_memories(
        memories,
        "Tell me about food I like",
        topics=["food"],
        limit=3,
        now=NOW,
    )

    assert len(result.selected) == 3


def test_zero_limit_returns_empty():
    result = MR11.select_memories(
        [
            item(
                "m1",
                "preference.food",
                "biryani",
            )
        ],
        "What food do I like?",
        limit=0,
        now=NOW,
    )

    assert result.selected == ()


def test_limit_is_bounded_to_twenty():
    result = MR11.select_memories(
        [
            item(
                f"m{x}",
                "preference.food",
                f"food-{x}",
                topics=["food"],
            )
            for x in range(30)
        ],
        "Tell me about food",
        topics=["food"],
        limit=100,
        minimum_score=0.0,
        now=NOW,
    )

    assert result.limit == 20
    assert len(result.selected) <= 20


def test_old_temporary_decayed_memory_excluded():
    memory = item(
        "m1",
        "temporary.note",
        "buy milk",
        confidence=0.2,
        importance=0.1,
        days=500,
        memory_type="temporary",
    )

    result = MR11.select_memories(
        [memory],
        "What did I say about milk?",
        now=NOW,
    )

    assert result.selected == ()


def test_stable_identity_survives_age():
    memory = item(
        "m1",
        "identity.name",
        "Ram",
        confidence=0.95,
        importance=0.95,
        days=1500,
    )

    result = MR11.select_memories(
        [memory],
        "What is my name?",
        topics=["identity"],
        now=NOW,
    )

    assert len(result.selected) == 1


def test_historical_query_can_select_old_employer():
    memories = [
        item(
            "m1",
            "employment.current",
            "Tesco",
            status="superseded",
            days=800,
        ),
        item(
            "m2",
            "employment.current",
            "Barclays",
            status="active",
            days=20,
        ),
    ]

    result = MR11.select_memories(
        memories,
        "Where did I work before?",
        topics=["employment"],
        limit=4,
        now=NOW,
    )

    values = {
        memory["value"]
        for memory in result.selected
    }

    assert "Tesco" in values


def test_current_query_excludes_old_employer():
    memories = [
        item(
            "m1",
            "employment.current",
            "Tesco",
            status="superseded",
        ),
        item(
            "m2",
            "employment.current",
            "Barclays",
        ),
    ]

    result = MR11.select_memories(
        memories,
        "Where do I work?",
        topics=["employment"],
        limit=4,
        minimum_score=0.0,
        now=NOW,
    )

    values = {
        memory["value"]
        for memory in result.selected
    }

    assert "Barclays" in values
    assert "Tesco" not in values


def test_selection_is_deterministic():
    memories = [
        item(
            "m1",
            "preference.food",
            "biryani",
        ),
        item(
            "m2",
            "preference.drink",
            "coffee",
        ),
    ]

    first = MR11.select_memories(
        memories,
        "What do I like?",
        now=NOW,
    )

    second = MR11.select_memories(
        memories,
        "What do I like?",
        now=NOW,
    )

    assert first == second


def test_selection_does_not_mutate_memories():
    memories = [
        item(
            "m1",
            "preference.food",
            "biryani",
        )
    ]

    before = [
        dict(memory)
        for memory in memories
    ]

    MR11.select_memories(
        memories,
        "What food do I like?",
        now=NOW,
    )

    assert memories == before


def test_safe_copy_has_no_private_reasoning():
    result = MR11.select_memories(
        [
            item(
                "m1",
                "identity.name",
                "Ram",
            )
        ],
        "Do you remember my name?",
        now=NOW,
    )

    safe = MR11.safe_retrieval_copy(
        result
    )

    text = str(
        safe
    )

    assert "chainOfThought" not in text
    assert "hiddenReasoning" not in text
    assert "reasoningTrace" not in text


def test_candidate_contains_original_memory():
    memory = item(
        "m1",
        "identity.name",
        "Ram",
    )

    candidate = MR11.score_memory(
        memory,
        "What is my name?",
        now=NOW,
    )

    assert candidate.memory["memoryId"] == "m1"


def test_no_relevant_memory_reason():
    result = MR11.select_memories(
        [],
        "What do I like?",
        now=NOW,
    )

    assert result.reason == "no_relevant_memory"


def test_explicit_recall_reason():
    result = MR11.select_memories(
        [
            item(
                "m1",
                "identity.name",
                "Ram",
            )
        ],
        "Do you remember my name Ram?",
        now=NOW,
    )

    assert result.reason == "explicit_recall"


def test_historical_recall_reason():
    result = MR11.select_memories(
        [
            item(
                "m1",
                "employment.current",
                "Tesco",
                status="superseded",
            )
        ],
        "Where did I work before?",
        topics=["employment"],
        minimum_score=0.0,
        now=NOW,
    )

    assert result.reason == "historical_recall"


def test_relationship_relevance_can_change_rank():
    memories = [
        item(
            "m1",
            "misc.fact",
            "something",
            importance=0.8,
        ),
        item(
            "m2",
            "relationship.boundary",
            "likes reassurance",
            importance=0.7,
        ),
    ]

    ranked = MR11.rank_memories(
        memories,
        "How should you respond to me?",
        relationship_relevant=True,
        now=NOW,
    )

    assert ranked[0].memory_id == "m2"


def test_minimum_score_filters_weak_memory():
    result = MR11.select_memories(
        [
            item(
                "m1",
                "misc.fact",
                "unrelated",
                confidence=0.1,
                importance=0.1,
                days=500,
            )
        ],
        "Tell me about work",
        limit=4,
        minimum_score=0.8,
        now=NOW,
    )

    assert result.selected == ()


def test_unrelated_high_strength_memory_is_filtered_even_at_zero_threshold():
    memories = [
        item(
            "m1",
            "employment.current",
            "Barclays",
            confidence=0.9,
            importance=0.7,
            topics=["employment"],
        ),
        item(
            "m2",
            "preference.food",
            "biryani",
            confidence=1.0,
            importance=1.0,
            topics=["food"],
        ),
    ]

    result = MR11.select_memories(
        memories,
        "Where do I work?",
        topics=["employment"],
        limit=4,
        minimum_score=0.0,
        now=NOW,
    )

    values = {
        memory["value"]
        for memory in result.selected
    }

    assert "Barclays" in values
    assert "biryani" not in values


def test_explicit_recall_does_not_dump_unrelated_memories():
    memories = [
        item(
            "m1",
            "identity.name",
            "Ram",
            importance=0.95,
        ),
        item(
            "m2",
            "preference.food",
            "biryani",
            importance=0.95,
        ),
    ]

    result = MR11.select_memories(
        memories,
        "Do you remember my name Ram?",
        limit=10,
        minimum_score=0.0,
        now=NOW,
    )

    values = {
        memory["value"]
        for memory in result.selected
    }

    assert "Ram" in values
    assert "biryani" not in values


def test_lifecycle_fallback_requires_explicit_opt_in():
    memory = item(
        "m1",
        "misc.fact",
        "high-strength-unrelated",
        confidence=1.0,
        importance=1.0,
    )

    normal = MR11.select_memories(
        [memory],
        "Tell me about checkout",
        minimum_score=0.0,
        now=NOW,
    )

    fallback = MR11.select_memories(
        [memory],
        "Tell me about checkout",
        minimum_score=0.0,
        allow_lifecycle_fallback=True,
        now=NOW,
    )

    assert normal.selected == ()
    assert len(fallback.selected) == 1


def test_no_query_relevance_reason():
    candidate = MR11.score_memory(
        item(
            "m1",
            "preference.food",
            "biryani",
            confidence=1.0,
            importance=1.0,
        ),
        "Where do I work?",
        topics=["employment"],
        now=NOW,
    )

    assert not candidate.retrieval_eligible
    assert candidate.score == 0.0
    assert candidate.reason == "no_query_relevance"



def test_bare_before_does_not_enable_historical_records():
    assert not MR11.is_historical_recall(
        "I told you before that I like biryani"
    )


def test_previous_employer_query_is_historical():
    assert MR11.is_historical_recall(
        "Where did I work before?"
    )


def test_explicit_revision_history_detector():
    assert MR11.is_revision_history_recall(
        "What information did I correct?"
    )


def test_generic_history_filters_corrected_retracted_records():
    memories = [
        {
            "memoryId": "current",
            "predicate": "employment.current",
            "value": "Barclays",
            "text": "I work at Barclays",
            "status": "active",
            "confidence": 0.95,
            "importance": 0.8,
        },
        {
            "memoryId": "old-real",
            "predicate": "employment.current",
            "value": "Tesco",
            "text": "I worked at Tesco",
            "status": "superseded",
            "confidence": 0.95,
            "importance": 0.8,
        },
        {
            "memoryId": "false",
            "predicate": "employment.current",
            "value": "FakeCorp",
            "text": "I worked at FakeCorp",
            "status": "retracted",
            "confidence": 0.95,
            "importance": 0.8,
        },
        {
            "memoryId": "wrong",
            "predicate": "employment.current",
            "value": "WrongCorp",
            "text": "I worked at WrongCorp",
            "status": "corrected",
            "confidence": 0.95,
            "importance": 0.8,
        },
    ]

    decision = MR11.select_memories(
        memories,
        "Where did I work before?",
        limit=20,
        minimum_score=0.0,
        allow_lifecycle_fallback=True,
    )

    ids = {
        memory.get("memoryId")
        for memory in decision.selected
    }

    assert "old-real" in ids
    assert "false" not in ids
    assert "wrong" not in ids

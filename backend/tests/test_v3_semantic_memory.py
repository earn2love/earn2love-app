from ai_engine import semantic_memory as S


def test_exact_similarity_is_high():
    assert S.semantic_similarity(
        "I work at HSBC",
        "I work at HSBC",
    ) >= 0.9


def test_conceptual_job_retrieval_without_exact_phrase():
    score = S.semantic_similarity(
        "Where are you working now?",
        "I joined HSBC as a business analyst",
    )

    assert score >= 0.20


def test_unrelated_memory_scores_lower():
    related = S.semantic_similarity(
        "How is your job going?",
        "I joined HSBC as a business analyst",
    )

    unrelated = S.semantic_similarity(
        "How is your job going?",
        "My favourite food is biryani",
    )

    assert related > unrelated


def test_location_concept():
    related = S.semantic_similarity(
        "Where do you live?",
        "I moved to London last year",
    )

    unrelated = S.semantic_similarity(
        "Where do you live?",
        "I love chess",
    )

    assert related > unrelated


def test_structured_memory_text():
    memory = {
        "text": "I joined HSBC",
        "subject": "user",
        "predicate": "employment.current",
        "value": "HSBC",
        "tags": ["career", "banking"],
    }

    text = S.memory_text(memory)

    assert "HSBC" in text
    assert "employment.current" in text
    assert "career" in text


def test_canonical_key_from_structured_fields():
    memory = {
        "subject": "user",
        "predicate": "employment.current",
    }

    assert S.canonical_key(memory) == "user:employment.current"


def test_explicit_canonical_key_wins():
    memory = {
        "canonicalKey": "USER:JOB",
        "subject": "ignored",
        "predicate": "ignored",
    }

    assert S.canonical_key(memory) == "user:job"


def test_superseded_memory_not_ranked():
    memories = [
        {
            "text": "I work at Tesco",
            "status": "superseded",
            "importance": 0.9,
        },
        {
            "text": "I joined HSBC",
            "status": "active",
            "importance": 0.8,
        },
    ]

    ranked = S.rank_semantic(
        "Where do I work?",
        memories,
    )

    assert len(ranked) == 1
    assert ranked[0]["text"] == "I joined HSBC"


def test_v2_memory_is_backward_compatible():
    memories = [
        {
            "text": "I study artificial intelligence",
            "importance": 0.6,
            "type": "episodic",
        }
    ]

    ranked = S.rank_semantic(
        "How is university going?",
        memories,
    )

    assert len(ranked) == 1
    assert "_semanticScore" in ranked[0]


def test_unicode_normalisation():
    assert S.normalize_text("RAM’S Job") == "ram's job"

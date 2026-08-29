from pathlib import Path


ENGINE = Path(
    "backend/ai_engine/engine.py"
).read_text(
    encoding="utf-8-sig"
)

RI = Path(
    "backend/ai_engine/relationship_intelligence.py"
).read_text(
    encoding="utf-8-sig"
)

RE15 = Path(
    "backend/ai_engine/relationship_emotional_intelligence.py"
).read_text(
    encoding="utf-8-sig"
)

EI = Path(
    "backend/ai_engine/emotional_intelligence.py"
).read_text(
    encoding="utf-8-sig"
)

REPOSITORY = Path(
    "backend/ai_engine/repository.py"
).read_text(
    encoding="utf-8-sig"
)


def test_engine_has_exactly_one_relationship_advance():
    assert (
        ENGINE.count(
            "R.advance(self.repo,"
        )
        == 1
    )


def test_relationship_persistence_remains_after_generation():
    generation = ENGINE.index(
        "await self._generate_guarded("
    )

    advance = ENGINE.index(
        "R.advance(self.repo,"
    )

    assert generation < advance


def test_relationship_persistence_remains_non_sandbox():
    generation = ENGINE.index(
        "await self._generate_guarded("
    )

    sandbox = ENGINE.index(
        "if not sandbox:",
        generation,
    )

    advance = ENGINE.index(
        "R.advance(self.repo,"
    )

    assert generation < sandbox < advance


def test_no_v15_parallel_relationship_collection():
    combined = (
        ENGINE
        + RI
        + RE15
        + EI
        + REPOSITORY
    )

    forbidden = (
        "aiCharacterRelationshipContinuity",
        "aiCharacterRepairState",
        "aiCharacterEmotionalState",
        "aiCharacterRelationshipEmotionalState",
    )

    for name in forbidden:
        assert name not in combined


def test_existing_relationship_collection_remains_authority():
    assert (
        '"aiCharacterRelationshipState"'
        in REPOSITORY
    )


def test_v15_pure_modules_have_no_firestore_writes():
    for source in (
        RI,
        RE15,
        EI,
    ):
        assert ".collection(" not in source
        assert "transaction.set(" not in source
        assert "firestore." not in source


def test_v15_pure_modules_have_no_direct_openai_calls():
    for source in (
        RI,
        RE15,
        EI,
    ):
        assert "AsyncOpenAI(" not in source
        assert "OpenAI(" not in source


def test_v15_does_not_mutate_global_character_personality():
    combined = (
        RI
        + RE15
        + EI
    )

    forbidden = (
        "set_character(",
        "update_character(",
        "save_character(",
        "personality_signature =",
    )

    for token in forbidden:
        assert token not in combined


def test_v10_generation_path_still_used():
    assert (
        "await self._generate_guarded("
        in ENGINE
    )


def test_v15_context_is_guidance_not_new_provider_path():
    assert (
        "V15_EMOTIONAL_RELATIONSHIP_INTELLIGENCE:"
        in ENGINE
    )

    assert (
        "RE15.build_relationship_emotional_guidance("
        in ENGINE
    )


def test_relationship_firestore_update_still_uses_ri_evolve():
    start = REPOSITORY.index(
        "def advance_relationship(",
        REPOSITORY.index(
            "class FirestoreCharacterRepository"
        ),
    )

    section = REPOSITORY[
        start:
        start + 5000
    ]

    assert "@firestore.transactional" in section
    assert "RI.evolve(" in section
    assert "transaction.set(" in section

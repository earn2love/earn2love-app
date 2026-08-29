from pathlib import Path


ENGINE = Path(
    "backend/ai_engine/engine.py"
).read_text(
    encoding="utf-8-sig"
)


def test_v15_bridge_imported():
    assert (
        "relationship_emotional_intelligence as RE15"
        in ENGINE
    )


def test_v15_emotion_before_generation():
    emotion = ENGINE.index(
        "EI.analyze_emotional_state_v15("
    )

    generation = ENGINE.index(
        "await self._generate_guarded("
    )

    assert emotion < generation


def test_v15_relationship_bridge_before_generation():
    bridge = ENGINE.index(
        "RE15.build_relationship_emotional_guidance("
    )

    generation = ENGINE.index(
        "await self._generate_guarded("
    )

    assert bridge < generation


def test_v15_prompt_exists_once():
    assert (
        ENGINE.count(
            "V15_EMOTIONAL_RELATIONSHIP_INTELLIGENCE:"
        )
        == 1
    )


def test_v15_prompt_precedes_v6_personality_prompt():
    v15 = ENGINE.index(
        "V15_EMOTIONAL_RELATIONSHIP_INTELLIGENCE:"
    )

    v6 = ENGINE.index(
        "V6_GLOBAL_CHARACTER_PERSONALITY:"
    )

    assert v15 < v6


def test_exactly_one_relationship_advance():
    assert (
        ENGINE.count(
            "R.advance(self.repo,"
        )
        == 1
    )


def test_generation_before_relationship_persistence():
    generation = ENGINE.index(
        "await self._generate_guarded("
    )

    advance = ENGINE.index(
        "R.advance(self.repo,"
    )

    assert generation < advance


def test_relationship_advance_inside_non_sandbox_path():
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


def test_failed_generation_returns_before_relationship_advance():
    generation = ENGINE.index(
        "await self._generate_guarded("
    )

    failure = ENGINE.index(
        'if not result["ok"]:',
        generation,
    )

    advance = ENGINE.index(
        "R.advance(self.repo,"
    )

    assert failure < advance


def test_v15_metadata_present():
    assert '"v15": {' in ENGINE
    assert '"repairNeeded": (' in ENGINE
    assert '"repairMode": (' in ENGINE


def test_no_v15_firestore_state_collection():
    assert (
        "aiCharacterEmotionalState"
        not in ENGINE
    )

    assert (
        "aiCharacterRelationshipEmotionalState"
        not in ENGINE
    )

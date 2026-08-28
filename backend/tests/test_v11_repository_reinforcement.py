from pathlib import Path
import ast

from ai_engine.repository import (
    CharacterRepository,
    InMemoryCharacterRepository,
)


def _repo():
    return InMemoryCharacterRepository()


def test_repository_contract_exposes_reinforcement():
    assert hasattr(
        CharacterRepository,
        "reinforce_memory",
    )


def test_inmemory_reinforcement_updates_existing_memory():
    repo = _repo()

    stored = repo.add_memory(
        "character-a",
        "user-a",
        {
            "predicate": "preference.food",
            "value": "biryani",
            "status": "active",
            "reinforcementCount": 2,
            "reinforcementScore": 0.25,
        },
    )

    result = repo.reinforce_memory(
        "character-a",
        "user-a",
        stored["memoryId"],
    )

    assert result is stored

    assert (
        result["reinforcementCount"]
        == 3
    )

    assert (
        result["reinforcementScore"]
        > 0.25
    )


def test_inmemory_reinforcement_accumulates():
    repo = _repo()

    stored = repo.add_memory(
        "character-a",
        "user-a",
        {
            "predicate": "preference.food",
            "value": "biryani",
            "status": "active",
        },
    )

    first = repo.reinforce_memory(
        "character-a",
        "user-a",
        stored["memoryId"],
    )

    second = repo.reinforce_memory(
        "character-a",
        "user-a",
        stored["memoryId"],
    )

    assert (
        second["reinforcementCount"]
        >
        first.get(
            "_test_previous_count",
            0,
        )
    )

    assert (
        second["reinforcementCount"]
        == 2
    )


def test_wrong_user_cannot_reinforce_memory():
    repo = _repo()

    stored = repo.add_memory(
        "character-a",
        "user-a",
        {
            "predicate": "identity.name",
            "value": "Ram",
            "status": "active",
        },
    )

    result = repo.reinforce_memory(
        "character-a",
        "user-b",
        stored["memoryId"],
    )

    assert result is None

    assert (
        stored.get(
            "reinforcementCount",
            0,
        )
        == 0
    )


def test_wrong_character_cannot_reinforce_memory():
    repo = _repo()

    stored = repo.add_memory(
        "character-a",
        "user-a",
        {
            "predicate": "identity.name",
            "value": "Ram",
            "status": "active",
        },
    )

    result = repo.reinforce_memory(
        "character-b",
        "user-a",
        stored["memoryId"],
    )

    assert result is None


def test_historical_memory_is_not_reinforced():
    repo = _repo()

    stored = repo.add_memory(
        "character-a",
        "user-a",
        {
            "predicate": "employment.current",
            "value": "Tesco",
            "status": "superseded",
        },
    )

    result = repo.reinforce_memory(
        "character-a",
        "user-a",
        stored["memoryId"],
    )

    assert result is None

    assert (
        stored.get(
            "reinforcementCount",
            0,
        )
        == 0
    )


def test_missing_memory_returns_none():
    repo = _repo()

    result = repo.reinforce_memory(
        "character-a",
        "user-a",
        "does-not-exist",
    )

    assert result is None


def test_firestore_reinforcement_is_transactional_and_scoped():
    source = Path(
        "backend/ai_engine/repository.py"
    ).read_text(
        encoding="utf-8"
    )

    tree = ast.parse(
        source
    )

    cls = next(
        node
        for node in tree.body
        if (
            isinstance(
                node,
                ast.ClassDef,
            )
            and node.name
            == "FirestoreCharacterRepository"
        )
    )

    method = next(
        node
        for node in cls.body
        if (
            isinstance(
                node,
                ast.FunctionDef,
            )
            and node.name
            == "reinforce_memory"
        )
    )

    method_source = ast.get_source_segment(
        source,
        method,
    )

    assert (
        'collection(\n            "aiCharacterMemories"\n        )'
        in method_source
    )

    assert (
        "self.db.transaction()"
        in method_source
    )

    assert (
        "@firestore.transactional"
        in method_source
    )

    assert (
        '"characterId"'
        in method_source
    )

    assert (
        '"userId"'
        in method_source
    )

    assert (
        '"status"'
        in method_source
    )

    assert (
        "transaction.update"
        in method_source
    )

    assert (
        "transaction.set"
        not in method_source
    )

    assert (
        "add_memory"
        not in method_source
    )


def test_firestore_reinforcement_uses_v11_lifecycle_calculation():
    source = Path(
        "backend/ai_engine/repository.py"
    ).read_text(
        encoding="utf-8"
    )

    assert (
        "ML11.reinforcement_update"
        in source
    )

    assert (
        "ML11.reinforcement_persistence_dict"
        in source
    )

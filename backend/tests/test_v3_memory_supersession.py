from ai_engine.repository import InMemoryCharacterRepository
from ai_engine import structured_facts as SF


CID = "character-test"
UID = "user-test"


def fact(text):
    facts = SF.extract_facts(text, {})
    assert facts

    f = facts[0]

    return {
        **f,
        "supersedesExisting": SF.supersedes_existing(f),
    }


def active(repo, predicate):
    return [
        m
        for m in repo.list_memories(CID, UID)
        if m.get("predicate") == predicate
        and m.get("status", "active") == "active"
    ]


def test_current_employer_supersedes_old_value():
    repo = InMemoryCharacterRepository()

    repo.save_structured_memory(
        CID,
        UID,
        fact("I work at Tesco"),
    )

    repo.save_structured_memory(
        CID,
        UID,
        fact("I joined HSBC"),
    )

    memories = repo.list_memories(CID, UID)

    assert len(memories) == 2

    tesco = next(
        m for m in memories
        if m.get("value") == "Tesco"
    )

    hsbc = next(
        m for m in memories
        if m.get("value") == "HSBC"
    )

    assert tesco["status"] == "superseded"
    assert tesco["supersededByValue"] == "HSBC"
    assert tesco.get("supersededAt")

    assert hsbc["status"] == "active"


def test_only_one_current_employer_remains_active():
    repo = InMemoryCharacterRepository()

    repo.save_structured_memory(
        CID,
        UID,
        fact("I work at Tesco"),
    )

    repo.save_structured_memory(
        CID,
        UID,
        fact("I joined HSBC"),
    )

    repo.save_structured_memory(
        CID,
        UID,
        fact("I joined Barclays"),
    )

    current = active(
        repo,
        "employment.current",
    )

    assert len(current) == 1
    assert current[0]["value"] == "Barclays"


def test_full_employer_history_is_preserved():
    repo = InMemoryCharacterRepository()

    for text in (
        "I work at Tesco",
        "I joined HSBC",
        "I joined Barclays",
    ):
        repo.save_structured_memory(
            CID,
            UID,
            fact(text),
        )

    memories = [
        m
        for m in repo.list_memories(CID, UID)
        if m.get("predicate") == "employment.current"
    ]

    assert len(memories) == 3

    by_value = {
        m["value"]: m
        for m in memories
    }

    assert by_value["Tesco"]["status"] == "superseded"
    assert by_value["HSBC"]["status"] == "superseded"
    assert by_value["Barclays"]["status"] == "active"


def test_duplicate_current_value_does_not_create_duplicate():
    repo = InMemoryCharacterRepository()

    first = repo.save_structured_memory(
        CID,
        UID,
        fact("I work at Tesco"),
    )

    second = repo.save_structured_memory(
        CID,
        UID,
        fact("I work at Tesco"),
    )

    memories = repo.list_memories(CID, UID)

    assert len(memories) == 1
    assert first["memoryId"] == second["memoryId"]


def test_location_current_supersedes_previous_current_location():
    repo = InMemoryCharacterRepository()

    repo.save_structured_memory(
        CID,
        UID,
        fact("I live in Manchester"),
    )

    repo.save_structured_memory(
        CID,
        UID,
        fact("I live in London"),
    )

    current = active(
        repo,
        "location.current",
    )

    assert len(current) == 1
    assert current[0]["value"] == "London"


def test_non_superseding_history_is_preserved():
    repo = InMemoryCharacterRepository()

    historical = {
        "subject": "user",
        "predicate": "employment.previous",
        "value": "Tesco",
        "canonicalKey": "user:employment.previous:tesco",
        "text": "I left Tesco",
        "type": "episodic",
        "status": "active",
        "confidence": 0.95,
        "importance": 0.75,
        "supersedesExisting": False,
    }

    repo.save_structured_memory(
        CID,
        UID,
        historical,
    )

    memories = repo.list_memories(CID, UID)

    assert len(memories) == 1
    assert memories[0]["status"] == "active"
    assert memories[0]["predicate"] == "employment.previous"


def test_structured_memory_receives_memory_id_and_timestamp():
    repo = InMemoryCharacterRepository()

    stored = repo.save_structured_memory(
        CID,
        UID,
        fact("I work at Tesco"),
    )

    assert stored.get("memoryId")
    assert stored.get("createdAt")

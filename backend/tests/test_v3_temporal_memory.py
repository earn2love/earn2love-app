from ai_engine.repository import InMemoryCharacterRepository
from ai_engine import memory as M
from ai_engine import structured_facts as SF


CID = "temporal-character"
UID = "temporal-user"


def understanding(text):
    return {
        "currentMessage": text,
        "userText": text,
        "semanticQuery": text,
        "topics": [],
        "userReferencedPast": False,
    }


def save(repo, text):
    facts = SF.extract_facts(text, {})

    assert facts

    for fact in facts:
        repo.save_structured_memory(
            CID,
            UID,
            {
                **fact,
                "supersedesExisting":
                    SF.supersedes_existing(fact),
            },
        )


def build_employer_history():
    repo = InMemoryCharacterRepository()

    save(repo, "I work at Tesco")
    save(repo, "I joined HSBC")
    save(repo, "I joined Barclays")

    return repo


def test_normal_retrieval_excludes_superseded_employers():
    repo = build_employer_history()

    memories = M.retrieve_temporal(
        repo,
        CID,
        UID,
        understanding("Where do I work?"),
        k=4,
    )

    values = [
        x.get("value")
        for x in memories
    ]

    assert "Barclays" in values
    assert "Tesco" not in values
    assert "HSBC" not in values


def test_previous_job_query_can_retrieve_history():
    repo = build_employer_history()

    memories = M.retrieve_temporal(
        repo,
        CID,
        UID,
        understanding("Where did I work before?"),
        k=4,
    )

    values = {
        x.get("value")
        for x in memories
    }

    assert "Barclays" in values
    assert (
        "HSBC" in values
        or "Tesco" in values
    )


def test_history_query_detected():
    assert M.wants_historical_memory(
        understanding("What was my previous job?")
    )

    assert M.wants_historical_memory(
        understanding("How has my career changed?")
    )

    assert not M.wants_historical_memory(
        understanding("Where do I work?")
    )


def test_superseded_employer_formats_as_previous():
    memory = {
        "predicate": "employment.current",
        "value": "Tesco",
        "status": "superseded",
        "text": "I work at Tesco",
    }

    rendered = M.format_memory_for_prompt(
        memory
    )

    assert rendered == "Previous employer: Tesco"


def test_active_employer_formats_as_current():
    memory = {
        "predicate": "employment.current",
        "value": "Barclays",
        "status": "active",
        "text": "I joined Barclays",
    }

    rendered = M.format_memory_for_prompt(
        memory
    )

    assert rendered == "Current employer: Barclays"


def test_location_temporal_history():
    repo = InMemoryCharacterRepository()

    save(repo, "I live in Manchester")
    save(repo, "I live in London")

    current = M.retrieve_temporal(
        repo,
        CID,
        UID,
        understanding("Where do I live?"),
        k=4,
    )

    current_values = {
        x.get("value")
        for x in current
    }

    assert "London" in current_values
    assert "Manchester" not in current_values

    historical = M.retrieve_temporal(
        repo,
        CID,
        UID,
        understanding("Where did I live before?"),
        k=4,
    )

    historical_values = {
        x.get("value")
        for x in historical
    }

    assert "London" in historical_values
    assert "Manchester" in historical_values


def test_historical_retrieval_does_not_change_status():
    repo = build_employer_history()

    M.retrieve_temporal(
        repo,
        CID,
        UID,
        understanding("Where did I work before?"),
        k=4,
    )

    all_memories = repo.list_memories(
        CID,
        UID,
    )

    statuses = {
        x["value"]: x.get("status")
        for x in all_memories
        if x.get("predicate") == "employment.current"
    }

    assert statuses["Tesco"] == "superseded"
    assert statuses["HSBC"] == "superseded"
    assert statuses["Barclays"] == "active"

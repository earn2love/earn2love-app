from ai_engine import belief_revision as BR
from ai_engine import structured_facts as SF
from ai_engine import memory as M
from ai_engine.repository import InMemoryCharacterRepository


CID = "belief-character"
UID = "belief-user"


def structured(text):
    return SF.extract_facts(text, {})


def save(repo, text):
    facts = structured(text)
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


def active_values(repo, predicate):
    return [
        m.get("value")
        for m in repo.list_memories(CID, UID)
        if (
            m.get("predicate") == predicate
            and m.get("status", "active") == "active"
        )
    ]


def test_detect_actual_correction():
    result = BR.detect_correction_intent(
        "Actually I work at HSBC"
    )

    assert result["isCorrection"]
    assert result["action"] == "correct"


def test_detect_forget():
    result = BR.detect_correction_intent(
        "Forget what I told you about that"
    )

    assert result["isCorrection"]
    assert result["action"] == "forget"


def test_detect_no_longer_work():
    result = BR.detect_correction_intent(
        "I no longer work at Tesco"
    )

    assert result["isCorrection"]
    assert result["action"] == "retract"


def test_retract_old_employer():
    repo = InMemoryCharacterRepository()

    save(repo, "I work at Tesco")

    existing = repo.list_memories(CID, UID)

    plan = BR.plan_revision(
        "I no longer work at Tesco",
        [],
        existing,
    )

    ids = [
        x["memoryId"]
        for x in plan["targets"]
    ]

    repo.revise_memories(
        CID,
        UID,
        ids,
        plan["action"],
        {"reason": plan["reason"]},
    )

    assert active_values(
        repo,
        "employment.current",
    ) == []

    old = repo.list_memories(CID, UID)[0]

    assert old["status"] == "retracted"


def test_actual_employer_replacement():
    repo = InMemoryCharacterRepository()

    save(repo, "I work at Barclays")

    text = "Actually I work at HSBC"

    plan = BR.plan_revision(
        text,
        structured(text),
        repo.list_memories(CID, UID),
    )

    ids = [
        x["memoryId"]
        for x in plan["targets"]
    ]

    repo.revise_memories(
        CID,
        UID,
        ids,
        plan["action"],
        {"reason": plan["reason"]},
    )

    for replacement in plan["replacementFacts"]:
        repo.save_structured_memory(
            CID,
            UID,
            replacement,
        )

    assert active_values(
        repo,
        "employment.current",
    ) == ["HSBC"]

    all_memories = repo.list_memories(CID, UID)

    barclays = next(
        x for x in all_memories
        if x.get("value") == "Barclays"
    )

    assert barclays["status"] == "corrected"


def test_move_back_replaces_location():
    repo = InMemoryCharacterRepository()

    save(repo, "I live in London")

    text = "I moved back to Manchester"

    plan = BR.plan_revision(
        text,
        structured(text),
        repo.list_memories(CID, UID),
    )

    ids = [
        x["memoryId"]
        for x in plan["targets"]
    ]

    repo.revise_memories(
        CID,
        UID,
        ids,
        plan["action"],
        {"reason": plan["reason"]},
    )

    for replacement in plan["replacementFacts"]:
        repo.save_structured_memory(
            CID,
            UID,
            replacement,
        )

    assert active_values(
        repo,
        "location.current",
    ) == ["Manchester"]


def test_call_me_replaces_identity():
    repo = InMemoryCharacterRepository()

    save(repo, "My name is Bala")

    text = "Don't call me Bala, call me Ram"

    plan = BR.plan_revision(
        text,
        [],
        repo.list_memories(CID, UID),
    )

    ids = [
        x["memoryId"]
        for x in plan["targets"]
    ]

    repo.revise_memories(
        CID,
        UID,
        ids,
        plan["action"],
        {"reason": plan["reason"]},
    )

    for replacement in plan["replacementFacts"]:
        repo.save_structured_memory(
            CID,
            UID,
            replacement,
        )

    assert active_values(
        repo,
        "identity.name",
    ) == ["Ram"]


def test_retracted_memory_not_used_in_normal_retrieval():
    repo = InMemoryCharacterRepository()

    save(repo, "I work at Tesco")

    memory = repo.list_memories(CID, UID)[0]

    repo.revise_memories(
        CID,
        UID,
        [memory["memoryId"]],
        "retract",
        {"reason": "employment_retraction"},
    )

    result = M.retrieve_temporal(
        repo,
        CID,
        UID,
        {
            "semanticQuery": "Where do I work?",
            "currentMessage": "Where do I work?",
            "topics": ["work"],
            "userReferencedPast": False,
        },
        k=4,
    )

    assert not any(
        x.get("value") == "Tesco"
        for x in result
    )


def test_revision_preserves_history():
    repo = InMemoryCharacterRepository()

    save(repo, "I work at Barclays")

    old = repo.list_memories(CID, UID)[0]

    repo.revise_memories(
        CID,
        UID,
        [old["memoryId"]],
        "correct",
        {"reason": "user_correction"},
    )

    memories = repo.list_memories(CID, UID)

    assert len(memories) == 1
    assert memories[0]["value"] == "Barclays"
    assert memories[0]["status"] == "corrected"
    assert memories[0].get("revisedAt")


def test_normal_statement_not_correction():
    result = BR.detect_correction_intent(
        "I work at HSBC"
    )

    assert result["isCorrection"] is False
    assert result["action"] == "none"

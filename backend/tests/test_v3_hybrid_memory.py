from ai_engine import memory as M


class FakeRepo:
    def __init__(self, memories):
        self.memories = memories

    def list_memories(self, cid, uid):
        return list(self.memories)


def understanding(message, topics=None, past=False):
    return {
        "semanticQuery": message,
        "topics": topics or [],
        "userReferencedPast": past,
    }


def test_semantic_job_memory_beats_food():
    repo = FakeRepo([
        {
            "memoryId": "job",
            "text": "I joined HSBC as a business analyst",
            "importance": 0.7,
            "type": "episodic",
            "status": "active",
        },
        {
            "memoryId": "food",
            "text": "My favourite food is biryani",
            "importance": 0.7,
            "type": "episodic",
            "status": "active",
        },
    ])

    result = M.retrieve(
        repo,
        "c1",
        "u1",
        understanding("How is your job going?"),
        k=2,
    )

    assert result
    assert result[0]["memoryId"] == "job"
    assert result[0]["_semanticScore"] > result[1]["_semanticScore"]


def test_location_paraphrase_retrieval():
    repo = FakeRepo([
        {
            "memoryId": "location",
            "text": "I moved to London last year",
            "importance": 0.6,
            "type": "episodic",
            "status": "active",
        },
        {
            "memoryId": "chess",
            "text": "I enjoy playing chess",
            "importance": 0.6,
            "type": "episodic",
            "status": "active",
        },
    ])

    result = M.retrieve(
        repo,
        "c1",
        "u1",
        understanding("Where are you living now?"),
        k=2,
    )

    assert result
    assert result[0]["memoryId"] == "location"


def test_superseded_fact_never_retrieved():
    repo = FakeRepo([
        {
            "memoryId": "old-job",
            "text": "I work at Tesco",
            "importance": 1.0,
            "explicitSave": True,
            "status": "superseded",
        },
        {
            "memoryId": "new-job",
            "text": "I joined HSBC",
            "importance": 0.7,
            "explicitSave": True,
            "status": "active",
        },
    ])

    result = M.retrieve(
        repo,
        "c1",
        "u1",
        understanding("Where do I work?", past=True),
        k=4,
    )

    ids = [x["memoryId"] for x in result]

    assert "old-job" not in ids
    assert "new-job" in ids


def test_v2_memory_without_status_still_active():
    repo = FakeRepo([
        {
            "memoryId": "legacy",
            "text": "I study artificial intelligence",
            "importance": 0.6,
            "type": "episodic",
        }
    ])

    result = M.retrieve(
        repo,
        "c1",
        "u1",
        understanding("How is university going?"),
    )

    assert any(x["memoryId"] == "legacy" for x in result)


def test_extract_adds_v3_metadata():
    result = M.maybe_extract(
        "Remember that my favourite food is biryani",
        {
            "topics": ["favourite", "food"],
            "seriousnessLevel": "medium",
        },
    )

    assert result is not None
    assert result["status"] == "active"
    assert result["confidence"] > 0
    assert result["source"] == "user_statement"

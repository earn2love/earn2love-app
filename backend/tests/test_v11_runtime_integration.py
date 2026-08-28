import asyncio
import copy
import types

from ai_engine.engine import CharacterEngine
from ai_engine.repository import InMemoryCharacterRepository


CHARACTER_ID = "global-ai-aisha"
USER_ID = "runtime-user"


def make_character():
    return {
        "characterId": CHARACTER_ID,
        "displayName": "Aisha",
        "name": "Aisha",
        "age": 26,
        "genderPresentation": "woman",
        "country": "United Kingdom",
        "profession": "AI companion",
        "communicationStyle": "warm, natural, direct when useful",
        "emojiStyle": "sparing",
        "enabled": True,
        "archived": False,

        "personalityTraits": [
            "warm",
            "playful",
            "curious",
            "witty",
        ],

        "personality": {
            "warmth": 0.88,
            "playfulness": 0.82,
            "curiosity": 0.85,
            "confidence": 0.75,
            "directness": 0.60,
            "humor": 0.72,
            "verbosity": 0.50,
            "formality": 0.18,
            "emojiUse": 0.28,
        },

        "warmthLevel": 0.88,
        "playfulnessLevel": 0.82,
        "curiosityLevel": 0.85,
        "confidenceLevel": 0.75,
        "directnessLevel": 0.60,

        "humorStyle": "light",
        "emojiFrequency": "sparing",

        "languages": [
            "en",
            "te",
        ],

        "defaultLanguage": "en",

        "city": "London",

        "worldFacts": [],

        "siblings": None,
        "onlyChild": None,
    }


def make_repo():
    repo = InMemoryCharacterRepository()

    repo.upsert_character(
        make_character()
    )

    return repo


def attach_fake_generation(
    engine,
    capture=None,
):
    async def fake_generate_guarded(
        self,
        sys,
        prompt,
        c,
        recent_ai,
        plan,
        session_id,
        routing,
        conversation_guidance=None,
        relationship_guidance=None,
        personality_fingerprint=None,
        adaptation_guidance=None,
        orchestration_guidance=None,
    ):
        if capture is not None:
            capture.append(
                {
                    "system": sys,
                    "prompt": prompt,
                    "sessionId": session_id,
                    "routing": dict(
                        routing
                        or {}
                    ),
                }
            )

        return (
            {
                "ok": True,
                "text": "Okay.",
                "provider": "runtime_stub",
                "model": "runtime_stub",
                "latencyMs": 1,
                "usage": {},
                "error": None,
            },
            {
                "passed": True,
                "fillerCount": 0,
            },
            1,
        )

    engine._generate_guarded = types.MethodType(
        fake_generate_guarded,
        engine,
    )


def run_response(
    engine,
    text,
    *,
    sandbox=False,
    conversation_id="runtime",
):
    return asyncio.run(
        engine.respond(
            CHARACTER_ID,
            USER_ID,
            text,
            sandbox=sandbox,
            conversation_id=conversation_id,
        )
    )


def preference_memories(
    repo,
    user_id=USER_ID,
):
    return [
        memory
        for memory in repo.list_memories(
            CHARACTER_ID,
            user_id,
        )
        if str(
            memory.get(
                "predicate",
                "",
            )
        ).startswith(
            "preference."
        )
    ]


def active_preference_memories(
    repo,
    user_id=USER_ID,
):
    return [
        memory
        for memory in preference_memories(
            repo,
            user_id,
        )
        if memory.get(
            "status",
            "active",
        )
        == "active"
    ]


def test_real_respond_sandbox_has_zero_persistent_mutation():
    repo = make_repo()

    engine = CharacterEngine(
        repo
    )

    attach_fake_generation(
        engine
    )

    before = copy.deepcopy(
        repo.__dict__
    )

    result = run_response(
        engine,
        "I like biryani",
        sandbox=True,
        conversation_id="sandbox-zero-write",
    )

    after = copy.deepcopy(
        repo.__dict__
    )

    assert result["ok"]

    assert (
        before
        == after
    )


def test_real_respond_production_stores_explicit_preference_once():
    repo = make_repo()

    engine = CharacterEngine(
        repo
    )

    attach_fake_generation(
        engine
    )

    result = run_response(
        engine,
        "I like biryani",
        sandbox=False,
        conversation_id="production-preference",
    )

    assert result["ok"]

    memories = active_preference_memories(
        repo
    )

    matching = [
        memory
        for memory in memories
        if (
            memory.get(
                "predicate"
            )
            == "preference.food"
            and str(
                memory.get(
                    "value",
                    "",
                )
            ).casefold()
            == "biryani"
            and memory.get(
                "polarity"
            )
            == "positive"
        )
    ]

    assert len(
        matching
    ) == 1


def test_real_respond_repeated_preference_reinforces_without_duplicate():
    repo = make_repo()

    engine = CharacterEngine(
        repo
    )

    attach_fake_generation(
        engine
    )

    first = run_response(
        engine,
        "I like biryani",
        sandbox=False,
        conversation_id="reinforce-1",
    )

    assert first["ok"]

    first_matching = [
        memory
        for memory in active_preference_memories(
            repo
        )
        if (
            memory.get(
                "predicate"
            )
            == "preference.food"
            and str(
                memory.get(
                    "value",
                    "",
                )
            ).casefold()
            == "biryani"
        )
    ]

    assert len(
        first_matching
    ) == 1

    memory_id = first_matching[0][
        "memoryId"
    ]

    first_count = first_matching[0].get(
        "reinforcementCount",
        0,
    )

    second = run_response(
        engine,
        "I like biryani",
        sandbox=False,
        conversation_id="reinforce-2",
    )

    assert second["ok"]

    second_matching = [
        memory
        for memory in active_preference_memories(
            repo
        )
        if (
            memory.get(
                "predicate"
            )
            == "preference.food"
            and str(
                memory.get(
                    "value",
                    "",
                )
            ).casefold()
            == "biryani"
        )
    ]

    assert len(
        second_matching
    ) == 1

    assert (
        second_matching[0][
            "memoryId"
        ]
        == memory_id
    )

    assert (
        second_matching[0].get(
            "reinforcementCount",
            0,
        )
        == first_count + 1
    )


def test_real_respond_v7_style_instruction_not_saved_as_v11_preference():
    repo = make_repo()

    engine = CharacterEngine(
        repo
    )

    attach_fake_generation(
        engine
    )

    result = run_response(
        engine,
        "Reply in Telugu",
        sandbox=False,
        conversation_id="v7-style",
    )

    assert result["ok"]

    assert (
        preference_memories(
            repo
        )
        == []
    )


def test_real_respond_user_character_memory_isolation():
    repo = make_repo()

    engine = CharacterEngine(
        repo
    )

    attach_fake_generation(
        engine
    )

    first = run_response(
        engine,
        "I like biryani",
        sandbox=False,
        conversation_id="isolation-user-a",
    )

    assert first["ok"]

    second_user = "runtime-user-b"

    second = asyncio.run(
        engine.respond(
            CHARACTER_ID,
            second_user,
            "I like coffee",
            sandbox=False,
            conversation_id="isolation-user-b",
        )
    )

    assert second["ok"]

    a = active_preference_memories(
        repo,
        USER_ID,
    )

    b = active_preference_memories(
        repo,
        second_user,
    )

    assert any(
        str(
            item.get(
                "value",
                "",
            )
        ).casefold()
        == "biryani"
        for item in a
    )

    assert not any(
        str(
            item.get(
                "value",
                "",
            )
        ).casefold()
        == "coffee"
        for item in a
    )

    assert any(
        str(
            item.get(
                "value",
                "",
            )
        ).casefold()
        == "coffee"
        for item in b
    )

    assert not any(
        str(
            item.get(
                "value",
                "",
            )
        ).casefold()
        == "biryani"
        for item in b
    )


def test_real_respond_v11_memory_filter_controls_prompt_and_metadata():
    repo = make_repo()

    repo.add_memory(
        CHARACTER_ID,
        USER_ID,
        {
            "memoryId": "job-current",
            "predicate": "employment.current",
            "canonicalKey": "employment.current",
            "value": "Barclays",
            "text": "I work at Barclays",
            "status": "active",
            "confidence": 0.95,
            "importance": 0.80,
            "topics": [
                "employment",
            ],
        },
    )

    repo.add_memory(
        CHARACTER_ID,
        USER_ID,
        {
            "memoryId": "food-pref",
            "predicate": "preference.food",
            "value": "biryani",
            "text": "I like biryani",
            "status": "active",
            "confidence": 0.95,
            "importance": 0.72,
            "topics": [
                "food",
            ],
        },
    )

    captured = []

    engine = CharacterEngine(
        repo
    )

    attach_fake_generation(
        engine,
        capture=captured,
    )

    result = run_response(
        engine,
        "Where do I work?",
        sandbox=True,
        conversation_id="retrieval-runtime",
    )

    assert result["ok"]

    assert len(
        captured
    ) == 1

    system_prompt = captured[0][
        "system"
    ]

    assert (
        "Barclays"
        in system_prompt
    )

    assert (
        "biryani"
        not in system_prompt.casefold()
    )

    assert (
        "job-current"
        in result[
            "memoryIdsUsed"
        ]
    )

    assert (
        "food-pref"
        not in result[
            "memoryIdsUsed"
        ]
    )


def test_real_respond_historical_retracted_memory_not_exposed_by_vague_before():
    repo = make_repo()

    repo.add_memory(
        CHARACTER_ID,
        USER_ID,
        {
            "memoryId": "old-job",
            "predicate": "employment.current",
            "canonicalKey": "employment.current",
            "value": "FakeCorp",
            "text": "I worked at FakeCorp",
            "status": "retracted",
            "confidence": 0.95,
            "importance": 0.80,
            "topics": [
                "employment",
            ],
        },
    )

    captured = []

    engine = CharacterEngine(
        repo
    )

    attach_fake_generation(
        engine,
        capture=captured,
    )

    result = run_response(
        engine,
        "What did I tell you before about FakeCorp?",
        sandbox=True,
        conversation_id="retracted-vague",
    )

    assert result["ok"]

    assert len(
        captured
    ) == 1

    assert (
        "FakeCorp"
        not in captured[0][
            "system"
        ]
    )

    assert (
        "old-job"
        not in result[
            "memoryIdsUsed"
        ]
    )


def test_real_respond_explicit_historical_recall_reaches_superseded_memory():
    repo = make_repo()

    repo.add_memory(
        CHARACTER_ID,
        USER_ID,
        {
            "memoryId": "job-old-barclays",
            "predicate": "employment.current",
            "canonicalKey": "employment.current",
            "value": "Barclays",
            "text": "I worked at Barclays",
            "status": "superseded",
            "confidence": 0.95,
            "importance": 0.80,
            "topics": [
                "employment",
            ],
        },
    )

    repo.add_memory(
        CHARACTER_ID,
        USER_ID,
        {
            "memoryId": "job-current-hsbc",
            "predicate": "employment.current",
            "canonicalKey": "employment.current",
            "value": "HSBC",
            "text": "I work at HSBC",
            "status": "active",
            "confidence": 0.95,
            "importance": 0.80,
            "topics": [
                "employment",
            ],
        },
    )

    captured = []

    engine = CharacterEngine(
        repo
    )

    attach_fake_generation(
        engine,
        capture=captured,
    )

    result = run_response(
        engine,
        "Where did I work before?",
        sandbox=True,
        conversation_id="historical-recall",
    )

    assert result["ok"]

    assert len(
        captured
    ) == 1

    assert (
        "Barclays"
        in captured[0][
            "system"
        ]
    )

    assert (
        "job-old-barclays"
        in result[
            "memoryIdsUsed"
        ]
    )


def test_real_respond_revision_history_can_reach_retracted_memory():
    repo = make_repo()

    repo.add_memory(
        CHARACTER_ID,
        USER_ID,
        {
            "memoryId": "wrong-employer",
            "predicate": "employment.current",
            "canonicalKey": "employment.current",
            "value": "WrongCorp",
            "text": "I work at WrongCorp",
            "status": "retracted",
            "confidence": 0.95,
            "importance": 0.80,
            "topics": [
                "employment",
            ],
        },
    )

    captured = []

    engine = CharacterEngine(
        repo
    )

    attach_fake_generation(
        engine,
        capture=captured,
    )

    result = run_response(
        engine,
        "What did I say was wrong before I corrected it?",
        sandbox=True,
        conversation_id="revision-history",
    )

    assert result["ok"]

    assert (
        "WrongCorp"
        in captured[0][
            "system"
        ]
    )

    assert (
        "wrong-employer"
        in result[
            "memoryIdsUsed"
        ]
    )


def test_real_respond_continuity_resume_reaches_generation_context():
    repo = make_repo()

    repo.append_turn(
        CHARACTER_ID,
        USER_ID,
        {
            "sender": "user",
            "text": (
                "We still need to fix the Firebase integration"
            ),
            "index": 1,
        },
        conversation_id="continuity-runtime",
    )

    repo.append_turn(
        CHARACTER_ID,
        USER_ID,
        {
            "sender": "character",
            "text": (
                "Yes, the Firebase integration is still pending."
            ),
            "index": 2,
        },
        conversation_id="continuity-runtime",
    )

    captured = []

    engine = CharacterEngine(
        repo
    )

    attach_fake_generation(
        engine,
        capture=captured,
    )

    result = run_response(
        engine,
        "Let's continue where we stopped",
        sandbox=True,
        conversation_id="continuity-runtime",
    )

    assert result["ok"]

    assert len(
        captured
    ) == 1

    system = captured[0][
        "system"
    ]

    assert (
        "V11_CONVERSATION_CONTINUITY"
        in system
    )

    assert (
        "Mode: resume"
        in system
    )

    assert (
        "Explicit resume: True"
        in system
    )


def test_real_respond_continuity_is_conversation_scoped():
    repo = make_repo()

    repo.append_turn(
        CHARACTER_ID,
        USER_ID,
        {
            "sender": "user",
            "text": "We still need to fix checkout",
            "index": 1,
        },
        conversation_id="conversation-a",
    )

    captured = []

    engine = CharacterEngine(
        repo
    )

    attach_fake_generation(
        engine,
        capture=captured,
    )

    result = run_response(
        engine,
        "Let's continue",
        sandbox=True,
        conversation_id="conversation-b",
    )

    assert result["ok"]

    assert (
        "checkout"
        not in captured[0][
            "system"
        ].casefold()
    )


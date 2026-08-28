import asyncio
import copy
import types

import pytest

from ai_engine.engine import CharacterEngine
from ai_engine.repository import InMemoryCharacterRepository
from ai_engine import live_knowledge_provider as LKP12


CHARACTER_ID = "v12-boundary-aisha"
USER_ID = "v12-boundary-user"


def make_character():
    return {
        "characterId": CHARACTER_ID,
        "displayName": "Aisha",
        "age": 25,
        "profession": "AI companion",
        "communicationStyle": (
            "warm, natural, direct when useful"
        ),
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


def attach_capture_generation(
    engine,
    captured,
    *,
    response_text="Test response.",
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
        captured.append(
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
                "text": response_text,
                "provider": "v12_boundary_stub",
                "model": "v12_boundary_stub",
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
    conversation_id,
):
    return asyncio.run(
        engine.respond(
            CHARACTER_ID,
            USER_ID,
            text,
            sandbox=True,
            conversation_id=conversation_id,
        )
    )


def test_static_knowledge_never_calls_live_retrieval(
    monkeypatch,
):
    repo = make_repo()

    engine = CharacterEngine(
        repo
    )

    captured = []

    attach_capture_generation(
        engine,
        captured,
        response_text=(
            "Photosynthesis is the process plants use "
            "to convert light energy into chemical energy."
        ),
    )

    calls = []

    async def forbidden_search_live(
        query,
        *args,
        **kwargs,
    ):
        calls.append(
            query
        )

        raise AssertionError(
            "Static knowledge must not invoke live retrieval"
        )

    monkeypatch.setattr(
        LKP12,
        "search_live",
        forbidden_search_live,
    )

    before = copy.deepcopy(
        repo.__dict__
    )

    result = run_response(
        engine,
        "What is photosynthesis?",
        conversation_id="v12-static-no-live",
    )

    after = copy.deepcopy(
        repo.__dict__
    )

    assert result["ok"] is True

    assert calls == []

    assert (
        result["freshness"][
            "requires_live_retrieval"
        ]
        is False
    )

    assert (
        result["freshness"][
            "classification"
        ]
        == "STABLE_KNOWLEDGE"
    )

    assert result["liveKnowledge"] == {
        "used": False,
        "status": None,
        "canAnswer": True,
        "confidence": None,
        "retrievedAt": None,
        "provider": None,
        "retrievalModel": None,
        "retrievalError": None,
        "sources": [],
    }

    assert len(
        captured
    ) == 1

    assert (
        "V12_LIVE_KNOWLEDGE_INTELLIGENCE"
        not in captured[0]["system"]
    )

    # Sandbox proof: this test cannot persist any state.
    assert before == after


def test_current_fact_retrieval_failure_injects_fail_safe_grounding(
    monkeypatch,
):
    repo = make_repo()

    engine = CharacterEngine(
        repo
    )

    captured = []

    attach_capture_generation(
        engine,
        captured,
        response_text=(
            "I can't verify the current Chief Minister "
            "of Tamil Nadu right now."
        ),
    )

    calls = []

    class FailedLiveSearch:
        ok = False
        results = ()
        provider = "openai-web-search"
        model = "gpt-5.6-luna"
        error = "simulated_live_retrieval_unavailable"

    async def failed_search_live(
        query,
        *args,
        **kwargs,
    ):
        calls.append(
            query
        )

        return FailedLiveSearch()

    monkeypatch.setattr(
        LKP12,
        "search_live",
        failed_search_live,
    )

    before = copy.deepcopy(
        repo.__dict__
    )

    result = run_response(
        engine,
        (
            "Who is the current Chief Minister "
            "of Tamil Nadu?"
        ),
        conversation_id="v12-current-fail-safe",
    )

    after = copy.deepcopy(
        repo.__dict__
    )

    assert result["ok"] is True

    assert calls == [
        (
            "Who is the current Chief Minister "
            "of Tamil Nadu?"
        )
    ]

    assert (
        result["freshness"][
            "requires_live_retrieval"
        ]
        is True
    )

    assert (
        result["freshness"][
            "classification"
        ]
        == "LIVE_REQUIRED"
    )

    live = result[
        "liveKnowledge"
    ]

    assert live["used"] is True
    assert live["status"] == "UNAVAILABLE"
    assert live["canAnswer"] is False

    assert (
        live["retrievalError"]
        == "simulated_live_retrieval_unavailable"
    )

    assert live["sources"] == []

    assert len(
        captured
    ) == 1

    system = captured[0][
        "system"
    ]

    assert (
        "V12_LIVE_KNOWLEDGE_INTELLIGENCE"
        in system
    )

    normalized = (
        " ".join(
            system.casefold().split()
        )
    )

    # These are the actual fail-safe semantics that must reach
    # the final conversational model.
    assert (
        "live knowledge status: unavailable"
        in normalized
    )

    assert (
        "do not guess"
        in normalized
    )

    assert (
        "stale model knowledge"
        in normalized
    )

    assert (
        "could not be verified"
        in normalized
        or
        "cannot be verified"
        in normalized
    )

    # The generated result used for this isolated engine test
    # must not pretend the stale fact was verified.
    response = result[
        "responseText"
    ].casefold()

    assert (
        "can't verify"
        in response
        or
        "cannot verify"
        in response
        or
        "could not verify"
        in response
    )

    # Sandbox proof: public retrieval/failure created no memory,
    # relationship, conversation, goal, plan, or adaptation write.
    assert before == after


def test_current_fact_retrieval_failure_exposes_no_sources(
    monkeypatch,
):
    repo = make_repo()

    engine = CharacterEngine(
        repo
    )

    captured = []

    attach_capture_generation(
        engine,
        captured,
        response_text=(
            "I can't verify that current information right now."
        ),
    )

    class FailedLiveSearch:
        ok = False
        results = ()
        provider = "openai-web-search"
        model = "gpt-5.6-luna"
        error = "network_unavailable"

    async def failed_search_live(
        query,
        *args,
        **kwargs,
    ):
        return FailedLiveSearch()

    monkeypatch.setattr(
        LKP12,
        "search_live",
        failed_search_live,
    )

    result = run_response(
        engine,
        "Who is the current UK Prime Minister?",
        conversation_id="v12-no-fake-sources",
    )

    assert result["ok"] is True

    live = result[
        "liveKnowledge"
    ]

    assert live["used"] is True
    assert live["status"] == "UNAVAILABLE"
    assert live["canAnswer"] is False
    assert live["sources"] == []
    assert live["confidence"] == 0.0

    assert (
        "network_unavailable"
        == live["retrievalError"]
    )


def test_live_public_fact_is_ephemeral_in_sandbox(
    monkeypatch,
):
    repo = make_repo()

    engine = CharacterEngine(
        repo
    )

    captured = []

    attach_capture_generation(
        engine,
        captured,
        response_text=(
            "The current answer is grounded in live sources."
        ),
    )

    class Evidence:
        def __init__(
            self,
            title,
            url,
            snippet,
        ):
            self.title = title
            self.url = url
            self.snippet = snippet
            self.source_domain = "gov.uk"
            self.retrieved_at = (
                "2026-08-28T12:00:00+00:00"
            )
            self.published_at = None
            self.authoritative = True
            self.score = 1.0

    class SuccessfulLiveSearch:
        ok = True
        results = (
            {
                "title": "Official current information",
                "url": "https://www.gov.uk/example",
                "snippet": (
                    "Official current information."
                ),
                "authoritative": True,
            },
        )
        provider = "openai-web-search"
        model = "gpt-5.6-luna"
        error = None

    async def successful_search_live(
        query,
        *args,
        **kwargs,
    ):
        return SuccessfulLiveSearch()

    monkeypatch.setattr(
        LKP12,
        "search_live",
        successful_search_live,
    )

    before = copy.deepcopy(
        repo.__dict__
    )

    result = run_response(
        engine,
        "Who is the current UK Prime Minister?",
        conversation_id="v12-public-ephemeral",
    )

    after = copy.deepcopy(
        repo.__dict__
    )

    assert result["ok"] is True
    assert result["liveKnowledge"]["used"] is True

    # Exact VERIFIED/PARTIAL status is owned by evidence scoring;
    # the boundary invariant here is that usable live evidence
    # reaches generation without becoming persistent user state.
    assert (
        result["liveKnowledge"]["canAnswer"]
        is True
    )

    assert len(
        captured
    ) == 1

    assert (
        "V12_LIVE_KNOWLEDGE_INTELLIGENCE"
        in captured[0]["system"]
    )

    assert before == after


def test_v12_unavailable_live_result_cannot_leak_stale_model_answer(
    monkeypatch,
):
    """
    Even if the conversational model produces a stale current-fact
    answer, CharacterEngine must replace it when V12 live evidence
    is unavailable.
    """
    repo = make_repo()

    engine = CharacterEngine(
        repo
    )

    captured = []

    stale_model_answer = (
        "The current Chief Minister of Tamil Nadu is M.K. Stalin."
    )

    attach_capture_generation(
        engine,
        captured,
        response_text=stale_model_answer,
    )

    calls = []

    class FailedLiveSearch:
        ok = False
        results = ()
        provider = "openai-web-search"
        model = "gpt-5.6-luna"
        error = "simulated_live_retrieval_unavailable"

    async def failed_search_live(
        query,
        *args,
        **kwargs,
    ):
        calls.append(
            query
        )

        return FailedLiveSearch()

    monkeypatch.setattr(
        LKP12,
        "search_live",
        failed_search_live,
    )

    result = run_response(
        engine,
        (
            "Who is the current Chief Minister "
            "of Tamil Nadu?"
        ),
        conversation_id="v12-hard-fail-closed",
    )

    assert result["ok"] is True

    assert calls == [
        (
            "Who is the current Chief Minister "
            "of Tamil Nadu?"
        )
    ]

    assert (
        result["freshness"][
            "requires_live_retrieval"
        ]
        is True
    )

    assert (
        result["liveKnowledge"][
            "used"
        ]
        is True
    )

    assert (
        result["liveKnowledge"][
            "canAnswer"
        ]
        is False
    )

    assert (
        result["liveKnowledge"][
            "status"
        ]
        == "UNAVAILABLE"
    )

    assert (
        result["responseText"]
        ==
        (
            "I can't verify the current information right now, "
            "so I don't want to guess."
        )
    )

    assert (
        stale_model_answer
        not in result["responseText"]
    )

    assert (
        "Stalin"
        not in result["responseText"]
    )


def test_v12_verified_live_result_is_not_overridden(
    monkeypatch,
):
    """
    Verified/answerable live knowledge must continue through the
    existing generation path without triggering the fail-closed
    replacement.
    """
    repo = make_repo()

    engine = CharacterEngine(
        repo
    )

    captured = []

    verified_answer = (
        "The current Chief Minister of Tamil Nadu "
        "is C. Joseph Vijay."
    )

    attach_capture_generation(
        engine,
        captured,
        response_text=verified_answer,
    )

    class SuccessfulLiveSearch:
        ok = True
        provider = "openai-web-search"
        model = "gpt-5.6-luna"
        error = None

        results = (
            {
                "title": "Lok Bhavan Tamil Nadu",
                "url": "https://lokbhavan.tn.gov.in/",
                "snippet": (
                    "Current Chief Minister information "
                    "from Lok Bhavan Tamil Nadu."
                ),
                "authoritative": True,
            },
        )

    async def successful_search_live(
        query,
        *args,
        **kwargs,
    ):
        return SuccessfulLiveSearch()

    monkeypatch.setattr(
        LKP12,
        "search_live",
        successful_search_live,
    )

    result = run_response(
        engine,
        (
            "Who is the current Chief Minister "
            "of Tamil Nadu?"
        ),
        conversation_id="v12-verified-not-overridden",
    )

    assert result["ok"] is True

    assert (
        result["liveKnowledge"][
            "canAnswer"
        ]
        is True
    )

    assert (
        result["responseText"]
        ==
        verified_answer
    )


def test_v12_static_answer_is_not_overridden_by_fail_closed_guard(
    monkeypatch,
):
    """
    Stable knowledge never uses the V12 fail-closed replacement.
    """
    repo = make_repo()

    engine = CharacterEngine(
        repo
    )

    captured = []

    normal_answer = (
        "Photosynthesis converts light energy "
        "into chemical energy."
    )

    attach_capture_generation(
        engine,
        captured,
        response_text=normal_answer,
    )

    async def forbidden_search_live(
        query,
        *args,
        **kwargs,
    ):
        raise AssertionError(
            "Static knowledge must not invoke live retrieval"
        )

    monkeypatch.setattr(
        LKP12,
        "search_live",
        forbidden_search_live,
    )

    result = run_response(
        engine,
        "What is photosynthesis?",
        conversation_id="v12-static-failclosed-bypass",
    )

    assert result["ok"] is True

    assert (
        result["freshness"][
            "requires_live_retrieval"
        ]
        is False
    )

    assert (
        result["liveKnowledge"][
            "used"
        ]
        is False
    )

    assert (
        result["responseText"]
        ==
        normal_answer
    )

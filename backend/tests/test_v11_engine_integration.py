import ast
from pathlib import Path

from ai_engine import engine
from ai_engine import preference_learning_intelligence as PL11
from ai_engine import memory_integrity_intelligence as MI11
from ai_engine.repository import InMemoryCharacterRepository


ENGINE_PATH = Path(
    "backend/ai_engine/engine.py"
)


def _source():
    return ENGINE_PATH.read_text(
        encoding="utf-8-sig"
    )


def _respond_source():
    source = _source()
    tree = ast.parse(
        source
    )

    respond = next(
        node
        for node in ast.walk(
            tree
        )
        if (
            isinstance(
                node,
                ast.AsyncFunctionDef,
            )
            and node.name == "respond"
        )
    )

    return ast.get_source_segment(
        source,
        respond,
    )


def test_v11_engine_marker():
    assert (
        engine.V11_ENGINE_MARKER
        == "V11_LONG_TERM_MEMORY_CONTINUITY_INTELLIGENCE"
    )


def test_v11_retrieval_extends_v3_before_v10():
    source = _respond_source()

    v3 = source.index(
        "M.retrieve_temporal"
    )

    v11 = source.index(
        "MR11.select_memories"
    )

    v10 = source.index(
        "CX10.select_memories",
        v11,
    )

    assert (
        v3
        < v11
        < v10
    )


def test_prompt_uses_final_selected_memories():
    source = _respond_source()

    prompt = source.index(
        "sys = build_system_prompt"
    )

    segment = source[
        prompt:
        prompt + 260
    ]

    assert (
        "selected_mems"
        in segment
    )

    assert (
        "\n            mems,\n"
        not in segment
    )


def test_v11_preference_write_inside_sandbox_gate():
    source = _respond_source()

    sandbox = source.index(
        "if not sandbox:"
    )

    preference = source.index(
        "PL11.analyze_preference"
    )

    reinforcement = source.index(
        "self.repo.reinforce_memory"
    )

    assert sandbox < preference
    assert sandbox < reinforcement


def test_v7_owned_style_preference_is_not_memory_persisted():
    signal = PL11.analyze_preference(
        "Reply in Telugu"
    )

    assert signal.detected
    assert signal.owner == "adaptation_v7"
    assert not signal.should_persist


def test_explicit_new_preference_accepts():
    signal = PL11.analyze_preference(
        "I like biryani"
    )

    candidate = PL11.build_memory_candidate(
        signal
    )

    scoped = {
        **candidate,
        "characterId": "c1",
        "userId": "u1",
        "status": "active",
    }

    decision = MI11.assess_integrity(
        [],
        scoped,
        user_id="u1",
        character_id="c1",
    )

    assert decision.allowed
    assert decision.action == "accept"


def test_explicit_same_preference_reinforces():
    existing = [
        {
            "memoryId": "food",
            "characterId": "c1",
            "userId": "u1",
            "predicate": "preference.food",
            "value": "biryani",
            "normalizedValue": "biryani",
            "polarity": "positive",
            "reinforcementKey":
                "preference:food:positive:biryani",
            "status": "active",
        }
    ]

    signal = PL11.analyze_preference(
        "I like biryani"
    )

    candidate = {
        **PL11.build_memory_candidate(
            signal
        ),
        "characterId": "c1",
        "userId": "u1",
        "status": "active",
    }

    decision = MI11.assess_integrity(
        existing,
        candidate,
        user_id="u1",
        character_id="c1",
    )

    assert decision.allowed
    assert decision.action == "reinforce"
    assert (
        decision.reinforcement_memory_id
        == "food"
    )


def test_repository_reinforcement_accumulates():
    repo = InMemoryCharacterRepository()

    memory = repo.add_memory(
        "c1",
        "u1",
        {
            "predicate": "preference.food",
            "value": "biryani",
            "normalizedValue": "biryani",
            "polarity": "positive",
            "reinforcementKey":
                "preference:food:positive:biryani",
            "status": "active",
        },
    )

    first = repo.reinforce_memory(
        "c1",
        "u1",
        memory["memoryId"],
    )

    first_count = first[
        "reinforcementCount"
    ]

    second = repo.reinforce_memory(
        "c1",
        "u1",
        memory["memoryId"],
    )

    assert first_count == 1

    assert (
        second["reinforcementCount"]
        == 2
    )


def test_conflicting_memory_defers_to_revision():
    existing = [
        {
            "memoryId": "job",
            "characterId": "c1",
            "userId": "u1",
            "predicate": "employment.current",
            "value": "Barclays",
            "status": "active",
        }
    ]

    candidate = {
        "characterId": "c1",
        "userId": "u1",
        "predicate": "employment.current",
        "value": "HSBC",
        "status": "active",
    }

    decision = MI11.assess_integrity(
        existing,
        candidate,
        user_id="u1",
        character_id="c1",
    )

    assert not decision.allowed
    assert decision.defer_to_belief_revision
    assert decision.action == "defer_revision"


def test_legacy_preference_fallback_is_preserved():
    source = _respond_source()

    assert (
        "PREF.plan_preference_updates"
        in source
    )

    assert (
        "if not v11_preference_handled"
        in source
    )


def test_v11_does_not_replace_belief_revision():
    source = _respond_source()

    assert (
        "BR.plan_revision"
        in source
    )

    assert (
        "self.repo.revise_memories"
        in source
    )


def test_v11_does_not_own_provider_or_router():
    source = _source()

    imports = [
        line
        for line in source.splitlines()
        if (
            "memory_retrieval_intelligence"
            in line
            or "preference_learning_intelligence"
            in line
            or "memory_integrity_intelligence"
            in line
        )
    ]

    assert imports

    for line in imports:
        assert "provider" not in line.casefold()
        assert "router" not in line.casefold()


def test_memory_metadata_uses_prompt_memories():
    source = _respond_source()

    assert (
        '"memoryIdsUsed": '
        '[m.get("memoryId") '
        'for m in selected_mems]'
        in source
    )

    assert (
        "for m in selected_mems"
        in source[
            source.index(
                '"memoryLayersUsed"'
            ):
            source.index(
                '"characterFactIdsUsed"'
            )
        ]
    )

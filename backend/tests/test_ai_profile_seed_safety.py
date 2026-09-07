from copy import deepcopy

from ai_engine.repository import (
    InMemoryCharacterRepository,
)
from ai_profiles.production_catalog import (
    PRODUCTION_AI_PROFILES,
)
from ai_profiles.seed_production_profiles import (
    build_plan,
    execute_seed,
    load_prepared_profiles,
    prepare_profile,
)


def test_loads_12_profiles():
    prepared = load_prepared_profiles()

    assert len(prepared) == 12


def test_all_profiles_forced_draft_hidden():
    for profile in load_prepared_profiles():
        assert (
            profile["profileStatus"]
            == "draft"
        )

        assert (
            profile["visibility"]
            == "hidden"
        )


def test_all_profiles_explicit_ai():
    for profile in load_prepared_profiles():
        assert profile["isAi"] is True
        assert (
            profile["aiDisclosure"]
            is True
        )


def test_prepare_profile_does_not_mutate_source():
    source = deepcopy(
        PRODUCTION_AI_PROFILES[0]
    )

    before = deepcopy(source)

    prepare_profile(source)

    assert source == before


def test_dry_run_creates_zero_records():
    repo = (
        InMemoryCharacterRepository()
    )

    results = execute_seed(
        repo,
        write=False,
    )

    assert len(
        repo.list_characters()
    ) == 0

    assert all(
        r["status"]
        == "would_create"
        for r in results
    )


def test_write_creates_12_records():
    repo = (
        InMemoryCharacterRepository()
    )

    results = execute_seed(
        repo,
        write=True,
    )

    assert len(
        repo.list_characters()
    ) == 12

    assert all(
        r["status"]
        == "created"
        for r in results
    )


def test_existing_profile_skipped_by_default():
    repo = (
        InMemoryCharacterRepository()
    )

    first = prepare_profile(
        PRODUCTION_AI_PROFILES[0]
    )

    repo.upsert_character(
        {
            **first,
            "displayName":
                "DO NOT OVERWRITE",
        }
    )

    execute_seed(
        repo,
        write=True,
    )

    stored = repo.get_character(
        first["characterId"]
    )

    assert (
        stored["displayName"]
        == "DO NOT OVERWRITE"
    )


def test_existing_profile_can_only_overwrite_explicitly():
    repo = (
        InMemoryCharacterRepository()
    )

    first = prepare_profile(
        PRODUCTION_AI_PROFILES[0]
    )

    repo.upsert_character(
        {
            **first,
            "displayName":
                "OLD PROFILE",
        }
    )

    results = execute_seed(
        repo,
        write=True,
        allow_overwrite=True,
    )

    stored = repo.get_character(
        first["characterId"]
    )

    assert (
        stored["displayName"]
        == first["displayName"]
    )

    matching = [
        r
        for r in results
        if r["characterId"]
        == first["characterId"]
    ][0]

    assert (
        matching["status"]
        == "overwritten"
    )


def test_allow_overwrite_without_write_does_not_write():
    repo = (
        InMemoryCharacterRepository()
    )

    first = prepare_profile(
        PRODUCTION_AI_PROFILES[0]
    )

    repo.upsert_character(
        {
            **first,
            "displayName":
                "KEEP ME",
        }
    )

    execute_seed(
        repo,
        write=False,
        allow_overwrite=True,
    )

    stored = repo.get_character(
        first["characterId"]
    )

    assert (
        stored["displayName"]
        == "KEEP ME"
    )


def test_plan_reports_create_for_empty_repo():
    repo = (
        InMemoryCharacterRepository()
    )

    plan = build_plan(repo)

    assert len(plan) == 12

    assert all(
        p["action"] == "create"
        for p in plan
    )


def test_plan_reports_existing():
    repo = (
        InMemoryCharacterRepository()
    )

    first = prepare_profile(
        PRODUCTION_AI_PROFILES[0]
    )

    repo.upsert_character(first)

    plan = build_plan(repo)

    matching = [
        p
        for p in plan
        if p["characterId"]
        == first["characterId"]
    ][0]

    assert (
        matching["action"]
        == "skip_existing"
    )


def test_write_never_publishes_profiles():
    repo = (
        InMemoryCharacterRepository()
    )

    execute_seed(
        repo,
        write=True,
    )

    for profile in (
        repo.list_characters()
    ):
        assert (
            profile["profileStatus"]
            == "draft"
        )

        assert (
            profile["visibility"]
            == "hidden"
        )


def test_write_never_creates_reference_ids():
    repo = (
        InMemoryCharacterRepository()
    )

    execute_seed(
        repo,
        write=True,
    )

    for profile in (
        repo.list_characters()
    ):
        assert not profile[
            "characterId"
        ].startswith("ref_")


def test_seed_preserves_12_unique_ids():
    prepared = (
        load_prepared_profiles()
    )

    ids = [
        p["characterId"]
        for p in prepared
    ]

    assert len(ids) == len(set(ids))

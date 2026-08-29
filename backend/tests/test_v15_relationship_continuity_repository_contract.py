from pathlib import Path


REPOSITORY = Path(
    "backend/ai_engine/repository.py"
).read_text(
    encoding="utf-8-sig"
)

RELATIONSHIP = Path(
    "backend/ai_engine/relationship_intelligence.py"
).read_text(
    encoding="utf-8-sig"
)


def test_existing_firestore_relationship_collection_is_reused():
    assert (
        '"aiCharacterRelationshipState"'
        in REPOSITORY
    )

    assert (
        "aiCharacterRelationshipContinuity"
        not in REPOSITORY
    )


def test_firestore_relationship_advance_remains_transactional():
    start = REPOSITORY.index(
        "def advance_relationship(",
        REPOSITORY.index(
            "class FirestoreCharacterRepository"
        ),
    )

    section = REPOSITORY[
        start:
        start + 5000
    ]

    assert "@firestore.transactional" in section
    assert "RI.evolve(" in section
    assert "transaction.set(" in section


def test_v15_3_does_not_add_repository_write_path():
    assert (
        "advance_relationship_continuity"
        not in REPOSITORY
    )

    assert (
        "set_relationship_continuity"
        not in REPOSITORY
    )


def test_relationship_module_is_provider_free():
    assert "AsyncOpenAI(" not in RELATIONSHIP
    assert "PROV.generate(" not in RELATIONSHIP


def test_relationship_module_is_firestore_free():
    assert ".collection(" not in RELATIONSHIP
    assert "firestore." not in RELATIONSHIP


def test_v5_relationship_version_preserved_in_source():
    assert (
        '"relationshipVersion": 5'
        in RELATIONSHIP
    )

    assert (
        'result["relationshipVersion"] = 5'
        in RELATIONSHIP
    )


def test_v15_3_continuity_version_is_additive():
    assert (
        '"relationshipContinuityVersion": "15.3"'
        in RELATIONSHIP
    )

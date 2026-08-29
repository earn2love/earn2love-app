from pathlib import Path

import ai_service


def test_v14_reuses_existing_conversation_collection():
    source = Path(
        "backend/ai_service.py"
    ).read_text(
        encoding="utf-8-sig"
    )

    marker = source.index(
        "# V14 IMAGE REQUEST IDEMPOTENCY"
    )

    section = source[
        marker:
        source.index(
            "\ndef _chat_lock(",
            marker,
        )
    ]

    assert (
        '"aiCharacterConversations"'
        in section
    )

    assert (
        "aiImageRequests"
        not in section
    )

    assert (
        "imageRequestCollection"
        not in section
    )


def test_begin_is_transactional():
    source = Path(
        "backend/ai_service.py"
    ).read_text(
        encoding="utf-8-sig"
    )

    assert (
        "def begin_image_request("
        in source
    )

    assert (
        "@firestore.transactional"
        in source
    )

    assert (
        '"status":\n                            "pending"'
        in source
        or
        '"status":\n                        "pending"'
        in source
    )


def test_complete_rejects_signed_url_persistence():
    source = Path(
        "backend/ai_service.py"
    ).read_text(
        encoding="utf-8-sig"
    )

    assert (
        '"signed_url_must_not_persist"'
        in source
    )

    assert (
        'if "url" in result:'
        in source
    )


def test_abort_only_clears_exact_pending_request():
    source = Path(
        "backend/ai_service.py"
    ).read_text(
        encoding="utf-8-sig"
    )

    start = source.index(
        "def abort_image_request("
    )

    end = source.index(
        "\ndef _chat_lock(",
        start,
    )

    section = source[
        start:end
    ]

    assert (
        '"clientRequestId"'
        in section
    )

    assert (
        '"requestFingerprint"'
        in section
    )

    assert (
        '"operation"'
        in section
    )

    assert (
        '"pending"'
        in section
    )

    assert (
        '"v14ImageRequest":\n                    None'
        in section
    )


def test_stale_lease_recovery_exists():
    source = Path(
        "backend/ai_service.py"
    ).read_text(
        encoding="utf-8-sig"
    )

    assert (
        "lease_seconds"
        in source
    )

    assert (
        "active_pending"
        in source
    )

    assert (
        '"reclaimed": True'
        in source
    )

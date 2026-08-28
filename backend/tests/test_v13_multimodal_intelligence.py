import pytest

from ai_engine import multimodal_intelligence as MM13


def image_url(
    image_id="img-1",
    url="https://cdn.example.com/a.jpg",
    **extra,
):
    value = {
        "imageId": image_id,
        "url": url,
    }

    value.update(
        extra
    )

    return value


def test_version_is_13():
    assert (
        MM13.MULTIMODAL_VERSION
        == 13
    )


def test_empty_image_list_is_valid():
    context = MM13.build_turn_context(
        "character-a",
        "user-a",
        "conversation-a",
        "hello",
        [],
    )

    assert context.ok is True
    assert context.has_images is False
    assert context.image_count == 0


def test_https_image_normalizes():
    context = MM13.build_turn_context(
        "character-a",
        "user-a",
        "conversation-a",
        "what is here?",
        [
            image_url()
        ],
    )

    assert context.ok is True
    assert context.image_count == 1

    image = context.images[0]

    assert image.image_id == "img-1"
    assert image.source_type == "url"
    assert image.detail == "auto"


def test_provider_payload_uses_input_image():
    context = MM13.build_turn_context(
        "character-a",
        "user-a",
        "conversation-a",
        "look",
        [
            image_url(
                detail="high"
            )
        ],
    )

    assert context.provider_images() == [
        {
            "type": "input_image",
            "detail": "high",
            "image_url":
                "https://cdn.example.com/a.jpg",
        }
    ]


def test_provider_file_id_supported():
    context = MM13.build_turn_context(
        "character-a",
        "user-a",
        "conversation-a",
        "look",
        [
            {
                "imageId": "img-file",
                "fileId": "file-abc123",
                "detail": "low",
            }
        ],
    )

    assert context.ok is True

    assert context.provider_images() == [
        {
            "type": "input_image",
            "detail": "low",
            "file_id": "file-abc123",
        }
    ]


@pytest.mark.parametrize(
    "url",
    [
        "http://example.com/a.jpg",
        "ftp://example.com/a.jpg",
        "data:image/jpeg;base64,AAAA",
        "/relative/a.jpg",
        "",
    ],
)
def test_non_https_sources_rejected(
    url,
):
    context = MM13.build_turn_context(
        "character-a",
        "user-a",
        "conversation-a",
        "look",
        [
            image_url(
                url=url
            )
        ],
    )

    assert context.ok is False


def test_url_credentials_rejected():
    context = MM13.build_turn_context(
        "character-a",
        "user-a",
        "conversation-a",
        "look",
        [
            image_url(
                url=(
                    "https://user:pass@"
                    "example.com/a.jpg"
                )
            )
        ],
    )

    assert context.ok is False
    assert (
        context.error
        == "image_url_credentials_forbidden"
    )


def test_exactly_one_source_required():
    context = MM13.build_turn_context(
        "character-a",
        "user-a",
        "conversation-a",
        "look",
        [
            {
                "imageId": "img-1",
                "url":
                    "https://example.com/a.jpg",
                "fileId": "file-abc",
            }
        ],
    )

    assert context.ok is False

    assert (
        context.error
        == "multiple_image_sources_forbidden"
    )


def test_missing_source_rejected():
    context = MM13.build_turn_context(
        "character-a",
        "user-a",
        "conversation-a",
        "look",
        [
            {
                "imageId": "img-1",
            }
        ],
    )

    assert context.ok is False
    assert (
        context.error
        == "image_source_required"
    )


def test_duplicate_image_ids_rejected():
    context = MM13.build_turn_context(
        "character-a",
        "user-a",
        "conversation-a",
        "look",
        [
            image_url(
                image_id="same",
                url="https://example.com/1.jpg",
            ),
            image_url(
                image_id="same",
                url="https://example.com/2.jpg",
            ),
        ],
    )

    assert context.ok is False
    assert context.error == "duplicate_image_id"


def test_max_four_images():
    context = MM13.build_turn_context(
        "character-a",
        "user-a",
        "conversation-a",
        "look",
        [
            image_url(
                image_id=f"img-{i}",
                url=f"https://example.com/{i}.jpg",
            )
            for i in range(
                5
            )
        ],
    )

    assert context.ok is False
    assert context.error == "too_many_images"


@pytest.mark.parametrize(
    "detail",
    [
        "auto",
        "low",
        "high",
    ],
)
def test_supported_details(
    detail,
):
    context = MM13.build_turn_context(
        "c",
        "u",
        "conversation",
        "look",
        [
            image_url(
                detail=detail
            )
        ],
    )

    assert context.ok is True


def test_invalid_detail_rejected():
    context = MM13.build_turn_context(
        "c",
        "u",
        "conversation",
        "look",
        [
            image_url(
                detail="ultra"
            )
        ],
    )

    assert context.ok is False
    assert (
        context.error
        == "invalid_image_detail"
    )


@pytest.mark.parametrize(
    "mime",
    [
        "image/jpeg",
        "image/jpg",
        "image/png",
        "image/webp",
        "image/gif",
    ],
)
def test_supported_mime_types(
    mime,
):
    context = MM13.build_turn_context(
        "c",
        "u",
        "conversation",
        "look",
        [
            image_url(
                mimeType=mime
            )
        ],
    )

    assert context.ok is True


def test_unsupported_mime_rejected():
    context = MM13.build_turn_context(
        "c",
        "u",
        "conversation",
        "look",
        [
            image_url(
                mimeType="image/svg+xml"
            )
        ],
    )

    assert context.ok is False

    assert (
        context.error
        == "unsupported_image_mime_type"
    )


def test_scope_changes_between_users():
    a = MM13.build_scope_token(
        "character",
        "user-a",
        "conversation",
    )

    b = MM13.build_scope_token(
        "character",
        "user-b",
        "conversation",
    )

    assert a != b


def test_scope_changes_between_conversations():
    a = MM13.build_scope_token(
        "character",
        "user",
        "conversation-a",
    )

    b = MM13.build_scope_token(
        "character",
        "user",
        "conversation-b",
    )

    assert a != b


def test_scope_changes_between_characters():
    a = MM13.build_scope_token(
        "character-a",
        "user",
        "conversation",
    )

    b = MM13.build_scope_token(
        "character-b",
        "user",
        "conversation",
    )

    assert a != b


def test_scope_is_deterministic():
    a = MM13.build_scope_token(
        "character",
        "user",
        "conversation",
    )

    b = MM13.build_scope_token(
        "character",
        "user",
        "conversation",
    )

    assert a == b


def test_safe_dict_does_not_expose_url():
    context = MM13.build_turn_context(
        "character",
        "user",
        "conversation",
        "look",
        [
            image_url(
                url=(
                    "https://example.com/"
                    "private-signed-image.jpg"
                )
            )
        ],
    )

    data = context.to_dict()

    serialized = str(
        data
    )

    assert (
        "private-signed-image"
        not in serialized
    )

    assert (
        "https://"
        not in serialized
    )


def test_memory_policy_is_ephemeral():
    policy = (
        MM13.multimodal_memory_policy()
    )

    assert (
        policy["persistImageBytes"]
        is False
    )

    assert (
        policy["persistVisualAnalysis"]
        is False
    )

    assert (
        policy["ephemeralContextOnly"]
        is True
    )


def test_directive_forbids_fabricated_visual_detail():
    context = MM13.build_turn_context(
        "character",
        "user",
        "conversation",
        "look",
        [
            image_url()
        ],
    )

    directive = (
        MM13.build_multimodal_directive(
            context
        )
    ).casefold()

    assert "actually supported" in directive
    assert "instead of inventing" in directive


def test_invalid_input_never_claims_image_seen():
    context = MM13.build_turn_context(
        "character",
        "user",
        "conversation",
        "look",
        [
            {
                "imageId": "bad",
            }
        ],
    )

    directive = (
        MM13.build_multimodal_directive(
            context
        )
    ).casefold()

    assert context.ok is False
    assert "do not claim" in directive


def test_module_has_no_firestore_write_surface():
    from pathlib import Path

    source = Path(
        "backend/ai_engine/"
        "multimodal_intelligence.py"
    ).read_text(
        encoding="utf-8"
    )

    forbidden = [
        ".collection(",
        "firestore.client",
        "firebase_admin",
        "add_memory(",
        "save_structured_memory(",
        "append_turn(",
    ]

    for marker in forbidden:
        assert marker not in source

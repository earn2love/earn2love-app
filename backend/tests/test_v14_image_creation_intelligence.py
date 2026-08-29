import pytest

from ai_engine import image_creation_intelligence as V14


def test_creation_request_defaults():
    request = V14.ImageCreationRequest.from_input(
        prompt="  create   a moonlit lake  ",
    )

    assert request.prompt == "create a moonlit lake"
    assert request.size == "1024x1024"
    assert request.quality == "medium"
    assert request.background == "auto"


@pytest.mark.parametrize(
    "value",
    [
        "",
        "   ",
        None,
        123,
    ],
)
def test_creation_prompt_fail_closed(value):
    with pytest.raises(ValueError):
        V14.ImageCreationRequest.from_input(
            prompt=value,
        )


def test_creation_prompt_is_bounded():
    with pytest.raises(
        ValueError,
        match="image_prompt_too_long",
    ):
        V14.ImageCreationRequest.from_input(
            prompt="x" * (
                V14.MAX_IMAGE_PROMPT_LENGTH + 1
            ),
        )


@pytest.mark.parametrize(
    "size",
    sorted(V14.SUPPORTED_IMAGE_SIZES),
)
def test_supported_sizes(size):
    request = V14.ImageCreationRequest.from_input(
        prompt="test",
        size=size,
    )

    assert request.size == size


def test_invalid_size_fails_closed():
    with pytest.raises(
        ValueError,
        match="invalid_image_size",
    ):
        V14.ImageCreationRequest.from_input(
            prompt="test",
            size="999x999",
        )


def test_edit_requires_source_image():
    with pytest.raises(
        ValueError,
        match="source_image_required",
    ):
        V14.ImageEditRequest.from_input(
            instruction="make it brighter",
            source_image_ids=[],
        )


def test_edit_preserves_opaque_image_id_case():
    request = V14.ImageEditRequest.from_input(
        instruction="make it brighter",
        source_image_ids=[
            "AbC123-XyZ",
        ],
    )

    assert request.source_image_ids == (
        "AbC123-XyZ",
    )


def test_edit_rejects_duplicate_source_ids():
    with pytest.raises(
        ValueError,
        match="duplicate_source_image_id",
    ):
        V14.ImageEditRequest.from_input(
            instruction="change background",
            source_image_ids=[
                "ImageABC",
                "ImageABC",
            ],
        )


def test_edit_source_count_bounded():
    with pytest.raises(
        ValueError,
        match="too_many_source_images",
    ):
        V14.ImageEditRequest.from_input(
            instruction="edit",
            source_image_ids=[
                "1",
                "2",
                "3",
                "4",
                "5",
            ],
        )


def test_result_normalization():
    result = V14.normalize_creation_result(
        {
            "imageBytes": b"abc",
            "mimeType": "image/png",
            "revisedPrompt": " revised ",
        }
    )

    assert result["imageBytes"] == b"abc"
    assert result["mimeType"] == "image/png"
    assert result["revisedPrompt"] == "revised"


def test_result_requires_bytes():
    with pytest.raises(
        ValueError,
        match="missing_generated_image",
    ):
        V14.normalize_creation_result(
            {
                "imageBytes": b"",
                "mimeType": "image/png",
            }
        )


def test_policy_is_backend_authoritative():
    policy = V14.image_creation_policy()

    assert policy["version"] == "V14"
    assert policy["providerBoundary"] == "provider.py"
    assert policy["persistentUserMemory"] is False
    assert policy["providerResultPersistence"] is False
    assert policy["privateTemporaryStorage"] is True
    assert policy["billingAuthority"] == "backend_only"
    assert policy["sourceImageIdsOpaque"] is True

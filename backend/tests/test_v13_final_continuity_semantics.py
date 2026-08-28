from ai_engine import multimodal_intelligence as MM13


def test_explicit_image_followups_are_detected():
    values = [
        "same image lo left side enti?",
        "ee photo lo background enti?",
        "previous picture lo person evaru?",
        "that screenshot lo text enti?",
        "can you check the same image again?",
        "this photo clear ga undha?",
        "uploaded image lo em undi?",
    ]

    for value in values:
        assert (
            MM13.is_image_followup_reference(
                value
            )
            is True
        ), value


def test_generic_language_does_not_activate_image_continuity():
    values = [
        "enti?",
        "background lo enti?",
        "left side",
        "right side",
        "background",
        "same thing",
        "that is nice",
        "what do you think?",
        "continue",
        "what?",
        "adi enti?",
    ]

    for value in values:
        assert (
            MM13.is_image_followup_reference(
                value
            )
            is False
        ), value


def test_opaque_image_ids_preserve_exact_value():
    image_id = (
        "AbCdEf0123456789AbCdEf0123456789.png"
    )

    turns = [
        {
            "sender": "user",
            "text": "image",
            "imageIds": [
                image_id
            ],
        }
    ]

    assert MM13.extract_turn_image_ids(
        turns
    ) == [
        image_id
    ]


def test_latest_scoped_user_media_turn_behavior_remains():
    old_id = (
        "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa.png"
    )

    new_id = (
        "BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB.png"
    )

    turns = [
        {
            "sender": "user",
            "text": "old",
            "imageIds": [
                old_id
            ],
        },
        {
            "sender": "character",
            "text": "reply",
        },
        {
            "sender": "user",
            "text": "new",
            "imageIds": [
                new_id
            ],
        },
    ]

    assert MM13.extract_turn_image_ids(
        turns
    ) == [
        new_id
    ]

from ai_engine import personality_engine as PE


def character_a():
    return {
        "characterId": "global-aisha",
        "personalityTraits": [
            "warm",
            "playful",
            "curious",
            "witty",
        ],
        "personality": {
            "warmth": 0.85,
            "playfulness": 0.80,
            "curiosity": 0.88,
            "directness": 0.55,
            "verbosity": 0.45,
            "emojiUse": 0.25,
        },
    }


def character_b():
    return {
        "characterId": "global-meera",
        "personalityTraits": [
            "calm",
            "reserved",
            "direct",
        ],
        "personality": {
            "warmth": 0.48,
            "playfulness": 0.20,
            "curiosity": 0.45,
            "directness": 0.82,
            "verbosity": 0.25,
            "emojiUse": 0.03,
            "formality": 0.65,
        },
    }


def test_same_character_produces_same_fingerprint():
    a = PE.build_fingerprint(
        character_a()
    )

    b = PE.build_fingerprint(
        character_a()
    )

    assert (
        a.identity_signature
        ==
        b.identity_signature
    )

    assert a.dimensions == b.dimensions


def test_fingerprint_is_global_not_user_specific():
    c = character_a()

    first = PE.build_fingerprint(
        c
    )

    second = PE.build_fingerprint(
        c
    )

    assert PE.same_identity(
        first,
        second,
    )


def test_different_characters_have_different_signatures():
    a = PE.build_fingerprint(
        character_a()
    )

    b = PE.build_fingerprint(
        character_b()
    )

    assert (
        a.identity_signature
        !=
        b.identity_signature
    )


def test_different_characters_have_personality_distance():
    a = PE.build_fingerprint(
        character_a()
    )

    b = PE.build_fingerprint(
        character_b()
    )

    distance = PE.personality_distance(
        a,
        b,
    )

    assert distance > 0.10


def test_explicit_dimensions_override_trait_defaults():
    character = {
        "characterId": "test",
        "personalityTraits": [
            "playful",
        ],
        "personality": {
            "playfulness": 0.10,
        },
    }

    dimensions = PE.resolve_dimensions(
        character
    )

    assert (
        dimensions["playfulness"]
        ==
        0.10
    )


def test_dimensions_are_clamped():
    character = {
        "characterId": "test",
        "personality": {
            "warmth": 9,
            "directness": -4,
        },
    }

    dimensions = PE.resolve_dimensions(
        character
    )

    assert dimensions["warmth"] == 1.0
    assert dimensions["directness"] == 0.0


def test_playful_character_gets_humour_style():
    fingerprint = PE.build_fingerprint(
        character_a()
    )

    assert fingerprint.humor_style in {
        "frequent_natural",
        "occasional_witty",
    }


def test_reserved_character_not_forced_playful():
    fingerprint = PE.build_fingerprint(
        character_b()
    )

    assert (
        fingerprint.teasing_style
        ==
        "none_or_rare"
    )


def test_direct_character_gets_direct_disagreement():
    fingerprint = PE.build_fingerprint(
        character_b()
    )

    assert fingerprint.disagreement_style in {
        "direct",
        "clear_but_warm",
    }


def test_low_verbosity_character_is_short():
    fingerprint = PE.build_fingerprint(
        character_b()
    )

    assert (
        fingerprint.response_length
        ==
        "short"
    )


def test_guidance_contains_identity_stability_rule():
    guidance = PE.build_guidance(
        character_a()
    )

    text = guidance.directive

    assert (
        "Keep this personality stable across users and conversations."
        in text
    )

    assert (
        "must not replace the core global character identity"
        in text
    )


def test_guidance_does_not_mutate_character():
    c = character_a()
    before = {
        **c,
        "personalityTraits": list(
            c["personalityTraits"]
        ),
        "personality": dict(
            c["personality"]
        ),
    }

    PE.build_guidance(
        c
    )

    assert c == before


def test_signature_changes_when_core_personality_changes():
    c1 = character_a()
    c2 = character_a()

    c2["personality"] = dict(
        c2["personality"]
    )

    c2["personality"]["warmth"] = 0.20

    a = PE.build_fingerprint(
        c1
    )

    b = PE.build_fingerprint(
        c2
    )

    assert (
        a.identity_signature
        !=
        b.identity_signature
    )


def test_signature_does_not_depend_on_dict_order():
    first = {
        "characterId": "same",
        "personality": {
            "warmth": 0.8,
            "curiosity": 0.7,
        },
    }

    second = {
        "personality": {
            "curiosity": 0.7,
            "warmth": 0.8,
        },
        "characterId": "same",
    }

    a = PE.build_fingerprint(
        first
    )

    b = PE.build_fingerprint(
        second
    )

    assert (
        a.identity_signature
        ==
        b.identity_signature
    )


def test_missing_character_id_rejected():
    try:
        PE.build_fingerprint(
            {
                "personalityTraits": [
                    "warm",
                ]
            }
        )
    except ValueError:
        return

    raise AssertionError(
        "Missing characterId must fail"
    )


def test_formal_character_rejects_bruh_language():
    character = {
        "characterId": "formal-ai",
        "personality": {
            "formality": 0.90,
        },
    }

    fp = PE.build_fingerprint(
        character
    )

    ok, reason = PE.output_personality_check(
        "Bruh lol that is wild.",
        fp,
    )

    assert ok is False
    assert reason == "formality_drift"


def test_formal_character_accepts_normal_language():
    character = {
        "characterId": "formal-ai",
        "personality": {
            "formality": 0.90,
        },
    }

    fp = PE.build_fingerprint(
        character
    )

    ok, reason = PE.output_personality_check(
        "That is an interesting point. I would approach it carefully.",
        fp,
    )

    assert ok is True
    assert reason == "ok"


def test_low_emoji_character_rejects_extreme_emoji_drift():
    character = {
        "characterId": "minimal-emoji",
        "personality": {
            "emojiUse": 0.05,
        },
    }

    fp = PE.build_fingerprint(
        character
    )

    ok, reason = PE.output_personality_check(
        "Nice 😂😂😂😂",
        fp,
    )

    assert ok is False
    assert reason == "excessive_emoji_for_character"


def test_low_emoji_character_allows_one_emoji():
    character = {
        "characterId": "minimal-emoji",
        "personality": {
            "emojiUse": 0.05,
        },
    }

    fp = PE.build_fingerprint(
        character
    )

    ok, reason = PE.output_personality_check(
        "That actually worked 😄",
        fp,
    )

    assert ok is True
    assert reason == "ok"


def test_global_personality_does_not_contain_user_id():
    fp = PE.build_fingerprint(
        character_a()
    )

    result = fp.to_dict()

    assert "userId" not in result
    assert "user_id" not in result


def test_personality_version_is_v6():
    fp = PE.build_fingerprint(
        character_a()
    )

    assert fp.version == 6

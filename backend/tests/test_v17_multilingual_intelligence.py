"""
Earn2Love AI Engine V17.3

Multilingual intelligence hardening.

No new language system is introduced here. These tests verify the existing
V4/V6/V7 language, personality and adaptation architecture remains stable
across language switching and per-user language preferences.
"""

from copy import deepcopy

from ai_engine import understanding as U
from ai_engine import language_style as L
from ai_engine import conversation_intelligence as CI
from ai_engine import adaptive_intelligence as AI
from ai_engine import personality_engine as PE


V17_3_MULTILINGUAL_INTELLIGENCE = True

CHARACTER_ID = "global-ananya"

CHARACTER = {
    "characterId": CHARACTER_ID,
    "languages": [
        "English",
        "Telugu",
        "Hindi",
    ],
    "personalityTraits": [
        "warm",
        "playful",
        "curious",
        "witty",
    ],
}

EXPECTED_PERSONALITY_SIGNATURE = (
    "940f14aaa62a1faaa4e58abc"
)


def _fingerprint():
    return PE.build_fingerprint(
        CHARACTER
    )


def _resolve(text):
    understanding = U.analyze(
        text,
        [],
    )

    style = L.resolve(
        understanding,
        CHARACTER,
    )

    return understanding, style


def test_v17_detects_english_telugu_hindi_and_code_mixed_inputs():
    cases = [
        (
            "How are you today?",
            "english",
        ),
        (
            "ఏం చేస్తున్నావు?",
            "telugu",
        ),
        (
            "क्या कर रहे हो अभी?",
            "hindi",
        ),
        (
            "em chestunnav?",
            "telugu-english",
        ),
        (
            "kya kar rahe ho abhi?",
            "hindi-english",
        ),
    ]

    for text, expected in cases:
        understanding, _ = _resolve(
            text
        )

        assert (
            understanding["languageCode"]
            == expected
        )


def test_v17_supported_character_follows_current_language():
    cases = [
        (
            "Hello, how are you?",
            "English",
        ),
        (
            "ఏం చేస్తున్నావు?",
            "Telugu",
        ),
        (
            "क्या कर रहे हो अभी?",
            "Hindi",
        ),
        (
            "em chestunnav?",
            "Telugu-English",
        ),
        (
            "kya kar rahe ho abhi?",
            "Hindi-English",
        ),
    ]

    for text, expected_fragment in cases:
        _, style = _resolve(
            text
        )

        assert (
            expected_fragment.casefold()
            in style[
                "responseLanguage"
            ].casefold()
        )


def test_v17_unsupported_language_falls_back_without_mutating_character():
    english_only = {
        "characterId": "english-only",
        "languages": [
            "English",
        ],
        "personalityTraits": [
            "warm",
            "curious",
        ],
    }

    original = deepcopy(
        english_only
    )

    understanding = U.analyze(
        "ఏం చేస్తున్నావు?",
        [],
    )

    style = L.resolve(
        understanding,
        english_only,
    )

    assert (
        style["responseLanguage"]
        .casefold()
        .startswith("english")
    )

    assert english_only == original


def test_v17_repeated_language_switching_never_mutates_personality():
    original = deepcopy(
        CHARACTER
    )

    baseline = _fingerprint()

    assert (
        baseline.identity_signature
        == EXPECTED_PERSONALITY_SIGNATURE
    )

    messages = [
        "Hello, how are you?",
        "em chestunnav?",
        "ఏం చేస్తున్నావు?",
        "kya kar rahe ho abhi?",
        "क्या कर रहे हो अभी?",
    ]

    for turn in range(5000):
        text = messages[
            turn % len(messages)
        ]

        understanding, style = _resolve(
            text
        )

        assert understanding[
            "languageCode"
        ]

        assert style[
            "responseLanguage"
        ]

        if turn % 100 == 0:
            current = _fingerprint()

            assert (
                current.identity_signature
                == baseline.identity_signature
            )

    final = _fingerprint()

    assert (
        final.identity_signature
        == baseline.identity_signature
        == EXPECTED_PERSONALITY_SIGNATURE
    )

    assert CHARACTER == original


def test_v17_explicit_language_preferences_remain_user_scoped():
    user_telugu = AI.default_user_adaptation(
        CHARACTER_ID,
        "language-user-telugu",
    )

    user_english = AI.default_user_adaptation(
        CHARACTER_ID,
        "language-user-english",
    )

    for _ in range(100):
        user_telugu = (
            AI.evolve_user_adaptation(
                user_telugu,
                CHARACTER_ID,
                "language-user-telugu",
                "Use Telugu and English",
            )
        )

        user_english = (
            AI.evolve_user_adaptation(
                user_english,
                CHARACTER_ID,
                "language-user-english",
                "English only please",
            )
        )

    assert (
        user_telugu["languagePreference"]




        == "telugu_english"
    )

    assert (
        user_english["languagePreference"]




        == "english"
    )

    assert (
        user_telugu["userId"]
        == "language-user-telugu"
    )

    assert (
        user_english["userId"]
        == "language-user-english"
    )

    assert user_telugu != user_english


def test_v17_same_user_language_preference_remains_character_scoped():
    second_character = (
        "global-second-character"
    )

    first = AI.default_user_adaptation(
        CHARACTER_ID,
        "same-language-user",
    )

    second = AI.default_user_adaptation(
        second_character,
        "same-language-user",
    )

    for _ in range(50):
        first = AI.evolve_user_adaptation(
            first,
            CHARACTER_ID,
            "same-language-user",
            "Use Telugu and English",
        )

        second = AI.evolve_user_adaptation(
            second,
            second_character,
            "same-language-user",
            "English only please",
        )

    assert (
        first["characterId"]
        == CHARACTER_ID
    )

    assert (
        second["characterId"]
        == second_character
    )

    assert (
        first["languagePreference"]


        == "telugu_english"
    )

    assert (
        second["languagePreference"]


        == "english"
    )


def test_v17_current_language_switch_beats_old_script_continuity():
    history = [
        {
            "role": "user",
            "text": "ఏం చేస్తున్నావు?",
        },
        {
            "role": "assistant",
            "text": "Just chatting.",
        },
    ]

    guidance = CI.multilingual_guidance(
        "How are you today?",
        history,
        {
            "languageCode": "english",
        },
    )

    lowered = guidance.casefold()

    assert (
        "changed writing script"
        in lowered
        or "follow the current message"
        in lowered
        or "match the person's conversational language"
        in lowered
    )


def test_v17_code_switch_guidance_never_forces_language_demonstration():
    guidance = CI.multilingual_guidance(
        "em chestunnav?",
        [],
        {
            "languageCode":
                "telugu-english",
        },
    )

    lowered = guidance.casefold()

    assert (
        "do not switch languages merely"
        in lowered
    )

    assert (
        "code-switch"
        in lowered
    )


def test_v17_language_activity_cannot_change_global_personality_signature():
    baseline = _fingerprint()

    states = {}

    for user_index in range(100):
        user_id = (
            f"multilingual-user-{user_index:03d}"
        )

        state = AI.default_user_adaptation(
            CHARACTER_ID,
            user_id,
        )

        preference = (
            "Use Telugu and English"
            if user_index % 2 == 0
            else "English only please"
        )

        for _ in range(20):
            state = (
                AI.evolve_user_adaptation(
                    state,
                    CHARACTER_ID,
                    user_id,
                    preference,
                )
            )

        states[user_id] = state

    assert len(states) == 100

    after = _fingerprint()

    assert (
        after.identity_signature
        == baseline.identity_signature
        == EXPECTED_PERSONALITY_SIGNATURE
    )


def test_v17_multilingual_marker():
    assert (
        V17_3_MULTILINGUAL_INTELLIGENCE
        is True
    )




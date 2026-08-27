from ai_engine import emotional_intelligence as EI
from ai_engine.engine import (
    _emotion_context,
    _last_user_text,
    _persist_emotional_event,
    build_system_prompt,
)
from ai_engine.repository import InMemoryCharacterRepository


CID = "emotion-character"
UID = "emotion-user"


def test_last_user_message_skips_character_turn():
    history = [
        {"sender": "user", "text": "I'm nervous."},
        {"sender": "character", "text": "You'll be okay."},
    ]

    assert _last_user_text(history) == "I'm nervous."


def test_no_previous_user_message():
    history = [
        {"sender": "character", "text": "Hey"},
    ]

    assert _last_user_text(history) is None


def test_emotion_context_detects_current_emotion():
    emotional = _emotion_context(
        "I'm extremely nervous!",
        [],
    )

    assert emotional["current"]["primaryEmotion"] == "anxiety"
    assert emotional["current"]["intensity"] > 0.5
    assert emotional["trajectory"] == "new"


def test_emotion_context_detects_intensifying_trajectory():
    history = [
        {
            "sender": "user",
            "text": "I'm a little nervous.",
        },
        {
            "sender": "character",
            "text": "Makes sense.",
        },
    ]

    emotional = _emotion_context(
        "I'm extremely nervous!!!",
        history,
    )

    assert emotional["trajectory"] == "intensifying"


def test_emotion_context_detects_settling():
    history = [
        {
            "sender": "user",
            "text": "I'm really angry!",
        },
        {
            "sender": "character",
            "text": "Yeah, that sounds frustrating.",
        },
    ]

    emotional = _emotion_context(
        "Anyway, what movie should I watch?",
        history,
    )

    assert emotional["trajectory"] == "settling"


def test_ordinary_mood_is_not_persisted():
    repo = InMemoryCharacterRepository()

    emotional = _emotion_context(
        "I'm a little annoyed.",
        [],
    )

    result = _persist_emotional_event(
        repo,
        CID,
        UID,
        "I'm a little annoyed.",
        emotional,
    )

    assert result is None
    assert repo.list_memories(CID, UID) == []


def test_meaningful_emotional_event_is_persisted():
    repo = InMemoryCharacterRepository()

    text = "I'm so excited, I got the job!"

    emotional = _emotion_context(
        text,
        [],
    )

    stored = _persist_emotional_event(
        repo,
        CID,
        UID,
        text,
        emotional,
    )

    assert stored is not None
    assert stored["predicate"] == "emotional.event"
    assert stored["emotion"] == "joy"

    memories = repo.list_memories(
        CID,
        UID,
    )

    assert len(memories) == 1


def test_same_emotional_event_is_not_duplicated():
    repo = InMemoryCharacterRepository()

    text = "I'm so excited, I got the job!"

    emotional = _emotion_context(
        text,
        [],
    )

    _persist_emotional_event(
        repo,
        CID,
        UID,
        text,
        emotional,
    )

    _persist_emotional_event(
        repo,
        CID,
        UID,
        text,
        emotional,
    )

    memories = repo.list_memories(
        CID,
        UID,
    )

    assert len(memories) == 1


def test_system_prompt_contains_emotional_guidance():
    character = {
        "displayName": "Ananya",
        "age": 25,
        "genderPresentation": "female",
        "city": "Hyderabad",
        "country": "India",
        "profession": "Designer",
        "languages": ["English", "Telugu"],
        "personalityTraits": ["warm", "playful"],
        "communicationStyle": "warm and conversational",
        "humorStyle": "playful",
        "emojiStyle": "sparing",
        "worldFacts": [],
        "playfulnessLevel": 0.8,
        "directnessLevel": 0.5,
        "warmthLevel": 0.8,
        "confidenceLevel": 0.7,
        "curiosityLevel": 0.8,
    }

    plan = {
        "responseType": "empathetic",
        "tone": "warm",
        "targetLength": "short",
        "askQuestion": False,
        "referenceMemory": False,
        "humor": "low",
        "acknowledgeEmotion": True,
        "challenge": False,
    }

    rel = {
        "state": "acquaintance",
    }

    lang = {
        "instruction": "Reply in English.",
    }

    guidance = (
        "Current user emotion: sadness; intensity 0.66; "
        "response energy: gentle; humor: low"
    )

    prompt = build_system_prompt(
        character,
        plan,
        [],
        rel,
        lang,
        {},
        "",
        emotional_guidance=guidance,
    )

    assert "EMOTIONAL CONTEXT:" in prompt
    assert "Current user emotion: sadness" in prompt
    assert "response energy: gentle" in prompt
    assert "Do not diagnose mental-health conditions" in prompt


def test_neutral_guidance_does_not_manufacture_emotion():
    emotional = _emotion_context(
        "What film should I watch?",
        [],
    )

    assert emotional["current"]["primaryEmotion"] == "neutral"
    assert "without manufacturing emotion" in emotional["guidance"]

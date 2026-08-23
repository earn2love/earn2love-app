"""Conversation planner — compact, deterministic response plan.

Decides purpose, tone, length, whether to ask a question / reference memory / use
humor / challenge, and which character traits to express. Kept server-side; never
exposed to the user.
"""


def _length(understanding, character):
    if understanding.get("replyShouldBeShort"):
        return "very_short"
    if understanding.get("conversationalMode") == "greeting":
        return "very_short"
    pref = character.get("replyLengthPreference", "short")
    order = ["very_short", "short", "medium", "long"]
    # On serious topics, allow a bit more room — but keep direct/concise characters crisp.
    if understanding.get("seriousnessLevel") == "high":
        direct = character.get("directnessLevel", 0.5) >= 0.75
        bump = 0 if direct else 1
        return order[min(order.index(pref) + bump, order.index("medium"))]
    return pref


def _tone(understanding, character):
    if understanding.get("userIsVenting"):
        return "warm_supportive"
    if understanding.get("userIsJoking") and character.get("playfulnessLevel", 0.5) >= 0.4:
        return "playful"
    if understanding.get("seriousnessLevel") == "high":
        return "thoughtful"
    if character.get("playfulnessLevel", 0.5) >= 0.7:
        return "playful"
    if character.get("warmthLevel", 0.5) >= 0.7:
        return "warm"
    if character.get("directnessLevel", 0.5) >= 0.7:
        return "direct"
    return "friendly"


def plan(understanding, character, relationship_state, memories, language_style):
    length = _length(understanding, character)
    serious = understanding.get("seriousnessLevel") == "high"
    ask_q = False
    if not understanding.get("replyShouldBeShort"):
        # ask when it adds value AND fits the character's curiosity — never every message
        ask_q = understanding.get("followUpQuestionUseful") and character.get("curiosityLevel", 0.5) >= 0.4
    humor = "none"
    if character.get("humorStyle") and character.get("playfulnessLevel", 0.5) >= 0.5 and not understanding.get("userIsVenting") and not serious:
        humor = character.get("humorStyle", "light")
    challenge = (character.get("directnessLevel", 0.5) >= 0.7 and understanding.get("userNeedsAdvice"))
    return {
        "responseType": "support" if understanding.get("userIsVenting") else ("advice" if understanding.get("userNeedsAdvice") else ("banter" if understanding.get("userIsJoking") else "casual_reply")),
        "tone": _tone(understanding, character),
        "targetLength": length,
        "askQuestion": bool(ask_q),
        "referenceMemory": bool(memories),
        "humor": humor,
        "acknowledgeEmotion": bool(understanding.get("userIsVenting") or understanding.get("emotionalTone") == "distressed"),
        "challenge": bool(challenge),
        "languageStyle": language_style["responseLanguage"],
        "expressTraits": character.get("personalityTraits", [])[:3],
        "relationship": relationship_state.get("state"),
        "avoid": ["generic assistant wording", "repeating the user's message", "long explanation for a casual message",
                  "ending with a question every time", "excessive emojis", "overusing the user's name"],
    }


LENGTH_HINT = {
    "very_short": "1 short sentence or a few words. No preamble.",
    "short": "1–2 sentences, natural and easy.",
    "medium": "2–4 sentences; enough to reason, not an essay.",
    "long": "A fuller reply, but still conversational — never a lecture.",
}

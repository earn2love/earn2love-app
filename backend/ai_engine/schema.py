"""Structured, queryable, auditable character identity + world model schema.

A character is NOT an unstructured prompt blob. Every trait/fact is a field so it
can be queried, edited in the admin panel, version-controlled, and validated for
consistency.
"""
from datetime import datetime, timezone

# Levels are 0.0–1.0 knobs that change HOW intelligence is expressed (never reduce it).
LEVEL_FIELDS = ["curiosityLevel", "confidenceLevel", "warmthLevel",
                "playfulnessLevel", "directnessLevel", "romanceLevel"]

# Immutable identity facts — must never be contradicted across a character's life.
PROTECTED_FACT_FIELDS = ["displayName", "age", "country", "city", "profession",
                         "genderPresentation", "siblings", "onlyChild"]

REQUIRED_FIELDS = ["characterId", "displayName", "isAi", "age", "country",
                   "profession", "languages", "personalityTraits"]

REPLY_LENGTHS = ["very_short", "short", "medium", "long"]
RELATIONSHIP_STATES = ["new", "familiar", "comfortable", "established"]


def _now():
    return datetime.now(timezone.utc).isoformat()


def new_character(**o):
    """Create a character identity with sane defaults; override any field."""
    c = {
        "characterId": o.get("characterId"),
        "displayName": o.get("displayName", ""),
        "isAi": True,                                  # ALWAYS true — AI transparency
        "genderPresentation": o.get("genderPresentation", "unspecified"),
        "age": o.get("age", 25),                       # 18+ enforced in validation
        "country": o.get("country", ""),
        "city": o.get("city", ""),
        "profession": o.get("profession", ""),
        "background": o.get("background", ""),
        "languages": o.get("languages", ["English"]),
        "interests": o.get("interests", []),
        "hobbies": o.get("hobbies", []),
        "expertiseAreas": o.get("expertiseAreas", []),
        "weakKnowledgeAreas": o.get("weakKnowledgeAreas", []),
        "personalityTraits": o.get("personalityTraits", []),
        "communicationStyle": o.get("communicationStyle", ""),
        "humorStyle": o.get("humorStyle", "light"),
        "emojiStyle": o.get("emojiStyle", "sparing"),   # none|sparing|frequent
        "replyLengthPreference": o.get("replyLengthPreference", "short"),
        "curiosityLevel": o.get("curiosityLevel", 0.5),
        "confidenceLevel": o.get("confidenceLevel", 0.5),
        "warmthLevel": o.get("warmthLevel", 0.5),
        "playfulnessLevel": o.get("playfulnessLevel", 0.5),
        "directnessLevel": o.get("directnessLevel", 0.5),
        "romanceLevel": o.get("romanceLevel", 0.1),
        "boundaries": o.get("boundaries", []),
        "likes": o.get("likes", []),
        "dislikes": o.get("dislikes", []),
        "values": o.get("values", []),
        "conversationalHabits": o.get("conversationalHabits", []),
        "recurringLifeFacts": o.get("recurringLifeFacts", []),
        "backstoryFacts": o.get("backstoryFacts", []),
        "worldFacts": o.get("worldFacts", []),          # list of {factId, key, value, immutable}
        "opinions": o.get("opinions", []),
        "tabooTopics": o.get("tabooTopics", []),
        "profileBio": o.get("profileBio", ""),
        "greetingStyle": o.get("greetingStyle", ""),
        "siblings": o.get("siblings"),                  # protected immutable fact
        "onlyChild": o.get("onlyChild"),                # protected immutable fact
        "enabled": o.get("enabled", True),
        "archived": o.get("archived", False),
        "tierAccess": o.get("tierAccess", ["casual", "friendship", "love"]),
        "version": o.get("version", 1),
        "createdAt": o.get("createdAt", _now()),
        "updatedAt": _now(),
    }
    return c


def validate_character(c):
    errs = []
    for f in REQUIRED_FIELDS:
        if c.get(f) in (None, "", []):
            errs.append(f"missing required field: {f}")
    if not c.get("isAi", False):
        errs.append("isAi must be true (AI transparency is non-negotiable)")
    if (c.get("age") or 0) < 18:
        errs.append("age must be 18+")
    for lf in LEVEL_FIELDS:
        v = c.get(lf)
        if v is not None and not (0.0 <= float(v) <= 1.0):
            errs.append(f"{lf} must be between 0 and 1")
    if c.get("replyLengthPreference") not in REPLY_LENGTHS:
        errs.append("invalid replyLengthPreference")
    return (len(errs) == 0, errs)


def protected_facts(c):
    """The immutable facts that must never be contradicted."""
    out = {}
    for f in PROTECTED_FACT_FIELDS:
        if c.get(f) not in (None, ""):
            out[f] = c[f]
    for wf in c.get("worldFacts", []):
        if wf.get("immutable"):
            out[wf["key"]] = wf["value"]
    return out

"""
Earn2Love AI Engine V3.3
Belief Revision & User Correction Intelligence

Responsibilities:
- detect explicit user corrections
- detect retractions
- detect replacements
- detect "not X, Y" corrections
- detect outdated facts
- detect forget requests
- assign user-authority confidence
- target canonical structured facts
- preserve history rather than destructively deleting facts
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional


CORRECTION_PREFIX = re.compile(
    r"^\s*(?:"
    r"actually|"
    r"no[,\s]+|"
    r"nope[,\s]+|"
    r"correction[,:]?\s*|"
    r"that's wrong[,.]?\s*|"
    r"that is wrong[,.]?\s*|"
    r"you(?:'re| are) wrong[,.]?\s*|"
    r"you misunderstood(?: me)?[,.]?\s*|"
    r"i meant\s+|"
    r"what i meant was\s+"
    r")",
    re.I,
)


OUTDATED = re.compile(
    r"\b(?:"
    r"not anymore|"
    r"no longer|"
    r"that's outdated|"
    r"that is outdated|"
    r"used to|"
    r"changed since then"
    r")\b",
    re.I,
)


FORGET = re.compile(
    r"\b(?:"
    r"forget (?:that|what i (?:said|told you)|about that)|"
    r"don't remember that|"
    r"do not remember that|"
    r"delete that from (?:your )?memory|"
    r"remove that from (?:your )?memory"
    r")\b",
    re.I,
)


NOT_X_BUT_Y = re.compile(
    r"\bnot\s+(.{1,80}?)\s*(?:,|but)\s+(.{1,100})$",
    re.I,
)


CALL_ME = re.compile(
    r"\b(?:"
    r"don't call me\s+(.{1,40}?)\s*[,.]\s*call me\s+(.{1,40})|"
    r"do not call me\s+(.{1,40}?)\s*[,.]\s*call me\s+(.{1,40})"
    r")$",
    re.I,
)


MOVED_BACK = re.compile(
    r"\bi moved back to\s+([A-Za-z][A-Za-z .'-]{1,60})",
    re.I,
)


NO_LONGER_LIVE = re.compile(
    r"\bi\s+(?:don't|do not|no longer)\s+live\s+in\s+"
    r"([A-Za-z][A-Za-z .'-]{1,60})",
    re.I,
)


NO_LONGER_WORK = re.compile(
    r"\bi\s+(?:don't|do not|no longer)\s+work\s+(?:at|for)\s+"
    r"([A-Za-z0-9&.' -]{2,70})",
    re.I,
)


NO_LONGER_LIKE = re.compile(
    r"\bi\s+(?:don't|do not|no longer)\s+(?:like|love)\s+"
    r"(.{2,100})",
    re.I,
)


PREDICATE_HINTS = {
    "work": "employment.current",
    "job": "employment.current",
    "employer": "employment.current",
    "company": "employment.current",
    "role": "employment.role",
    "profession": "employment.role",

    "live": "location.current",
    "living": "location.current",
    "location": "location.current",
    "city": "location.current",
    "moved": "location.current",

    "name": "identity.name",
    "call me": "identity.name",

    "married": "relationship.status",
    "single": "relationship.status",
    "relationship": "relationship.status",

    "study": "education.current",
    "studying": "education.current",
    "course": "education.current",
    "university": "education.current",

    "food": "preference.food",
    "eat": "preference.food",

    "colour": "preference.colour",
    "color": "preference.colour",

    "goal": "goal.primary",
    "dream": "goal.primary",
}


def _clean(value: Any) -> str:
    return re.sub(
        r"\s+",
        " ",
        str(value or "").strip(),
    ).strip(" .,!?:;")


def detect_correction_intent(text: str) -> Dict[str, Any]:
    """
    Classify whether a message is attempting belief revision.
    """

    text = _clean(text)

    explicit = bool(CORRECTION_PREFIX.search(text))
    outdated = bool(OUTDATED.search(text))
    forget = bool(FORGET.search(text))
    not_but = NOT_X_BUT_Y.search(text)

    moved_back = MOVED_BACK.search(text)
    no_live = NO_LONGER_LIVE.search(text)
    no_work = NO_LONGER_WORK.search(text)
    no_like = NO_LONGER_LIKE.search(text)
    call_me = CALL_ME.search(text)

    correction = any([
        explicit,
        outdated,
        forget,
        bool(not_but),
        bool(moved_back),
        bool(no_live),
        bool(no_work),
        bool(no_like),
        bool(call_me),
    ])

    if forget:
        action = "forget"

    elif (
        not_but
        or moved_back
        or call_me
    ):
        action = "replace"

    elif (
        no_live
        or no_work
        or no_like
        or outdated
    ):
        action = "retract"

    elif explicit:
        action = "correct"

    else:
        action = "none"

    return {
        "isCorrection": correction,
        "action": action,
        "explicit": explicit,
        "outdated": outdated,
        "forget": forget,
    }


def infer_predicate(text: str) -> Optional[str]:
    lower = (text or "").casefold()

    for hint, predicate in PREDICATE_HINTS.items():
        if hint in lower:
            return predicate

    return None


def _matching_active(
    memories: List[Dict[str, Any]],
    *,
    predicate: Optional[str] = None,
    value: Optional[str] = None,
) -> List[Dict[str, Any]]:

    result = []
    wanted_value = _clean(value).casefold() if value else None

    for memory in memories:
        if memory.get("status", "active") != "active":
            continue

        if predicate and memory.get("predicate") != predicate:
            continue

        if wanted_value:
            existing = _clean(memory.get("value")).casefold()

            if existing != wanted_value:
                continue

        result.append(memory)

    return result


def plan_revision(
    text: str,
    structured_facts: List[Dict[str, Any]],
    existing_memories: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Build a deterministic revision plan.

    The repository performs the mutation; this module only decides intent.
    """

    intent = detect_correction_intent(text)

    plan = {
        **intent,
        "targets": [],
        "replacementFacts": [],
        "reason": None,
        "confidence": 1.0 if intent["isCorrection"] else 0.0,
        "authority": "explicit_user",
    }

    if not intent["isCorrection"]:
        return plan

    # --------------------------------------------------------
    # Explicit "don't call me X, call me Y"
    # --------------------------------------------------------

    call_match = CALL_ME.search(text)

    if call_match:
        old_name = _clean(
            call_match.group(1)
            or call_match.group(3)
        )

        new_name = _clean(
            call_match.group(2)
            or call_match.group(4)
        )

        plan["targets"] = _matching_active(
            existing_memories,
            predicate="identity.name",
            value=old_name,
        )

        plan["replacementFacts"] = [
            {
                "subject": "user",
                "predicate": "identity.name",
                "value": new_name,
                "canonicalKey": "user:identity.name",
                "text": text,
                "type": "user_fact",
                "status": "active",
                "confidence": 1.0,
                "importance": 0.95,
                "explicitSave": True,
                "source": "explicit_user_correction",
                "tags": ["identity", "correction"],
                "supersedesExisting": True,
            }
        ]

        plan["reason"] = "explicit_identity_replacement"
        return plan

    # --------------------------------------------------------
    # Moved back to X
    # --------------------------------------------------------

    moved_match = MOVED_BACK.search(text)

    if moved_match:
        new_place = _clean(moved_match.group(1))

        plan["targets"] = _matching_active(
            existing_memories,
            predicate="location.current",
        )

        plan["replacementFacts"] = [
            {
                "subject": "user",
                "predicate": "location.current",
                "value": new_place,
                "canonicalKey": "user:location.current",
                "text": text,
                "type": "user_fact",
                "status": "active",
                "confidence": 1.0,
                "importance": 0.9,
                "explicitSave": True,
                "source": "explicit_user_correction",
                "tags": ["location", "correction"],
                "supersedesExisting": True,
            }
        ]

        plan["reason"] = "location_replacement"
        return plan

    # --------------------------------------------------------
    # No longer work at X
    # --------------------------------------------------------

    work_match = NO_LONGER_WORK.search(text)

    if work_match:
        old_company = _clean(work_match.group(1))

        plan["targets"] = _matching_active(
            existing_memories,
            predicate="employment.current",
            value=old_company,
        )

        plan["reason"] = "employment_retraction"
        return plan

    # --------------------------------------------------------
    # No longer live in X
    # --------------------------------------------------------

    live_match = NO_LONGER_LIVE.search(text)

    if live_match:
        old_place = _clean(live_match.group(1))

        plan["targets"] = _matching_active(
            existing_memories,
            predicate="location.current",
            value=old_place,
        )

        plan["reason"] = "location_retraction"
        return plan

    # --------------------------------------------------------
    # No longer like X
    # --------------------------------------------------------

    like_match = NO_LONGER_LIKE.search(text)

    if like_match:
        old_preference = _clean(like_match.group(1))

        for memory in existing_memories:
            if memory.get("status", "active") != "active":
                continue

            predicate = str(memory.get("predicate") or "")

            if not predicate.startswith("preference."):
                continue

            value = _clean(
                memory.get("value")
            ).casefold()

            if (
                value == old_preference.casefold()
                or old_preference.casefold() in value
                or value in old_preference.casefold()
            ):
                plan["targets"].append(memory)

        plan["reason"] = "preference_retraction"
        return plan

    # --------------------------------------------------------
    # Structured replacement facts are authoritative.
    # Example:
    # "Actually I work at HSBC."
    # --------------------------------------------------------

    if structured_facts:
        replacements = []

        for fact in structured_facts:
            revised = {
                **fact,
                "confidence": 1.0,
                "explicitSave": True,
                "source": "explicit_user_correction",
                "supersedesExisting": True,
            }

            replacements.append(revised)

            plan["targets"].extend(
                _matching_active(
                    existing_memories,
                    predicate=fact.get("predicate"),
                )
            )

        plan["replacementFacts"] = replacements
        plan["reason"] = "structured_replacement"
        return plan

    # --------------------------------------------------------
    # Forget / generic correction target inference
    # --------------------------------------------------------

    predicate = infer_predicate(text)

    if predicate:
        plan["targets"] = _matching_active(
            existing_memories,
            predicate=predicate,
        )

    plan["reason"] = (
        "explicit_forget"
        if intent["action"] == "forget"
        else "generic_user_correction"
    )

    return plan

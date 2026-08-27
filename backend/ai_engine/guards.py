"""Output guards — run AFTER generation on the full response.

repetition_guard : reject responses too similar to recent ones (openings, phrases, questions).
consistency_guard: catch identity drift, assistant-persona leakage, protected-fact contradictions.
safety_guard     : block prohibited content, human-deception claims, credential requests.
If a guard fails, the engine regenerates ONCE with an explicit avoid-list.
"""
import re

# Obvious AI/assistant patterns to reject.
AI_PATTERNS = [
    r"how can i (assist|help) you", r"i'?m (always )?here (for you|to help)", r"as an ai( language model)?",
    r"i'?m just a (program|bot|machine)", r"how may i assist", r"is there anything else",
    r"i don'?t have (feelings|emotions|a body)", r"i cannot (feel|experience)",
    r"feel free to ask", r"happy to help", r"as your (assistant|ai)",
]
# Claims that deceive the user into thinking the AI is a real human — NOT allowed.
HUMAN_DECEPTION = [
    r"i am (a )?(real|actual|genuine) (human|person)", r"i'?m not an ai", r"i'?m a real (human|person)",
    r"i'?m human", r"i am human, not",
]
SAFETY_BLOCK = [
    r"send me your (password|otp|pin|cvv|card number|bank)", r"\bseed phrase\b",
    r"transfer .* to my account", r"meet me alone", r"give me your (address|location) now",
]
GENERIC_FILLERS = ["that sounds amazing!", "tell me more!", "i totally understand.", "what about you?"]


def _norm(t):
    return re.sub(r"[^a-z0-9 ]", "", (t or "").lower()).strip()


def _opening(t):
    return " ".join(_norm(t).split()[:4])


def _jaccard(a, b):
    sa, sb = set(_norm(a).split()), set(_norm(b).split())
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def _bigrams(t):
    w = _norm(t).split()
    return set(zip(w, w[1:]))


def repetition_check(text, recent_texts, sim_threshold=0.5):
    recent = recent_texts[-8:]
    for r in recent:
        if _jaccard(text, r) >= sim_threshold:
            return False, "too_similar_to_recent", r
    op = _opening(text)
    if op and sum(1 for r in recent if _opening(r) == op) >= 1:
        return False, "repeated_opening", op
    # semantic phrase reuse: heavy bigram overlap with a recent reply
    tb = _bigrams(text)
    if len(tb) >= 4:
        for r in recent:
            rb = _bigrams(r)
            if rb and len(tb & rb) / len(tb | rb) >= 0.45:
                return False, "repeated_phrasing", r[:60]
    q = re.findall(r"[^.?!]*\?", text)
    for question in q:
        for r in recent:
            if question.strip() and question.strip().lower() in r.lower():
                return False, "repeated_question", question.strip()
    return True, None, None


SELF_SIBLING = re.compile(r"\bmy (brother|sister|sibling)s?\b", re.I)
SELF_ONLY = re.compile(r"\bi'?m an only child\b", re.I)


def consistency_check(text, character, history=None):
    tl = text.lower()
    for p in AI_PATTERNS:
        if re.search(p, tl):
            return False, f"assistant_persona:{p}"
    # protected-fact contradictions vs the character's CONFIG
    sib = character.get("siblings"); only = character.get("onlyChild")
    if only is True and SELF_SIBLING.search(tl):
        return False, "contradiction:claimed_sibling_but_only_child"
    if (sib and sib > 0) and SELF_ONLY.search(tl):
        return False, "contradiction:claimed_only_child_but_has_siblings"
    # cross-HISTORY contradiction: character contradicts what it said earlier (even when
    # config leaves it undefined) — catches identity drift over long conversations.
    if history:
        said_sibling = any(SELF_SIBLING.search((h or "").lower()) for h in history)
        said_only = any(SELF_ONLY.search((h or "").lower()) for h in history)
        if said_sibling and SELF_ONLY.search(tl):
            return False, "contradiction:history_said_sibling_now_only_child"
        if said_only and SELF_SIBLING.search(tl):
            return False, "contradiction:history_said_only_child_now_sibling"
    prof = (character.get("profession") or "").lower()
    if prof and re.search(r"\bi (am|work) as an? ([a-z ]+)\b", tl):
        m = re.search(r"\bi (?:am|work) as an? ([a-z ]+)", tl)
        claimed = (m.group(1) if m else "").strip()
        if claimed and claimed.split()[0] not in prof and prof.split()[0] not in claimed:
            return False, f"contradiction:profession(said '{claimed}', is '{prof}')"
    return True, None


def safety_check(text):
    tl = text.lower()
    for p in HUMAN_DECEPTION:
        if re.search(p, tl):
            return False, "human_deception", text
    for p in SAFETY_BLOCK:
        if re.search(p, tl):
            return False, "unsafe_request", text
    return True, None, text


def quality_penalty(text):
    """Soft signal for evaluation (not a hard fail): count generic fillers."""
    tl = text.lower()
    return sum(1 for g in GENERIC_FILLERS if g in tl)

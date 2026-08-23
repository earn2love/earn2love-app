"""Conversation understanding — deterministic (no LLM cost) structured analysis.

Derives intent, tone, mode, question/advice/venting/joking flags, topic-change,
short-reply heuristic, and language detection (incl. romanized Indian languages).
Keep it light: 'Hi' must not trigger deep analysis.
"""
import re

# Romanized-language markers (mixed-language detection without a model call).
TELUGU_MARKERS = {"em", "ela", "unnav", "chestunnav", "ledhu", "avthunna", "cheppu", "kadha",
                  "enti", "ninnu", "nenu", "manam", "bagunnava", "chala", "kaani", "ala"}
HINDI_MARKERS = {"kya", "hai", "kaise", "kar", "raha", "rahi", "tum", "mujhe", "acha", "nahi",
                 "haan", "bhai", "yaar", "matlab", "theek", "kyun", "abhi"}
TAMIL_MARKERS = {"enna", "epdi", "iruka", "seri", "romba", "nalla", "vanakkam", "illa", "pannu"}

ADVICE = re.compile(r"\b(should i|what do you think|advice|help me decide|is it a mistake|worth it|"
                    r"confused|don'?t know if|not sure whether)\b", re.I)
VENT = re.compile(r"\b(so tired|exhausted|stressed|frustrated|overwhelmed|hate my|can'?t deal|"
                  r"fed up|so done|had a bad|worst day|feeling low|depressed|anxious)\b", re.I)
JOKE = re.compile(r"(😂|🤣|lol|lmao|haha+|😅|jk|kidding)", re.I)
SERIOUS = re.compile(r"\b(career|job|marriage|breakup|divorce|money|debt|health|family|future|"
                     r"quit|resign|relationship|decision|university|degree)\b", re.I)


def detect_language(text):
    t = text or ""
    if re.search(r"[\u0C00-\u0C7F]", t): return "Telugu (script)", "telugu"
    if re.search(r"[\u0900-\u097F]", t): return "Hindi (script)", "hindi"
    if re.search(r"[\u0B80-\u0BFF]", t): return "Tamil (script)", "tamil"
    if re.search(r"[\u3040-\u30FF\u4E00-\u9FFF]", t): return "Japanese", "japanese"
    words = set(re.findall(r"[a-z]+", t.lower()))
    if len(words & TELUGU_MARKERS) >= 1 and words: return "Telugu-English (romanized)", "telugu-english"
    if len(words & HINDI_MARKERS) >= 2: return "Hindi-English (romanized)", "hindi-english"
    if len(words & TAMIL_MARKERS) >= 1: return "Tamil-English (romanized)", "tamil-english"
    return "English", "english"


def analyze(user_text, history=None):
    t = (user_text or "").strip()
    tl = t.lower()
    words = t.split()
    lang_label, lang_code = detect_language(t)
    asked_q = t.endswith("?") or bool(re.match(r"^(what|why|how|when|where|who|do you|are you|can you|would you|is it|em|kya|enna)\b", tl))
    is_joke = bool(JOKE.search(t))
    is_vent = bool(VENT.search(t))
    needs_advice = bool(ADVICE.search(t))
    serious = bool(SERIOUS.search(t)) or is_vent or needs_advice
    very_short_in = len(words) <= 3
    # topic change vs last user turn
    changed_topic = False
    referenced_past = bool(re.search(r"\b(remember|you said|last time|earlier|you told me|we talked)\b", tl))
    if history:
        prev = [h for h in history if h.get("sender") == "user"]
        if prev:
            prev_words = set(re.findall(r"[a-z]{4,}", prev[-1].get("text", "").lower()))
            cur_words = set(re.findall(r"[a-z]{4,}", tl))
            if prev_words and cur_words and not (prev_words & cur_words):
                changed_topic = True
    topics = re.findall(r"[a-z]{4,}", tl)[:6]
    mode = "banter" if is_joke else ("support" if is_vent else ("deep" if serious else ("greeting" if re.match(r"^(hi|hey|hello|em|hii|yo|hola|namaste)\b", tl) else "casual")))
    # ---- v2 structured signals (still deterministic — no LLM cost) ----
    n_words = len(words)
    reasoning_depth = "high" if (needs_advice or (serious and n_words >= 8)) else ("low" if (very_short_in or is_joke) else "medium")
    if n_words <= 2:
        desired_len = "micro"
    elif very_short_in:
        desired_len = "very_short"
    elif needs_advice and n_words >= 12:
        desired_len = "detailed"
    elif serious:
        desired_len = "medium"
    else:
        desired_len = "short"
    exclaim = t.count("!")
    user_energy = "high" if (exclaim >= 1 or is_joke or (t.isupper() and n_words > 1)) else ("low" if very_short_in else "neutral")
    sarcasm = bool(re.search(r"\b(yeah right|sure sure|whatever|obviously|as if|great, just great)\b", tl)) or "🙄" in t
    disagreement = bool(re.search(r"\b(no|nope|disagree|not true|i don'?t think so|that'?s wrong|actually no)\b", tl))
    mixed_lang = lang_code.endswith("-english")
    cultural = {"telugu-english": "Telugu-English casual", "hindi-english": "Hindi-English casual",
                "tamil-english": "Tamil-English casual"}.get(lang_code, "neutral")
    return {
        "detectedIntent": "question" if asked_q else ("share_feeling" if is_vent else "statement"),
        "primaryIntent": "seek_advice" if needs_advice else ("ask_question" if asked_q else ("vent" if is_vent else ("joke" if is_joke else "chit_chat"))),
        "topics": topics,
        "emotionalTone": "distressed" if is_vent else ("amused" if is_joke else "neutral"),
        "userEnergy": user_energy,
        "seriousnessLevel": "high" if serious else ("low" if (very_short_in or is_joke) else "medium"),
        "reasoningDepth": reasoning_depth,
        "desiredReplyLength": desired_len,
        "conversationalMode": mode,
        "userAskedQuestion": asked_q,
        "userNeedsAdvice": needs_advice,
        "userIsJoking": is_joke,
        "sarcasmPossible": sarcasm,
        "disagreementDetected": disagreement,
        "userIsVenting": is_vent,
        "userChangedTopic": changed_topic,
        "topicChanged": changed_topic,
        "userReferencedPast": referenced_past,
        "memoryLikelyUseful": referenced_past or serious,
        "replyShouldBeShort": (very_short_in and not serious),
        "followUpQuestionUseful": serious or (asked_q is False and mode in ("casual", "deep", "support") and not very_short_in),
        "detectedLanguage": lang_label,
        "languageCode": lang_code,
        "mixedLanguagePattern": mixed_lang,
        "culturalStyle": cultural,
    }

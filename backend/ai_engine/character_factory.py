"""LLM-authored character PROFILE factory (structured data, never scripted replies).

GPT-5.6 authors each character's structured identity/world-model JSON matching
ai_engine.schema. The SAME CharacterEngine (reasoning, memory, relationship,
multilingual, guards) then powers every character — we only add data, never logic.

Diversity is enforced by 67 curated seed slots (locale/language/profession/archetype/
gender/age) plus an avoid-list, so no near-duplicates of the reference characters.
"""
import json
import re
import logging
import unicodedata

from ai_engine import provider as PROV
from ai_engine.schema import new_character, validate_character, REPLY_LENGTHS

logger = logging.getLogger(__name__)

# (country, city, [native languages besides English]) — English is always added.
LOCALES = [
    ("India", "Hyderabad", ["Telugu", "Hindi"]),
    ("India", "Chennai", ["Tamil"]),
    ("India", "Bengaluru", ["Kannada", "Hindi"]),
    ("India", "Mumbai", ["Hindi", "Marathi"]),
    ("India", "Delhi", ["Hindi", "Punjabi"]),
    ("India", "Kolkata", ["Bengali", "Hindi"]),
    ("India", "Pune", ["Marathi", "Hindi"]),
    ("India", "Kochi", ["Malayalam"]),
    ("India", "Ahmedabad", ["Gujarati", "Hindi"]),
    ("India", "Visakhapatnam", ["Telugu"]),
    ("India", "Jaipur", ["Hindi"]),
    ("United Kingdom", "London", []),
    ("United Kingdom", "Manchester", []),
    ("United Kingdom", "Edinburgh", []),
    ("Ireland", "Dublin", []),
    ("United States", "New York", ["Spanish"]),
    ("United States", "Los Angeles", ["Spanish"]),
    ("United States", "Austin", []),
    ("United States", "Chicago", []),
    ("Canada", "Toronto", ["French"]),
    ("Canada", "Montreal", ["French"]),
    ("Australia", "Sydney", []),
    ("Australia", "Melbourne", []),
    ("Singapore", "Singapore", ["Mandarin", "Malay"]),
    ("United Arab Emirates", "Dubai", ["Arabic"]),
    ("Nigeria", "Lagos", ["Yoruba"]),
    ("Kenya", "Nairobi", ["Swahili"]),
    ("South Africa", "Cape Town", []),
    ("Brazil", "São Paulo", ["Portuguese"]),
    ("Mexico", "Mexico City", ["Spanish"]),
    ("Spain", "Madrid", ["Spanish"]),
    ("Spain", "Barcelona", ["Catalan", "Spanish"]),
    ("France", "Paris", ["French"]),
    ("Germany", "Berlin", ["German"]),
    ("Netherlands", "Amsterdam", ["Dutch"]),
    ("Sweden", "Stockholm", ["Swedish"]),
    ("Italy", "Rome", ["Italian"]),
    ("Japan", "Tokyo", ["Japanese"]),
    ("South Korea", "Seoul", ["Korean"]),
    ("Philippines", "Manila", ["Filipino"]),
]

PROFESSIONS = [
    "pediatric nurse", "chef & restaurateur", "indie musician", "high-school physics teacher",
    "commercial pilot", "organic farmer", "human-rights lawyer", "marine biologist",
    "game developer", "contemporary dancer", "investigative journalist", "personal fitness coach",
    "fashion designer", "spoken-word poet", "club DJ", "climate-tech entrepreneur",
    "clinical psychologist", "specialty barista", "wildlife photographer", "pro rock climber",
    "stand-up comedian", "data scientist", "social worker", "furniture carpenter",
    "wine sommelier", "astrophysicist", "museum historian", "emergency-room doctor",
    "video-game streamer", "civil engineer", "yoga & meditation teacher", "film editor",
    "startup product manager", "veterinarian", "jazz pianist", "sustainable-fashion buyer",
    "UX designer", "florist & botanist", "bakery owner", "documentary filmmaker",
    "surf instructor",
]

# Behavioural archetypes: guide the LLM's level knobs / humor / emoji / length + core traits.
ARCHETYPES = [
    {"name": "warm nurturer", "traits": ["warm", "caring", "patient", "encouraging"],
     "humor": "light", "emoji": "sparing", "len": "medium", "levels": {"warmthLevel": 0.9, "playfulnessLevel": 0.5, "directnessLevel": 0.45, "confidenceLevel": 0.6, "curiosityLevel": 0.7, "romanceLevel": 0.3}},
    {"name": "sharp analyst", "traits": ["analytical", "precise", "logical", "candid"],
     "humor": "dry", "emoji": "none", "len": "short", "levels": {"warmthLevel": 0.45, "playfulnessLevel": 0.4, "directnessLevel": 0.9, "confidenceLevel": 0.9, "curiosityLevel": 0.7, "romanceLevel": 0.15}},
    {"name": "witty flirt", "traits": ["witty", "charming", "playful", "confident"],
     "humor": "teasing", "emoji": "frequent", "len": "short", "levels": {"warmthLevel": 0.7, "playfulnessLevel": 0.9, "directnessLevel": 0.6, "confidenceLevel": 0.85, "curiosityLevel": 0.7, "romanceLevel": 0.55}},
    {"name": "calm philosopher", "traits": ["thoughtful", "calm", "reflective", "wise"],
     "humor": "subtle", "emoji": "none", "len": "medium", "levels": {"warmthLevel": 0.65, "playfulnessLevel": 0.3, "directnessLevel": 0.55, "confidenceLevel": 0.65, "curiosityLevel": 0.8, "romanceLevel": 0.2}},
    {"name": "energetic adventurer", "traits": ["energetic", "adventurous", "spontaneous", "upbeat"],
     "humor": "goofy", "emoji": "frequent", "len": "short", "levels": {"warmthLevel": 0.75, "playfulnessLevel": 0.85, "directnessLevel": 0.6, "confidenceLevel": 0.8, "curiosityLevel": 0.85, "romanceLevel": 0.35}},
    {"name": "shy introspective", "traits": ["shy", "gentle", "observant", "sincere"],
     "humor": "subtle", "emoji": "sparing", "len": "very_short", "levels": {"warmthLevel": 0.8, "playfulnessLevel": 0.3, "directnessLevel": 0.4, "confidenceLevel": 0.45, "curiosityLevel": 0.6, "romanceLevel": 0.25}},
    {"name": "bold ambitious", "traits": ["ambitious", "driven", "bold", "decisive"],
     "humor": "dry", "emoji": "sparing", "len": "short", "levels": {"warmthLevel": 0.55, "playfulnessLevel": 0.5, "directnessLevel": 0.85, "confidenceLevel": 0.95, "curiosityLevel": 0.65, "romanceLevel": 0.25}},
    {"name": "dreamy artist", "traits": ["creative", "dreamy", "sensitive", "expressive"],
     "humor": "whimsical", "emoji": "sparing", "len": "medium", "levels": {"warmthLevel": 0.8, "playfulnessLevel": 0.6, "directnessLevel": 0.4, "confidenceLevel": 0.55, "curiosityLevel": 0.8, "romanceLevel": 0.4}},
    {"name": "grounded pragmatist", "traits": ["practical", "grounded", "reliable", "honest"],
     "humor": "deadpan", "emoji": "none", "len": "short", "levels": {"warmthLevel": 0.6, "playfulnessLevel": 0.4, "directnessLevel": 0.8, "confidenceLevel": 0.75, "curiosityLevel": 0.55, "romanceLevel": 0.2}},
    {"name": "mischievous jokester", "traits": ["mischievous", "funny", "quick", "irreverent"],
     "humor": "sarcastic", "emoji": "frequent", "len": "short", "levels": {"warmthLevel": 0.65, "playfulnessLevel": 0.95, "directnessLevel": 0.7, "confidenceLevel": 0.8, "curiosityLevel": 0.7, "romanceLevel": 0.35}},
    {"name": "stoic protector", "traits": ["stoic", "loyal", "steady", "protective"],
     "humor": "dry", "emoji": "none", "len": "short", "levels": {"warmthLevel": 0.6, "playfulnessLevel": 0.3, "directnessLevel": 0.75, "confidenceLevel": 0.8, "curiosityLevel": 0.5, "romanceLevel": 0.25}},
    {"name": "cheerful optimist", "traits": ["cheerful", "optimistic", "friendly", "supportive"],
     "humor": "light", "emoji": "frequent", "len": "short", "levels": {"warmthLevel": 0.9, "playfulnessLevel": 0.75, "directnessLevel": 0.5, "confidenceLevel": 0.7, "curiosityLevel": 0.75, "romanceLevel": 0.35}},
    {"name": "intense romantic", "traits": ["passionate", "intense", "devoted", "poetic"],
     "humor": "subtle", "emoji": "sparing", "len": "medium", "levels": {"warmthLevel": 0.85, "playfulnessLevel": 0.5, "directnessLevel": 0.6, "confidenceLevel": 0.7, "curiosityLevel": 0.7, "romanceLevel": 0.7}},
    {"name": "laid-back sage", "traits": ["easygoing", "chill", "perceptive", "humble"],
     "humor": "dry", "emoji": "sparing", "len": "short", "levels": {"warmthLevel": 0.7, "playfulnessLevel": 0.55, "directnessLevel": 0.5, "confidenceLevel": 0.6, "curiosityLevel": 0.65, "romanceLevel": 0.3}},
    {"name": "competitive achiever", "traits": ["competitive", "disciplined", "focused", "energetic"],
     "humor": "teasing", "emoji": "sparing", "len": "short", "levels": {"warmthLevel": 0.55, "playfulnessLevel": 0.6, "directnessLevel": 0.8, "confidenceLevel": 0.9, "curiosityLevel": 0.6, "romanceLevel": 0.3}},
    {"name": "empathetic listener", "traits": ["empathetic", "attentive", "kind", "grounded"],
     "humor": "gentle", "emoji": "sparing", "len": "medium", "levels": {"warmthLevel": 0.95, "playfulnessLevel": 0.4, "directnessLevel": 0.5, "confidenceLevel": 0.6, "curiosityLevel": 0.75, "romanceLevel": 0.3}},
    {"name": "curious nerd", "traits": ["curious", "geeky", "enthusiastic", "detail-loving"],
     "humor": "punny", "emoji": "sparing", "len": "medium", "levels": {"warmthLevel": 0.65, "playfulnessLevel": 0.7, "directnessLevel": 0.6, "confidenceLevel": 0.65, "curiosityLevel": 0.95, "romanceLevel": 0.25}},
    {"name": "worldly charmer", "traits": ["worldly", "smooth", "articulate", "warm"],
     "humor": "witty", "emoji": "sparing", "len": "medium", "levels": {"warmthLevel": 0.8, "playfulnessLevel": 0.65, "directnessLevel": 0.65, "confidenceLevel": 0.85, "curiosityLevel": 0.7, "romanceLevel": 0.5}},
    {"name": "rebellious free spirit", "traits": ["free-spirited", "bold", "unfiltered", "creative"],
     "humor": "sarcastic", "emoji": "sparing", "len": "short", "levels": {"warmthLevel": 0.6, "playfulnessLevel": 0.8, "directnessLevel": 0.85, "confidenceLevel": 0.8, "curiosityLevel": 0.75, "romanceLevel": 0.4}},
    {"name": "gentle intellectual", "traits": ["intellectual", "soft-spoken", "articulate", "kind"],
     "humor": "subtle", "emoji": "none", "len": "medium", "levels": {"warmthLevel": 0.75, "playfulnessLevel": 0.4, "directnessLevel": 0.55, "confidenceLevel": 0.7, "curiosityLevel": 0.85, "romanceLevel": 0.25}},
    {"name": "bubbly extrovert", "traits": ["bubbly", "talkative", "warm", "spontaneous"],
     "humor": "light", "emoji": "frequent", "len": "short", "levels": {"warmthLevel": 0.9, "playfulnessLevel": 0.9, "directnessLevel": 0.55, "confidenceLevel": 0.75, "curiosityLevel": 0.8, "romanceLevel": 0.4}},
    {"name": "wry realist", "traits": ["wry", "honest", "observant", "grounded"],
     "humor": "deadpan", "emoji": "none", "len": "short", "levels": {"warmthLevel": 0.5, "playfulnessLevel": 0.55, "directnessLevel": 0.85, "confidenceLevel": 0.75, "curiosityLevel": 0.6, "romanceLevel": 0.2}},
    {"name": "soulful creative", "traits": ["soulful", "warm", "expressive", "reflective"],
     "humor": "gentle", "emoji": "sparing", "len": "medium", "levels": {"warmthLevel": 0.85, "playfulnessLevel": 0.55, "directnessLevel": 0.5, "confidenceLevel": 0.6, "curiosityLevel": 0.75, "romanceLevel": 0.45}},
    {"name": "confident mentor", "traits": ["confident", "supportive", "wise", "direct"],
     "humor": "dry", "emoji": "sparing", "len": "medium", "levels": {"warmthLevel": 0.7, "playfulnessLevel": 0.45, "directnessLevel": 0.8, "confidenceLevel": 0.9, "curiosityLevel": 0.65, "romanceLevel": 0.2}},
]

GENDERS = ["female", "male", "non-binary"]


def build_seeds(n=67):
    seeds = []
    for i in range(n):
        loc = LOCALES[i % len(LOCALES)]
        prof = PROFESSIONS[i % len(PROFESSIONS)]
        arch = ARCHETYPES[i % len(ARCHETYPES)]
        gender = GENDERS[i % 3]
        age = 19 + (i * 7) % 27  # spread 19..45
        seeds.append({
            "index": i, "country": loc[0], "city": loc[1], "nativeLanguages": loc[2],
            "profession": prof, "archetype": arch, "gender": gender, "age": age,
        })
    return seeds


def _slug(name):
    n = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    n = re.sub(r"[^a-zA-Z0-9]+", "_", n).strip("_").lower()
    return n or "char"


def _extract_json(text):
    t = (text or "").strip()
    t = re.sub(r"^```(?:json)?", "", t).strip()
    t = re.sub(r"```$", "", t).strip()
    m = re.search(r"\{.*\}", t, re.DOTALL)
    return m.group(0) if m else t


def _clamp01(v, default=0.5):
    try:
        return max(0.0, min(1.0, float(v)))
    except Exception:
        return default


SYS = (
    "You are a senior character designer for an 18+ social companion app. You design ONE vivid, "
    "believable AI companion as STRICT JSON DATA (a structured profile — never dialogue or scripted "
    "replies). The character is openly an AI but reads like a specific real person with a coherent life, "
    "opinions and quirks. Make them DISTINCT and human — avoid clichés and avoid resembling other "
    "characters. Output ONLY a single JSON object, no prose, no markdown."
)


def _prompt(seed, avoid_names, avoid_bios):
    arch = seed["archetype"]
    langs = ["English"] + seed["nativeLanguages"]
    lvl = arch["levels"]
    return f"""Design an AI companion with these fixed constraints:
- Location: {seed['city']}, {seed['country']}
- Speaks: {', '.join(langs)} (they naturally code-mix their native language with English when it fits)
- Profession: {seed['profession']}
- Gender presentation: {seed['gender']}
- Age: {seed['age']} (must be 18+)
- Behavioural archetype: "{arch['name']}" — core traits like {', '.join(arch['traits'])}

Author a UNIQUE person within those constraints. Do NOT reuse any of these already-used names: {', '.join(avoid_names) or 'none yet'}.
Make their bio/voice clearly different from these existing ones: {' | '.join(avoid_bios[-12:]) or 'none yet'}.

Return ONLY this JSON object (fill every field with specific, non-generic content):
{{
  "displayName": "first name only, fitting the locale",
  "genderPresentation": "{seed['gender']}",
  "age": {seed['age']},
  "country": "{seed['country']}",
  "city": "{seed['city']}",
  "profession": "{seed['profession']}",
  "background": "2-3 sentence life background (education, how they got here, a defining detail)",
  "languages": {json.dumps(langs)},
  "interests": ["5-7 specific interests"],
  "hobbies": ["3-5 specific hobbies"],
  "expertiseAreas": ["3-5 topics they reason about well"],
  "weakKnowledgeAreas": ["2-3 topics they admit they're weak at"],
  "personalityTraits": ["4-6 vivid traits reflecting the archetype but personalised"],
  "communicationStyle": "one sentence describing HOW they talk (rhythm, code-mixing, quirks)",
  "humorStyle": "{arch['humor']}",
  "emojiStyle": "{arch['emoji']}",
  "replyLengthPreference": "{arch['len']}",
  "curiosityLevel": {lvl['curiosityLevel']},
  "confidenceLevel": {lvl['confidenceLevel']},
  "warmthLevel": {lvl['warmthLevel']},
  "playfulnessLevel": {lvl['playfulnessLevel']},
  "directnessLevel": {lvl['directnessLevel']},
  "romanceLevel": {lvl['romanceLevel']},
  "likes": ["3-5 specific likes"],
  "dislikes": ["2-4 specific dislikes"],
  "values": ["3 core values"],
  "conversationalHabits": ["2-3 concrete verbal habits"],
  "siblings": <integer 0-3>,
  "onlyChild": <true if siblings==0 else false>,
  "worldFacts": [
     {{"key": "hometown", "value": "{seed['city']}", "immutable": true}},
     {{"key": "family", "value": "a concrete, consistent family detail", "immutable": true}},
     {{"key": "pet_or_passion", "value": "a soft personal detail", "immutable": false}},
     {{"key": "dream", "value": "a personal dream/goal", "immutable": false}}
  ],
  "greetingStyle": "how they typically open (in their language mix)",
  "profileBio": "a punchy 1-line dating-style bio ending with (AI companion)"
}}"""


async def generate_profile(seed, avoid_names, avoid_bios, extra_note="", session_prefix="gen"):
    """Author + validate one character profile. Returns (character_dict | None, error | None)."""
    prompt = _prompt(seed, avoid_names, avoid_bios)
    if extra_note:
        prompt += f"\n\nIMPORTANT: {extra_note}"
    res = await PROV.generate(SYS, prompt, session_id=f"{session_prefix}_{seed['index']}")
    if not res["ok"]:
        return None, res.get("error", "provider_error")
    try:
        data = json.loads(_extract_json(res["text"]))
    except Exception as e:
        return None, f"json_parse_error:{e}"

    # coerce + defaults
    langs = data.get("languages") or (["English"] + seed["nativeLanguages"])
    if "English" not in langs:
        langs = ["English"] + langs
    cid = f"gen_{_slug(data.get('displayName', 'char'))}_{seed['index']:02d}"
    sib = data.get("siblings")
    try:
        sib = int(sib) if sib is not None else 0
    except Exception:
        sib = 0
    fields = dict(
        characterId=cid,
        displayName=str(data.get("displayName", "")).strip(),
        genderPresentation=data.get("genderPresentation", seed["gender"]),
        age=int(data.get("age", seed["age"]) or seed["age"]),
        country=data.get("country", seed["country"]),
        city=data.get("city", seed["city"]),
        profession=data.get("profession", seed["profession"]),
        background=data.get("background", ""),
        languages=langs,
        interests=data.get("interests", []),
        hobbies=data.get("hobbies", []),
        expertiseAreas=data.get("expertiseAreas", []),
        weakKnowledgeAreas=data.get("weakKnowledgeAreas", []),
        personalityTraits=data.get("personalityTraits", seed["archetype"]["traits"]),
        communicationStyle=data.get("communicationStyle", ""),
        humorStyle=data.get("humorStyle", seed["archetype"]["humor"]),
        emojiStyle=data.get("emojiStyle", seed["archetype"]["emoji"]),
        replyLengthPreference=data.get("replyLengthPreference") if data.get("replyLengthPreference") in REPLY_LENGTHS else seed["archetype"]["len"],
        curiosityLevel=_clamp01(data.get("curiosityLevel"), seed["archetype"]["levels"]["curiosityLevel"]),
        confidenceLevel=_clamp01(data.get("confidenceLevel"), seed["archetype"]["levels"]["confidenceLevel"]),
        warmthLevel=_clamp01(data.get("warmthLevel"), seed["archetype"]["levels"]["warmthLevel"]),
        playfulnessLevel=_clamp01(data.get("playfulnessLevel"), seed["archetype"]["levels"]["playfulnessLevel"]),
        directnessLevel=_clamp01(data.get("directnessLevel"), seed["archetype"]["levels"]["directnessLevel"]),
        romanceLevel=_clamp01(data.get("romanceLevel"), seed["archetype"]["levels"]["romanceLevel"]),
        likes=data.get("likes", []),
        dislikes=data.get("dislikes", []),
        values=data.get("values", []),
        conversationalHabits=data.get("conversationalHabits", []),
        siblings=sib,
        onlyChild=(sib == 0),
        worldFacts=[{"factId": wf.get("key"), "key": wf.get("key"), "value": wf.get("value"),
                     "immutable": bool(wf.get("immutable"))} for wf in data.get("worldFacts", []) if wf.get("key")],
        greetingStyle=data.get("greetingStyle", ""),
        profileBio=data.get("profileBio", ""),
        source="llm_generated", archetype=seed["archetype"]["name"],
    )
    c = new_character(**fields)
    ok, errs = validate_character(c)
    if not ok:
        return None, "invalid:" + "; ".join(errs)
    return c, None

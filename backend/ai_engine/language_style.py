"""Language / cultural style resolution.

Resolves the response language + cultural rhythm from the user's detected language
and the character's language repertoire. Preserves slang, politeness style and voice
— NOT literal translation of an English response.
"""

MIXED_GUIDANCE = {
    "telugu-english": ("Telugu-English (romanized, code-mixed)",
        "Reply in natural romanized Telugu-English the way friends text (e.g. 'em ledhu, konchem chill avthunna'). "
        "Keep it casual; do not translate word-for-word from English; keep Telugu slang and rhythm."),
    "hindi-english": ("Hindi-English (romanized, code-mixed)",
        "Reply in natural Hinglish the way friends chat (e.g. 'kuch khaas nahi, bas chill kar raha'). "
        "Keep Hindi slang and rhythm; don't sound like a formal translation."),
    "tamil-english": ("Tamil-English (romanized, code-mixed)",
        "Reply in natural romanized Tamil-English (e.g. 'onnum illa, konjam relax panren'). Keep it casual and authentic."),
    "telugu": ("Telugu", "Reply in natural Telugu matching the user's script and tone."),
    "hindi": ("Hindi", "Reply in natural Hindi matching the user's script and tone."),
    "tamil": ("Tamil", "Reply in natural Tamil matching the user's script and tone."),
    "japanese": ("Japanese", "Reply in natural, friendly Japanese matching the user's tone."),
    "english": ("English", "Reply in natural, conversational English."),
}


def resolve(understanding, character):
    code = understanding.get("languageCode", "english")
    label, instruction = MIXED_GUIDANCE.get(code, MIXED_GUIDANCE["english"])
    langs = [l.lower() for l in character.get("languages", [])]
    base = code.split("-")[0]
    # If the character doesn't speak that language, respond in English but stay warm.
    speaks = base in ("english",) or any(base in l for l in langs) or code in [l.replace(" ", "-") for l in langs]
    if not speaks and base != "english":
        instruction = (f"The user wrote in {label}, but this character isn't fluent in it. "
                       f"Respond warmly in English, and it's okay to acknowledge lightly that {base} isn't your strong language.")
        label = f"English (user wrote {label})"
    return {"responseLanguage": label, "languageCode": code, "instruction": instruction}

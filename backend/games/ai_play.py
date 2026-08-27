"""Group Play AI — lets any AI character take authoritative turns in a game.

The AI plays through the EXACT same validated action path as a human
(engines.available_actions -> engines.apply_action). It never sees hidden state
(correct answers, the opponent's secret) — it reasons from the public prompt, in
character, using the same GPT-5.6 provider. Deterministic fallbacks guarantee a
game never stalls if the LLM is slow or returns something unparseable.
"""
import re
import json
import uuid
import random
import logging

from ai_engine import provider as PROV

logger = logging.getLogger(__name__)

MAX_AI_STEPS = 16  # safety cap on consecutive AI moves per drive


def _voice(c):
    bits = [f"You are {c.get('displayName','someone')}, {c.get('age','')} from {c.get('city','')}, {c.get('country','')}.",
            f"Personality: {', '.join(c.get('personalityTraits', [])[:5])}.",
            f"Style: {c.get('communicationStyle','natural, casual')}."]
    if c.get("languages"):
        bits.append(f"You may naturally code-mix {', '.join(c['languages'][:3])}.")
    bits.append("You're playing a fun social game with another person. Stay fully in character, be concise.")
    return " ".join(bits)


def _extract_json(text):
    t = re.sub(r"^```(?:json)?|```$", "", (text or "").strip()).strip()
    m = re.search(r"\{.*\}", t, re.DOTALL)
    return m.group(0) if m else t


async def _ask(character, instruction, session_id):
    res = await PROV.generate(_voice(character), instruction, session_id=session_id)
    if not res.get("ok"):
        return None
    try:
        return json.loads(_extract_json(res["text"]))
    except Exception:
        return {"_raw": res["text"]}


def _options(ctx):
    p = ctx.get("currentPrompt") or {}
    return p.get("options") or []


async def decide_action(character, ctx):
    """Return a valid engine action dict for `character` given the public game context."""
    actions = ctx.get("availableActions") or []
    if not actions:
        return None
    tmpl = actions[0]
    typ = tmpl["type"]
    prompt_text = (ctx.get("currentPrompt") or {}).get("prompt", "")
    mech = ctx.get("mechanic")
    sid = f"play_{ctx.get('sessionId','x')}_{ctx.get('round',0)}"
    aid = {"actionId": uuid.uuid4().hex}

    # ---- pick-one (choice / trivia) ----
    if typ == "answer":
        opts = _options(ctx)
        keys = tmpl.get("options") or [o["key"] for o in opts]
        if not keys:
            return None
        labels = "; ".join(f'{o["key"]}="{o["label"]}"' for o in opts) or ", ".join(keys)
        if mech == "trivia":
            instr = (f'Trivia question: "{prompt_text}". Options: {labels}. '
                     f'Answer CORRECTLY using your knowledge. Reply ONLY JSON: {{"key":"<one of {keys}>"}}.')
        else:
            instr = (f'Prompt: "{prompt_text}". Options: {labels}. Pick the ONE that genuinely fits YOUR '
                     f'personality and preferences. Reply ONLY JSON: {{"key":"<one of {keys}>"}}.')
        r = await _ask(character, instr, sid)
        key = (r or {}).get("key")
        if key not in keys:
            key = random.choice(keys) if keys else None
        return {**aid, "type": "answer", "value": key}

    # ---- open text (prompt) ----
    if typ == "respond":
        instr = (f'Conversation prompt: "{prompt_text}". Respond in YOUR voice, 1-2 sentences, genuine and specific. '
                 f'Reply ONLY JSON: {{"text":"<your reply>"}}.')
        r = await _ask(character, instr, sid)
        text = (r or {}).get("text") or (r or {}).get("_raw") or "Hmm, good one — let me think about that."
        return {**aid, "type": "respond", "value": str(text)[:490]}

    # ---- coop contribute (text or option) ----
    if typ == "contribute":
        opts = _options(ctx)
        if opts:
            keys = [o["key"] for o in opts]
            labels = "; ".join(f'{o["key"]}="{o["label"]}"' for o in opts)
            instr = (f'Collaborative prompt: "{prompt_text}". Options: {labels}. Pick the one you like. '
                     f'Reply ONLY JSON: {{"key":"<one of {keys}>"}}.')
            r = await _ask(character, instr, sid)
            key = (r or {}).get("key")
            if key not in keys:
                key = random.choice(keys)
            return {**aid, "type": "contribute", "value": key}
        instr = (f'Add the next line to this collaborative prompt: "{prompt_text}". One vivid sentence in YOUR voice. '
                 f'Reply ONLY JSON: {{"text":"<your contribution>"}}.')
        r = await _ask(character, instr, sid)
        text = (r or {}).get("text") or (r or {}).get("_raw") or "…and then something unexpected happened."
        return {**aid, "type": "contribute", "value": str(text)[:290]}

    # ---- guess: set the secret ----
    if typ == "set_secret":
        if "statements" in tmpl:  # two-truths-and-a-lie
            instr = ('Two Truths and a Lie about yourself: give 2 TRUE statements and 1 believable LIE, in character. '
                     'Reply ONLY JSON: {"statements":["s1","s2","s3"],"lieIndex":<0|1|2>}.')
            r = await _ask(character, instr, sid) or {}
            stmts = r.get("statements") if isinstance(r.get("statements"), list) else None
            lie = r.get("lieIndex")
            if not (isinstance(stmts, list) and len(stmts) == 3 and all(isinstance(s, str) and s.strip() for s in stmts) and lie in (0, 1, 2)):
                stmts = [f"I once lived in {character.get('city','a big city')}.",
                         f"I work as a {character.get('profession','creative')}.",
                         "I have climbed Mount Everest."]
                lie = 2
            return {**aid, "type": "set_secret", "statements": [s[:200] for s in stmts], "lieIndex": lie}
        opts = _options(ctx)
        keys = tmpl.get("options") or [o["key"] for o in opts]
        if not keys:
            return None
        labels = "; ".join(f'{o["key"]}="{o["label"]}"' for o in opts) or ", ".join(keys)
        instr = (f'For "{prompt_text}", choose YOUR true answer (the other player will try to guess it). Options: {labels}. '
                 f'Reply ONLY JSON: {{"key":"<one of {keys}>"}}.')
        r = await _ask(character, instr, sid)
        key = (r or {}).get("key")
        if key not in keys:
            key = random.choice(keys) if keys else None
        return {**aid, "type": "set_secret", "value": key}

    # ---- guess: predict the opponent's secret ----
    if typ == "guess":
        opts = tmpl.get("options") or []
        if opts and all(isinstance(o, int) for o in opts):  # truths_lie -> index
            instr = (f'The other player gave three statements for "{prompt_text}". Guess which is the LIE (0, 1 or 2). '
                     f'Reply ONLY JSON: {{"value":<0|1|2>}}.')
            r = await _ask(character, instr, sid) or {}
            val = r.get("value")
            if val not in (0, 1, 2):
                val = random.choice([0, 1, 2])
            return {**aid, "type": "guess", "value": val}
        keys = opts or [o["key"] for o in _options(ctx)]
        if not keys:
            return None
        labels = "; ".join(f'{o["key"]}="{o["label"]}"' for o in _options(ctx)) or ", ".join(map(str, keys))
        instr = (f'Guess the other player\'s answer to "{prompt_text}". Options: {labels}. '
                 f'Reply ONLY JSON: {{"key":"<one of {keys}>"}}.')
        r = await _ask(character, instr, sid)
        key = (r or {}).get("key")
        if key not in keys:
            key = random.choice(keys) if keys else None
        return {**aid, "type": "guess", "value": key}

    return None

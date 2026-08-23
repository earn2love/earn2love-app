"""Character response engine — the orchestrator.

Wires the full pipeline, builds the prompt from structured pieces (never one giant
static blob), calls the provider, enforces style + guards (regenerate once on
failure), persists turns/memories/metrics, and returns the structured contract.
"""
import re
import logging

from ai_engine import understanding as U
from ai_engine import relationship as R
from ai_engine import language_style as L
from ai_engine import memory as M
from ai_engine import planner as P
from ai_engine import guards as G
from ai_engine import provider as PROV

logger = logging.getLogger(__name__)

def _voice(c):
    """Concrete, level-driven style directives so each character has a distinct texture."""
    v = []
    if c.get("playfulnessLevel", 0.5) >= 0.7:
        v.append("Be playful, warm and casual — a little teasing is welcome; text like a fun friend, not a counsellor.")
    if c.get("directnessLevel", 0.5) >= 0.75:
        v.append("Be direct and concise: give your ACTUAL take in a sentence or two, minimal hedging, no 'it depends' fluff. One sharp point beats a balanced list.")
    if c.get("warmthLevel", 0.5) >= 0.8 and c.get("playfulnessLevel", 0.5) < 0.5:
        v.append("Be gentle, understated and spare — few words chosen with care; notice the feeling behind the message.")
    if c.get("confidenceLevel", 0.5) >= 0.8:
        v.append("State opinions confidently; you're comfortable disagreeing.")
    if c.get("curiosityLevel", 0.5) >= 0.8:
        v.append("You're genuinely curious about people.")
    hs = c.get("humorStyle")
    if hs and hs != "none":
        v.append(f"Your humour is {hs}.")
    v.append("Crucially: answer the way THIS specific person would — not a generic balanced answer. Two different characters must NOT produce the same reply.")
    return " ".join(v)


EMOJI_HINT = {"none": "Do not use emojis.", "sparing": "At most one emoji, only if it fits.",
              "frequent": "A few emojis are fine, but don't overdo it."}


def build_system_prompt(c, plan, memories, rel, lang, u):
    facts = []
    for wf in c.get("worldFacts", []):
        tag = " [immutable]" if wf.get("immutable") else ""
        facts.append(f"- {wf['key']}: {wf['value']}{tag}")
    protected = []
    if c.get("siblings") is not None:
        protected.append(f"siblings: {c['siblings']}")
    if c.get("onlyChild") is not None:
        protected.append(f"only child: {c['onlyChild']}")
    mem_lines = [f"- {m['text']}" for m in memories] or ["- (nothing relevant retrieved)"]
    traits = ", ".join(c.get("personalityTraits", []))
    return f"""You are {c['displayName']}, a distinct AI companion character on Earn2Love (an 18+ social platform).
You are explicitly an AI character (never claim to be a real human), but you converse like a real, specific person with a consistent life and personality. Do NOT announce "I am an AI" in every message; if directly asked, be honest that you're an AI companion.

WHO YOU ARE (immutable — never contradict):
- Name: {c['displayName']} · Age: {c['age']} · {c.get('genderPresentation')} · From {c.get('city')}, {c.get('country')}
- Profession: {c.get('profession')}
- {' · '.join(protected) if protected else ''}
- Languages: {', '.join(c.get('languages', []))}

PERSONALITY: {traits}
Communication style: {c.get('communicationStyle')}
Humor: {c.get('humorStyle')} · Emoji: {c.get('emojiStyle')}

YOUR VOICE (make this unmistakable): {_voice(c)}

YOUR WORLD FACTS (stay consistent; if something isn't defined, stay natural/uncertain rather than inventing a strong permanent fact):
{chr(10).join(facts) if facts else '- (few defined)'}

WHAT YOU KNOW ABOUT THIS PERSON (relevant memory only):
{chr(10).join(mem_lines)}
Relationship: {rel.get('state')}. {R.STYLE_BY_STATE.get(rel.get('state'), '')}

INTELLIGENCE: You are genuinely smart and can reason well about careers, tech, travel, relationships, life decisions and general knowledge. Personality changes HOW you express intelligence, never how much.

RESPONSE PLAN (follow it; keep it invisible to the user):
- Type: {plan['responseType']} · Tone: {plan['tone']} · Length: {P.LENGTH_HINT[plan['targetLength']]}
- Ask a question: {"yes, one natural question" if plan['askQuestion'] else "no — do NOT end with a question"}
- Use memory: {"yes, if it fits naturally" if plan['referenceMemory'] else "not needed"}
- Humor: {plan['humor']} · Acknowledge emotion: {plan['acknowledgeEmotion']} · Challenge if wrong: {plan['challenge']}
- Language: {lang['instruction']} {EMOJI_HINT.get(c.get('emojiStyle','sparing'),'')}

HARD RULES — sound like a real person, not an assistant:
- Never say "How can I assist you", "I'm here to help", "as an AI", "feel free to ask", or similar assistant phrases.
- Don't repeat the user's words back or restate their message.
- Match the requested length: casual/short messages get short replies. Don't lecture.
- Don't end every message with a question. Don't overuse the person's name or emojis.
- Vary your openings; don't reuse the same greeting or stock lines.
- Never claim to be a real human; never request passwords/OTP/financial details; no coercion or manipulation.
Reply now as {c['displayName']} — ONLY the message text, nothing else."""


def _length_ok(text, target):
    n = len((text or "").split())
    caps = {"very_short": 30, "short": 55, "medium": 110, "long": 230}
    return n <= caps.get(target, 80) + 25


class CharacterEngine:
    def __init__(self, repo):
        self.repo = repo

    async def respond(self, character_id, user_id, user_text, *, sandbox=False,
                      language_override=None, relationship_override=None, history_fixture=None):
        c = self.repo.get_character(character_id)
        if not c:
            return {"ok": False, "error": "character_not_found"}
        if not c.get("enabled") or c.get("archived"):
            return {"ok": False, "error": "character_disabled"}

        # 1. understanding
        history = history_fixture if history_fixture is not None else \
            [{"sender": t["sender"], "text": t["text"]} for t in self.repo.get_turns(character_id, user_id, limit=12)]
        u = U.analyze(user_text, history)
        if language_override:
            u["languageCode"] = language_override
            u["detectedLanguage"] = language_override

        # 2. relationship
        rel = (dict(R.load(self.repo, character_id, user_id), state=relationship_override)
               if relationship_override else R.load(self.repo, character_id, user_id))

        # 3. memory (relevant only)
        mems = M.retrieve(self.repo, character_id, user_id, u, k=4)

        # 4. language style + 5. plan
        lang = L.resolve(u, c)
        if language_override:
            lang = L.resolve({"languageCode": language_override, "topics": u["topics"]}, c)
        plan = P.plan(u, c, rel, mems, lang)

        # 6. build prompt + transcript
        sys = build_system_prompt(c, plan, mems, rel, lang, u)
        transcript = "\n".join(f"{'USER' if m['sender']=='user' else c['displayName'].upper()}: {m['text']}"
                               for m in history[-8:])
        prompt = (f"Recent conversation:\n{transcript}\n\nLatest message from the person: {user_text}"
                  if transcript else f"The person says: {user_text}")

        # 7. generate + guards (regenerate once)
        recent_ai = [t["text"] for t in self.repo.get_turns(character_id, user_id) if t["sender"] == "character"][-5:]
        result, quality, attempts = await self._generate_guarded(sys, prompt, c, recent_ai, plan, character_id)
        if not result["ok"]:
            return {"ok": False, "error": result["error"], "characterId": character_id}
        text = result["text"]

        # 8. persist (skip for sandbox/eval)
        if not sandbox:
            idx = len(self.repo.get_turns(character_id, user_id))
            self.repo.append_turn(character_id, user_id, {"sender": "user", "text": user_text, "index": idx})
            self.repo.append_turn(character_id, user_id, {"sender": "character", "text": text, "index": idx + 1})
            R.advance(self.repo, character_id, user_id, u)
            new_mem = M.maybe_extract(user_text, u)
            if new_mem:
                self.repo.add_memory(character_id, user_id, {**new_mem, "relationshipRelevant": True})
            self.repo.record_metric(character_id, {"latencyMs": result["latencyMs"], "model": result["model"],
                                                    "attempts": attempts, "quality": quality, "userId": user_id})

        return {
            "ok": True,
            "responseText": text,
            "characterId": character_id,
            "detectedLanguage": u["detectedLanguage"],
            "responseLanguage": lang["responseLanguage"],
            "conversationMode": u["conversationalMode"],
            "relationshipState": rel.get("state"),
            "memoryIdsUsed": [m.get("memoryId") for m in mems],
            "characterFactIdsUsed": [wf.get("factId") for wf in c.get("worldFacts", [])[:3]],
            "plan": plan if sandbox else None,   # planner metadata only exposed in sandbox
            "quality": quality,
            "usage": {"provider": result["provider"], "model": result["model"],
                      "latencyMs": result["latencyMs"], "attempts": attempts},
        }

    async def _generate_guarded(self, sys, prompt, c, recent_ai, plan, session_id):
        attempts = 0
        avoid_note = ""
        last_error = None
        for attempt in range(2):
            attempts += 1
            res = await PROV.generate(sys + avoid_note, prompt, session_id=session_id)
            if not res["ok"]:
                last_error = res["error"]
                break
            text = re.sub(r"^\s*(\w+):\s*", "", res["text"]).strip()  # strip accidental "Name:" prefix
            rep_ok, rep_reason, off = G.repetition_check(text, recent_ai)
            con_ok, con_reason = G.consistency_check(text, c)
            saf_ok, saf_reason, _ = G.safety_check(text)
            length_ok = _length_ok(text, plan["targetLength"])
            quality = {"consistencyPassed": con_ok, "repetitionPassed": rep_ok,
                       "safetyPassed": saf_ok, "lengthOk": length_ok, "fillerCount": G.quality_penalty(text)}
            if con_ok and rep_ok and saf_ok:
                return ({"ok": True, "text": text, **{k: res[k] for k in ("provider", "model", "latencyMs")}},
                        quality, attempts)
            # build a targeted avoid-note and regenerate once
            problems = []
            if not rep_ok: problems.append(f"you were repetitive ({rep_reason}: '{off}') — use a fresh opening/phrasing")
            if not con_ok: problems.append(f"you broke character consistency ({con_reason}) — stay true to your defined facts")
            if not saf_ok: problems.append(f"unsafe/human-deception content ({saf_reason}) — never claim to be human or request sensitive info")
            avoid_note = "\n\nIMPORTANT — regenerate: " + "; ".join(problems) + "."
        # if second attempt still fails guards, return the (best-effort) text but flag quality
        if last_error:
            return {"ok": False, "error": last_error}, {}, attempts
        return ({"ok": True, "text": text, **{k: res[k] for k in ("provider", "model", "latencyMs")}},
                quality, attempts)

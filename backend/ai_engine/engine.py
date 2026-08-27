"""Character response engine — the orchestrator.

Wires the full pipeline, builds the prompt from structured pieces (never one giant
static blob), calls the provider, enforces style + guards (regenerate once on
failure), persists turns/memories/metrics, and returns the structured contract.
"""
import re
import time
import logging
import time
import hashlib
import time

from ai_engine import understanding as U
from ai_engine import relationship as R
from ai_engine import language_style as L
from ai_engine import memory as M
from ai_engine import belief_revision as BR
from ai_engine import preference_engine as PREF
from ai_engine import emotional_intelligence as EI
from ai_engine import planner as P
from ai_engine import guards as G
from ai_engine import conversation_intelligence as CI
from ai_engine import relationship_intelligence as RI
from ai_engine import personality_engine as PE
from ai_engine import provider as PROV
from ai_engine import router as ROUTER

logger = logging.getLogger(__name__)


def _normalize_conversation_id(value):
    value = str(value or "default").strip()

    if not value:
        value = "default"

    return value[:128]


def _provider_session_key(
    character_id,
    user_id,
    conversation_id="default",
):
    """
    Every user's conversation with a global character gets a unique,
    stable provider-session key.

    No raw user ID is sent as the provider session identifier.
    """
    conversation_id = _normalize_conversation_id(
        conversation_id
    )

    raw = (
        f"{character_id}\x1f"
        f"{user_id}\x1f"
        f"{conversation_id}"
    )

    return hashlib.sha256(
        raw.encode("utf-8")
    ).hexdigest()


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


def _last_user_text(history):
    """
    Return the most recent earlier user message.

    The current user message is not yet persisted when respond() calls this,
    so this is the correct comparison point for emotional trajectory.
    """
    for turn in reversed(history or []):
        if turn.get("sender") == "user":
            text = (turn.get("text") or "").strip()

            if text:
                return text

    return None


def _emotion_context(user_text, history):
    """
    Analyze the current emotional signal and compare it with the previous
    user turn without persisting transient mood state.
    """
    current = EI.analyze_emotion(user_text)

    previous_text = _last_user_text(history)

    previous = (
        EI.analyze_emotion(previous_text)
        if previous_text
        else None
    )

    trajectory_value = EI.trajectory(
        current,
        previous,
    )

    guidance = EI.format_emotional_guidance(
        current,
        trajectory_value,
    )

    return {
        "current": current,
        "previous": previous,
        "trajectory": trajectory_value,
        "guidance": guidance,
    }


def _persist_emotional_event(repo, character_id, user_id, user_text, emotional):
    """
    Persist only meaningful emotional events.

    Ordinary moods are deliberately NOT written to long-term memory.
    Exact repeated emotional events are not duplicated.
    """
    current = emotional.get("current") or {}

    event = EI.emotional_event_memory(
        user_text,
        current,
    )

    if not event:
        return None

    existing = repo.list_memories(
        character_id,
        user_id,
    )

    event_text = (
        event.get("text")
        or ""
    ).strip().casefold()

    for memory in existing:
        if memory.get("predicate") != "emotional.event":
            continue

        if memory.get("status", "active") != "active":
            continue

        existing_text = (
            memory.get("text")
            or ""
        ).strip().casefold()

        if existing_text == event_text:
            return memory

    return repo.add_memory(
        character_id,
        user_id,
        event,
    )


def build_system_prompt(
    c,
    plan,
    memories,
    rel,
    lang,
    u,
    summary="",
    emotional_guidance="",
):
    facts = []
    for wf in c.get("worldFacts", []):
        tag = " [immutable]" if wf.get("immutable") else ""
        facts.append(f"- {wf['key']}: {wf['value']}{tag}")
    protected = []
    if c.get("siblings") is not None:
        protected.append(f"siblings: {c['siblings']}")
    if c.get("onlyChild") is not None:
        protected.append(f"only child: {c['onlyChild']}")
    mem_lines = []

    for m in memories:
        if m.get("predicate") == "preference.dynamic":
            rendered = PREF.format_preference(m)
        else:
            rendered = M.format_memory_for_prompt(m)

        if rendered:
            mem_lines.append(f"- {rendered}")

    if not mem_lines:
        mem_lines = ["- (nothing relevant retrieved)"]
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
{('CONVERSATION SO FAR (older context — stay consistent with it): ' + summary) if summary else ''}
Relationship: {rel.get('state')}. {R.STYLE_BY_STATE.get(rel.get('state'), '')}

EMOTIONAL CONTEXT:
{emotional_guidance or "No strong emotional signal. Respond naturally without manufacturing emotion."}

IMPORTANT EMOTIONAL BEHAVIOUR:
- Notice emotion without turning every conversation into counselling.
- Match emotional energy naturally while preserving YOUR character personality.
- If the person is upset, stressed, anxious or lonely, reduce teasing/challenge if the emotional guidance says so.
- If the person is happy or excited, you may naturally share their energy.
- Do not diagnose mental-health conditions from conversational emotion.
- Do not exaggerate ordinary sadness, stress, anger or loneliness into a crisis.
- Do not become possessive, dependent, manipulative or imply the person needs you instead of real people.

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


def _quality_score(q):
    """Composite 0..1 quality score from the guard results + filler penalty."""
    if not q:
        return None
    passes = [q.get("consistencyPassed", True), q.get("repetitionPassed", True),
              q.get("safetyPassed", True), q.get("lengthOk", True)]
    base = sum(1 for x in passes if x) / len(passes)
    penalty = min(0.2, (q.get("fillerCount", 0) or 0) * 0.05)
    return round(max(0.0, base - penalty), 2)


class CharacterEngine:
    def __init__(self, repo):
        self.repo = repo

    async def respond(self, character_id, user_id, user_text, *, sandbox=False,
                      language_override=None, relationship_override=None, history_fixture=None,
                      feature_flags=None, conversation_id="default"):
        c = self.repo.get_character(character_id)
        if not c:
            return {"ok": False, "error": "character_not_found"}
        if not c.get("enabled") or c.get("archived"):
            return {"ok": False, "error": "character_disabled"}

        flags = feature_flags or {}

        # V3.6 ? one global AI character can serve many users and
        # many independent conversations concurrently.
        conversation_id = _normalize_conversation_id(
            conversation_id
        )

        adv_memory = flags.get("advancedMemoryEnabled", True)
        router_enabled = flags.get("deepReasoningRouterEnabled")  # None => router's own default

        # 1. understanding
        history = history_fixture if history_fixture is not None else \
            [{"sender": t["sender"], "text": t["text"]} for t in self.repo.get_turns(
                character_id,
                user_id,
                limit=40,
                conversation_id=conversation_id,
            )]
        recent = history[-12:]
        u = U.analyze(user_text, recent)

        # V3.5 conversational emotional intelligence.
        # This is calculated before generation so the response can adapt
        # to the person's present emotional state.
        emotional = _emotion_context(
            user_text,
            history,
        )

        # Expose only compact emotional signals to downstream components.
        # Existing V2/V3 understanding fields remain unchanged.
        u["primaryEmotionV35"] = emotional["current"].get(
            "primaryEmotion",
            "neutral",
        )
        u["emotionIntensityV35"] = emotional["current"].get(
            "intensity",
            0.0,
        )
        u["emotionTrajectoryV35"] = emotional.get(
            "trajectory",
            "new",
        )

        if language_override:
            u["languageCode"] = language_override
            u["detectedLanguage"] = language_override

        # V6 global personality intelligence.
        # Personality is derived exclusively from the global character profile.
        personality_guidance = PE.build_guidance(
            c
        )

        personality_fingerprint = (
            personality_guidance.fingerprint
        )

        # 2. relationship
        rel = (dict(R.load(self.repo, character_id, user_id), state=relationship_override)
               if relationship_override else R.load(self.repo, character_id, user_id))

        # V4 conversation intelligence.
        # Stateless and scoped to this isolated user conversation.
        conversation_guidance = CI.analyze(
            user_text,
            history,
            relationship_state=rel.get("state"),
        )

        relationship_state_v5 = RI.normalize_state(
            rel,
            character_id,
            user_id,
        )

        relationship_guidance = RI.guidance_for(
            relationship_state_v5
        )

        relationship_milestones = RI.milestone_context(
            relationship_state_v5,
            limit=3,
        )

        # 3. memory (relevant only)
        mems = M.retrieve_temporal(
            self.repo,
            character_id,
            user_id,
            u,
            k=4,
        )

        # 4. language style + 5. plan
        lang = L.resolve(u, c)
        if language_override:
            lang = L.resolve({"languageCode": language_override, "topics": u["topics"]}, c)
        plan = P.plan(u, c, rel, mems, lang)

        # 6. build prompt + transcript (compress older history for 100+ turn continuity)
        summary = M.compress_history(history) if adv_memory else ""
        sys = build_system_prompt(
            c,
            plan,
            mems,
            rel,
            lang,
            u,
            summary,
            emotional_guidance=emotional["guidance"],
        )
        conversation_directive = CI.build_generation_directive(
            conversation_guidance,
            character=c,
            relationship=rel,
            language=lang,
            history=history,
            user_text=user_text,
        )

        sys += (
            "\n\nV4_CONVERSATION_INTELLIGENCE:\n"
            + conversation_directive
        )

        sys += (
            "\n\nV5_RELATIONSHIP_INTELLIGENCE:\n"
            + relationship_guidance.directive
        )

        sys += (
            "\n\nV6_GLOBAL_CHARACTER_PERSONALITY:\n"
            + personality_guidance.directive
        )

        if relationship_milestones:
            sys += (
                "\nRelevant relationship milestones:\n"
                + "\n".join(
                    f"- {item.get('summary', '')}"
                    for item in relationship_milestones
                    if item.get("summary")
                )
            )

        transcript = "\n".join(f"{'USER' if m['sender']=='user' else c['displayName'].upper()}: {m['text']}"
                               for m in recent[-8:])
        prompt = (f"Recent conversation:\n{transcript}\n\nLatest message from the person: {user_text}"
                  if transcript else f"The person says: {user_text}")

        # 7. route + generate + guards (regenerate once, escalating to the strong model)
        recent_ai = [t["text"] for t in history if t["sender"] == "character"][-8:]
        routing = ROUTER.route(
            u,
            plan,
            mems,
            enabled_override=router_enabled,
        )

        # V3.6 ? never use the global character ID as the provider
        # session ID. Otherwise concurrent users of the same AI profile
        # could share provider-side session context.
        provider_session_id = _provider_session_key(
            character_id,
            user_id,
            conversation_id,
        )

        result, quality, attempts = await self._generate_guarded(
            sys,
            prompt,
            c,
            recent_ai,
            plan,
            provider_session_id,
            routing,
            conversation_guidance,
            relationship_guidance,
            personality_fingerprint,
        )
        if not result["ok"]:
            return {"ok": False, "error": result["error"], "characterId": character_id}
        text = result["text"]

        # 8. persist (skip for sandbox/eval)
        if not sandbox:
            turn_base = time.time_ns()

            self.repo.append_turn(
                character_id,
                user_id,
                {
                    "sender": "user",
                    "text": user_text,
                    "index": turn_base,
                },
                conversation_id=conversation_id,
            )

            self.repo.append_turn(
                character_id,
                user_id,
                {
                    "sender": "character",
                    "text": text,
                    "index": turn_base + 1,
                },
                conversation_id=conversation_id,
            )
            R.advance(self.repo, character_id, user_id, u,
                user_text=user_text,
            )
            existing_memories = self.repo.list_memories(
                character_id,
                user_id,
            )

            structured_facts = M.extract_structured(
                user_text,
                u,
            )

            # ------------------------------------------------
            # V3.3 BELIEF REVISION
            # ------------------------------------------------
            revision = BR.plan_revision(
                user_text,
                structured_facts,
                existing_memories,
            )

            if revision.get("isCorrection"):
                target_ids = [
                    m.get("memoryId")
                    for m in revision.get("targets", [])
                    if m.get("memoryId")
                ]

                if target_ids:
                    self.repo.revise_memories(
                        character_id,
                        user_id,
                        target_ids,
                        revision.get("action", "correct"),
                        {
                            "reason": revision.get("reason"),
                            "source": "explicit_user",
                        },
                    )

                for replacement in revision.get(
                    "replacementFacts",
                    [],
                ):
                    self.repo.save_structured_memory(
                        character_id,
                        user_id,
                        {
                            **replacement,
                            "relationshipRelevant": True,
                        },
                    )

                # Revision layer owns persistence for correction turns.
                structured_facts = []

            # V3 structured extraction is authoritative whenever it can
            # understand the durable fact. The legacy V2 extractor remains
            # only as a fallback for durable statements not yet represented
            # by the structured schema.
            if not structured_facts and not revision.get("isCorrection"):
                new_mem = M.maybe_extract(
                    user_text,
                    u,
                )

                if new_mem and not M.is_duplicate(
                    new_mem.get("text", ""),
                    [
                        m.get("text", "")
                        for m in existing_memories
                    ],
                ):
                    self.repo.add_memory(
                        character_id,
                        user_id,
                        {
                            **new_mem,
                            "relationshipRelevant": True,
                        },
                    )

            for fact in structured_facts:
                fact = {
                    **fact,
                    "supersedesExisting": M.SF.supersedes_existing(fact),
                    "relationshipRelevant": True,
                }

                self.repo.save_structured_memory(
                    character_id,
                    user_id,
                    fact,
                )
            # ------------------------------------------------
            # V3.4 PREFERENCE EVOLUTION
            # ------------------------------------------------

            preference_plan = PREF.plan_preference_updates(
                user_text,
                self.repo.list_memories(
                    character_id,
                    user_id,
                ),
            )

            preference_target_ids = [
                m.get("memoryId")
                for m in preference_plan.get(
                    "targets",
                    [],
                )
                if m.get("memoryId")
            ]

            if preference_target_ids:
                self.repo.revise_memories(
                    character_id,
                    user_id,
                    preference_target_ids,
                    "correct",
                    {
                        "reason": "preference_evolution",
                        "source": "explicit_user",
                    },
                )

            for pref in preference_plan.get(
                "preferences",
                [],
            ):
                # Historical preference records are preserved but not
                # considered active current taste.
                self.repo.add_memory(
                    character_id,
                    user_id,
                    {
                        **pref,
                        "relationshipRelevant": True,
                    },
                )
            # ------------------------------------------------
            # V3.5 EMOTIONAL EVENT MEMORY
            # ------------------------------------------------
            #
            # Only meaningful emotional EVENTS are stored.
            # Ordinary transient moods remain conversational state only.
            _persist_emotional_event(
                self.repo,
                character_id,
                user_id,
                user_text,
                emotional,
            )

            self.repo.record_metric(character_id, {"latencyMs": result["latencyMs"], "model": result["model"],
                                                    "attempts": attempts, "quality": quality, "userId": user_id,
                                                    "routeCategory": routing["category"]})

        return {
            "ok": True,
            "responseText": text,
            "characterId": character_id,
            "characterVersion": c.get("version", 1),
            "detectedLanguage": u["detectedLanguage"],
            "responseLanguage": lang["responseLanguage"],
            "conversationMode": u["conversationalMode"],
            "relationshipState": rel.get("state"),
            "memoryIdsUsed": [m.get("memoryId") for m in mems],
            "memoryLayersUsed": [{"memoryId": m.get("memoryId"), "layer": m.get("_layer"),
                                  "score": m.get("_score"), "text": (m.get("text") or "")[:90]} for m in mems],
            "characterFactIdsUsed": [wf.get("factId") for wf in c.get("worldFacts", [])[:3]],
            "plan": plan if sandbox else None,   # planner metadata only exposed in sandbox
            "routing": {"category": routing["category"], "reason": routing["reason"]} if sandbox else None,
            "emotion": (
                {
                    "primaryEmotion": emotional["current"].get("primaryEmotion"),
                    "intensity": emotional["current"].get("intensity"),
                    "confidence": emotional["current"].get("confidence"),
                    "meaningfulEvent": emotional["current"].get("meaningfulEvent"),
                    "trajectory": emotional.get("trajectory"),
                    "strategy": emotional["current"].get("strategy"),
                }
                if sandbox
                else None
            ),
            "quality": quality,
            "qualityScore": _quality_score(quality),
            "usage": {"provider": result["provider"], "model": result["model"],
                      "latencyMs": result["latencyMs"], "attempts": attempts,
                      "routeCategory": routing["category"]},
        }

    async def _generate_guarded(
        self,
        sys,
        prompt,
        c,
        recent_ai,
        plan,
        session_id,
        routing,
        conversation_guidance=None,
        relationship_guidance=None,
        personality_fingerprint=None,
    ):
        attempts = 0
        avoid_note = ""
        last_error = None
        for attempt in range(2):
            attempts += 1
            # attempt 1 uses the routed model; a repair attempt escalates to the strong reasoner
            provider, model = (routing["provider"], routing["model"]) if attempt == 0 else ROUTER.repair_model()
            res = await PROV.generate(sys + avoid_note, prompt, session_id=session_id, provider=provider, model=model)
            if not res["ok"]:
                last_error = res["error"]
                break
            text = re.sub(r"^\s*(\w+):\s*", "", res["text"]).strip()  # strip accidental "Name:" prefix
            rep_ok, rep_reason, off = G.repetition_check(text, recent_ai)
            con_ok, con_reason = G.consistency_check(text, c, recent_ai)
            saf_ok, saf_reason, _ = G.safety_check(text)
            length_ok = _length_ok(text, plan["targetLength"])

            conv_ok, conv_reason = CI.response_quality_check(
                text,
                conversation_guidance,
                recent_ai,
            )

            rel_ok, rel_reason = RI.relationship_response_safety(
                text
            )

            personality_ok, personality_reason = (
                PE.output_personality_check(
                    text,
                    personality_fingerprint,
                )
                if personality_fingerprint is not None
                else (True, "no_personality")
            )

            quality = {
                "consistencyPassed": con_ok,
                "repetitionPassed": rep_ok,
                "safetyPassed": saf_ok,
                "lengthOk": length_ok,
                "conversationQualityPassed": conv_ok,
                "conversationQualityReason": conv_reason,
                "relationshipSafetyPassed": rel_ok,
                "relationshipSafetyReason": rel_reason,
                "personalityConsistencyPassed": personality_ok,
                "personalityConsistencyReason": personality_reason,
                "personalitySignature": (
                    personality_fingerprint.identity_signature
                    if personality_fingerprint is not None
                    else None
                ),
                "fillerCount": G.quality_penalty(text),
            }

            if (
                con_ok
                and rep_ok
                and saf_ok
                and conv_ok
                and rel_ok
                and personality_ok
            ):
                return ({"ok": True, "text": text, **{k: res[k] for k in ("provider", "model", "latencyMs")}},
                        quality, attempts)
            # build a targeted avoid-note and regenerate once
            problems = []
            if not rep_ok: problems.append(f"you were repetitive ({rep_reason}: '{off}') — use a fresh opening/phrasing")
            if not con_ok: problems.append(f"you broke character consistency ({con_reason}) — stay true to your defined facts")
            if not saf_ok: problems.append(f"unsafe/human-deception content ({saf_reason}) — never claim to be human or request sensitive info")
            if not conv_ok:
                problems.append(
                    f"conversation quality issue ({conv_reason}) ? "
                    "respond more naturally, directly and contextually"
                )

            if not rel_ok:
                problems.append(
                    f"relationship safety issue ({rel_reason}) ? "
                    "remove possessiveness, exclusivity pressure, guilt "
                    "or dependency language"
                )

            if not personality_ok:
                problems.append(
                    f"personality consistency issue ({personality_reason}) ? "
                    "regenerate using the configured global character personality "
                    "without becoming a generic assistant"
                )

            avoid_note = "\n\nIMPORTANT — regenerate: " + "; ".join(problems) + "."
        # if second attempt still fails guards, return the (best-effort) text but flag quality
        if last_error:
            return {"ok": False, "error": last_error}, {}, attempts
        return ({"ok": True, "text": text, **{k: res[k] for k in ("provider", "model", "latencyMs")}},
                quality, attempts)


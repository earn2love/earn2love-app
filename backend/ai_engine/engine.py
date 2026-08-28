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
from ai_engine import adaptive_intelligence as AI
from ai_engine import goal_intelligence as GI
from ai_engine import proactive_intelligence as PI
from ai_engine import reasoning_intelligence as RI9
from ai_engine import plan_intelligence as PL9
from ai_engine import execution_intelligence as EX9
from ai_engine import verification_intelligence as VE9
from ai_engine import orchestration_intelligence as OI10
from ai_engine import routing_intelligence as RT10
from ai_engine import context_intelligence as CX10
from ai_engine import reliability_intelligence as RL10
from ai_engine import memory_retrieval_intelligence as MR11
from ai_engine import conversation_continuity_intelligence as CC11
from ai_engine import preference_learning_intelligence as PL11
from ai_engine import memory_integrity_intelligence as MI11
from ai_engine import provider as PROV
from ai_engine import freshness_intelligence as FI12
from ai_engine import live_knowledge_intelligence as LK12
from ai_engine import live_knowledge_provider as LKP12
from ai_engine import engagement_intelligence as EI12
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


V11_ENGINE_MARKER = (
    "V11_LONG_TERM_MEMORY_CONTINUITY_INTELLIGENCE"
)


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

        # V11.3 conversational continuity intelligence.
        #
        # Continuity is derived ephemerally from the existing
        # conversation-scoped turn history. V11 does not create
        # or persist a second thread-state store.
        v11_continuity_threads = []

        if history:
            continuity_text = " ".join(
                str(
                    item.get(
                        "text",
                        "",
                    )
                ).strip()
                for item in history[-12:]
                if str(
                    item.get(
                        "text",
                        "",
                    )
                ).strip()
            )

            continuity_topic = " ".join(
                str(topic)
                for topic in u.get(
                    "topics",
                    [],
                )[:3]
                if str(topic).strip()
            )

            if not continuity_topic:
                continuity_topic = continuity_text[:160]

            v11_continuity_thread = (
                CC11.build_thread_candidate(
                    thread_id=conversation_id,
                    topic=continuity_topic,
                    summary=continuity_text[:800],
                    turn_count=len(history),
                    last_turn_index=len(history),
                    status="active",
                )
            )

            v11_continuity_threads.append(
                {
                    "threadId":
                        v11_continuity_thread.thread_id,

                    "topic":
                        v11_continuity_thread.topic,

                    "summary":
                        v11_continuity_thread.summary,

                    "status":
                        v11_continuity_thread.status,

                    "unresolved":
                        v11_continuity_thread.unresolved,

                    "commitment":
                        v11_continuity_thread.commitment,

                    "turnCount":
                        v11_continuity_thread.turn_count,

                    "lastTurnIndex":
                        v11_continuity_thread.last_turn_index,
                }
            )

        v11_continuity = CC11.analyze_continuity(
            user_text,
            v11_continuity_threads,
            active_thread_id=(
                conversation_id
                if v11_continuity_threads
                else ""
            ),
            current_topic=" ".join(
                str(topic)
                for topic in u.get(
                    "topics",
                    [],
                )[:3]
                if str(topic).strip()
            ),
        )

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

        # V7 adaptive communication intelligence.
        # This state is isolated by global character + user.
        adaptation_state = self.repo.get_adaptation(
            character_id,
            user_id,
        )

        adaptation_guidance = AI.combined_adaptation_guidance(
            user_text,
            adaptation_state,
        )

        # V8 goal / intent / proactive / decision intelligence.
        # Persistent state is isolated by character + user.
        # Reading state here does not persist learning.
        goal_state = self.repo.get_goal_state(
            character_id,
            user_id,
        )

        goal_guidance = GI.build_goal_guidance(
            user_text,
            goal_state,
        )

        # Use goal age as a bounded anti-annoyance signal.
        # Explicit requests for next steps continue to override it.
        proactive_suppression_turns = min(
            int(
                goal_state.get(
                    "goalTurnCount",
                    0,
                )
                or 0
            ),
            2,
        )

        proactive_guidance = PI.build_intelligence_guidance(
            user_text,
            has_active_goal=GI.has_active_goal(
                goal_state
            ),
            prior_proactive_turns=proactive_suppression_turns,
        )

        # V9 structured reasoning / plan execution intelligence.
        # Persistent plan state is isolated by character + user.
        # Reading and guidance construction never mutate state.
        plan_state = self.repo.get_plan_state(
            character_id,
            user_id,
        )

        reasoning_guidance = RI9.build_reasoning_guidance(
            user_text,
        )

        plan_guidance = PL9.build_plan_guidance(
            user_text,
            plan_state,
            character_id,
            user_id,
            goal_state,
        )

        execution_guidance = EX9.build_execution_guidance(
            user_text,
            plan_state,
            character_id,
            user_id,
        )

        verification_guidance = VE9.build_verification_guidance(
            user_text,
            plan_state,
            character_id,
            user_id,
        )

        # V3 memory candidates must exist before V10 orchestration.
        #
        # This is the same V3 memory source used by V11 later in the
        # pipeline. Retrieval is read-only and scoped by character+user.
        mems = M.retrieve_temporal(
            self.repo,
            character_id,
            user_id,
            u,
            k=4,
        )

        # V10 adaptive orchestration intelligence.
        #
        # V10 is a pure decision layer. It reads existing structured
        # intelligence but never mutates V6 personality, V7 adaptation,
        # V8 goals, or V9 plan state.
        orchestration_guidance = OI10.build_orchestration_guidance(
            user_text,
            intent=goal_guidance.intent,
            reasoning=reasoning_guidance.analysis,
            plan_state=plan_state,
            execution=execution_guidance.analysis,
            verification=verification_guidance.analysis,
            memories=mems,
        )

        v10_routing = RT10.choose_route(
            orchestration_guidance.decision,
            user_text=user_text,
            memory_count=len(mems or []),
            active_goal=GI.has_active_goal(
                goal_state
            ),
            active_plan=PL9.has_active_plan(
                plan_state
            ),
        )

        context_selection = CX10.select_context(
            orchestration_guidance.decision,
            history_count=len(history or []),
            memory_count=len(mems or []),
            has_active_goal=GI.has_active_goal(
                goal_state
            ),
            has_active_plan=PL9.has_active_plan(
                plan_state
            ),
        )


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

        # 3. memory relevance refinement.
        #
        # Raw V3 memory candidates were loaded earlier because V10
        # orchestration/routing/context sizing also needs their count.
        # V11 now refines those same V3 candidates; no second source.
        #
        # V11.1 + V11.2 long-term memory intelligence.
        #
        # V11 retrieval evaluates lifecycle strength, decay eligibility,
        # query relevance and historical safety without mutating memory.
        # It extends the V3 memory candidates rather than replacing V3.
        v11_memory_source = mems

        if MR11.is_historical_recall(
            user_text
        ):
            v11_memory_source = self.repo.list_memories(
                character_id,
                user_id,
            )

        v11_memory_retrieval = MR11.select_memories(
            v11_memory_source,
            user_text,
            topics=u.get(
                "topics",
                [],
            ),
            relationship_relevant=bool(
                relationship_milestones
            ),
            limit=4,
            allow_lifecycle_fallback=False,
        )

        v11_mems = list(
            v11_memory_retrieval.selected
        )

        # V10 remains the final context-budget authority.
        #
        # Explicit V11 historical/revision recall requires at least one
        # authorized memory slot; otherwise a V10 mode whose ordinary
        # budget is zero would make explicit recall unreachable.
        #
        # Preserve every other V10 context-selection field unchanged.
        v11_explicit_history = MR11.is_historical_recall(
            user_text
        )

        v11_context_selection = context_selection

        if (
            v11_explicit_history
            and v11_mems
            and context_selection.memory_limit < 1
        ):
            v11_context_selection = CX10.ContextSelection(
                recent_turn_limit=(
                    context_selection.recent_turn_limit
                ),
                memory_limit=1,
                include_summary=(
                    context_selection.include_summary
                ),
                include_goal=(
                    context_selection.include_goal
                ),
                include_plan=(
                    context_selection.include_plan
                ),
                include_relationship=(
                    context_selection.include_relationship
                ),
                include_adaptation=(
                    context_selection.include_adaptation
                ),
                include_verification=(
                    context_selection.include_verification
                ),
                reason=(
                    context_selection.reason
                    + "; explicit V11 historical recall"
                ),
            )

        selected_mems = CX10.select_memories(
            v11_mems,
            v11_context_selection,
        )

        selected_history = CX10.select_recent_turns(
            history,
            context_selection,
        )

        # 4. language style + 5. legacy response-style plan
        lang = L.resolve(u, c)
        if language_override:
            lang = L.resolve({"languageCode": language_override, "topics": u["topics"]}, c)
        plan = P.plan(
            u,
            c,
            rel,
            selected_mems,
            lang,
        )

        # 6. build prompt + transcript.
        #
        # Summarization remains the existing memory-layer responsibility,
        # while V10 decides when a long-history summary is worth including.
        summary = (
            CX10.bound_summary(
                M.compress_history(history)
            )
            if (
                adv_memory
                and context_selection.include_summary
            )
            else ""
        )
        sys = build_system_prompt(
            c,
            plan,
            selected_mems,
            rel,
            lang,
            u,
            summary,
            emotional_guidance=emotional["guidance"],
        )
        v11_continuity_safe = CC11.safe_continuity_copy(
            v11_continuity
        )

        sys += (
            "\n\nV11_CONVERSATION_CONTINUITY:\n"
            f"- Mode: {v11_continuity_safe.get('mode', 'new')}\n"
            f"- Topic: {v11_continuity_safe.get('topic', '')}\n"
            f"- Explicit resume: "
            f"{v11_continuity_safe.get('explicit_resume', False)}\n"
            f"- Explicit return: "
            f"{v11_continuity_safe.get('explicit_return', False)}\n"
            "Use this only to preserve conversational continuity. "
            "Do not mention internal thread IDs or analysis metadata."
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

        # V12 conversation engagement intelligence.
        #
        # Stateless generation policy only:
        # - V4 remains the hard question-count authority;
        # - V11-selected memories are the only callback candidates;
        # - V6 global personality is never mutated;
        # - no persistence or provider call occurs in this layer.
        engagement_guidance = EI12.build_engagement_guidance(
            user_text,
            conversation_guidance,
            selected_memories=selected_mems,
            relationship=rel,
            history=history,
        )

        sys += (
            "\n\nV12_CONVERSATION_ENGAGEMENT_INTELLIGENCE:\n"
            + engagement_guidance.directive
        )

        sys += (
            "\n\nV5_RELATIONSHIP_INTELLIGENCE:\n"
            + relationship_guidance.directive
        )

        sys += (
            "\n\nV6_GLOBAL_CHARACTER_PERSONALITY:\n"
            + personality_guidance.directive
        )

        sys += (
            "\n\nV7_ADAPTIVE_INTELLIGENCE:\n"
            + adaptation_guidance.directive
        )

        sys += (
            "\n\nV8_GOAL_INTENT_PROACTIVE_DECISION_INTELLIGENCE:\n"
            + goal_guidance.directive
            + "\n"
            + proactive_guidance.directive
        )

        sys += (
            "\n\nV9_REASONING_PLANNING_EXECUTION_VERIFICATION_INTELLIGENCE:\n"
            + reasoning_guidance.directive
            + "\n"
            + plan_guidance.directive
            + "\n"
            + execution_guidance.directive
            + "\n"
            + verification_guidance.directive
        )

        sys += (
            "\n\nV10_ADAPTIVE_ORCHESTRATION_INTELLIGENCE:\n"
            + orchestration_guidance.directive
            + "\n"
            + CX10.build_context_guidance(
                orchestration_guidance.decision,
                history_count=len(history or []),
                memory_count=len(mems or []),
                has_active_goal=GI.has_active_goal(
                    goal_state
                ),
                has_active_plan=PL9.has_active_plan(
                    plan_state
                ),
            )
            + "\n"
            + RT10.build_routing_guidance(
                orchestration_guidance.decision,
                user_text=user_text,
                memory_count=len(mems or []),
                active_goal=GI.has_active_goal(
                    goal_state
                ),
                active_plan=PL9.has_active_plan(
                    plan_state
                ),
            )
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

        transcript_source = (
            selected_history
            if selected_history
            else recent
        )

        # V12 live knowledge / freshness intelligence.
        #
        # Stateless public-knowledge layer:
        # - current/historical facts may use external retrieval;
        # - public live facts are never written into V11 user memory;
        # - router.py remains normal model/provider authority;
        # - provider.py remains normal conversational LLM boundary;
        # - if current evidence is unavailable, stale model knowledge
        #   must not be presented as verified current information.
        freshness_decision = FI12.assess_freshness(
            user_text
        )

        live_search_result = None
        live_knowledge_packet = None
        live_knowledge_context = ""

        if freshness_decision.requires_live_retrieval:
            live_search_result = await LKP12.search_live(
                user_text
            )

            live_knowledge_packet = LK12.build_live_knowledge_packet(
                user_text,
                (
                    list(live_search_result.results)
                    if live_search_result is not None
                    and live_search_result.ok
                    else []
                ),
                requires_live_retrieval=True,
            )

            live_knowledge_context = LK12.build_grounding_context(
                live_knowledge_packet
            )

            sys += (
                "\n\nV12_LIVE_KNOWLEDGE_INTELLIGENCE:\n"
                + live_knowledge_context
            )

        else:
            # Keep the classification available for structured metadata
            # without invoking any external retrieval.
            live_knowledge_packet = None

        transcript = "\n".join(
            f"{'USER' if m['sender']=='user' else c['displayName'].upper()}: {m['text']}"
            for m in transcript_source[
                -context_selection.recent_turn_limit:
            ]
        )
        prompt = (f"Recent conversation:\n{transcript}\n\nLatest message from the person: {user_text}"
                  if transcript else f"The person says: {user_text}")

        # 7. route + generate + guards (regenerate once, escalating to the strong model)
        recent_ai = [t["text"] for t in history if t["sender"] == "character"][-8:]
        # Existing router.py remains authoritative for actual provider/model
        # configuration. V10 supplies only the orchestration-aware category.
        routing = ROUTER.route(
            u,
            plan,
            selected_mems,
            category_override=(
                v10_routing.category
                if (
                    router_enabled is not False
                )
                else None
            ),
            enabled_override=router_enabled,
        )

        # Keep V10's deterministic explanation for observability.
        routing["v10Reason"] = (
            v10_routing.reason
        )
        routing["v10Confidence"] = (
            v10_routing.confidence
        )
        routing["v10Mode"] = (
            orchestration_guidance.decision.mode
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
            adaptation_guidance,
            orchestration_guidance,
        )
        if not result["ok"]:
            return {"ok": False, "error": result["error"], "characterId": character_id}
        text = result["text"]

        # ------------------------------------------------
        # V12 DETERMINISTIC LIVE-KNOWLEDGE FAIL-CLOSED GUARD
        # ------------------------------------------------
        #
        # Prompt grounding alone is not a sufficient production
        # guarantee for freshness-required facts. If live retrieval
        # could not establish an answerable evidence packet, never
        # allow possibly stale model knowledge to reach the user or
        # conversation history.
        #
        # This guard intentionally runs AFTER normal guarded generation
        # and BEFORE the existing persistence lifecycle so V3-V11 turn,
        # relationship, goal, plan, adaptation, memory, and metrics
        # semantics remain unchanged.
        #
        # Public live facts remain ephemeral and are not converted into
        # durable user memory by this guard.
        live_knowledge_fail_closed = bool(
            freshness_decision.requires_live_retrieval
            and live_knowledge_packet is not None
            and not live_knowledge_packet.can_answer
        )

        if live_knowledge_fail_closed:
            text = (
                "I can't verify the current information right now, "
                "so I don't want to guess."
            )

        # 8. persist (skip for sandbox/eval)
        if not sandbox:

            # V8 per-user goal / intent persistence.
            # Firestore repository advances this transactionally.
            updated_goal_state = self.repo.advance_goal_state(
                character_id,
                user_id,
                user_text,
            )

            # V9 per-user reasoning / execution plan persistence.
            # Firestore repository advances this transactionally.
            self.repo.advance_plan_state(
                character_id,
                user_id,
                user_text,
                updated_goal_state,
            )

            # V7 per-user preference learning.
            # Firestore implementation performs this transactionally.
            self.repo.advance_adaptation(
                character_id,
                user_id,
                user_text,
            )

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

            # ------------------------------------------------
            # V11.4 + V11.5 EXPLICIT PREFERENCE INTELLIGENCE
            # ------------------------------------------------
            #
            # Candidate extraction is pure.
            # Scope is attached here by the engine rather than trusted
            # from candidate data.
            # Persistence remains inside the existing non-sandbox gate.
            v11_preference_signal = PL11.analyze_preference(
                user_text
            )

            v11_preference_handled = False

            if (
                v11_preference_signal.detected
                and v11_preference_signal.explicit
                and v11_preference_signal.owner == "memory"
                and v11_preference_signal.should_persist
            ):
                v11_preference_candidate = (
                    PL11.build_memory_candidate(
                        v11_preference_signal
                    )
                )

                if v11_preference_candidate:
                    v11_scoped_candidate = {
                        **v11_preference_candidate,
                        "characterId": character_id,
                        "userId": user_id,
                        "status": "active",
                        "relationshipRelevant": True,
                    }

                    v11_integrity = MI11.assess_integrity(
                        existing_memories,
                        v11_scoped_candidate,
                        user_id=user_id,
                        character_id=character_id,
                    )

                    if (
                        v11_integrity.allowed
                        and v11_integrity.action
                        == "reinforce"
                        and v11_integrity.reinforcement_memory_id
                    ):
                        reinforced = self.repo.reinforce_memory(
                            character_id,
                            user_id,
                            v11_integrity.reinforcement_memory_id,
                        )

                        v11_preference_handled = (
                            reinforced is not None
                        )

                    elif (
                        v11_integrity.allowed
                        and v11_integrity.action
                        == "accept"
                    ):
                        self.repo.add_memory(
                            character_id,
                            user_id,
                            {
                                **v11_preference_candidate,
                                "relationshipRelevant": True,
                            },
                        )

                        v11_preference_handled = True

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

            preference_plan = (
                PREF.plan_preference_updates(
                    user_text,
                    self.repo.list_memories(
                        character_id,
                        user_id,
                    ),
                )
                if not v11_preference_handled
                else {
                    "targets": [],
                    "preferences": [],
                }
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
            "freshness": freshness_decision.to_dict(),
            "liveKnowledge": (
                {
                    "used": True,
                    "status": live_knowledge_packet.status,
                    "canAnswer": live_knowledge_packet.can_answer,
                    "confidence": live_knowledge_packet.confidence,
                    "retrievedAt": live_knowledge_packet.retrieved_at,
                    "provider": (
                        live_search_result.provider
                        if live_search_result is not None
                        else None
                    ),
                    "retrievalModel": (
                        live_search_result.model
                        if live_search_result is not None
                        else None
                    ),
                    "retrievalError": (
                        live_search_result.error
                        if live_search_result is not None
                        else None
                    ),
                    "sources": [
                        {
                            "title": item.title,
                            "url": item.url,
                            "domain": item.source_domain,
                            "authoritative": item.authoritative,
                        }
                        for item in (
                            live_knowledge_packet.evidence[:5]
                        )
                    ],
                }
                if freshness_decision.requires_live_retrieval
                and live_knowledge_packet is not None
                else {
                    "used": False,
                    "status": None,
                    "canAnswer": True,
                    "confidence": None,
                    "retrievedAt": None,
                    "provider": None,
                    "retrievalModel": None,
                    "retrievalError": None,
                    "sources": [],
                }
            ),
            "characterId": character_id,
            "characterVersion": c.get("version", 1),
            "detectedLanguage": u["detectedLanguage"],
            "responseLanguage": lang["responseLanguage"],
            "conversationMode": u["conversationalMode"],
            "relationshipState": rel.get("state"),
            "memoryIdsUsed": [m.get("memoryId") for m in selected_mems],
            "memoryLayersUsed": [{"memoryId": m.get("memoryId"), "layer": m.get("_layer"),
                                  "score": m.get("_score"), "text": (m.get("text") or "")[:90]} for m in selected_mems],
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
            "usage": {
                "provider": result["provider"],
                "model": result["model"],
                "latencyMs": result["latencyMs"],
                "attempts": attempts,
                "routeCategory": routing["category"],
                "v10Mode": routing.get(
                    "v10Mode"
                ),
                "v10RouteReason": routing.get(
                    "v10Reason"
                ),
                "v10RouteConfidence": routing.get(
                    "v10Confidence"
                ),
                "v10ContextRecentTurns": (
                    context_selection.recent_turn_limit
                ),
                "v10ContextMemoryItems": (
                    context_selection.memory_limit
                ),
            },
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
        adaptation_guidance=None,
        orchestration_guidance=None,
    ):
        attempts = 0
        avoid_note = ""
        last_error = None

        # V7 guidance must remain a delivery-layer adaptation only.
        # The global V6 personality remains authoritative.
        if adaptation_guidance is not None:
            adaptation_context = adaptation_guidance.context.context_type
        else:
            adaptation_context = None
        for attempt in range(2):
            attempts += 1
            # attempt 1 uses the routed model; a repair attempt escalates to the strong reasoner
            provider, model = (routing["provider"], routing["model"]) if attempt == 0 else ROUTER.repair_model()
            res = await PROV.generate(sys + avoid_note, prompt, session_id=session_id, provider=provider, model=model)
            if not res["ok"]:
                last_error = res["error"]

                reliability = RL10.decide_reliability(
                    provider_ok=False,
                    provider_error=last_error,
                    attempt=attempts,
                    verification_required=(
                        bool(
                            orchestration_guidance
                            and orchestration_guidance.decision.requires_verification
                        )
                    ),
                )

                # First provider failure may use the existing strong repair
                # route. A repeated provider failure exits safely.
                if (
                    reliability.action == RL10.ESCALATE
                    and attempt == 0
                ):
                    continue

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

            reliability = RL10.decide_reliability(
                provider_ok=True,
                quality=quality,
                attempt=attempts,
                verification_required=(
                    bool(
                        orchestration_guidance
                        and orchestration_guidance.decision.requires_verification
                    )
                ),
            )

            quality["v10ReliabilityAction"] = (
                reliability.action
            )
            quality["v10ReliabilityConfidence"] = (
                reliability.confidence
            )

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


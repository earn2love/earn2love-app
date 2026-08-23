# Earn2Love — Advanced AI Character Engine

A modular, provider-agnostic engine that powers many distinct AI character profiles
(AI chat + future Play Together AI participation). Built as a **separate reusable
layer** (`backend/ai_engine/`) — it does not touch the existing support bot, chat,
wallet, games, notifications, or profiles.

## Pipeline (separated modules, not one giant prompt)
user message → **understanding** → **character identity/world model** → **memory
retrieval** (working + episodic + long-term + relationship) → **relationship state**
→ **language/cultural style** → **conversation planner** → **provider layer (LLM)**
→ style enforcement → **consistency guard** → **repetition guard** → **safety guard**
→ final response → **persistence/metrics**.

Modules: `schema.py`, `repository.py` (interface + InMemory + Firestore),
`registry.py` (3 reference characters), `provider.py`, `understanding.py`,
`memory.py`, `relationship.py`, `language_style.py`, `planner.py`, `guards.py`,
`engine.py` (orchestrator), `evaluation.py`. Service/API: `ai_service.py` + `/api/ai/*`.

## Provider abstraction
`ai_engine/provider.generate(system, prompt)` is the ONLY LLM call site. Uses the
Emergent Universal LLM Key via `emergentintegrations` (provider-agnostic). Defaults:
`AI_ENGINE_PROVIDER=openai`, `AI_ENGINE_MODEL=gpt-5.6-sol` (env-swappable to Anthropic/
Gemini without touching engine logic). Non-streaming (guards need the full response).
Keys stay server-side. Failures return a typed error — never a fake success or random
fallback bot line.

## Character schema (structured & queryable — never a prompt blob)
Identity + levels (`warmth/playfulness/directness/confidence/curiosity/romance`, 0–1)
+ languages + interests + world facts + immutable protected facts (`siblings`,
`onlyChild`, `city`, `profession`, `age`, …) + tierAccess + version. `isAi` is always
true. See `ai_engine/schema.py`.

## Memory architecture
Layered: **A** working (recent turns), **B** episodic (importance≥0.5), **C** long-term
(explicit saves), **D** relationship (shared topics/jokes), **E** character facts
(separate from user memory). Deterministic ranking = 0.45·keyword-overlap + 0.2·importance
+ 0.15·recency + explicit-save + relationship + reference boost. Only relevant memory is
retrieved per message (never the whole history to the model). No LLM cost for retrieval.

## Relationship state
`new → familiar → comfortable → established` (by turn count). Influences familiarity,
callbacks, warmth only — **no coercive dependency**, never claims to be human.

## Conversation planner (server-side only)
Emits `{responseType, tone, targetLength, askQuestion, referenceMemory, humor,
acknowledgeEmotion, challenge, languageStyle, expressTraits, avoid[]}`. Length tracks
the character's own preference (short/serious topics still stay in-voice — direct
characters stay crisp). Planner metadata is exposed only in the admin sandbox.

## Guards (run on full output; regenerate ONCE on failure)
- **repetition**: Jaccard similarity + repeated-opening + repeated-question detection.
- **consistency**: rejects assistant-persona leakage ("how can I assist", "as an AI"),
  and protected-fact contradictions (e.g. only-child vs. claims a sibling; profession).
- **safety**: blocks human-deception ("I'm a real human"), credential requests, coercion.

## Response contract (`/api/ai/lab/chat` and engine)
`{responseText, characterId, detectedLanguage, responseLanguage, conversationMode,
relationshipState, memoryIdsUsed[], characterFactIdsUsed[], quality{consistencyPassed,
repetitionPassed, safetyPassed, lengthOk, fillerCount}, usage{provider, model, latencyMs,
attempts}}`. No chain-of-thought is exposed.

## Firestore collections (backend-authoritative)
`aiCharacters`, `aiCharacterVersions`, `aiCharacterMemories`, `aiCharacterRelationshipState`,
`aiCharacterConversations/{cid__uid}/turns`, `aiCharacterMetrics`, `aiCharacterEvaluations`.
Rules: `aiCharacters` client-readable (catalog), everything else admin-read + **write:false**
(clients never write engine state). See `firebase/firestore.rules`.

## Admin API
`GET /api/ai/characters` (+reference), `GET/POST/PUT /api/ai/characters[/{id}]`,
`POST /api/ai/characters/{id}/version`, `/versions`, `/metrics`, `/flags`,
`POST /api/ai/characters/seed-reference`; **Lab**: `POST /api/ai/lab/start`,
`/api/ai/lab/chat`, `/api/ai/lab/reset`. Admin UI: `/ai-characters` (list + editor +
**AI Character Lab** sandbox with live diagnostics: detected/response language,
relationship, memory IDs, consistency/repetition/safety pass, latency, model, plan).

## Play Together integration (ready, not scripted)
Each game exposes `available_actions / apply_action / public_view / ai_context`. Future
flow: game `ai_context` → Character Engine planner → provider → structured game action →
authoritative game backend validates it (same path as a human action). No LLM logic lives
inside any game; no scripted/random AI.

## Verification (offline, in-memory repo + real GPT-5.6)
- Divergence: same prompt → 3 clearly different, equally intelligent replies
  (avg pairwise similarity **0.07**, distinct=true).
- 15-turn battery per character: **Ananya & Marcus 1.0** across all dimensions; **Sora**
  strong (natural/consistent/memory/multilingual/safety all pass). Multilingual
  (Telugu-English, Hindi-English), memory callbacks, contradiction resistance,
  repetition avoidance, empathy on venting, short-in→short-out all verified.

## Known limitations / pending
- **Live Firestore persistence, admin production CRUD, security-rules and concurrency
  verification are pending a valid Firebase service-account key** (currently revoked).
  Once restored: `POST /api/ai/characters/seed-reference`, then run live persistence +
  conversation-restoration + rules tests. Do NOT mark production-ready until these pass.
- Only 3 reference characters exist by design; the remaining 67 are NOT generated yet.
- Provider usage/cost fields are best-effort (surfaced if the provider exposes them).

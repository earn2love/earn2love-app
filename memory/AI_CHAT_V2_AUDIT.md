# Phase 1 Audit — Earn2Love Maximum Intelligence AI v2 + Chat v3
Read-only architecture audit. NO code changed in this pass. For approval before further work.

## 0. IMPORTANT STATUS NOTE (already implemented in prior phases)
Some of this "master prompt" was already delivered & live-verified in earlier phases. This audit
distinguishes DONE vs REMAINING so we don't re-do working code:
- DONE: Model Router (5 tiers), AI-chat rate limiting + platform circuit breaker + preview budget,
  AI-chat reliability slice (idempotent clientMessageId, per-(char,user) lock, generationId),
  Understanding v2 (rich deterministic signals), Memory v2 (layered retrieval + dedup + history
  compression), Consistency v2 (semantic anti-repetition + cross-history contradiction), evaluation
  harness (divergence + 15-turn battery), Group Play AI, 70 characters.
- REMAINING (this proposal): Admin Character Lab v2 + Model Benchmark, centralized Feature Flags,
  full evaluation v2 (100/250-turn + contradiction-trap suite) + published report, optional semantic
  (embedding) memory, Firestore index/cost audit for AI collections.

## 1. CURRENT ARCHITECTURE MAP
### AI engine (`/app/backend/ai_engine/`) — modular, NOT one giant prompt
- provider.py — LlmChat wrapper; now accepts provider+model per call (used by router).
- router.py — deterministic 5-tier routing (FAST_SOCIAL gpt-5.4-mini, STANDARD gpt-5.4,
  DEEP_REASONING/MEMORY_HEAVY gpt-5.6-sol, STRUCTURED gpt-5.4); env-tunable; flag AI_ROUTER_ENABLED.
- understanding.py — deterministic intent/emotion/language/reasoning-depth/energy signals.
- language_style.py — multilingual + code-mix (Telugu/Hindi/Tamil-English…).
- relationship.py — states new→familiar→comfortable→established + style.
- memory.py — layered retrieval (explicit/episodic/relationship/working), dedup, compress_history.
- planner.py — response plan (tone/length/question/memory/humour).
- guards.py — semantic repetition + consistency/contradiction + safety.
- engine.py — orchestrator: understanding→relationship→memory→language→plan→route→generate→
  guarded-repair(strong model)→persist→metrics. sandbox flag skips persistence.
- rate_limit.py — per-user (min/hr/day) + dup-spam + platform breaker + preview budget.
- evaluation.py — divergence + 15-turn battery (consistency/repetition/multilingual/safety/memory).
- registry.py / schema.py / repository.py / character_factory.py — 70 characters, Firestore repo.
- games/ai_play.py — Group Play AI (decides valid in-character game moves).
### AI service + endpoints (`ai_service.py`, `server.py`)
- POST /api/ai/chat (persistent, guarded), GET /api/ai/chat/{cid}/history,
  POST /api/ai/lab/* (sandbox), CRUD /api/ai/characters, POST /api/ai/characters/{cid}/flags
  (PER-CHARACTER enabled flag only — no centralized feature-flag store yet).
### Chat surface in THIS repo
- ONLY: /api/support/* (admin↔user tickets, supportTickets/{id}/messages) and the AI chat above.
- NO user↔user chat backend/endpoints/state-machine/delivery/typing/presence/media here.
- Firestore RULES (deliverables/flutter-production-hardening/firebase/firestore.rules) DO declare
  user-chat collections: chats, chatRooms, messages, chatPrefs, calls, blocks, blockedUsers,
  followers/following, friendRequests, likes, media, reports, etc. → the SCHEMA exists but the
  chat ENGINE lives in the Flutter client (not in this repository).

## 2. EXACT REUSE PLAN (remaining work)
- Admin Lab v2: REUSE engine sandbox response (already returns plan+routing) + evaluation.py.
  Extend the existing `/api/ai/lab/*` endpoints and `AICharacters.jsx` Lab dialog. No new engine logic.
- Model Benchmark: REUSE router TIERS + provider; add an admin-only endpoint that runs the same
  prompt across N models and returns per-model {reply, latency, consistency, repetition, multilingual}.
- Feature Flags: NEW small Firestore-backed store `aiFeatureFlags/global`; REUSE the existing
  admin-guarded endpoint pattern; read flags in engine/router/ai_service (router already env-flagged).
- Evaluation v2: REUSE evaluation.py; ADD a long-conversation runner (100/250 turns) + contradiction-
  trap + returning-after-gap suites; write a report artifact under /app/test_reports or /app/memory.
- Chat v3 (Part B): OUT OF SCOPE here (no Flutter client). Only firestore.rules could be reviewed.

## 3. PROPOSED FILES
CREATE:
- backend/ai_engine/feature_flags.py — Firestore-backed flag get/set + cache.
- backend/ai_engine/benchmark.py — run one prompt across multiple models, score, compare.
- backend/scripts/eval_long_conversation.py — 100/250-turn + contradiction-trap runner → JSON report.
MODIFY:
- backend/server.py — add GET/PUT /api/ai/flags (admin), POST /api/ai/lab/benchmark (admin);
  optionally expose routing/memory-layer detail in lab response (already partially there).
- backend/ai_service.py + ai_engine/engine.py + router.py — read feature flags (router/deep/per-character).
- frontend/src/pages/AICharacters.jsx — Lab v2 panels (routing tier, memory IDs+layers, quality/
  consistency/repetition status, model-benchmark compare, character version) + a Feature Flags admin panel.
NO changes to working engine pipeline logic unless a flag hook is needed.

## 4. DATABASE IMPACT
- NEW collection: aiFeatureFlags (1 doc `global`). Admin-write, backend-read. Add to firestore.rules.
- NEW (optional) collection: aiEvaluationRuns (store long-conversation report summaries). Admin-read.
- Existing AI collections unchanged: aiCharacters, aiCharacterVersions, aiCharacterMemories,
  aiCharacterRelationshipState, aiCharacterConversations/{cid__uid}/turns, aiCharacterMetrics,
  aiCharacterEvaluations, aiRateLimits.
- Firestore INDEXES to review/add: aiCharacterMemories(characterId,userId), aiCharacterMetrics(characterId
  [+userId]), aiCharacterVersions(characterId) — confirm composite indexes exist for the where() queries
  to avoid runtime index errors at scale.
- No destructive migrations. No change to production user data.

## 5. RISK ANALYSIS
- LLM COST/LATENCY: Model Benchmark + 100/250-turn eval are LLM-heavy → admin-only, run in background,
  bounded concurrency, and count against the preview/eval budget. Risk: budget spend. Mitigation: caps + flags.
- FALSE POSITIVES in contradiction/repetition guards → unnecessary regenerations (cost + latency).
  Mitigation: conservative rules already; monitor guard-failure metrics; keep repair retries capped at 1.
- FEATURE-FLAG MISCONFIG could disable AI globally. Mitigation: safe defaults (enabled), env override,
  admin-only writes, audit log.
- FIRESTORE INDEX MISSING → 500s on memory/metric queries at volume. Mitigation: index audit before load.
- SEMANTIC (EMBEDDING) MEMORY (optional): adds an embedding provider + vector storage + cost + new failure
  modes. Recommendation: keep current keyword+bidirectional retrieval (proven 1.0 memory in battery) unless
  scale demands embeddings; treat as a separate opt-in phase.
- CHAT v3: attempting mobile chat reliability without the Flutter repo = unverifiable/fake work. Excluded.
- REGRESSION: all changes are additive + flag-gated; existing /api/ai/chat, Group Play, 70 chars untouched.
  Mitigation: re-run the 15-turn battery + a smoke after each change.

## 6. RECOMMENDED PHASE ORDER (for approval)
2e-i  Feature Flags store + admin panel (safe rollback foundation).
2e-ii Admin Character Lab v2 (routing/memory/quality/consistency panels).
2e-iii Model Benchmark (admin-only compare).
3     Evaluation v2 harness — live 100/250-turn + contradiction-trap + returning-after-gap → report.
4     Firestore index/cost audit for AI collections.
(Optional) Semantic embedding memory — separate opt-in phase.
STOP — awaiting approval before implementing any of the above.

# Earn2Love Admin — PRD

## Original Problem Statement
Build the full Earn2Love Admin Panel from the uploaded spec (Earn2Love Admin Panel.docx).
Earn2Love is an 18+ social connection & earning platform (UK + India): users connect, chat,
audio/video call, complete tasks, earn Silver/Gold/Diamond coins, convert coins, subscribe
(Casual/Friendship/Love), and withdraw earnings.

## User Choices
- Auth: JWT email/password (Google optional, deferred)
- Scope: ALL 24 modules
- Theme: Light + Dark mode toggle
- Data: Seeded mock/demo data only (no live Stripe/Razorpay/Agora)
- Stack: React + FastAPI + MongoDB

## Architecture / Tasks Done (2026-07-13)
- Backend (FastAPI, MongoDB, string-uuid ids): JWT auth w/ httpOnly cookies, bcrypt, brute-force
  lockout (X-Forwarded-For aware), forgot/reset password, RBAC (7 roles via ROLE_PERMISSIONS),
  audit logging on every write action.
- Generic resource engine: /api/resources/{module} (list w/ pagination+search+filters+sort),
  detail, and action endpoints for 18 modules; dedicated endpoints for users, dashboard,
  analytics, settings, admins, countries.
- Idempotent seed: 5 admins, 250 users (UK+India), plus reports, verifications, subscriptions,
  payments, wallet tx, conversions, withdrawals, calls, tasks, ads, friend requests, chats,
  moderation, notifications, tickets, audit logs, 2 countries, system settings.
- Frontend: premium dark/light dashboard (Manrope/IBM Plex/Fira Code), collapsible sidebar
  (23 sections in 6 groups), Dashboard (KPIs + recharts donuts/area + recent tables),
  User Management + User Detail (8 tabs, notes, actions), generic ModulePage for all list
  modules, Analytics, Settings (editable config), Admin Roles (create/manage + permission
  matrix), Countries & Pricing (edit/add). Theme toggle, mobile nav, CSV export, confirm dialogs.

## Personas
- Owner (Ram) — full access. Super Admin — full. Finance/Safety/Verification/Support Admins —
  scoped write. Read-only Analyst — view only.

## Implemented (with dates)
- 2026-07-13: Full MVP across all modules; auth+RBAC; seed; dashboard/analytics; tested
  (46/47 backend pytest, 100% frontend flows). Fixed analytics param shadowing + rate-limit IP.

## Test Credentials
See /app/memory/test_credentials.md (primary: ram@earn2love.com / Owner@2026).

## Backlog / Remaining
- P1: Bulk actions + saved filters on tables; column visibility toggle; report detail drill-down
  page with evidence; verification document viewer (secured).
- P1: Notifications composer (schedule/send) UI; ticket conversation thread + replies.
- P2: Optional Emergent Google login; 2FA; real gateway integrations (Stripe/Razorpay/TrueLayer),
  Agora call metadata webhook, KYC/liveness provider; export to Excel; real-time updates.
- P2: Split server.py into routers (resources/users/dashboard/admin) as it grows.

## 2026-06 — Admin panel integration completed & verified (23/23 backend)
Every admin action mapped to EXACT Flutter fields (freeze/ban/force-logout/liveness/
verification/report/withdrawal-state-machine/subscription/wallet/audit). Withdrawals
use users/{uid}/walletHistory type=withdraw (no separate collection) with secure
atomic diamond unlock + transition validation. Fixed post-login redirect race and
removed silent exception swallowing (now logged). Deliverables: /app/e2l_production_hardening/
ADMIN_INTEGRATION.md. Download via Save to GitHub (no direct file download on platform).

## 2026-07 — Documents module (89 docs) + logo rebrand
Added a full Documents CRUD system (Firestore `adminDocuments`): 89 professionally-
generated, category-tailored documents (headers via branded viewer, footers, theme,
definition/roles/version tables, figures/logo). Endpoints: GET/POST/PUT/DELETE
/api/documents + POST /api/documents/seed (idempotent). Frontend page: grouped list,
search, category filter, View (branded iframe), Edit (HTML editor + live preview),
Delete (confirm), Download (print-to-PDF), New Document. Files: backend/documents_service.py,
frontend/src/pages/Documents.jsx. Replaced Heart-icon logo with official earn2love-logo.png
everywhere (Sidebar, Login, Topbar, favicon). All CRUD verified via curl + screenshots.
NOTE: fresh environments must call POST /api/documents/seed once to populate.

## 2026-07 — App Config module (Phase 1 of dashboard expansion)
Added "App" nav section → App Configuration page (Firestore `appConfig/current`):
editable coin packages, membership plans, call rates (audio/video caller+receiver
per min), conversion ratios (UK/India) + diamond cash unit + withdrawal minimums,
and a key/value settings list. Backend: appconfig_service.py, GET/PUT /api/app-config
(audit-logged). Frontend: pages/AppConfig.jsx (tabbed, inline-editable, add/delete rows).
Removed remaining cosmetic "Demo" labels (Report/Verification evidence). Verified via
curl (seed+persist) + screenshots. Integration note: deliverables/.../APP_CONFIG_INTEGRATION.md.

REMAINING (agreed order): ② User Support inbox (tickets + user chat routed to employees),
③ Employee/HR module + Admin Profile (KYC, contracts, docs, badges, payslips, attendance,
RBAC permissions matrix), ④ full production Notifications (FCM push + Resend email, queue/
schedule/status, needs Resend API key + FCM setup), richer charts. Username scheme
achanta01 (lastname+NN) for app users — to build when admin user-creation is added.

## 2026-07 — User Support + AI assistant (Phase 2)
Added "User Support" inbox. AI assistant "Aria" (Emergent LLM, openai/gpt-5.4) answers
users first and escalates account-specific issues to human agents. Backend:
support_service.py (Firestore `supportConversations`, run_bot + CRUD), endpoints
POST /api/support/message (app users via get_current_user token verify), GET
/api/support/conversations[/{id}], POST .../reply, POST .../status (audit-logged).
Frontend pages/Support.jsx: conversation list + status filters + threaded chat
(user/bot/agent bubbles) + agent reply + resolve/reopen, 15s polling. EMERGENT_LLM_KEY
added to backend/.env. Verified via curl (bot answer + escalate + reply + resolve) + screenshot.

REMAINING: ③ full production Notifications (FCM push + Resend email; needs RESEND_API_KEY
+ FCM setup) and ④ Employee/HR module + Admin Profile (KYC, contracts, docs, badges,
payslips, attendance, RBAC permissions matrix). Username scheme achanta01 for app users.

## Next Tasks
1. Report/Verification detail pages with evidence & full action set.
2. Bulk actions, saved filters, Excel export.
3. When user provides RESEND_API_KEY: email channel auto-activates (already wired).

## 2026-07 — Employee/HR module + Admin Profile + functional RBAC matrix (Task 1 DONE)
Wired the HR module end-to-end. Employees page (CRUD + auto employee code lastname+NN +
payslips/attendance/documents/contracts sub-records), Permissions Matrix page (super_admin-only
edit of view/edit per role per module; super_admin locked full-access), and Admin Profile
(/profile via avatar "My Profile" — shows own employee record, create-if-missing). Backend:
hr_service.py (get/update_permissions, can(role,module,perm), editable_modules(role)).
IMPORTANT: RBAC is now ENFORCED from the stored matrix (appConfig/rolePermissions) as source of
truth — server.py require_write consults hr.can(...) with 30s cache + fallback to fb static
defaults; get_current_admin.permissions now = hr.editable_modules(role). Admin-only nav items
(Employees, Permissions) hidden from non-super_admin. Routes: /employees /permissions /profile.
Verified: iteration_7.json (15/15 pytest + 100% UI flows).

## 2026-07 — Production Notifications engine (Task 2 — FCM + in-app + Resend)
Rebuilt Notifications as a real multi-channel engine (no mock data). backend/notifications_service.py:
resolve_audience (all/country/tier/unverified), send_campaign delivering across channels
in_app (writes users/{uid}/notifications in EXACT Flutter schema: title/body/type/category/isRead/createdAt),
push (firebase_admin.messaging.send_each_for_multicast to device tokens on user docs, 500 batch),
email (Resend — NO-OP/queued until RESEND_API_KEY is set in backend/.env; auto-activates once set).
Stores campaigns in `adminCampaigns` with delivery stats. Endpoints: GET /notifications/meta,
GET /notifications/campaigns[/{id}], POST /notifications/audience-preview, POST /notifications/send.
Frontend pages/Notifications.jsx: campaign list + Compose (channels, audience targeting, LIVE
audience preview, delivery stats). NOTE: live DB has ~8 users & NO device tokens → push sent=0 is
correct; emails are @earn2love.app placeholders → email recipients 0 is correct.
BLOCKED for full email: awaiting RESEND_API_KEY (+ optional NOTIFICATIONS_FROM_EMAIL) from user.

## 2026-08 — Play Together game platform (backend + admin) — CODE COMPLETE, live testing BLOCKED
Built ONE reusable production game platform powering all 50 games.
- Backend package `backend/games/`: `engines.py` (5 reusable mechanics — choice, trivia,
  prompt, guess, coop — each exposing available_actions/apply_action/public_view/ai_context,
  with public/private state separation), `registry.py` (all 50 games as data-driven defs +
  engine mapping), `content.py` (genuine starter content pools, English, admin-expandable).
- `backend/games_service.py`: authoritative session engine — create/join/act/advance/abandon/
  rematch, Firestore transactions + monotonic `revision` + `actionId` idempotency, tier
  entitlements, genuine analytics events (game_opened/started/round_completed/completed/
  abandoned/rematch), and a SANDBOXED preview (gamePreviewSessions, no analytics). Public
  session doc is client-readable; hidden state in private subcollection.
- server.py endpoints: admin `/api/games*`, `/api/games-content*`, `/api/games/{id}/preview/*`,
  stats; player `/api/play/*` (catalog, sessions, act, advance, abandon, rematch, join).
- Frontend `pages/PlayTogether.jsx`: dashboard (overview + search/filter + enable/disable/
  feature/archive/duplicate/seed), game editor, content manager, PLAYABLE sandbox preview
  (uses real engine), genuine empty-state stats. Route `/play-together`, nav under Engagement (key `games`).
- Deliverables: `firestore.rules` extended (games/gameContent read-only to clients;
  gameSessions read-for-participants + write:false; private/** + gameEvents server-only);
  `PLAY_TOGETHER_API_CONTRACT.md` for the Flutter team.
- VERIFIED OFFLINE: all 50 games complete cleanly across 5 mechanics; 8 security/edge cases
  pass (idempotency, invalid-action rejection, double-answer, turn enforcement, trivia scoring,
  inactive guard, public-state redaction of hidden answers).

### 🚨 BLOCKER (2026-08): Firebase service account REVOKED
`FIREBASE_CLIENT_EMAIL` (…@earn2love-app.iam.gserviceaccount.com) now returns
`invalid_grant: account not found` on direct OAuth token fetch — the service-account key was
deleted/disabled on Google's side (it worked earlier this session; system clock is correct).
This takes the ENTIRE backend Firestore layer down (existing admin panel + new platform).
ACTION REQUIRED FROM USER: provide a fresh Firebase service-account JSON key for project
`earn2love-app` (updates FIREBASE_PROJECT_ID / FIREBASE_CLIENT_EMAIL / FIREBASE_PRIVATE_KEY).
Once restored: (1) Play Together → Seed catalog, (2) run testing_agent end-to-end.

- P2: split server.py (~709 lines) into modules/*.py APIRouters (HR, notifications).
- P2: strict Pydantic model for PUT /role-permissions matrix payload.
- P2: a11y — aria-disabled on locked super_admin permission switches.


## 2026-06 — Flutter app production-hardening (cross-repo, server-side only)
Worked on `github.com/earn2love/earn2love-app` (Flutter) — this Emergent env cannot
build/run Flutter. Delivered as branch `feature/production-hardening` (bundle+patches
in `/app/e2l_production_hardening/`, audit in `PRODUCTION_AUDIT.md`):
- Firestore + Storage security rules, composite indexes, firebase.json wiring.
- Modular v2 Cloud Functions: Stripe webhook (idempotent, only crediting path),
  createStripePaymentIntent (topup+subscription), convertCoins, startCall/endCall +
  generateAgoraToken (disabled until secrets), requestWithdrawal + admin review,
  adminSetAccountState/setAdminRole, onReportCreated auto-freeze; audit logging.
- Fixed field drift (silverBalance vs silverCoins; walletHistory vs walletTransactions),
  removed leaked dotfiles, hardened .gitignore.
- Validated: node --check + full require() graph load (real deps) + ESLint 0 errors.
  NOT verified (needs live Firebase+secrets+devices): Stripe webhook credit, Agora,
  Android/iOS builds. Flutter UI/branding/entrypoint fixes remain (see spec §11).



## 2026-08 — Advanced AI Character Engine (Phases 1–5) — ENGINE PROVEN OFFLINE, live persistence BLOCKED
Built a modular, provider-agnostic AI Character Engine as a SEPARATE layer (backend/ai_engine/),
touching no existing systems (support bot, chat, wallet, games, notifications, profiles preserved).
Pipeline: understanding → identity/world-model → layered memory → relationship state → language
style → conversation planner → provider layer → consistency/repetition/safety guards → persistence.
- Modules: schema, repository (interface + InMemory + Firestore), registry (3 reference chars),
  provider (emergentintegrations; env AI_ENGINE_PROVIDER=openai / AI_ENGINE_MODEL=gpt-5.6-sol; swappable),
  understanding, memory (A working/B episodic/C long-term/D relationship/E character facts + deterministic
  ranking), relationship (new/familiar/comfortable/established, non-manipulative), language_style
  (Telugu/Hindi/Tamil-English mixing), planner, guards, engine (orchestrator), evaluation.
- Service ai_service.py + endpoints /api/ai/* (character CRUD/versions/metrics/flags/seed + AI Character
  Lab: start/chat/reset). Firestore-guarded so admin UI never hangs while creds down.
- Frontend pages/AICharacters.jsx: list + editor (identity + level sliders) + AI Character Lab sandbox
  (chat + live diagnostics: language, relationship, memory IDs, guard pass/fail, latency, model, plan).
  Route /ai-characters, nav under Engagement (key ai-characters).
- 3 reference characters (intentionally different, all strong reasoning): Ananya (warm/playful, Hyderabad,
  Telugu-English), Marcus (direct/witty, London), Sora (quiet/perceptive, Vancouver).
- Firestore collections (backend-authoritative, client write:false): aiCharacters (client-read),
  aiCharacterVersions/Memories/RelationshipState/Conversations/Metrics/Evaluations. Rules added.
- VERIFIED OFFLINE (in-memory repo + real GPT-5.6): divergence distinct (avg sim 0.07); 15-turn battery
  Ananya & Marcus 1.0 all dimensions, Sora strong; multilingual + memory callback + contradiction
  resistance + repetition avoidance + guards all pass.
- BLOCKED (needs Firebase key): live Firestore persistence, production CRUD, security-rules + concurrency,
  conversation restoration. Do NOT mark production-ready until these live tests pass.
- Deliverable: deliverables/flutter-production-hardening/AI_CHARACTER_ENGINE.md. 67 production characters NOT generated yet (by design).

## ⏳ Pending live-test queue (run in order the moment the new Firebase service-account key is active)
1. Verify Firebase auth/token. 2. Play Together: seed 50 games + 535 content, run full E2E. 3. AI Engine:
seed-reference, live persistence/restoration/rules tests. Do not reset unrelated production data.

## 2026-08 — Firebase RESTORED + LIVE E2E of Play Together & AI Engine (DONE & VERIFIED)
Rotated Firebase service-account key injected into backend/.env (same service account
firebase-adminsdk-fbsvc@earn2love-app; project earn2love-app). Firestore connectivity confirmed.
Seeded LIVE (idempotent, no force, production user data untouched): 50 games + 535 gameContent
docs + 3 AI reference characters (ref_ananya/ref_marcus/ref_sora, all enabled).
- iteration_8: live E2E — backend 37/38, frontend 95%. Confirmed live Firestore transactions,
  actionId idempotency, revision-lock 409, out-of-turn rejection, completion + hidden-state
  redaction, sandbox preview (5 mechanics, zero analytics), AI CRUD/versioning, AI Lab.
- FIXES (verified live): (1) tier lockout — games_service._user_tier now defaults untiered/missing
  users to 'casual' (base entitlement) so gameplay is unblocked; love-only game still gated.
  (2) POST /api/play/sessions/{sid}/advance body now optional (Body(None)) — no more 422.
  (3) NEW production persistent chat: POST /api/ai/chat + GET /api/ai/chat/{cid}/history
  (ai_service.chat/chat_history/relationship_state via CharacterEngine(prod_repo()).respond(sandbox=False)) —
  memory/relationship/turns/metrics now written to Firestore; cross-session recall confirmed.
  (4) DELETE /api/ai/characters/{cid} (rejects reference chars) + UI delete/enable-disable buttons
  + 'Disabled' badge on cards.
- iteration_9 retest: all 4 fixes GREEN (25/27 backend; 2 were documented follow-ups). Then fixed
  the follow-ups (verified live): AI-chat error→status mapping (character_not_found→404,
  character_disabled→403), materialised aiCharacterConversations parent doc (characterId/userId/
  turnCount, now listable), CASCADE delete (versions/memories/relationship/metrics/turns),
  userId on aiCharacterMetrics, bounded Firestore reads (get_turns order_by+limit, list_memories
  limit 500), 2000-char message cap on /api/ai/chat, and a card enable/disable toggle wired to /flags.
- Test credentials: demo.admin@earn2love.com / Earn2Love@Demo2026 (super_admin). The bootstrapped
  earn2loveofficial@gmail.com currently FAILS signInWithPassword. App redirects to '/' post-login.
- P1 NEXT: generate the remaining 67 production AI characters (only now that live persistence is proven).
  P2: integrate the AI Character Engine into a Play Together session (Group Play AI); add rate-limiting
  to /api/ai/chat; add DialogDescription/aria-describedby to admin dialogs.

## 2026-08 — AI-chat rate limiting + FULL 70-character roster (DONE & VERIFIED)
### Part 1 — Production AI-chat rate limiting & abuse/cost guards
New module backend/ai_engine/rate_limit.py — Firestore-backed atomic counters (survive
restarts, safe across pods) enforced in ai_service.chat() before any LLM call:
- Per-user sliding windows: 20/min, 300/hour, 1500/day (env-overridable AI_CHAT_PER_MINUTE/HOUR/DAY).
- Duplicate-spam guard: same message 5×+ in a row (AI_CHAT_DUP_SPAM_THRESHOLD).
- Platform-wide daily circuit breaker (AI_CHAT_PLATFORM_DAILY_CAP, default 50000) to protect the LLM budget.
- 2000-char message cap; fail-OPEN on Firestore errors (never blocks legit chat on a transient outage).
- On any trip → SOFT cooldown response (ok:true, cooldown:true, friendly responseText, retryAfterSeconds,
  usage.provider="guard") — NO LLM call, so no cost. Doc ids avoid Firestore-reserved "__..__" (use
  "platform_daily"). Verified live: minute cap (20→deny), dup (5th→deny), circuit breaker, soft cooldown.

### Part 2 — Generated the remaining 67 production AI characters (70 total incl. 3 reference)
Data-only generation — NO engine changes, NO scripted replies. Every character is a structured
profile authored by GPT-5.6 (backend/ai_engine/character_factory.py: 67 curated diversity seeds
across locale/language/profession/archetype/gender/age) and runs through the identical
CharacterEngine (reasoning/memory/relationship/multilingual/consistency/repetition/safety).
Orchestrator backend/scripts/generate_characters.py — resumable, batches of 7, concurrency-limited,
and GATES each batch before seeding the next:
- divergence: each new char's reply to a shared prompt must be distinct from every other char
  (max pairwise Jaccard <0.45, batch avg <0.30) — measured vs a cached population baseline.
- 15-turn long-conversation battery: characterConsistency ≥0.9, nonRepetition ≥0.7,
  multilingualQuality ≥0.75, safety =1.0, 0 errors. Failing chars regenerate once with a
  distinctness/consistency nudge; only passing chars are seeded to Firestore.
RESULT: 67/67 seeded, 0 failures. Population: avg pairwise similarity 0.149 (gate <0.30),
max pair 0.386 (<0.45); all batteries passed. Diversity: 22 countries; languages incl.
Telugu/Hindi/Tamil/Marathi/Bengali/Kannada/Gujarati/Punjabi + Spanish/French/Japanese/Korean/
Swahili/Yoruba etc. No duplicate names (one collision auto-fixed: gen_marisol_18 → gen_mara_18).
Per-batch eval reports saved under /app/memory/character_gen/batch_*.json; progress checkpoint at
/app/memory/character_gen/progress.json. GET /api/ai/characters now returns 70. characterIds: gen_<name>_<nn>.
NOTE: provider timeouts on a few seeds were retried (they stay "pending", never falsely "failed"); one
needed AI_ENGINE_TIMEOUT=90 to complete. Testing: verified at the service/eval/Firestore layer (not via
testing_agent this round).
- P2 REMAINING: Group Play AI (drop a character into a Play Together session); pagination/search on the
  70-card admin grid; DialogDescription/aria-describedby on admin dialogs; consider order_by index on
  aiCharacterMemories for very high-volume users.

## 2026-08 — Group Play AI + Roster browsing (DONE & VERIFIED)
### Group Play AI — users can play AGAINST any of the 70 characters
New backend/games/ai_play.py — decide_action() maps every engine action type
(answer/respond/contribute/set_secret/guess) to a VALID in-character move via GPT-5.6, with
deterministic fallbacks and empty-option guards. The AI plays through the SAME validated action
path as a human (engines.available_actions -> apply_action); it never sees hidden state (correct
answers / opponent secret) — it reasons from the public prompt. NO scripted replies, NO engine changes.
- games_service.run_ai_turns(sid) drives authoritative AI turns (each move via transactional act());
  preview_run_ai_turns(sid) drives them in the admin sandbox. Wired into player API
  (/api/play/sessions[/{sid}/join|act|advance] now auto-play AI then return refreshed session) and
  preview API (/api/games/{gid}/preview/start accepts {aiCharacterId}; act/advance drive AI).
- create_session()/preview_start() now VALIDATE aiCharacterIds against the enabled roster (unknown/
  disabled/AI-unsupported -> 400) so an AI seat can never stall a session; silent AI-turn skips now log.
- Frontend PlayTogether.jsx sandbox: Opponent selector (data-testid preview-opponent-select) with
  'Player 2 (human)' + 70 AI options; picking an AI plays You-vs-AI with auto-moves and named scores.
- VERIFIED (iteration_10, 88% backend before fix->fixed, 100% frontend): all 5 mechanics complete with
  the AI playing; trivia AI reasoned 8/8 correct; no hidden-answer leak; zero preview analytics writes.
  Self-verified after fix: invalid AI id -> 400, valid id seats & plays.

### Roster browsing — AI Characters admin grid (70 cards)
AICharacters.jsx: added country filter (ai-filter-country) + language filter (ai-filter-language),
result count (ai-result-count), and pagination (ai-pagination / ai-page-prev/next/indicator, PAGE_SIZE 12
-> 6 pages). Search combines with filters. VERIFIED: India->23, +Telugu->5, clearing restores 70.

### Known minor (not blocking)
- Preview AI drives are admin-only but unbounded LLM spend (no rate limit like /api/ai/chat) — add a
  per-admin preview cap if abused. Roster filtering/paging is client-side (fine at 70; add server paging if it grows).
- P3: DialogDescription/aria-describedby on admin dialogs; 'clear all filters' button; batch multi-AI turns.

## 2026-08 — Play & Chat + Multi-AI Rooms + Preview Budget + Clear Filters (DONE & VERIFIED)
### Play & Chat (new page /play-chat, PlayChat.jsx)
Admin acts as the end-user (same Firebase token drives /api/ai/chat + /api/play/*). Pick any of the
70 characters -> PERSISTENT chat (history restored from Firestore across sessions) -> "Challenge to a
game" starts a REAL match inline; you play via action controls and the AI(s) auto-play to completion
with named scores. Nav "Play & Chat" (key ai-characters), route in App.js.
### Multi-AI Rooms
Engine was already N-player; raised maxPlayers 2->6 on all 50 games (registry + Firestore migration).
create_session()/preview_start() de-duplicate ai ids, validate them, and enforce maxPlayers (7 -> 400).
Player API + Play & Chat "group game" UI seat up to 6 players (you + up to 5 AIs); all AIs auto-play.
### Preview Budget Guard
ai_engine/rate_limit.consume_preview_ai(db, admin_uid): per-admin daily cap (AI_PREVIEW_DAILY_CAP=400,
env-tunable) on sandbox AI moves. When hit, preview keeps working but AI stops auto-moving and
_public_doc surfaces aiBudgetExceeded -> PlayTogether shows preview-ai-budget note.
### Clear Filters
AICharacters.jsx: one-tap ai-clear-filters button + country/language persisted to localStorage
(ai_filter_country / ai_filter_language).
### Verification (iteration_11: backend 15/15, frontend 100%)
Persistent chat + reload restore, trivia vs Marcus 8/8, 3-player multi-AI trivia (draw 8-8), 6 allowed /
7 rejected, unknown AI 400, budget cap [T,T,T,F], clear-filters+persistence, single-AI preview regression.
Fixed after report (self-tested): duplicate ai ids now de-duplicated; PlayChat GameRunner now abandons the
session on exit/unmount (Leave button + cleanup) so no orphan ACTIVE sessions; RevealView formatted (no raw JSON).
Known optional nits: language dropdown not narrowed by country; preview dialog still single-AI (multi-AI reachable via Play & Chat).

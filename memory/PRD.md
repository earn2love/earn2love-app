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


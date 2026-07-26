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

## Next Tasks
1. Report/Verification detail pages with evidence & full action set.
2. Notifications composer + ticket threads.
3. Bulk actions, saved filters, Excel export.

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


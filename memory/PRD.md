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

## Next Tasks
1. Report/Verification detail pages with evidence & full action set.
2. Notifications composer + ticket threads.
3. Bulk actions, saved filters, Excel export.

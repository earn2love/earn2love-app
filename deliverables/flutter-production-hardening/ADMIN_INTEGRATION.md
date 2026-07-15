# Earn2Love Admin Panel — Integration Complete (verified)

Backend verified 23/23 (testing agent, iteration_5.json) against LIVE Firestore.
Frontend login + withdrawals + sidebar verified. Every admin action uses the
EXACT Flutter/app field names — no invented fields.

## 1. Exact admin fields mapped to the Flutter app

| Admin action | Firestore write (users/{uid} unless noted) | Source of truth |
|---|---|---|
| Freeze | `accountStatus:'Frozen'`, `frozen:true` | users |
| Unfreeze | `accountStatus:'Active'`, `frozen:false` | users |
| Ban | `accountStatus:'Banned'`, `banned:true` + Firebase Auth `disabled=true` + revoke tokens | users + Auth |
| Unban | `accountStatus:'Active'`, `banned:false` + Auth `disabled=false` | users + Auth |
| Force logout | `activeSessionId:''`, `forceLogoutAt:<ts>` + revoke refresh tokens | users + Auth |
| Under review | `accountStatus:'Under Review'` | users |
| Require verification | `verificationStatus:'Pending'`, `livenessRequired:true` | users |
| Reset liveness | `verificationStatus:'Needs Review'`, `livenessRequired:true` | users |
| Reset reports | `reportsCount:0` | users |
| Freeze / unfreeze wallet | `walletFrozen:true/false` | users |
| Change tier | `tier:'casual'|'friendship'|'love'` | users |
| Cancel subscription | `subscriptionStatus:'cancelled'` | users |
| Verification approve | verificationRequests `status:'approved'` → user `verificationStatus:'Verified'`, `verified:true`, `livenessVerifiedAt:<ts>`, `livenessRequired:false` | verificationRequests + users |
| Verification reject | request `status:'rejected'` → user `verificationStatus:'Rejected'` | verificationRequests + users |
| Report resolve / dismiss | reports `status:'resolved'|'dismissed'` | reports |
| Withdrawal | `users/{uid}/walletHistory` doc `type=='withdraw'` — see state machine | walletHistory (NO separate collection) |

### Withdrawal state machine (secure diamond unlock, atomic txn)
States: `requested → under_review → approved → processing → paid`;
`rejected`/`cancelled`/`failed` reachable per rules; `paid`/`rejected`/`cancelled`/`failed` are terminal.
- Refund states (`rejected`,`cancelled`,`failed`): `diamondBalance += amt`, `lockedDiamond -= amt`, delete `pendingWithdrawalId`, set `rejectionReason`.
- `paid`: `lockedDiamond -= amt` (consumed), delete `pendingWithdrawalId`, `paidAt`.
- Every transition sets `reviewedAt` (server ts) + `reviewedBy`, validates the transition (illegal → HTTP 400), and writes `adminAuditLogs`.

### Audit log (`adminAuditLogs`)
Every write action records: `adminUid, adminEmail, adminRole, action, module, target, targetId, previousValue, updatedValue, reason, ip, result, timestamp`.

## 2. Changed admin files
- `/app/backend/server.py` — `resource_action()` (withdrawals state machine + verification mirror + `dismiss`), `user_action()` (force-logout fields, `livenessRequired`, `cancel-subscription`, logged Auth errors), `withdrawal_review` endpoint, `WithdrawalReview` model.
- `/app/backend/firestore_repo.py` — `transition_withdrawal()`, `mirror_verification_to_user()`, `WITHDRAWAL_TRANSITIONS`, logger + specific exception logging (removed silent `except Exception` that hid index errors).
- `/app/frontend/src/config/modules.js` — withdrawals actions/filters (full lifecycle), reports `dismiss`.
- `/app/frontend/src/pages/Login.jsx` — redirect gated on committed `admin` (fixes post-login race).
- `/app/frontend/src/components/Sidebar.jsx` + `/app/frontend/src/pages/Analytics.jsx` — website link + "Live data" label.
- `/app/frontend/.env` — `REACT_APP_WEBSITE_URL`.
- `/app/backend/seed_test_data.py` — QA seed/clean for withdrawal + verification testing.

## 3. Required Firestore indexes (for the admin/app at scale)
See `/app/e2l_production_hardening/patches` (`firestore.indexes.json`). Key ones:
`walletHistory` collection-group `(type, createdAt)` & `(status, createdAt)`;
`reports (status, createdAt)`; `friendRequests (toUid,status,createdAt)`;
`media` collection-group `(flagged)` for moderation count;
`supportTickets (status, createdAt)`; `verificationRequests (type,status,createdAt)`.
> The admin backend currently filters walletHistory in Python (no composite index needed) and degrades gracefully if an index is missing (logged warning).

## 4. Unresolved blockers
- None on the admin side. Verification/Reports modules show empty states (no Firestore data yet) — expected until the Flutter app writes those collections.
- Cross-repo: the Flutter client still writes balances directly (P0 in PRODUCTION_AUDIT.md §11) — must migrate to the Cloud Functions before deploying strict Firestore rules.

## 5. Test results
- Backend: 23/23 PASS (iteration_5.json) — all 10 action categories + audit + wallet visibility.
- Withdrawal lifecycle self-verified via curl: reject-refund, approve→processing→paid, illegal transition → 400.
- Frontend: login→dashboard redirect, withdrawals table + all action buttons, sidebar website link — verified.

## 6. Deployment steps (admin panel)
This admin panel is deployed via Emergent (Deploy button) — backend (FastAPI) + frontend (React) + env vars. No extra steps; Firebase service-account + web keys already in env. To download this branch/patches, use **Save to GitHub**.

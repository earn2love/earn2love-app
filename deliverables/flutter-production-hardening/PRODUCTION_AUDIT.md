# Earn2Love — Production Hardening: Audit & Server-Side Deliverables

Branch: `feature/production-hardening`
Scope of THIS phase: read-only audit of the Flutter repo + build/harden the
**server-side** pieces only (Firestore/Storage rules, indexes, Cloud Functions).
No Flutter UI files were changed. Nothing here fakes payments, rewards, calls or
withdrawals. External-dependent features stay disabled until real keys are set.

> ⚠️ This environment cannot compile/run Flutter (no Flutter/Dart/Android/iOS
> toolchain). Cloud Functions were validated with `node --check`, a real
> `require()` load of the full module graph (firebase-functions v7,
> firebase-admin, stripe, agora-token), and ESLint (0 errors). Rules/indexes are
> written to Firebase spec but must be deployed & emulator-tested by you.

---

## 1. Complete Flutter Repository Audit

**Stack:** Flutter (Dart SDK ≥3.3), Firebase (Auth, Firestore, Storage,
Functions), `flutter_stripe`, `just_audio`/`video_player`/`record` for media.
47 Dart files, flat structure (`lib/screens`, `lib/services`, `lib/widgets`).
Cloud Functions in `functions/` (Node 22, v2 SDK).

### Working / partially-working features
- Firebase Auth flow scaffolding: phone-OTP + email + password + vibe selection,
  handled by `lib/screens/auth_gate.dart` (states: loggedOut, emailVerify,
  phonePasswordSetup, vibeSelection, home).
- Firestore-backed users, chats/chatRooms, friendRequests/requests, media,
  wallet history, notifications, reports, support tickets.
- Coin conversion math and streak logic exist (client-side — insecure, see below).
- Stripe PaymentIntent creation via Cloud Function (`createStripePaymentIntent`).

### 🔴 Production blockers found
1. **App entrypoint is a test page.** `lib/main.dart` sets `home: PaymentTestPage()`
   instead of `AuthGate()`. The real app never launches. **(Blocker)**
2. **Fake payment confirmation.** `confirmStripeTopupDev` credited Silver with **no
   Stripe verification and no webhook** — closing the Payment Sheet was treated as
   success. Violates "never mark a payment successful because the sheet closed".
3. **Client directly mutates money balances.** `coin_service.dart`
   (`addSilver`/`spendSilver`/`convertCoins`) and `withdraw_page.dart` write coin
   balances straight from the client via `FieldValue.increment`. Any user could
   inflate their own balance. Wallet/streak must be server-authoritative.
4. **No Agora integration at all.** `pubspec.yaml` has no Agora package; audio/video
   calling is not implemented. Call charging (10/25 Silver per min) does not exist.
5. **No Firestore or Storage security rules, no indexes** were in the repo —
   `firebase.json` configured functions only. Data was effectively unprotected.
6. **Leaked files committed** inside `lib/screens/`: `.bash_history`,
   `.emulator_console_auth_token`, `.gitconfig`, `.lesshst`. Removed in this branch.
7. **Withdrawals are placeholder** ("Phase 1 placeholder"); no state machine, no
   locking, no admin review.

### 🟠 Data-consistency / correctness issues
- **Coin field mismatch:** app reads `silverBalance`/`goldBalance`/`diamondBalance`,
  but the top-up function wrote `silverCoins`. Top-ups never showed in the wallet.
  Canonicalised to `silverBalance` etc. server-side.
- **Two transaction stores:** app writes `users/{uid}/walletHistory`; the function
  wrote top-level `walletTransactions`. The admin panel reads the `walletHistory`
  collection-group, so function writes were invisible to admins. Canonicalised to
  `users/{uid}/walletHistory`.
- **Duplicate collections:** `chats` vs `chatRooms`, `requests` vs `friendRequests`,
  `blocks` vs `blockedUsers`. Pick one per concern (recommend `chatRooms`,
  `friendRequests`, `blockedUsers`) and migrate. Rules currently cover both to avoid
  breakage; consolidation is a documented Flutter task.
- **Account-status field drift:** app uses lowercase `status`; admin panel uses
  `accountStatus` ("Active/Frozen/Banned/Under Review") + `banned`/`frozen`. App must
  read `accountStatus`/`banned`/`frozen` to enforce admin actions.
- Stray misplaced file `androidapp...MainActivity.kt` at repo root (removed; real one
  is at `android/app/src/main/kotlin/com/earn2love/app/MainActivity.kt`).

### 🟡 Lower priority
- `main.dart` theme is `seedColor: Colors.deepPurple` (generic). No central theme /
  design system, no official logo wiring (Flutter UI task).
- Streak eligibility computed client-side (spoofable); should be a scheduled/verified
  function.
- Client-side ad reward buttons (if present) must be gated behind a verified ad
  callback flag.

### ✅ Security positives
- No `google-services.json`, `GoogleService-Info.plist`, service-account JSON, or
  Stripe **secret** key are committed. Only the Stripe **publishable** test key is in
  `main.dart` (client-safe, but move to central config).

---

## 2. Exact Firestore Schema (as used by app + admin panel)

```
users/{uid}
  displayName, name, email, phoneNumber, photoUrl, bio, interests[]
  dob, gender, connectionPreference
  country, countryCode, dialCode, currencyCode, currencySymbol, pricingRegion
  tier: 'casual' | 'friendship' | 'love'                 (server-managed)
  subscriptionPlan, subscriptionStatus, subscriptionActivatedAt (server-managed)
  silverBalance, goldBalance, diamondBalance, lockedDiamond : number (server-managed)
  accountStatus: 'Active'|'Frozen'|'Banned'|'Under Review' (admin-managed)
  banned:bool, frozen:bool, walletFrozen:bool             (admin-managed)
  verificationStatus, livenessRequired, livenessVerifiedAt, nextLivenessDueAt
  reportsCount:int                                        (server-managed)
  vibeSelectionCompleted:bool, vibeSelectionCompletedAt
  activeSessionId, activeSessionAt                        (single-device)
  requestsEnabled:bool, showOnlineStatus:bool
  streakDays, streakBonusPct, streakLastDate, lastConversionAt (server-managed)
  pendingWithdrawalId, bankDetails{...}
  deleted, deletedAt, createdAt, updatedAt

  users/{uid}/walletHistory/{id}   (canonical wallet ledger; admin reads via group)
     type: 'topup'|'conversion'|'withdraw'|'call_spend'|'call_earning'|'subscription'|'ads'
     title, fromCoin, fromAmount, toCoin, toAmount, bonusPct
     amount, currency, currencyCode, status, provider, paymentIntentId, callId
     country, cashValue, createdAt
  users/{uid}/notifications/{id}   type, title, body, category, read, createdAt
  users/{uid}/media/{id}           type(image/video), url, flagged, ownerName, createdAt
  users/{uid}/{chatPrefs|blockedUsers|blocks|following|followers|likes|requests|limits}

chatRooms/{roomId}   participants[], lastMessage, lastMessageAt, unread{uid:count}
  chatRooms/{roomId}/messages/{msgId}  senderId, text, translatedText, type, createdAt, seen
chats/{roomId}       (legacy duplicate of chatRooms — consolidate)

friendRequests/{id}  fromUid, toUid, status('pending'|'accepted'|'rejected'), initialMessage, createdAt
requests/{id}        (legacy duplicate — consolidate)

reports/{id}         reporterUid, targetUid, reason, issue, evidenceRef, status('pending'|...), createdAt
supportTickets/{id}  uid, subject, message, status('open'|'assigned'|...), messages[], createdAt
verificationRequests/{id}  uid, type('liveness'|'identity'), status, docRef, createdAt

calls/{id}           callerUid, calleeUid, type('audio'|'video'), channelName,
                     status('ringing'|'ended'), charged, durationSeconds, billedMinutes,
                     charge, reward, createdAt, endedAt          (server-only writes)

paymentIntents/{stripeId}  uid, kind, amount, currency, silver|tier, packId|planId,
                           status('created'|'credited'|'failed'|'refunded'), provider, createdAt
stripeEvents/{eventId}     type, processedAt                     (webhook idempotency)
adminAuditLogs/{id}        adminUid, adminEmail, adminRole, action, module, target,
                           targetId, prev, new, reason, source, timestamp
```

## 3. Exact Storage Paths
```
users/{uid}/profile/{file}      profile pictures    (owner write, signed-in read, image ≤10MB)
users/{uid}/media/{file}        gallery photos/videos (owner write, signed-in read, ≤100MB)
chats/{roomId}/{file}           chat attachments    (signed-in, ≤100MB)
verification/{uid}/{file}       KYC/liveness docs   (owner write, ADMIN-ONLY read, ≤50MB)
```

## 4. Required Indexes
See `firestore.indexes.json` (deploy: `firebase deploy --only firestore:indexes`).
Highlights: `walletHistory` collection-group `(type, createdAt)` & `(status, createdAt)`;
`chatRooms (participants CONTAINS, lastMessageAt)`; `friendRequests (toUid,status,createdAt)`;
`reports (status,createdAt)` & `(targetUid,createdAt)`; `calls (calleeUid,status,createdAt)`;
`messages (senderId, createdAt)` for streak; `notifications` group `(createdAt)`.

## 5. Firestore & Storage Rules
See `firestore.rules` and `storage.rules`. Enforced: auth required; profile owners
cannot write money/state fields (`protectedUserFields()`); wallet ledger, payments,
calls, audit logs are **server-write-only**; chat access is participant-only; reports &
verification docs are admin-restricted; default-deny catch-all.
> Deploying these rules **requires the Flutter client migration** in §11 (client can no
> longer write balances directly — it must call the new callables).

## 6. Environment Variables & Secrets Checklist
Set as Firebase **secrets** (`firebase functions:secrets:set NAME`):
- `STRIPE_SECRET_KEY` — Stripe secret (server only).
- `STRIPE_WEBHOOK_SECRET` — from the Stripe webhook endpoint.
- `AGORA_APP_ID` — Agora project App ID.
- `AGORA_APP_CERTIFICATE` — Agora primary certificate (server only).

Runtime env flags (default OFF / safe):
- `ALLOW_DEV_STRIPE_CONFIRM` — dev only; must be unset/`false` in production.
- `ADS_REWARD_ENABLED` — keep `false` until a verified ad-network callback exists.
- `AUTO_PAYOUT_ENABLED` — keep `false`; withdrawals stay manual-admin until a payout
  provider confirms `paid`.

Client-safe (in central Flutter config, not secrets): Stripe **publishable** key,
Agora App ID, Functions region (`us-central1`), legal URLs, support email, website URL.

## 7. Firebase Console Manual Steps
1. Enable Auth providers: Phone, Email/Password, Google (if used).
2. `firebase deploy --only firestore:rules,storage,firestore:indexes`.
3. Set the 4 secrets above; grant the functions service account access.
4. `firebase deploy --only functions`.
5. Confirm the composite indexes finish building (Firestore → Indexes).
6. Ensure `google-services.json` / `GoogleService-Info.plist` are added to the app
   locally (they stay git-ignored).

## 8. Stripe Console Manual Steps
1. Get live + test secret keys.
2. Create a webhook endpoint → the deployed `stripeWebhook` URL; subscribe to
   `payment_intent.succeeded`, `payment_intent.payment_failed`, `charge.refunded`
   (add `invoice.paid`/`customer.subscription.*` when moving to real recurring plans).
3. Copy the signing secret into `STRIPE_WEBHOOK_SECRET`.
4. Test with a card (`4242…`) → verify a `walletHistory` `topup` row appears **once**.

## 9. Agora Manual Steps
1. Create an Agora project (App ID + primary certificate, token auth ON).
2. Set `AGORA_APP_ID` / `AGORA_APP_CERTIFICATE` secrets. Until then
   `generateAgoraToken` returns `failed-precondition` (calls disabled by design).
3. Flutter: add `agora_rtc_engine`, fetch tokens from `generateAgoraToken`, and use
   `startCall`/`endCall` for server-side charging.

## 10. Deployment Commands
```bash
cd functions && npm install
firebase deploy --only firestore:rules,storage,firestore:indexes
firebase functions:secrets:set STRIPE_SECRET_KEY
firebase functions:secrets:set STRIPE_WEBHOOK_SECRET
firebase functions:secrets:set AGORA_APP_ID
firebase functions:secrets:set AGORA_APP_CERTIFICATE
firebase deploy --only functions
```

## 11. Remaining Flutter / Mobile Implementation Spec (must be done in a Flutter env)
- **P0 Fix entrypoint:** `main.dart` → `home: const AuthGate()`; move Stripe
  publishable key to central config.
- **P0 Migrate wallet/streak/withdraw off direct writes** to the callables:
  `convertCoins`, `requestWithdrawal`, and (for top-ups) rely on `stripeWebhook`
  instead of `confirmStripeTopupDev`. Remove client balance increments in
  `coin_service.dart` / `withdraw_page.dart`.
- **P0 Enforce account state** from `accountStatus`/`banned`/`frozen`/`forceLogoutAt`
  on launch & on stream errors (react to admin freeze/ban/force-logout).
- **P1 Calls:** add `agora_rtc_engine`, wire ringing/accept/reject/timeout, call
  `startCall`→token→`endCall`. Show insufficient-balance & permission handling.
- **P1 Branding/design system:** official logo on splash/auth/nav/empty states;
  central theme (pink/purple/gold, light+dark); reusable components; fix overflow on
  small phones. Coin colours: Silver ≠ Gold ≠ Diamond.
- **P1 Consolidate duplicate collections** (`chats`/`requests`/`blocks`).
- **P2 Notifications (FCM):** token registration/refresh, deep links, foreground/bg.
- **P2 Account deletion & privacy request** flows via secure functions.

## 12. Production Blockers & Test Checklist
**Blockers before launch:** entrypoint fix (P0); client wallet-write migration (P0);
account-state enforcement (P0); Stripe webhook configured + secrets set; Agora
configured (or calls stay disabled); rules + indexes deployed; official logo/design.

**Server-side verified in this phase:** all 12 functions load with real deps; ESLint 0
errors; rules/indexes written to spec. **NOT verified here** (needs a real
Firebase/emulator + device): live Stripe payment→webhook credit, Agora calls,
end-to-end on two devices, Android/iOS release builds.

Do NOT declare production-ready until the §11 P0 items ship and the §12 device/payment
tests pass with real keys.

# Earn2Love — Production Hardening branch handoff

Branch: `feature/production-hardening` (4 commits, +1486 / −197, 21 files).
Built against `github.com/earn2love/earn2love-app` @ `main`.

## What's here
- `feature-production-hardening.bundle` — the full branch as a git bundle.
- `patches/` — the 4 commits as `git am`-applicable patch files.
- `PRODUCTION_AUDIT.md` — full audit + schema + rules + indexes + console steps + Flutter spec.

## Apply the branch (option A — bundle)
```bash
git clone https://github.com/earn2love/earn2love-app && cd earn2love-app
git fetch /path/to/feature-production-hardening.bundle main..HEAD
git checkout -b feature/production-hardening FETCH_HEAD
git push -u origin feature/production-hardening   # then open a PR
```

## Apply the branch (option B — patches)
```bash
cd earn2love-app
git checkout -b feature/production-hardening
git am /path/to/patches/*.patch
git push -u origin feature/production-hardening
```

## After merging — deploy (needs real keys, see PRODUCTION_AUDIT.md §6–§10)
```bash
cd functions && npm install
firebase deploy --only firestore:rules,storage,firestore:indexes
firebase functions:secrets:set STRIPE_SECRET_KEY STRIPE_WEBHOOK_SECRET AGORA_APP_ID AGORA_APP_CERTIFICATE
firebase deploy --only functions
```

> ⚠️ Deploying `firestore.rules` requires the Flutter client migration in
> PRODUCTION_AUDIT.md §11 (client can no longer write balances directly — it must
> call `convertCoins` / `requestWithdrawal`, and rely on `stripeWebhook`).
> Do this on a staging project first.

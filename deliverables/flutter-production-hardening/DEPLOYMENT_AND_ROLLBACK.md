# Deployment & Rollback

## A. Cloud Functions + Rules + Indexes (Flutter Firebase project `earn2love-app`)

### Deploy
```bash
cd functions && npm install
# Set secrets (values NOT stored in git):
firebase functions:secrets:set STRIPE_SECRET_KEY
firebase functions:secrets:set STRIPE_WEBHOOK_SECRET
firebase functions:secrets:set AGORA_APP_ID
firebase functions:secrets:set AGORA_APP_CERTIFICATE
# Deploy rules + indexes FIRST on a staging project, then functions:
firebase deploy --only firestore:rules,storage,firestore:indexes
firebase deploy --only functions
```
> ⚠️ Do NOT deploy `firestore.rules` to production until the Flutter client migration
> (PRODUCTION_AUDIT.md §11) ships — strict rules block client balance writes the
> current app still performs.

### Rollback
```bash
# Functions: redeploy the previous git revision of functions/
git checkout <previous-commit> -- functions && cd functions && npm ci
firebase deploy --only functions

# Rules: Firebase Console → Firestore/Storage → Rules → "Rollback" to a prior version,
#        OR re-deploy the previous firestore.rules/storage.rules from git:
git checkout <previous-commit> -- firestore.rules storage.rules
firebase deploy --only firestore:rules,storage

# Indexes are additive; delete unwanted ones in Console → Firestore → Indexes.
# Git rollback of the whole branch:
git revert <commit>            # safe, keeps history
# or drop the branch entirely and recreate from patches (see README).
```

## B. Admin panel (this Emergent workspace)
- Deployed via Emergent "Deploy". Backend (FastAPI) + Frontend (React) + env vars are
  managed by the platform; `backend/.env` / `frontend/.env` are git-ignored and never pushed.
- Rollback: use Emergent's **Rollback** feature to return to any prior checkpoint
  (free, non-destructive) — do NOT `git reset`.

## C. Save to GitHub (this repo)
- Push to branch **`feature/production-hardening`** (select it in the Save-to-GitHub UI).
- Do **not** merge into `main`; open a PR for review.

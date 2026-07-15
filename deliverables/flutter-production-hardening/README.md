# Flutter production-hardening — deliverables (server-side)

> These files are **deliverables for the separate Flutter app repository**, kept
> here (inside the admin-panel workspace) only because Emergent's "Save to GitHub"
> pushes this admin repo. They are NOT part of the admin panel source tree.
> Apply them to the Flutter repo as described below.

## Source Flutter repository
- Repo: `https://github.com/earn2love/earn2love-app`
- Base branch: `main`
- Base commit: `9e3c55e1b471c05bbee873b3d665a0c61122b0e9` ("Complete Stripe payment test flow")
- Feature branch to create: `feature/production-hardening`

## Commits on the feature branch (4, grouped)
| Hash | Message |
|------|---------|
| `9a44f26` | chore(security): remove leaked dotfiles & stray files, harden .gitignore |
| `83014e3` | feat(functions): server-authoritative Cloud Functions (v2, modular) |
| `555bf65` | feat(rules): Firestore + Storage security rules, indexes, firebase.json |
| `65b0142` | docs: production audit, exact schema, indexes, rules, console steps & Flutter spec |

(+1486 / −197 across 21 files. Validated: `node --check` + full `require()` load with
real deps + ESLint 0 errors. Rules/indexes written to Firebase spec — deploy & emulator-test.)

## What's in this folder
- `feature-production-hardening.bundle` — the whole branch as a git bundle.
- `patches/000{1..4}-*.patch` — the 4 commits as `git am`-applicable patches.
- `PRODUCTION_AUDIT.md` — full audit, exact Firestore schema, storage paths, indexes,
  rules summary, env/secrets checklist, Firebase/Stripe/Agora console steps, Flutter spec §11.
- `ADMIN_INTEGRATION.md` — admin-panel ↔ app field mapping + withdrawal state machine.
- `env-templates/` — placeholder env/secret templates (NO real values).
- `DEPLOYMENT_AND_ROLLBACK.md` — deploy + rollback commands.

## Apply to the Flutter repo — option A (bundle)
```bash
git clone https://github.com/earn2love/earn2love-app && cd earn2love-app
git fetch /path/to/feature-production-hardening.bundle feature/production-hardening
git checkout -b feature/production-hardening FETCH_HEAD
git push -u origin feature/production-hardening    # open a PR; DO NOT merge to main yet
```

## Apply to the Flutter repo — option B (patches)
```bash
git clone https://github.com/earn2love/earn2love-app && cd earn2love-app
git checkout main && git checkout -b feature/production-hardening
git am /path/to/patches/*.patch
git push -u origin feature/production-hardening
```

## Recreate the feature branch from scratch (verify base)
```bash
git checkout 9e3c55e1b471c05bbee873b3d665a0c61122b0e9   # base commit on main
git checkout -b feature/production-hardening
git am patches/0001-*.patch patches/0002-*.patch patches/0003-*.patch patches/0004-*.patch
git log --oneline main..HEAD   # expect the 4 commits above
```

## Notes
- Deploying `firestore.rules` REQUIRES the Flutter client migration in
  `PRODUCTION_AUDIT.md §11` (client can no longer write balances directly).
- Do not commit `google-services.json`, `GoogleService-Info.plist`, service-account
  JSON, Stripe secret, or Agora certificate — all are git-ignored in the branch.

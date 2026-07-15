# Firestore Indexes — Earn2Love Admin

The admin backend deliberately **fetches with single-field constraints and sorts/paginates in memory**
(`firestore_repo.py`) to avoid drops caused by `order_by` on documents missing the sort field
(e.g. legacy `users` without `createdAt`) and to avoid mandatory composite indexes for the current data volume.

## Currently required indexes
None beyond Firestore's automatic single-field indexes. The following queries all rely on
auto-created single-field indexes:

- `users` — equality filters on `country`, `tier`, `gender`, `accountStatus`
- `reports` — `where(status == ...)`, `where(targetUid == ...)`
- `supportTickets` — `where(status == ...)`, `where(uid == ...)`
- `friendRequests` — `where(status == ...)`
- collection group `walletHistory` — `where(type == ...)` (withdraw/topup/conversion) and `where(ownerUid ...)`
- collection group `notifications`
- collection group `media` — `where(flagged == true)`
- Count aggregations (`.count()`) on the single-field equality queries above

## Recommended composite indexes (enable when data grows large, >2–3k docs)
If you later switch the repository to server-side `order_by` + range pagination for performance,
create these composite indexes in the Firebase console (Firestore → Indexes):

| Collection / Group | Fields (order) | Query scope |
|---|---|---|
| reports | status ASC, createdAt DESC | Collection |
| supportTickets | status ASC, createdAt DESC | Collection |
| friendRequests | status ASC, createdAt DESC | Collection |
| walletHistory | type ASC, createdAt DESC | Collection group |
| walletHistory | ownerUid ASC, createdAt DESC | Collection group |
| media | flagged ASC, createdAt DESC | Collection group |

To deploy via CLI, add them to `firestore.indexes.json` and run `firebase deploy --only firestore:indexes`.

## Notes
- `CAP = 400` in `firestore_repo.py` bounds how many docs are scanned per module page for
  in-memory search/sort. Raise it (and add the composite indexes above) as collections grow.

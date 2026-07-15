# Firestore Indexes — Earn2Love Admin

The admin backend deliberately **fetches with single-field constraints and sorts/paginates in memory**
(`firestore_repo.py`) to avoid drops caused by `order_by` on documents missing the sort field
(e.g. legacy `users` without `createdAt`) and to avoid mandatory composite indexes for the current data volume.

## Currently required indexes
**None.** The repository (`firestore_repo._fetch`) fetches each collection/collection-group with a
single unfiltered `.limit(CAP)` read and then applies all equality filters, search and sorting in
Python. This is intentional: `collection_group('walletHistory').where('type','==',...)` would
otherwise require an explicit **collection-group index** (single-field indexes do NOT cover
collection-group filters). By filtering in memory we avoid every composite/collection-group index
for the current data volume, and `_fetch` also catches `FailedPrecondition`/`InvalidArgument` and
degrades to an empty list if a query ever does need one.

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

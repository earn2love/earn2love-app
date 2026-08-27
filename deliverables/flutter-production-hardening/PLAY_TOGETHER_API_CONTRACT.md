# Earn2Love — Play Together Platform · Flutter API Contract

The backend (FastAPI + Firebase Admin SDK) is the **single authoritative game engine**.
Firestore is the **server-written real-time sync layer**. The Flutter client:

- **reads** the session document from Firestore in real time (never writes it),
- **sends every player action** to the FastAPI `/play/*` API,
- renders the shared game UI from the public session state.

Base URL: `REACT_APP_BACKEND_URL` (same host the admin panel uses). All routes are
prefixed with `/api`. Auth: `Authorization: Bearer <Firebase ID token>`.

---

## 1. Catalog

`GET /api/play/catalog` → games available to the signed-in user's tier.
```json
{ "tier": "love",
  "items": [ { "gameId":"would_you_rather","name":"Would You Rather","gameType":"choice",
               "category":"Conversation & Connection","shortDescription":"…",
               "icon":"Split","difficulty":"easy","estimatedMinutes":5,
               "tierAccess":["casual","friendship","love"],"supportsAI":true,
               "supportsUserVsUser":true,"configuration":{"rounds":6,"timerSeconds":45},
               "locked":false } ] }
```
`locked:true` → user's tier is not entitled (show a lock / upsell, do not start).

## 2. Create / join a session
```
POST /api/play/sessions            { "gameId":"would_you_rather", "opponentUid":"<uid|null>",
                                     "aiCharacterIds":["<id>"]? }
POST /api/play/sessions/{sid}/join
```
Returns the **public session state** (see §5). If only the host is present the session
starts as `status:"waiting"` until a second participant joins (then `active`).

## 3. Real-time sync (Firestore listener)
Listen to: `gameSessions/{sessionId}` (document).
This document holds ONLY the public state and is **server-written**. The private
subcollection `gameSessions/{sessionId}/private/**` is denied to clients by rules.
> Use the Firestore listener for live UI. Only fall back to polling `GET /api/play/sessions/{sid}` on listener error/recovery.

## 4. Player actions (authoritative)
All actions go through FastAPI. Always include an `actionId` (UUID) for idempotency and,
optionally, `expectedRevision` (the last `revision` you saw) to reject stale writes.
```
POST /api/play/sessions/{sid}/act      { "action": { "type":"answer", "value":"a",
                                                       "actionId":"<uuid>" },
                                         "expectedRevision": 4 }
POST /api/play/sessions/{sid}/advance  { "expectedRevision": 5 }     // reveal → next round
POST /api/play/sessions/{sid}/abandon
POST /api/play/sessions/{sid}/rematch
GET  /api/play/sessions/{sid}                                        // fetch + yourActions
```
Errors: `403` not a participant / tier locked / inactive · `409` rule violation or
`revision mismatch` (refresh) · duplicate `actionId` → **no-op** (safe on double-tap/retry).

### Action schema per mechanic (from `availableActions`)
| gameType | action.type      | payload                                             |
|----------|------------------|-----------------------------------------------------|
| choice   | `answer`         | `value`= option key (from `prompt.options[].key`)   |
| trivia   | `answer`         | `value`= option key                                 |
| prompt   | `respond`        | `value`= text (≤500)                                |
| guess    | `set_secret`     | `value`= option key **or** `{statements:[3], lieIndex}` (truths_lie) |
| guess    | `guess`          | `value`= option key or `0|1|2` (truths_lie)         |
| coop     | `contribute`     | `value`= option key (if options) or text (≤300)     |

The backend tells you exactly what's allowed **right now** for the current user via
`yourActions` (on `GET .../{sid}` and on every act response). Render from that — do not
hardcode turn logic on the client.

## 5. Public session state (what the client renders)
```json
{ "sessionId":"…","gameId":"…","gameName":"…","status":"active",
  "participantIds":["u1","u2"],"aiCharacterIds":[],"hostUserId":"u1",
  "mechanic":"choice","round":2,"totalRounds":6,"phase":"answering",
  "turn":"u1|null","setter":"u1|null","subphase":"set|guess|null",
  "prompt":{ "id":"…","prompt":"Would you rather…","options":[{"key":"a","label":"…"}] },
  "submitted":{ "u1":true,"u2":false },      // flags only — never other players' picks
  "revealed":{ … },                          // present only when phase in reveal|complete
  "scores":{ "u1":1,"u2":0 }, "artifact":[…] (coop only),
  "revision":7, "result":null,
  "startedAt":"…","lastActivityAt":"…","completedAt":null }
```
Phases: `waiting → answering → reveal → (next round …) → complete`.
`result.type`: `scored` (`winners`,`draw`), `cooperative` (`artifact`), or `completed`.

## 6. AI Character Engine (future)
AI participants are just another authenticated participant. The AI engine calls the
**same** `/play/sessions/{sid}/act` path. Per-game context is available server-side via
`engines.ai_context(auth, participantId)` → `{ availableActions, publicState, currentPrompt,
phase, isYourTurn }`. No LLM calls live inside any game; games only expose structured
state/actions. Wire your provider (OpenAI/Gemini/Anthropic) at the engine layer.

## 7. Security summary
- Clients never write authoritative state; FastAPI validates membership, turn, phase,
  option validity, and applies transitions inside a Firestore **transaction**.
- `revision` is monotonic; `expectedRevision` guards against stale/duplicate writes.
- Hidden info (correct answers, un-revealed picks, the lie index) is kept in the
  server-only private subcollection and never placed in the client-readable document.
- Firestore rules: see `firebase/firestore.rules` (games/gameContent read-only to clients,
  gameSessions read-for-participants + write:false, private/** + gameEvents server-only).

## 8. Deploy steps
1. Provide a valid Firebase **service-account key** to the admin backend env
   (`FIREBASE_PROJECT_ID`, `FIREBASE_CLIENT_EMAIL`, `FIREBASE_PRIVATE_KEY`).
2. In the admin panel: **Play Together → Seed catalog** (writes `games` + `gameContent`).
3. Deploy `firestore.rules` (adds the game collections above).
4. No composite indexes are required by the backend (it filters in memory and reads
   sessions by id). If you later query `gameEvents` by `gameId` + `event` for dashboards,
   add a composite index on `(gameId ASC, event ASC)`.

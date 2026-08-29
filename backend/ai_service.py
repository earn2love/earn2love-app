"""Service layer wiring the AI Character Engine to the admin/API.

- Production character CRUD -> FirestoreCharacterRepository (backend-authoritative).
- AI Character Lab -> isolated in-memory repos per lab session (seeded with the
  reference characters + optional fixtures). Sandbox NEVER writes production data.
The SAME engine/planner/guards/provider run in both — only storage differs.
"""
import os
import uuid
import asyncio
import logging

from ai_engine.repository import FirestoreCharacterRepository, InMemoryCharacterRepository
from ai_engine.registry import REFERENCE_CHARACTERS, seed_reference
from ai_engine.engine import CharacterEngine
from ai_engine import multimodal_intelligence as MM13
from ai_engine import provider as PROV
import ai_media_service as ai_media
from ai_engine import evaluation as EVAL
from ai_engine import rate_limit as RL
from ai_engine import feature_flags as FF
from ai_engine.schema import new_character, validate_character

logger = logging.getLogger(__name__)

_prod_repo = None
_lab_sessions = {}   # sessionId -> {repo, engine, characterId}


def prod_repo():
    global _prod_repo
    if _prod_repo is None:
        _prod_repo = FirestoreCharacterRepository()
    return _prod_repo


def reference_characters():
    return [dict(c) for c in REFERENCE_CHARACTERS]


# ---------------- Production CRUD (Firestore) ----------------
def list_stored():
    return prod_repo().list_characters()


def get_character(cid):
    return prod_repo().get_character(cid) or next((dict(c) for c in REFERENCE_CHARACTERS if c["characterId"] == cid), None)


def upsert_character(data, author=""):
    if not data.get("characterId"):
        data["characterId"] = data.get("slug") or f"char_{uuid.uuid4().hex[:8]}"
    c = new_character(**{**data})
    ok, errs = validate_character(c)
    if not ok:
        raise ValueError("; ".join(errs))
    repo = prod_repo()
    existing = repo.get_character(c["characterId"])
    if existing:
        c["version"] = existing.get("version", 1)
        c["createdAt"] = existing.get("createdAt", c["createdAt"])
    repo.upsert_character(c)
    return c


def new_version(cid, author=""):
    repo = prod_repo()
    c = repo.get_character(cid)
    if not c:
        return None
    c["version"] = c.get("version", 1) + 1
    repo.save_version(cid, dict(c))
    repo.upsert_character(c)
    return c


def list_versions(cid):
    return prod_repo().list_versions(cid)


def set_flags(cid, enabled=None, archived=None):
    repo = prod_repo()
    c = repo.get_character(cid)
    if not c:
        return None
    if enabled is not None:
        c["enabled"] = enabled
    if archived is not None:
        c["archived"] = archived
    repo.upsert_character(c)
    return c


def metrics(cid):
    ms = prod_repo().get_metrics(cid)
    if not ms:
        return {"hasData": False, "count": 0}
    lat = [m["latencyMs"] for m in ms if m.get("latencyMs")]
    return {"hasData": True, "count": len(ms),
            "avgLatencyMs": round(sum(lat) / len(lat)) if lat else None,
            "consistencyPassRate": round(sum(1 for m in ms if (m.get("quality") or {}).get("consistencyPassed", True)) / len(ms), 2),
            "repetitionPassRate": round(sum(1 for m in ms if (m.get("quality") or {}).get("repetitionPassed", True)) / len(ms), 2)}


def delete_character(cid):
    return prod_repo().delete_character(cid)


def seed_reference_to_firestore():
    return seed_reference(prod_repo())


# ---------------- Feature flags (centralized, Firestore-backed) ----------------
def flag_defaults():
    return {"flags": dict(FF.DEFAULTS), "meta": FF.FLAG_META, "defaults": dict(FF.DEFAULTS)}


def get_feature_flags():
    return {"flags": FF.get_flags(prod_repo().db), "meta": FF.FLAG_META, "defaults": dict(FF.DEFAULTS)}


def update_feature_flags(updates, author=""):
    flags = FF.set_flags(prod_repo().db, updates, author)
    return {"flags": flags, "meta": FF.FLAG_META, "defaults": dict(FF.DEFAULTS)}


def _live_flags():
    """Best-effort flag read; fail-open to all-enabled defaults."""
    try:
        return FF.get_flags(prod_repo().db)
    except Exception:
        return dict(FF.DEFAULTS)


# ---------------- Production chat (persistent — Firestore) ----------------

# ---------------- V13 multimodal preparation ----------------

_REFERENCED_IMAGE_UNAVAILABLE_ERRORS = frozenset(
    {
        "image_not_found",
        "image_expired",
        "image_scope_mismatch",
    }
)


def _is_referenced_image_unavailable_error(
    error,
):
    return (
        str(
            error
            or ""
        ).strip()
        in _REFERENCED_IMAGE_UNAVAILABLE_ERRORS
    )


def _referenced_image_unavailable_result(
    character_id,
):
    """
    Fail closed when an explicitly referenced historical image can no
    longer be safely resolved in the exact conversation scope.
    """
    return {
        "ok": False,
        "error":
            "referenced_image_unavailable",
        "needsImageReupload":
            True,
        "responseText":
            (
                "I can?t access that earlier image anymore. "
                "Please upload it again so I can look at it safely."
            ),
        "characterId":
            character_id,
        "relationshipState":
            None,
        "memoryIdsUsed":
            [],
        "usage": {
            "provider": "guard",
            "model":
                "referenced_image_unavailable",
            "latencyMs": 0,
            "attempts": 0,
        },
    }

async def _resolve_continuity_image_ids(
    character_id,
    user_id,
    conversation_id,
    message,
):
    """
    Recover opaque image IDs only from this authenticated
    character + user + conversation history.

    Historical visual summaries are never reused.
    """
    if not MM13.is_image_followup_reference(
        message
    ):
        return []

    turns = prod_repo().get_turns(
        character_id,
        user_id,
        limit=
            MM13.MAX_CONTINUITY_LOOKBACK_TURNS,
        conversation_id=
            conversation_id,
    )

    return MM13.extract_turn_image_ids(
        turns
    )


async def _prepare_multimodal_context(
    character_id,
    user_id,
    conversation_id,
    message,
    image_ids,
):
    """
    Resolve only authenticated, conversation-scoped temporary images
    and produce an ephemeral visual observation.

    Nothing in this helper writes V11 memory, adaptation, goals,
    relationship state, plans, or Firestore conversation state.
    """
    if not image_ids:
        return None

    if not isinstance(
        image_ids,
        (
            list,
            tuple,
        ),
    ):
        raise ValueError(
            "image_ids_must_be_list"
        )

    cleaned = []
    seen_image_ids = set()

    for value in image_ids:
        # Image IDs are opaque references. Never lowercase,
        # casefold, rewrite, or otherwise transform them.
        image_id = str(
            value
            or ""
        ).strip()

        if not image_id:
            raise ValueError(
                "image_id_required"
            )

        if image_id in seen_image_ids:
            raise ValueError(
                "duplicate_image_id"
            )

        seen_image_ids.add(
            image_id
        )

        cleaned.append(
            image_id
        )

    if len(
        cleaned
    ) > MM13.MAX_IMAGES_PER_TURN:
        raise ValueError(
            "too_many_images"
        )

    resolved = []

    for image_id in cleaned:
        reference = (
            await ai_media.resolve_image_reference(
                image_id,
                user_id=user_id,
                character_id=character_id,
                conversation_id=
                    conversation_id,
                detail="auto",
            )
        )

        resolved.append(
            reference
        )

    context = MM13.build_turn_context(
        character_id,
        user_id,
        conversation_id,
        message,
        resolved,
    )

    if not context.ok:
        raise ValueError(
            context.error
            or "invalid_multimodal_input"
        )

    provider_name = os.environ.get(
        "AI_MULTIMODAL_PROVIDER",
        "openai",
    ).strip().casefold()

    model_name = os.environ.get(
        "AI_MULTIMODAL_MODEL",
        os.environ.get(
            "AI_ENGINE_MODEL",
            "gpt-5.6-sol",
        ),
    ).strip()

    vision_prompt = (
        str(
            message
            or ""
        ).strip()
        or (
            "Describe only the relevant visible content "
            "in the attached image or images."
        )
    )

    vision_system = (
        "You are the V13 visual-understanding capability for Earn2Love. "
        "Inspect only the supplied authenticated image inputs. "
        "Return a concise factual visual observation that the conversation "
        "model can use to answer the user's message. "
        "Do not invent details that are not visible. "
        "If something is unclear, state that it is unclear. "
        "Do not reveal hidden reasoning. "
        "Do not mention storage URLs, authentication, provider internals, "
        "or implementation details."
    )

    result = await PROV.analyze_images(
        vision_system,
        vision_prompt,
        context.provider_images(),
        provider=provider_name,
        model=model_name,
    )

    if not result.get(
        "ok"
    ):
        raise RuntimeError(
            "multimodal_provider_failed:"
            + str(
                result.get(
                    "error",
                    "unknown",
                )
            )
        )

    summary = (
        MM13.normalize_visual_summary(
            result.get(
                "text",
                "",
            )
        )
    )

    return {
        "visualSummary": summary,
        "imageCount":
            context.image_count,
        "scopeToken":
            context.scope_token,
        "imageIds": [
            image.image_id
            for image in context.images
        ],
        "usage": {
            "provider":
                result.get(
                    "provider"
                ),
            "model":
                result.get(
                    "model"
                ),
            "latencyMs":
                result.get(
                    "latencyMs"
                ),
        },
    }


_prod_engine = None


def prod_engine():
    global _prod_engine
    if _prod_engine is None:
        _prod_engine = CharacterEngine(prod_repo())
    return _prod_engine


async def chat(
    character_id,
    user_id,
    message,
    language=None,
    client_message_id=None,
    conversation_id="default",
    image_ids=None,
):
    """Production, PERSISTENT conversation with reliability guards:
    - rate limiting / abuse / platform circuit breaker (SOFT cooldown, no LLM call);
    - idempotency: a repeated clientMessageId (double-tap / retry) replays the stored
      reply instead of generating again;
    - concurrency: per-(character,user) lock serialises overlapping sends so we never
      double-generate or interleave, and never attach a stale reply.
    Persists memory/relationship/turns/metrics to Firestore (sandbox=False)."""
    gate = RL.check_and_consume(prod_repo().db, user_id, message)
    if not gate["allowed"]:
        return {"ok": True, "rateLimited": True, "cooldown": True,
                "cooldownReason": gate["reason"], "retryAfterSeconds": gate["retryAfter"],
                "responseText": RL.cooldown_message(gate["reason"]),
                "characterId": character_id, "relationshipState": None, "memoryIdsUsed": [],
                "usage": {"provider": "guard", "model": "rate_limit", "latencyMs": 0, "attempts": 0}}

    flags = _live_flags()
    if not flags.get("aiCharactersEnabled", True):
        return {"ok": True, "disabled": True,
                "responseText": "I'm taking a short break right now — chat will be back shortly. 💛",
                "characterId": character_id, "relationshipState": None, "memoryIdsUsed": [],
                "usage": {"provider": "guard", "model": "feature_flag", "latencyMs": 0, "attempts": 0}}

    conversation_id = str(conversation_id or "default").strip() or "default"

    # Use the exact repository conversation document mapping so
    # idempotency metadata and persisted turns always share one parent.
    from ai_engine.repository import _conversation_doc_id

    conv = prod_repo().db.collection(
        "aiCharacterConversations"
    ).document(
        _conversation_doc_id(
            character_id,
            user_id,
            conversation_id,
        )
    )
    if client_message_id:
        snap = conv.get()
        d = snap.to_dict() if snap.exists else {}
        if d.get("lastClientMessageId") == client_message_id and d.get("lastResponseText"):
            return {"ok": True, "idempotentReplay": True, "generationId": d.get("lastGenerationId"),
                    "responseText": d["lastResponseText"], "characterId": character_id,
                    "relationshipState": d.get("lastRelationshipState"), "memoryIdsUsed": [],
                    "usage": {"provider": "cache", "model": "idempotent", "latencyMs": 0, "attempts": 0}}

    generation_id = uuid.uuid4().hex
    async with _chat_lock(character_id, user_id, conversation_id):
        # V13.3 authenticated multimodal preparation.
        #
        # Runs after idempotency replay and inside the exact
        # character/user/conversation lock.
        multimodal_context = None

        # V13.4 recover image IDs only from this exact conversation.
        effective_image_ids = list(
            image_ids
            or []
        )

        continuity_reused = False

        # Historical visual continuity is activated only by an
        # explicit image reference and only when the client did not
        # supply new image IDs for this turn.
        continuity_requested = bool(
            not effective_image_ids
            and MM13.is_image_followup_reference(
                message
            )
        )

        if continuity_requested:
            effective_image_ids = (
                await _resolve_continuity_image_ids(
                    character_id,
                    user_id,
                    conversation_id,
                    message,
                )
            )

            # Never answer an explicitly visual follow-up without the
            # actual historical image. Falling through to text-only
            # generation could invent visual facts.
            if not effective_image_ids:
                return (
                    _referenced_image_unavailable_result(
                        character_id
                    )
                )

            continuity_reused = True

        if effective_image_ids:
            try:
                multimodal_context = (
                    await _prepare_multimodal_context(
                        character_id,
                        user_id,
                        conversation_id,
                        message,
                        effective_image_ids,
                    )
                )

            except ValueError as exc:
                # Historical continuity references that disappeared,
                # expired, or no longer resolve in this exact scope
                # collapse into one safe client contract.
                if (
                    continuity_reused
                    and
                    _is_referenced_image_unavailable_error(
                        exc
                    )
                ):
                    return (
                        _referenced_image_unavailable_result(
                            character_id
                        )
                    )

                # New image uploads retain their precise validation
                # errors; only historical continuity is normalized.
                return {
                    "ok": False,
                    "error": str(
                        exc
                    ),
                    "characterId":
                        character_id,
                }

            except RuntimeError as exc:
                logger.warning(
                    "V13 multimodal preparation failed: %s",
                    exc,
                )

                return {
                    "ok": False,
                    "error":
                        "multimodal_unavailable",
                    "characterId":
                        character_id,
                }

        r = await prod_engine().respond(
            character_id,
            user_id,
            message,
            sandbox=False,
            language_override=language or None,
            feature_flags=flags,
            conversation_id=conversation_id,
            multimodal_context=multimodal_context,
        )
        if r.get("ok"):
            r["generationId"] = generation_id

            if multimodal_context:
                r["multimodal"] = {
                    "version": 13,
                    "imageCount":
                        multimodal_context.get(
                            "imageCount",
                            0,
                        ),
                    "imageIds": list(
                        multimodal_context.get(
                            "imageIds",
                            [],
                        )
                    ),
                    "ephemeral": True,
                    "continuityReused":
                        continuity_reused,
                }
            if client_message_id:
                conv.set({"lastClientMessageId": client_message_id, "lastResponseText": r["responseText"],
                          "lastGenerationId": generation_id, "lastRelationshipState": r.get("relationshipState")},
                         merge=True)
        return r


# Per-(character,user) in-flight locks — serialise concurrent sends (single backend).
_locks = {}



# ============================================================
# V14 IMAGE REQUEST IDEMPOTENCY
# ============================================================

def _v14_image_request_ref(
    character_id,
    user_id,
    conversation_id,
):
    """
    Exact existing conversation-document authority.

    No new Firestore collection is introduced.
    """
    from ai_engine.repository import (
        _conversation_doc_id,
    )

    conversation_id = str(
        conversation_id
        or "default"
    ).strip() or "default"

    db = prod_repo().db

    return (
        db,
        db.collection(
            "aiCharacterConversations"
        ).document(
            _conversation_doc_id(
                character_id,
                user_id,
                conversation_id,
            )
        ),
    )


def begin_image_request(
    character_id,
    user_id,
    conversation_id,
    client_request_id,
    request_fingerprint,
    operation,
    *,
    lease_seconds=180,
):
    """
    Transactionally reserve one V14 image operation.

    Returns one of:
      new
      replay
      in_progress
      busy
      conflict

    Same completed request ID + same fingerprint replays.
    Same request ID + changed payload fails closed as conflict.
    Pending requests are protected by a bounded lease so process
    crashes cannot permanently deadlock a conversation.
    """
    import time
    from google.cloud import firestore

    client_request_id = str(
        client_request_id
        or ""
    ).strip()

    request_fingerprint = str(
        request_fingerprint
        or ""
    ).strip()

    operation = str(
        operation
        or ""
    ).strip()

    lease_seconds = max(
        30,
        int(
            lease_seconds
            or 180
        ),
    )

    if not client_request_id:
        raise ValueError(
            "client_request_id_required"
        )

    if not request_fingerprint:
        raise ValueError(
            "request_fingerprint_required"
        )

    if operation not in {
        "generate",
        "edit",
    }:
        raise ValueError(
            "invalid_image_operation"
        )

    db, ref = _v14_image_request_ref(
        character_id,
        user_id,
        conversation_id,
    )

    txn = db.transaction()

    @firestore.transactional
    def _txn(t):
        snap = ref.get(
            transaction=t
        )

        data = (
            snap.to_dict()
            if snap.exists
            else {}
        )

        current = (
            data.get(
                "v14ImageRequest"
            )
            or {}
        )

        now = time.time()

        current_id = str(
            current.get(
                "clientRequestId"
            )
            or ""
        )

        current_fp = str(
            current.get(
                "requestFingerprint"
            )
            or ""
        )

        current_operation = str(
            current.get(
                "operation"
            )
            or ""
        )

        current_status = str(
            current.get(
                "status"
            )
            or ""
        )

        try:
            started_at = float(
                current.get(
                    "startedAtEpoch",
                    0,
                )
                or 0
            )
        except Exception:
            started_at = 0.0

        age = max(
            0.0,
            now - started_at,
        )

        active_pending = (
            current_status == "pending"
            and
            age < lease_seconds
        )

        if (
            current_id
            == client_request_id
        ):
            if (
                current_fp
                != request_fingerprint
                or
                current_operation
                != operation
            ):
                return {
                    "action": "conflict",
                }

            if (
                current_status
                == "complete"
                and
                isinstance(
                    current.get(
                        "result"
                    ),
                    dict,
                )
            ):
                return {
                    "action": "replay",
                    "result": dict(
                        current[
                            "result"
                        ]
                    ),
                }

            if active_pending:
                return {
                    "action":
                        "in_progress",
                    "retryAfter": 2,
                }

            # Same request after a stale/dead lease:
            # reclaim reservation safely.
            t.set(
                ref,
                {
                    "v14ImageRequest": {
                        "clientRequestId":
                            client_request_id,
                        "requestFingerprint":
                            request_fingerprint,
                        "operation":
                            operation,
                        "status":
                            "pending",
                        "startedAtEpoch":
                            now,
                        "updatedAtEpoch":
                            now,
                        "result":
                            None,
                    }
                },
                merge=True,
            )

            return {
                "action": "new",
                "reclaimed": True,
            }

        if active_pending:
            return {
                "action": "busy",
                "retryAfter": 2,
            }

        t.set(
            ref,
            {
                "v14ImageRequest": {
                    "clientRequestId":
                        client_request_id,
                    "requestFingerprint":
                        request_fingerprint,
                    "operation":
                        operation,
                    "status":
                        "pending",
                    "startedAtEpoch":
                        now,
                    "updatedAtEpoch":
                        now,
                    "result":
                        None,
                }
            },
            merge=True,
        )

        return {
            "action": "new",
            "reclaimed": False,
        }

    return _txn(
        txn
    )


def complete_image_request(
    character_id,
    user_id,
    conversation_id,
    client_request_id,
    request_fingerprint,
    operation,
    result,
):
    """
    Transactionally commit the completed image result.

    The signed URL is intentionally NOT persisted. Replay resolves a
    fresh scoped short-lived URL from the stored opaque image ID.
    """
    import time
    from google.cloud import firestore

    result = dict(
        result
        or {}
    )

    if "url" in result:
        raise ValueError(
            "signed_url_must_not_persist"
        )

    db, ref = _v14_image_request_ref(
        character_id,
        user_id,
        conversation_id,
    )

    txn = db.transaction()

    @firestore.transactional
    def _txn(t):
        snap = ref.get(
            transaction=t
        )

        data = (
            snap.to_dict()
            if snap.exists
            else {}
        )

        current = (
            data.get(
                "v14ImageRequest"
            )
            or {}
        )

        if (
            current.get(
                "clientRequestId"
            )
            != client_request_id
            or
            current.get(
                "requestFingerprint"
            )
            != request_fingerprint
            or
            current.get(
                "operation"
            )
            != operation
        ):
            return False

        if (
            current.get(
                "status"
            )
            == "complete"
        ):
            return True

        if (
            current.get(
                "status"
            )
            != "pending"
        ):
            return False

        now = time.time()

        t.set(
            ref,
            {
                "v14ImageRequest": {
                    "clientRequestId":
                        client_request_id,
                    "requestFingerprint":
                        request_fingerprint,
                    "operation":
                        operation,
                    "status":
                        "complete",
                    "startedAtEpoch":
                        current.get(
                            "startedAtEpoch",
                            now,
                        ),
                    "updatedAtEpoch":
                        now,
                    "completedAtEpoch":
                        now,
                    "result":
                        result,
                }
            },
            merge=True,
        )

        return True

    return bool(
        _txn(
            txn
        )
    )


def abort_image_request(
    character_id,
    user_id,
    conversation_id,
    client_request_id,
    request_fingerprint,
    operation,
):
    """
    Best-effort transactional reservation release.

    Only the exact currently-pending request may clear itself.
    A newer or completed request can never be erased by an older
    failing worker.
    """
    from google.cloud import firestore

    db, ref = _v14_image_request_ref(
        character_id,
        user_id,
        conversation_id,
    )

    txn = db.transaction()

    @firestore.transactional
    def _txn(t):
        snap = ref.get(
            transaction=t
        )

        if not snap.exists:
            return False

        data = (
            snap.to_dict()
            or {}
        )

        current = (
            data.get(
                "v14ImageRequest"
            )
            or {}
        )

        if (
            current.get(
                "clientRequestId"
            )
            != client_request_id
            or
            current.get(
                "requestFingerprint"
            )
            != request_fingerprint
            or
            current.get(
                "operation"
            )
            != operation
            or
            current.get(
                "status"
            )
            != "pending"
        ):
            return False

        t.set(
            ref,
            {
                "v14ImageRequest":
                    None
            },
            merge=True,
        )

        return True

    return bool(
        _txn(
            txn
        )
    )



def _chat_lock(character_id, user_id, conversation_id="default"):
    conversation_id = str(conversation_id or "default").strip() or "default"
    return _locks.setdefault(
        f"{character_id}:{user_id}:{conversation_id}",
        asyncio.Lock(),
    )


def chat_history(
    character_id,
    user_id,
    limit=100,
    conversation_id="default",
):
    return prod_repo().get_turns(
        character_id,
        user_id,
        limit=limit,
        conversation_id=conversation_id,
    )


def relationship_state(character_id, user_id):
    return prod_repo().get_relationship(character_id, user_id) or {"state": "new"}


# ---------------- AI Character Lab (sandbox, in-memory) ----------------
def lab_start(character_id, memory_fixtures=None):
    repo = InMemoryCharacterRepository()
    seed_reference(repo)
    # if the character is a stored (non-reference) one, try to load it into the sandbox
    if not repo.get_character(character_id):
        try:
            stored = prod_repo().get_character(character_id)
            if stored:
                repo.upsert_character(dict(stored))
        except Exception:
            pass
    if not repo.get_character(character_id):
        raise ValueError("character_not_found")
    sid = "lab_" + uuid.uuid4().hex[:10]
    for fx in (memory_fixtures or []):
        repo.add_memory(character_id, "lab_user", {"text": fx, "importance": 0.8, "explicitSave": True})
    _lab_sessions[sid] = {"repo": repo, "engine": CharacterEngine(repo), "characterId": character_id, "history": []}
    return {"sessionId": sid, "characterId": character_id,
            "character": {k: repo.get_character(character_id).get(k) for k in
                          ("displayName", "personalityTraits", "languages", "city", "country", "profession")}}


async def lab_chat(session_id, message, language=None, relationship_state=None):
    sess = _lab_sessions.get(session_id)
    if not sess:
        raise ValueError("lab_session_not_found")
    r = await sess["engine"].respond(
        sess["characterId"], "lab_user", message, sandbox=True,
        language_override=language or None, relationship_override=relationship_state or None,
        history_fixture=list(sess["history"]), feature_flags=_live_flags())
    if r.get("ok"):
        sess["history"].append({"sender": "user", "text": message})
        sess["history"].append({"sender": "character", "text": r["responseText"]})
    return r


def lab_reset(session_id):
    sess = _lab_sessions.get(session_id)
    if sess:
        sess["history"] = []
    return {"ok": True}


# ---------------- Evaluation (offline / sandbox) ----------------
async def run_evaluation(character_ids=None):
    repo = InMemoryCharacterRepository()
    ids = seed_reference(repo)
    engine = CharacterEngine(repo)
    targets = character_ids or ids
    return await EVAL.run_full(engine, targets)

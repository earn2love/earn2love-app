"""Persistence behind a clean repository interface.

Business logic (engine, memory, planner, guards, provider) is identical regardless
of backend. `InMemoryCharacterRepository` is used for tests / sandbox / evaluation;
`FirestoreCharacterRepository` is the production backend. NEVER create simplified AI
logic just for the in-memory backend — only storage differs.
"""
import time
import uuid
import hashlib
from abc import ABC, abstractmethod
from ai_engine import relationship_intelligence as RI
from ai_engine import adaptive_intelligence as AI
from ai_engine import goal_intelligence as GI
from ai_engine import plan_intelligence as PL9
from datetime import datetime, timezone
from google.cloud import firestore


def _now():
    return datetime.now(timezone.utc).isoformat()


def _normalize_conversation_id(value):
    """
    Stable conversation namespace.

    Existing callers that do not provide a conversation ID continue to use
    the historical/default conversation.
    """
    value = str(value or "default").strip()

    if not value:
        value = "default"

    return value[:128]


def _conversation_doc_id(cid, uid, conversation_id="default"):
    """
    Preserve the existing Firestore parent document for the default
    conversation while giving additional sessions their own physical parent.

    The conversation ID itself is hashed before it becomes part of a
    Firestore document ID.
    """
    conversation_id = _normalize_conversation_id(conversation_id)

    legacy = f"{cid}__{uid}"

    if conversation_id == "default":
        return legacy

    digest = hashlib.sha256(
        conversation_id.encode("utf-8")
    ).hexdigest()[:24]

    return f"{legacy}__{digest}"


class CharacterRepository(ABC):
    # --- characters ---
    @abstractmethod
    def list_characters(self, include_archived=True): ...
    @abstractmethod
    def get_character(self, cid): ...
    @abstractmethod
    def upsert_character(self, c): ...
    @abstractmethod
    def save_version(self, cid, snapshot): ...
    @abstractmethod
    def list_versions(self, cid): ...
    # --- world facts ---
    @abstractmethod
    def get_world_facts(self, cid): ...
    # --- memories ---
    @abstractmethod
    def add_memory(self, cid, uid, mem): ...
    @abstractmethod
    def list_memories(self, cid, uid): ...
    @abstractmethod
    def save_structured_memory(self, cid, uid, mem): ...

    @abstractmethod
    def revise_memories(self, cid, uid, memory_ids, action, metadata=None): ...
    # --- relationship ---
    @abstractmethod
    def get_relationship(self, cid, uid): ...
    @abstractmethod
    def set_relationship(self, cid, uid, state): ...

    # --- V7 per-user communication adaptation ---
    @abstractmethod
    def get_adaptation(self, cid, uid): ...
    @abstractmethod
    def set_adaptation(self, cid, uid, state): ...
    @abstractmethod
    def advance_adaptation(self, cid, uid, user_text): ...

    # --- V8 per-user goal / intent state ---
    @abstractmethod
    def get_goal_state(self, cid, uid): ...

    @abstractmethod
    def set_goal_state(self, cid, uid, state): ...

    @abstractmethod
    def advance_goal_state(self, cid, uid, user_text): ...

    # --- V9 per-user reasoning / execution plan state ---
    @abstractmethod
    def get_plan_state(self, cid, uid): ...

    @abstractmethod
    def set_plan_state(self, cid, uid, state): ...

    @abstractmethod
    def advance_plan_state(
        self,
        cid,
        uid,
        user_text,
        goal_state=None,
    ): ...


    def advance_relationship(
        self,
        cid,
        uid,
        understanding,
        user_text=None,
    ):
        state = self.get_relationship(cid, uid)

        if user_text is not None:
            state = RI.evolve(
                state,
                cid,
                uid,
                user_text,
            )

            self.set_relationship(
                cid,
                uid,
                state,
            )

            return state

        state = state or {
            "characterId": cid,
            "userId": uid,
            "turnCount": 0,
            "state": "new",
            "sharedTopics": [],
            "recurringJokes": [],
            "milestones": [],
        }

        state = dict(state)
        state["turnCount"] = int(state.get("turnCount", 0)) + 1

        topics = list(state.get("sharedTopics", []))

        for topic in (understanding or {}).get("topics", [])[:2]:
            if topic not in topics and len(topic) >= 4:
                topics.append(topic)

        state["sharedTopics"] = topics[-25:]

        self.set_relationship(cid, uid, state)
        return state

    # --- conversations ---
    @abstractmethod
    def append_turn(self, cid, uid, turn, conversation_id="default"): ...
    @abstractmethod
    def get_turns(self, cid, uid, limit=None, conversation_id="default"): ...
    # --- metrics / evaluations ---
    @abstractmethod
    def record_metric(self, cid, metric): ...
    @abstractmethod
    def get_metrics(self, cid): ...
    @abstractmethod
    def save_evaluation(self, ev): ...
    @abstractmethod
    def list_evaluations(self, cid=None): ...


class InMemoryCharacterRepository(CharacterRepository):
    def __init__(self):
        self.characters = {}
        self.versions = {}
        self.memories = {}          # (cid,uid) -> [mem]
        self.relationships = {}     # (cid,uid) -> state dict
        self.turns = {}             # (cid,uid) -> [turn]
        self.metrics = {}           # cid -> [metric]
        self.evaluations = []
        self.adaptations = {}
        self.plan_states = {}

    def list_characters(self, include_archived=True):
        out = list(self.characters.values())
        if not include_archived:
            out = [c for c in out if not c.get("archived")]
        return out

    def get_character(self, cid): return self.characters.get(cid)

    def delete_character(self, cid): return self.characters.pop(cid, None) is not None

    def upsert_character(self, c):
        c["updatedAt"] = _now()
        self.characters[c["characterId"]] = c
        return c

    def save_version(self, cid, snapshot):
        self.versions.setdefault(cid, []).append({"version": snapshot.get("version"), "at": _now(), "snapshot": snapshot})

    def list_versions(self, cid): return self.versions.get(cid, [])

    def get_world_facts(self, cid):
        c = self.characters.get(cid) or {}
        return c.get("worldFacts", [])

    def add_memory(self, cid, uid, mem):
        mem = {**mem, "memoryId": mem.get("memoryId") or uuid.uuid4().hex[:10], "createdAt": _now()}
        self.memories.setdefault((cid, uid), []).append(mem)
        return mem

    def list_memories(self, cid, uid): return list(self.memories.get((cid, uid), []))

    def save_structured_memory(self, cid, uid, mem):
        """
        Persist one structured fact.

        Current-state canonical slots supersede their previous active value.
        Historical/episodic facts remain independently active.
        """
        incoming = dict(mem or {})
        canonical_key = incoming.get("canonicalKey")
        should_supersede = bool(incoming.get("supersedesExisting"))

        existing = self.memories.setdefault((cid, uid), [])

        if canonical_key:
            for old in existing:
                if (
                    old.get("canonicalKey") == canonical_key
                    and old.get("status", "active") == "active"
                ):
                    same_value = (
                        str(old.get("value", "")).strip().casefold()
                        == str(incoming.get("value", "")).strip().casefold()
                    )

                    if same_value:
                        return old

                    if should_supersede:
                        old["status"] = "superseded"
                        old["supersededAt"] = _now()
                        old["supersededByValue"] = incoming.get("value")

        incoming.setdefault("status", "active")
        return self.add_memory(cid, uid, incoming)

    def revise_memories(self, cid, uid, memory_ids, action, metadata=None):
        ids = set(memory_ids or [])
        metadata = dict(metadata or {})
        changed = []

        if not ids:
            return changed

        for memory in self.memories.get((cid, uid), []):
            if memory.get("memoryId") not in ids:
                continue

            if memory.get("status", "active") != "active":
                continue

            if action == "forget":
                memory["status"] = "forgotten"
            elif action == "retract":
                memory["status"] = "retracted"
            else:
                memory["status"] = "corrected"

            memory["revisedAt"] = _now()
            memory["revisionReason"] = metadata.get("reason")
            memory["revisionSource"] = metadata.get(
                "source",
                "explicit_user",
            )

            changed.append(memory)

        return changed
    def get_relationship(self, cid, uid): return self.relationships.get((cid, uid))

    def set_relationship(self, cid, uid, state):
        self.relationships[(cid, uid)] = state
        return state

    # --- V7 per-user communication adaptation ---
    def get_adaptation(self, cid, uid):
        existing = self.adaptations.get(
            (cid, uid)
        )

        return AI.normalize_user_adaptation(
            existing,
            cid,
            uid,
        )

    def set_adaptation(self, cid, uid, state):
        normalized = AI.normalize_user_adaptation(
            state,
            cid,
            uid,
        )

        stored = dict(
            normalized
        )

        self.adaptations[(cid, uid)] = stored

        return dict(stored)

    def advance_adaptation(self, cid, uid, user_text):
        existing = self.adaptations.get(
            (cid, uid)
        )

        state = AI.evolve_user_adaptation(
            existing,
            cid,
            uid,
            user_text,
        )

        stored = dict(
            state
        )

        self.adaptations[(cid, uid)] = stored

        return dict(stored)

    # --- V8 per-user goal / intent state ---

    def get_goal_state(
        self,
        cid,
        uid,
    ):
        store = getattr(
            self,
            "goal_states",
            None,
        )

        existing = (
            store.get((cid, uid))
            if store is not None
            else None
        )

        return GI.normalize_goal_state(
            existing,
            cid,
            uid,
        )

    def set_goal_state(
        self,
        cid,
        uid,
        state,
    ):
        if not hasattr(
            self,
            "goal_states",
        ):
            self.goal_states = {}

        normalized = GI.normalize_goal_state(
            state,
            cid,
            uid,
        )

        # normalize again to keep stored state independent
        # from the object returned to the caller.
        self.goal_states[
            (cid, uid)
        ] = GI.normalize_goal_state(
            normalized,
            cid,
            uid,
        )

        return GI.normalize_goal_state(
            normalized,
            cid,
            uid,
        )

    def advance_goal_state(
        self,
        cid,
        uid,
        user_text,
    ):
        current = self.get_goal_state(
            cid,
            uid,
        )

        state = GI.evolve_goal_state(
            current,
            cid,
            uid,
            user_text,
        )

        return self.set_goal_state(
            cid,
            uid,
            state,
        )

    # --- V9 per-user reasoning / execution plan state ---

    def get_plan_state(
        self,
        cid,
        uid,
    ):
        existing = self.plan_states.get(
            (cid, uid)
        )

        return PL9.normalize_plan_state(
            existing,
            cid,
            uid,
        )

    def set_plan_state(
        self,
        cid,
        uid,
        state,
    ):
        normalized = PL9.normalize_plan_state(
            state,
            cid,
            uid,
        )

        # Store an independent normalized copy so callers
        # cannot mutate repository state by reference.
        self.plan_states[
            (cid, uid)
        ] = PL9.normalize_plan_state(
            normalized,
            cid,
            uid,
        )

        return PL9.normalize_plan_state(
            normalized,
            cid,
            uid,
        )

    def advance_plan_state(
        self,
        cid,
        uid,
        user_text,
        goal_state=None,
    ):
        current = self.get_plan_state(
            cid,
            uid,
        )

        state = PL9.evolve_plan_state(
            current,
            cid,
            uid,
            user_text,
            goal_state,
        )

        return self.set_plan_state(
            cid,
            uid,
            state,
        )


    def append_turn(
        self,
        cid,
        uid,
        turn,
        conversation_id="default",
    ):
        conversation_id = _normalize_conversation_id(
            conversation_id
        )

        stored = {
            **turn,
            "conversationId": conversation_id,
            "at": time.time(),
        }

        self.turns.setdefault(
            (
                cid,
                uid,
                conversation_id,
            ),
            [],
        ).append(stored)

        return stored

    def get_turns(
        self,
        cid,
        uid,
        limit=None,
        conversation_id="default",
    ):
        conversation_id = _normalize_conversation_id(
            conversation_id
        )

        turns = self.turns.get(
            (
                cid,
                uid,
                conversation_id,
            ),
            [],
        )

        return (
            turns[-limit:]
            if limit
            else list(turns)
        )

    def record_metric(self, cid, metric):
        self.metrics.setdefault(cid, []).append({**metric, "at": _now()})

    def get_metrics(self, cid): return self.metrics.get(cid, [])

    def save_evaluation(self, ev): self.evaluations.append({**ev, "at": _now()})

    def list_evaluations(self, cid=None):
        return [e for e in self.evaluations if cid is None or e.get("characterId") == cid]


class FirestoreCharacterRepository(CharacterRepository):
    """Production backend. Backend-authoritative writes only.
    Collections: aiCharacters, aiCharacterVersions, aiCharacterMemories,
    aiCharacterRelationshipState, aiCharacterConversations, aiCharacterMetrics,
    aiCharacterEvaluations.
    """
    def __init__(self, db=None):
        self._db = db

    @property
    def db(self):
        if self._db is None:
            from firebase_service import get_db
            self._db = get_db()
        return self._db

    def list_characters(self, include_archived=True):
        out = [d.to_dict() for d in self.db.collection("aiCharacters").stream()]
        if not include_archived:
            out = [c for c in out if not c.get("archived")]
        return out

    def get_character(self, cid):
        d = self.db.collection("aiCharacters").document(cid).get()
        return d.to_dict() if d.exists else None

    def delete_character(self, cid):
        ref = self.db.collection("aiCharacters").document(cid)
        if not ref.get().exists:
            return False
        # cascade: delete child records keyed by characterId
        for coll in ("aiCharacterVersions", "aiCharacterMemories", "aiCharacterMetrics", "aiCharacterEvaluations"):
            for d in self.db.collection(coll).where("characterId", "==", cid).stream():
                d.reference.delete()
        # relationship + conversation docs are keyed "{cid}__{uid}" (parent may be phantom -> use list_documents)
        for d in self.db.collection("aiCharacterRelationshipState").list_documents():
            if d.id.startswith(f"{cid}__"):
                d.delete()
        for d in self.db.collection("aiCharacterConversations").list_documents():
            if d.id.startswith(f"{cid}__"):
                for t in d.collection("turns").stream():
                    t.reference.delete()
                d.delete()
        ref.delete()
        return True

    def upsert_character(self, c):
        c["updatedAt"] = _now()
        self.db.collection("aiCharacters").document(c["characterId"]).set(c, merge=True)
        return c

    def save_version(self, cid, snapshot):
        self.db.collection("aiCharacterVersions").add(
            {"characterId": cid, "version": snapshot.get("version"), "at": _now(), "snapshot": snapshot})

    def list_versions(self, cid):
        q = self.db.collection("aiCharacterVersions").where("characterId", "==", cid)
        return [d.to_dict() for d in q.stream()]

    def get_world_facts(self, cid):
        c = self.get_character(cid) or {}
        return c.get("worldFacts", [])

    def add_memory(self, cid, uid, mem):
        mem = {**mem, "characterId": cid, "userId": uid,
               "memoryId": mem.get("memoryId") or uuid.uuid4().hex[:10], "createdAt": _now()}
        self.db.collection("aiCharacterMemories").document(mem["memoryId"]).set(mem)
        return mem

    def list_memories(self, cid, uid):
        q = self.db.collection("aiCharacterMemories").where("characterId", "==", cid).where("userId", "==", uid).limit(500)
        return [d.to_dict() for d in q.stream()]

    def save_structured_memory(self, cid, uid, mem):
        """
        Persist a structured fact while preserving historical values.

        Firestore transaction semantics are used so a current-state slot cannot
        end up with two active values because of concurrent writes.
        """
        incoming = dict(mem or {})
        canonical_key = incoming.get("canonicalKey")
        should_supersede = bool(incoming.get("supersedesExisting"))

        collection = self.db.collection("aiCharacterMemories")
        transaction = self.db.transaction()

        @firestore.transactional
        def _save(transaction):
            existing_docs = []

            if canonical_key:
                q = (
                    collection
                    .where("characterId", "==", cid)
                    .where("userId", "==", uid)
                    .where("canonicalKey", "==", canonical_key)
                )

                existing_docs = list(q.stream(transaction=transaction))

                for doc in existing_docs:
                    old = doc.to_dict() or {}

                    if old.get("status", "active") != "active":
                        continue

                    same_value = (
                        str(old.get("value", "")).strip().casefold()
                        == str(incoming.get("value", "")).strip().casefold()
                    )

                    if same_value:
                        return old

                    if should_supersede:
                        transaction.update(
                            doc.reference,
                            {
                                "status": "superseded",
                                "supersededAt": _now(),
                                "supersededByValue": incoming.get("value"),
                            },
                        )

            memory_id = incoming.get("memoryId") or uuid.uuid4().hex[:10]

            stored = {
                **incoming,
                "characterId": cid,
                "userId": uid,
                "memoryId": memory_id,
                "createdAt": _now(),
                "status": incoming.get("status", "active"),
            }

            ref = collection.document(memory_id)
            transaction.set(ref, stored)

            return stored

        return _save(transaction)

    def revise_memories(self, cid, uid, memory_ids, action, metadata=None):
        ids = list(dict.fromkeys(memory_ids or []))
        metadata = dict(metadata or {})

        if not ids:
            return []

        collection = self.db.collection("aiCharacterMemories")
        changed = []

        status = {
            "forget": "forgotten",
            "retract": "retracted",
        }.get(action, "corrected")

        # Each revision is scoped to the exact memory document and verified
        # against character/user ownership before mutation.
        for memory_id in ids:
            ref = collection.document(memory_id)
            snap = ref.get()

            if not snap.exists:
                continue

            current = snap.to_dict() or {}

            if current.get("characterId") != cid:
                continue

            if current.get("userId") != uid:
                continue

            if current.get("status", "active") != "active":
                continue

            update = {
                "status": status,
                "revisedAt": _now(),
                "revisionReason": metadata.get("reason"),
                "revisionSource": metadata.get(
                    "source",
                    "explicit_user",
                ),
            }

            ref.update(update)

            changed.append({
                **current,
                **update,
            })

        return changed
    def get_relationship(self, cid, uid):
        d = self.db.collection("aiCharacterRelationshipState").document(f"{cid}__{uid}").get()
        return d.to_dict() if d.exists else None

    def set_relationship(self, cid, uid, state):
        self.db.collection("aiCharacterRelationshipState").document(
            f"{cid}__{uid}"
        ).set(state, merge=True)
        return state

    def advance_relationship(
        self,
        cid,
        uid,
        understanding,
        user_text=None,
    ):
        ref = self.db.collection(
            "aiCharacterRelationshipState"
        ).document(f"{cid}__{uid}")

        transaction = self.db.transaction()

        @firestore.transactional
        def _advance(transaction):
            snap = ref.get(
                transaction=transaction
            )

            existing = (
                snap.to_dict()
                if snap.exists
                else None
            )

            if user_text is not None:

                state = RI.evolve(
                    existing,
                    cid,
                    uid,
                    user_text,
                )

            else:

                state = existing or {
                    "characterId": cid,
                    "userId": uid,
                    "turnCount": 0,
                    "state": "new",
                    "sharedTopics": [],
                    "recurringJokes": [],
                    "milestones": [],
                }

                state = dict(state)

                state["turnCount"] = (
                    int(
                        state.get(
                            "turnCount",
                            0,
                        )
                    )
                    + 1
                )

                topics = list(
                    state.get(
                        "sharedTopics",
                        [],
                    )
                )

                for topic in (
                    understanding
                    or {}
                ).get(
                    "topics",
                    [],
                )[:2]:

                    if (
                        topic not in topics
                        and len(topic) >= 4
                    ):
                        topics.append(
                            topic
                        )

                state["sharedTopics"] = topics[-25:]

            transaction.set(
                ref,
                state,
                merge=True,
            )

            return state

        return _advance(
            transaction
        )

    # --- V7 per-user communication adaptation ---
    def get_adaptation(self, cid, uid):
        ref = (
            self.db
            .collection("aiCharacterAdaptationState")
            .document(f"{cid}__{uid}")
        )

        snap = ref.get()

        existing = (
            snap.to_dict()
            if snap.exists
            else None
        )

        return AI.normalize_user_adaptation(
            existing,
            cid,
            uid,
        )

    def set_adaptation(self, cid, uid, state):
        normalized = AI.normalize_user_adaptation(
            state,
            cid,
            uid,
        )

        ref = (
            self.db
            .collection("aiCharacterAdaptationState")
            .document(f"{cid}__{uid}")
        )

        ref.set(
            normalized,
            merge=True,
        )

        return normalized

    def advance_adaptation(self, cid, uid, user_text):
        ref = (
            self.db
            .collection("aiCharacterAdaptationState")
            .document(f"{cid}__{uid}")
        )

        transaction = self.db.transaction()

        @firestore.transactional
        def _advance(transaction):
            snap = ref.get(
                transaction=transaction
            )

            existing = (
                snap.to_dict()
                if snap.exists
                else None
            )

            state = AI.evolve_user_adaptation(
                existing,
                cid,
                uid,
                user_text,
            )

            transaction.set(
                ref,
                state,
                merge=True,
            )

            return state

        return _advance(
            transaction
        )

    # --- V8 per-user goal / intent state ---

    def get_goal_state(
        self,
        cid,
        uid,
    ):
        ref = (
            self.db
            .collection("aiCharacterGoalState")
            .document(f"{cid}__{uid}")
        )

        snap = ref.get()

        existing = (
            snap.to_dict()
            if snap.exists
            else None
        )

        return GI.normalize_goal_state(
            existing,
            cid,
            uid,
        )

    def set_goal_state(
        self,
        cid,
        uid,
        state,
    ):
        normalized = GI.normalize_goal_state(
            state,
            cid,
            uid,
        )

        ref = (
            self.db
            .collection("aiCharacterGoalState")
            .document(f"{cid}__{uid}")
        )

        ref.set(
            normalized,
            merge=True,
        )

        return normalized

    def advance_goal_state(
        self,
        cid,
        uid,
        user_text,
    ):
        ref = (
            self.db
            .collection("aiCharacterGoalState")
            .document(f"{cid}__{uid}")
        )

        transaction = self.db.transaction()

        @firestore.transactional
        def _advance_goal(
            transaction,
        ):
            snap = ref.get(
                transaction=transaction
            )

            existing = (
                snap.to_dict()
                if snap.exists
                else None
            )

            state = GI.evolve_goal_state(
                existing,
                cid,
                uid,
                user_text,
            )

            transaction.set(
                ref,
                state,
                merge=True,
            )

            return state

        return _advance_goal(
            transaction
        )

    # --- V9 per-user reasoning / execution plan state ---

    def get_plan_state(
        self,
        cid,
        uid,
    ):
        ref = (
            self.db
            .collection("aiCharacterPlanState")
            .document(f"{cid}__{uid}")
        )

        snap = ref.get()

        existing = (
            snap.to_dict()
            if snap.exists
            else None
        )

        return PL9.normalize_plan_state(
            existing,
            cid,
            uid,
        )

    def set_plan_state(
        self,
        cid,
        uid,
        state,
    ):
        normalized = PL9.normalize_plan_state(
            state,
            cid,
            uid,
        )

        ref = (
            self.db
            .collection("aiCharacterPlanState")
            .document(f"{cid}__{uid}")
        )

        ref.set(
            normalized,
            merge=True,
        )

        return normalized

    def advance_plan_state(
        self,
        cid,
        uid,
        user_text,
        goal_state=None,
    ):
        ref = (
            self.db
            .collection("aiCharacterPlanState")
            .document(f"{cid}__{uid}")
        )

        transaction = self.db.transaction()

        @firestore.transactional
        def _advance_plan(
            transaction,
        ):
            snap = ref.get(
                transaction=transaction
            )

            existing = (
                snap.to_dict()
                if snap.exists
                else None
            )

            state = PL9.evolve_plan_state(
                existing,
                cid,
                uid,
                user_text,
                goal_state,
            )

            transaction.set(
                ref,
                state,
                merge=True,
            )

            return state

        return _advance_plan(
            transaction
        )


    def append_turn(
        self,
        cid,
        uid,
        turn,
        conversation_id="default",
    ):
        conversation_id = _normalize_conversation_id(
            conversation_id
        )

        conversation_ref = (
            self.db
            .collection("aiCharacterConversations")
            .document(
                _conversation_doc_id(
                    cid,
                    uid,
                    conversation_id,
                )
            )
        )

        conversation_ref.set(
            {
                "characterId": cid,
                "userId": uid,
                "conversationId": conversation_id,
                "updatedAt": _now(),
            },
            merge=True,
        )

        stored = {
            **turn,
            "characterId": cid,
            "userId": uid,
            "conversationId": conversation_id,
            "at": _now(),
        }

        conversation_ref.collection(
            "turns"
        ).add(stored)

        return stored

    def get_turns(
        self,
        cid,
        uid,
        limit=None,
        conversation_id="default",
    ):
        conversation_id = _normalize_conversation_id(
            conversation_id
        )

        conversation_ref = (
            self.db
            .collection("aiCharacterConversations")
            .document(
                _conversation_doc_id(
                    cid,
                    uid,
                    conversation_id,
                )
            )
        )

        docs = [
            doc.to_dict()
            for doc in conversation_ref
            .collection("turns")
            .stream()
        ]

        docs.sort(
            key=lambda turn: turn.get(
                "index",
                0,
            )
        )

        if limit:
            docs = docs[-limit:]

        return docs

    def record_metric(self, cid, metric):
        self.db.collection("aiCharacterMetrics").add({**metric, "characterId": cid, "at": _now()})

    def get_metrics(self, cid):
        q = self.db.collection("aiCharacterMetrics").where("characterId", "==", cid).limit(1000)
        return [d.to_dict() for d in q.stream()]

    def save_evaluation(self, ev):
        self.db.collection("aiCharacterEvaluations").add({**ev, "at": _now()})

    def list_evaluations(self, cid=None):
        col = self.db.collection("aiCharacterEvaluations")
        q = col.where("characterId", "==", cid) if cid else col
        return [d.to_dict() for d in q.stream()]

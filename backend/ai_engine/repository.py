"""Persistence behind a clean repository interface.

Business logic (engine, memory, planner, guards, provider) is identical regardless
of backend. `InMemoryCharacterRepository` is used for tests / sandbox / evaluation;
`FirestoreCharacterRepository` is the production backend. NEVER create simplified AI
logic just for the in-memory backend — only storage differs.
"""
import time
import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timezone


def _now():
    return datetime.now(timezone.utc).isoformat()


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
    # --- relationship ---
    @abstractmethod
    def get_relationship(self, cid, uid): ...
    @abstractmethod
    def set_relationship(self, cid, uid, state): ...
    # --- conversations ---
    @abstractmethod
    def append_turn(self, cid, uid, turn): ...
    @abstractmethod
    def get_turns(self, cid, uid, limit=None): ...
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

    def list_characters(self, include_archived=True):
        out = list(self.characters.values())
        if not include_archived:
            out = [c for c in out if not c.get("archived")]
        return out

    def get_character(self, cid): return self.characters.get(cid)

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

    def get_relationship(self, cid, uid): return self.relationships.get((cid, uid))

    def set_relationship(self, cid, uid, state):
        self.relationships[(cid, uid)] = state
        return state

    def append_turn(self, cid, uid, turn):
        self.turns.setdefault((cid, uid), []).append({**turn, "at": time.time()})

    def get_turns(self, cid, uid, limit=None):
        t = self.turns.get((cid, uid), [])
        return t[-limit:] if limit else list(t)

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
        q = self.db.collection("aiCharacterMemories").where("characterId", "==", cid).where("userId", "==", uid)
        return [d.to_dict() for d in q.stream()]

    def get_relationship(self, cid, uid):
        d = self.db.collection("aiCharacterRelationshipState").document(f"{cid}__{uid}").get()
        return d.to_dict() if d.exists else None

    def set_relationship(self, cid, uid, state):
        self.db.collection("aiCharacterRelationshipState").document(f"{cid}__{uid}").set(state, merge=True)
        return state

    def append_turn(self, cid, uid, turn):
        self.db.collection("aiCharacterConversations").document(f"{cid}__{uid}").collection("turns").add(turn)

    def get_turns(self, cid, uid, limit=None):
        col = self.db.collection("aiCharacterConversations").document(f"{cid}__{uid}").collection("turns")
        docs = [d.to_dict() for d in col.stream()]
        docs.sort(key=lambda t: t.get("index", 0))
        return docs[-limit:] if limit else docs

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

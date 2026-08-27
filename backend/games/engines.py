"""Reusable game MECHANICS (engines).

Every mechanic implements the same contract so the future AI Character Engine can
participate through the exact same validated action path as a human:

    start(auth)                         -> initialise first round (mutates auth)
    available_actions(auth, pid)        -> [ {type, ...schema} ]   (structured)
    apply(auth, pid, action)            -> [events]  (validates + mutates auth)
    public_view(auth)                   -> dict safe for ALL participants
    ai_context(auth, pid)               -> dict for the AI engine
    (completion + result are set inside apply)

`auth` is the AUTHORITATIVE server-side state (never sent raw to clients). The
public projection strips hidden info (correct answers, un-revealed picks, the lie
index, etc.). Clients read only public_view(auth) via the session document.
"""
from datetime import datetime, timezone


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------
def _cur_item(auth):
    i = auth["round"] - 1
    items = auth.get("items") or []
    return items[i] if 0 <= i < len(items) else {}


def _all_players(auth):
    return list(auth.get("participants", [])) + list(auth.get("ai", []))


def _public_item(item, mechanic):
    """Project a content item to its client-safe shape (never expose answers)."""
    out = {"id": item.get("id"), "prompt": item.get("prompt", "")}
    if item.get("options"):
        out["options"] = [{"key": o["key"], "label": o["label"]} for o in item["options"]]
    if item.get("tags"):
        out["tags"] = item["tags"]
    if mechanic == "prompt":
        out["mode"] = item.get("mode", "each")
    return out


def _advance_or_finish(auth):
    """Move to the next round or complete the game."""
    if auth["round"] >= auth["totalRounds"]:
        auth["phase"] = "complete"
        auth["status"] = "completed"
        auth["result"] = _build_result(auth)
    else:
        auth["round"] += 1
        auth["phase"] = "answering"
        auth["pending"] = {}
        auth["turnIndex"] = 0
        auth["subphase"] = None
        auth["setter"] = None
        # coop keeps its artifact; guess resets setter below in start-of-round
        _init_round(auth)


def _init_round(auth):
    mech = auth["mechanic"]
    if mech == "guess":
        players = _all_players(auth)
        # alternate the "setter" each round
        auth["setter"] = players[(auth["round"] - 1) % len(players)]
        auth["subphase"] = "set"
    if mech == "coop":
        players = _all_players(auth)
        auth["turnIndex"] = (auth["round"] - 1) % len(players)


def _build_result(auth):
    scores = auth.get("scores", {})
    mech = auth["mechanic"]
    if mech in ("prompt", "coop"):
        return {"type": "cooperative", "completedRounds": auth["totalRounds"],
                "artifact": auth.get("artifact", []), "scores": scores}
    if scores:
        top = max(scores.values()) if scores else 0
        winners = [p for p, s in scores.items() if s == top]
        return {"type": "scored", "scores": scores,
                "winners": winners, "draw": len(winners) > 1}
    return {"type": "completed", "scores": scores}


def _dedupe(auth, action):
    aid = action.get("actionId")
    if aid:
        if aid in auth.get("processed", []):
            return True
        auth.setdefault("processed", []).append(aid)
        # keep last 200
        auth["processed"] = auth["processed"][-200:]
    return False


class GameError(ValueError):
    pass


# --------------------------------------------------------------------------
# CHOICE  — preferences, no correct answer (Would You Rather, This or That…)
# also powers "guess my answer" style compare when config.compare = True
# --------------------------------------------------------------------------
def choice_start(auth):
    auth["phase"] = "answering"; auth["pending"] = {}
    _init_round(auth)


def choice_actions(auth, pid):
    item = _cur_item(auth)
    if auth["phase"] != "answering" or pid in auth.get("pending", {}):
        return []
    return [{"type": "answer", "value": None,
             "options": [o["key"] for o in item.get("options", [])]}]


def choice_apply(auth, pid, action):
    if action.get("type") != "answer":
        raise GameError("Only 'answer' is allowed here")
    if auth["phase"] != "answering":
        raise GameError("Not in the answering phase")
    if pid in auth.get("pending", {}):
        raise GameError("You have already answered this round")
    item = _cur_item(auth)
    keys = [o["key"] for o in item.get("options", [])]
    val = action.get("value")
    if val not in keys:
        raise GameError("Invalid option")
    auth.setdefault("pending", {})[pid] = val
    events = [{"event": "answer_submitted", "pid": pid, "round": auth["round"]}]
    if len(auth["pending"]) >= len(_all_players(auth)):
        # reveal + score (matches earn a point for compare-style games)
        auth.setdefault("revealed", {})[str(auth["round"])] = dict(auth["pending"])
        if auth.get("config", {}).get("scoreOnMatch"):
            vals = list(auth["pending"].values())
            if len(set(vals)) == 1 and len(vals) > 1:
                for p in auth["pending"]:
                    auth["scores"][p] = auth["scores"].get(p, 0) + 1
        auth["phase"] = "reveal"
        events.append({"event": "round_revealed", "round": auth["round"]})
    return events


# --------------------------------------------------------------------------
# TRIVIA — multiple choice WITH a correct answer, scored
# --------------------------------------------------------------------------
def trivia_start(auth):
    auth["phase"] = "answering"; auth["pending"] = {}


def trivia_actions(auth, pid):
    item = _cur_item(auth)
    if auth["phase"] != "answering" or pid in auth.get("pending", {}):
        return []
    return [{"type": "answer", "value": None,
             "options": [o["key"] for o in item.get("options", [])]}]


def trivia_apply(auth, pid, action):
    if action.get("type") != "answer":
        raise GameError("Only 'answer' is allowed here")
    if auth["phase"] != "answering":
        raise GameError("Not in the answering phase")
    if pid in auth.get("pending", {}):
        raise GameError("You have already answered this round")
    item = _cur_item(auth)
    keys = [o["key"] for o in item.get("options", [])]
    val = action.get("value")
    if val not in keys:
        raise GameError("Invalid option")
    auth.setdefault("pending", {})[pid] = val
    events = [{"event": "answer_submitted", "pid": pid, "round": auth["round"]}]
    if len(auth["pending"]) >= len(_all_players(auth)):
        correct = item.get("correct")
        for p, v in auth["pending"].items():
            if v == correct:
                auth["scores"][p] = auth["scores"].get(p, 0) + 1
        rev = dict(auth["pending"]); rev["_correct"] = correct
        auth.setdefault("revealed", {})[str(auth["round"])] = rev
        auth["phase"] = "reveal"
        events.append({"event": "round_revealed", "round": auth["round"], "correct": correct})
    return events


# --------------------------------------------------------------------------
# PROMPT — open conversation prompts (each answers, or strict turn), no scoring
# --------------------------------------------------------------------------
def prompt_start(auth):
    auth["phase"] = "answering"; auth["pending"] = {}; auth["turnIndex"] = 0


def prompt_actions(auth, pid):
    item = _cur_item(auth)
    mode = item.get("mode", "each")
    if auth["phase"] != "answering":
        return []
    if mode == "turn":
        players = _all_players(auth)
        if players[auth["turnIndex"] % len(players)] != pid:
            return []
    elif pid in auth.get("pending", {}):
        return []
    return [{"type": "respond", "value": None, "maxLen": 500}]


def prompt_apply(auth, pid, action):
    if action.get("type") != "respond":
        raise GameError("Only 'respond' is allowed here")
    if auth["phase"] != "answering":
        raise GameError("Not in the answering phase")
    item = _cur_item(auth)
    mode = item.get("mode", "each")
    text = (action.get("value") or "").strip()
    if not text:
        raise GameError("Response cannot be empty")
    text = text[:500]
    players = _all_players(auth)
    if mode == "turn":
        if players[auth["turnIndex"] % len(players)] != pid:
            raise GameError("It is not your turn")
    elif pid in auth.get("pending", {}):
        raise GameError("You have already responded")
    auth.setdefault("pending", {})[pid] = text
    events = [{"event": "response_submitted", "pid": pid, "round": auth["round"]}]
    done = (mode == "turn") or (len(auth["pending"]) >= len(players))
    if done:
        auth.setdefault("revealed", {})[str(auth["round"])] = dict(auth["pending"])
        auth["phase"] = "reveal"
        events.append({"event": "round_revealed", "round": auth["round"]})
    return events


# --------------------------------------------------------------------------
# GUESS — one player sets a secret, the other predicts (How Well Do You Know Me,
# Guess My Answer, Two Truths and a Lie). Two sub-phases: set -> guess.
# --------------------------------------------------------------------------
def guess_start(auth):
    auth["phase"] = "answering"; auth["pending"] = {}
    _init_round(auth)


def guess_actions(auth, pid):
    if auth["phase"] != "answering":
        return []
    item = _cur_item(auth)
    setter = auth.get("setter")
    if auth.get("subphase") == "set":
        if pid != setter:
            return []
        if item.get("kind") == "truths_lie":
            return [{"type": "set_secret", "statements": ["", "", ""], "lieIndex": None}]
        return [{"type": "set_secret", "value": None,
                 "options": [o["key"] for o in item.get("options", [])]}]
    # guess sub-phase — everyone except the setter guesses
    if pid == setter or pid in auth.get("pending", {}):
        return []
    if item.get("kind") == "truths_lie":
        return [{"type": "guess", "value": None, "options": [0, 1, 2]}]
    return [{"type": "guess", "value": None,
             "options": [o["key"] for o in item.get("options", [])]}]


def guess_apply(auth, pid, action):
    if auth["phase"] != "answering":
        raise GameError("Not in the answering phase")
    item = _cur_item(auth)
    setter = auth.get("setter")
    typ = action.get("type")
    if auth.get("subphase") == "set":
        if typ != "set_secret":
            raise GameError("The setter must set the secret first")
        if pid != setter:
            raise GameError("Only the setter can set the secret this round")
        if item.get("kind") == "truths_lie":
            stmts = [s.strip() for s in (action.get("statements") or []) if isinstance(s, str)]
            lie = action.get("lieIndex")
            if len(stmts) != 3 or any(not s for s in stmts) or lie not in (0, 1, 2):
                raise GameError("Provide 3 statements and mark which one is the lie")
            auth["secret"] = {"statements": stmts, "lieIndex": lie}
        else:
            keys = [o["key"] for o in item.get("options", [])]
            if action.get("value") not in keys:
                raise GameError("Invalid option")
            auth["secret"] = {"value": action["value"]}
        auth["subphase"] = "guess"
        return [{"event": "secret_set", "round": auth["round"], "setter": setter}]

    # guess sub-phase
    if typ != "guess":
        raise GameError("Only 'guess' is allowed here")
    if pid == setter:
        raise GameError("The setter cannot guess their own secret")
    if pid in auth.get("pending", {}):
        raise GameError("You have already guessed")
    secret = auth.get("secret", {})
    if item.get("kind") == "truths_lie":
        if action.get("value") not in (0, 1, 2):
            raise GameError("Pick which statement is the lie")
        correct = (action["value"] == secret.get("lieIndex"))
    else:
        keys = [o["key"] for o in item.get("options", [])]
        if action.get("value") not in keys:
            raise GameError("Invalid option")
        correct = (action["value"] == secret.get("value"))
    auth.setdefault("pending", {})[pid] = {"guess": action["value"], "correct": correct}
    if correct:
        auth["scores"][pid] = auth["scores"].get(pid, 0) + 1
    events = [{"event": "guess_submitted", "pid": pid, "correct": correct}]
    guessers = [p for p in _all_players(auth) if p != setter]
    if len(auth["pending"]) >= len(guessers):
        rev = {"secret": secret, "guesses": dict(auth["pending"])}
        auth.setdefault("revealed", {})[str(auth["round"])] = rev
        auth["phase"] = "reveal"
        events.append({"event": "round_revealed", "round": auth["round"]})
    return events


# --------------------------------------------------------------------------
# COOP — collaborative builder, strict turns (Build a Story, Dream Trip…)
# --------------------------------------------------------------------------
def coop_start(auth):
    auth["phase"] = "answering"; auth["artifact"] = []; auth["turnIndex"] = 0
    _init_round(auth)


def coop_actions(auth, pid):
    if auth["phase"] != "answering":
        return []
    players = _all_players(auth)
    if players[auth["turnIndex"] % len(players)] != pid:
        return []
    item = _cur_item(auth)
    if item.get("options"):
        return [{"type": "contribute", "value": None,
                 "options": [o["key"] for o in item["options"]]}]
    return [{"type": "contribute", "value": None, "maxLen": 300}]


def coop_apply(auth, pid, action):
    if action.get("type") != "contribute":
        raise GameError("Only 'contribute' is allowed here")
    if auth["phase"] != "answering":
        raise GameError("Not in the answering phase")
    players = _all_players(auth)
    if players[auth["turnIndex"] % len(players)] != pid:
        raise GameError("It is not your turn")
    item = _cur_item(auth)
    if item.get("options"):
        keys = {o["key"]: o["label"] for o in item["options"]}
        if action.get("value") not in keys:
            raise GameError("Invalid option")
        contribution = keys[action["value"]]
    else:
        contribution = (action.get("value") or "").strip()[:300]
        if not contribution:
            raise GameError("Contribution cannot be empty")
    auth.setdefault("artifact", []).append(
        {"round": auth["round"], "pid": pid, "prompt": item.get("prompt", ""), "text": contribution})
    events = [{"event": "contribution_added", "pid": pid, "round": auth["round"]}]
    auth.setdefault("revealed", {})[str(auth["round"])] = {"pid": pid, "text": contribution}
    auth["phase"] = "reveal"
    events.append({"event": "round_revealed", "round": auth["round"]})
    return events


# --------------------------------------------------------------------------
# public projection + registry
# --------------------------------------------------------------------------
def public_view(auth):
    item = _cur_item(auth)
    mech = auth["mechanic"]
    players = _all_players(auth)
    turn = None
    if mech in ("prompt",):
        if item.get("mode") == "turn":
            turn = players[auth.get("turnIndex", 0) % len(players)] if players else None
    if mech == "coop":
        turn = players[auth.get("turnIndex", 0) % len(players)] if players else None
    pub = {
        "mechanic": mech,
        "round": auth["round"],
        "totalRounds": auth["totalRounds"],
        "phase": auth["phase"],
        "status": auth["status"],
        "turn": turn,
        "prompt": _public_item(item, mech) if item else None,
        "submitted": {p: (p in auth.get("pending", {})) for p in players},
        "scores": auth.get("scores", {}),
        "participants": auth.get("participants", []),
        "ai": auth.get("ai", []),
        "revision": auth.get("revision", 0),
        "result": auth.get("result"),
    }
    if mech == "guess":
        pub["setter"] = auth.get("setter")
        pub["subphase"] = auth.get("subphase")
    if mech == "coop":
        pub["artifact"] = auth.get("artifact", [])
    if auth["phase"] in ("reveal", "complete"):
        pub["revealed"] = auth.get("revealed", {}).get(str(auth["round"]))
    return pub


def ai_context(auth, pid):
    """Structured context the AI Character Engine can reason over (no LLM here)."""
    return {
        "gameId": auth["gameId"],
        "sessionId": auth["sessionId"],
        "mechanic": auth["mechanic"],
        "round": auth["round"],
        "totalRounds": auth["totalRounds"],
        "phase": auth["phase"],
        "participantId": pid,
        "isYourTurn": bool(available_actions(auth, pid)),
        "publicState": public_view(auth),
        "availableActions": available_actions(auth, pid),
        "currentPrompt": _public_item(_cur_item(auth), auth["mechanic"]) if _cur_item(auth) else None,
    }


_MECH = {
    "choice": (choice_start, choice_actions, choice_apply),
    "trivia": (trivia_start, trivia_actions, trivia_apply),
    "prompt": (prompt_start, prompt_actions, prompt_apply),
    "guess": (guess_start, guess_actions, guess_apply),
    "coop": (coop_start, coop_actions, coop_apply),
}

MECHANICS = list(_MECH.keys())


def start_game(auth):
    _MECH[auth["mechanic"]][0](auth)


def available_actions(auth, pid):
    if auth.get("status") != "active" or auth.get("phase") == "complete":
        return []
    if pid not in _all_players(auth):
        return []
    return _MECH[auth["mechanic"]][1](auth, pid)


def apply_action(auth, pid, action):
    """Validate + apply an action. Raises GameError on any rule violation."""
    if auth.get("status") != "active":
        raise GameError("This game is not active")
    if pid not in _all_players(auth):
        raise GameError("You are not a participant in this game")
    if _dedupe(auth, action):
        return []  # duplicate actionId — idempotent no-op
    events = _MECH[auth["mechanic"]][2](auth, pid, action)
    auth["revision"] = auth.get("revision", 0) + 1
    auth["lastActivityAt"] = _now_iso()
    return events


def next_round(auth, pid=None):
    """Advance from a 'reveal' phase to the next round (host/participant driven)."""
    if auth.get("phase") != "reveal":
        raise GameError("Round is not complete yet")
    _advance_or_finish(auth)
    auth["revision"] = auth.get("revision", 0) + 1
    auth["lastActivityAt"] = _now_iso()
    return [{"event": "round_advanced", "round": auth["round"], "phase": auth["phase"]}]

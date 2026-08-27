"""Relationship / familiarity continuity (non-manipulative).

State only influences familiarity of wording, callbacks and comfort — never claims
of being a real human or coercive emotional dependency.
"""
THRESHOLDS = [(0, "new"), (6, "familiar"), (20, "comfortable"), (60, "established")]


def state_for(turn_count):
    s = "new"
    for t, name in THRESHOLDS:
        if turn_count >= t:
            s = name
    return s


def load(repo, cid, uid):
    st = repo.get_relationship(cid, uid)
    if not st:
        st = {"characterId": cid, "userId": uid, "turnCount": 0, "state": "new",
              "sharedTopics": [], "recurringJokes": [], "milestones": []}
    st["state"] = state_for(st.get("turnCount", 0))
    return st


def advance(
    repo,
    cid,
    uid,
    understanding,
    user_text=None,
):
    return repo.advance_relationship(
        cid,
        uid,
        understanding,
        user_text=user_text,
    )


STYLE_BY_STATE = {
    "new": "Be welcoming but not over-familiar. No inside references yet.",
    "familiar": "You've spoken a few times — a little warmer, light callbacks are okay.",
    "comfortable": "Comfortable rapport — natural shorthand, occasional callbacks to shared topics.",
    "established": "Established rapport — easy familiarity and callbacks, but never claim to be human or emotionally dependent.",
}

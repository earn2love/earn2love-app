from ai_engine import preference_engine as P
from ai_engine.repository import InMemoryCharacterRepository


CID = "pref-character"
UID = "pref-user"


def test_extract_simple_like():
    prefs = P.extract_preferences(
        "I love biryani"
    )

    assert prefs
    assert prefs[0]["value"].lower() == "biryani"
    assert prefs[0]["sentiment"] == "like"


def test_extract_simple_dislike():
    prefs = P.extract_preferences(
        "I hate mushrooms"
    )

    assert prefs
    assert prefs[0]["value"].lower() == "mushrooms"
    assert prefs[0]["sentiment"] == "dislike"


def test_used_to_like_then_now_prefer():
    prefs = P.extract_preferences(
        "I used to love pizza, but now I prefer biryani"
    )

    by_value = {
        x["value"].lower(): x
        for x in prefs
    }

    assert "pizza" in by_value
    assert "biryani" in by_value

    assert by_value["pizza"]["status"] == "historical"
    assert by_value["pizza"]["trend"] == "declining"

    assert by_value["biryani"]["status"] == "active"
    assert by_value["biryani"]["trend"] == "increasing"


def test_started_liking_trend():
    prefs = P.extract_preferences(
        "I've started liking anime recently"
    )

    assert prefs
    assert prefs[0]["trend"] == "increasing"


def test_no_longer_like_becomes_dislike():
    prefs = P.extract_preferences(
        "I don't like horror movies anymore"
    )

    assert prefs

    pref = prefs[0]

    assert pref["sentiment"] == "dislike"
    assert pref["trend"] == "declining"


def test_contextual_preference():
    prefs = P.extract_preferences(
        "When I'm stressed, I prefer short replies"
    )

    assert prefs

    pref = prefs[0]

    assert "short replies" in pref["value"].lower()
    assert pref["context"] is not None


def test_preference_change_targets_old_memory():
    repo = InMemoryCharacterRepository()

    old = P.preference_fact(
        "pizza",
        sentiment="like",
        text="I love pizza",
    )

    repo.add_memory(
        CID,
        UID,
        old,
    )

    plan = P.plan_preference_updates(
        "I don't like pizza anymore",
        repo.list_memories(CID, UID),
    )

    assert plan["targets"]

    assert (
        plan["targets"][0]["value"].lower()
        == "pizza"
    )


def test_unrelated_preference_does_not_replace():
    repo = InMemoryCharacterRepository()

    repo.add_memory(
        CID,
        UID,
        P.preference_fact(
            "pizza",
            sentiment="like",
            text="I love pizza",
        ),
    )

    plan = P.plan_preference_updates(
        "I love anime",
        repo.list_memories(CID, UID),
    )

    assert plan["targets"] == []


def test_format_like():
    memory = P.preference_fact(
        "biryani",
        sentiment="like",
        text="I love biryani",
    )

    assert P.format_preference(memory).startswith(
        "Likes: biryani"
    )


def test_format_dislike():
    memory = P.preference_fact(
        "mushrooms",
        sentiment="dislike",
        text="I hate mushrooms",
    )

    assert P.format_preference(memory).startswith(
        "Dislikes: mushrooms"
    )


def test_active_preferences_excludes_historical():
    active = P.preference_fact(
        "biryani",
        sentiment="like",
        text="I love biryani",
    )

    historical = P.preference_fact(
        "pizza",
        sentiment="like",
        text="I used to love pizza",
        status="historical",
    )

    result = P.active_preferences(
        [active, historical]
    )

    assert len(result) == 1
    assert result[0]["value"] == "biryani"


def test_preference_strength():
    love = P.preference_fact(
        "music",
        sentiment="like",
        text="I absolutely love music",
    )

    like = P.preference_fact(
        "music",
        sentiment="like",
        text="I like music",
    )

    assert love["strength"] > like["strength"]

from ai_engine import understanding as U
from ai_engine import structured_facts as SF
from ai_engine import memory as M


def first(text):
    facts = SF.extract_facts(text, U.analyze(text))
    assert facts
    return facts[0]


def test_understanding_exposes_full_semantic_query():
    u = U.analyze("How is my new job at HSBC going?")

    assert u["semanticQuery"] == "How is my new job at HSBC going?"
    assert u["currentMessage"] == u["semanticQuery"]


def test_extract_current_employer():
    f = first("I work at HSBC")

    assert f["predicate"] == "employment.current"
    assert f["value"] == "HSBC"
    assert f["canonicalKey"] == "user:employment.current"


def test_extract_joined_employer():
    f = first("I joined Barclays")

    assert f["predicate"] == "employment.current"
    assert f["value"] == "Barclays"


def test_extract_role():
    f = first("I work as a Business Analyst")

    assert f["predicate"] == "employment.role"
    assert f["value"].lower() == "business analyst"


def test_extract_location():
    f = first("I live in London")

    assert f["predicate"] == "location.current"
    assert f["value"] == "London"


def test_extract_move():
    facts = SF.extract_facts(
        "I moved from Manchester to London",
        {},
    )

    predicates = [x["predicate"] for x in facts]

    assert "location.current" not in predicates or any(
        x.get("value") == "London"
        for x in facts
    )
    assert "location.previous" in predicates


def test_extract_education():
    f = first("I am studying Artificial Intelligence")

    assert f["predicate"] == "education.current"
    assert "Artificial Intelligence" in f["value"]


def test_extract_relationship_status():
    f = first("I'm married")

    assert f["predicate"] == "relationship.status"
    assert f["value"].lower() == "married"


def test_extract_name():
    f = first("My name is Ram")

    assert f["predicate"] == "identity.name"
    assert f["value"] == "Ram"


def test_extract_food_preference():
    f = first("My favourite food is biryani")

    assert f["predicate"] == "preference.food"
    assert f["value"].lower() == "biryani"


def test_extract_goal():
    f = first("My dream is to build my own company")

    assert f["predicate"] == "goal.primary"
    assert "build my own company" in f["value"].lower()


def test_explicit_remember_sets_explicit_save():
    f = first("Remember that I work at HSBC")

    assert f["explicitSave"] is True


def test_current_job_is_superseding_slot():
    f = first("I work at HSBC")

    assert SF.supersedes_existing(f) is True


def test_previous_employer_is_not_single_slot():
    facts = SF.extract_facts("I left Tesco", {})

    f = next(
        x
        for x in facts
        if x["predicate"] == "employment.previous"
    )

    assert SF.supersedes_existing(f) is False


def test_memory_exposes_structured_extractor():
    facts = M.extract_structured(
        "I live in Birmingham",
        U.analyze("I live in Birmingham"),
    )

    assert facts
    assert facts[0]["predicate"] == "location.current"

def test_studying_is_not_employment_role():
    facts = SF.extract_facts(
        "I am studying Artificial Intelligence",
        {},
    )

    predicates = [x["predicate"] for x in facts]

    assert "education.current" in predicates
    assert "employment.role" not in predicates


def test_work_as_still_extracts_role():
    facts = SF.extract_facts(
        "I work as a Business Analyst",
        {},
    )

    role = next(
        x for x in facts
        if x["predicate"] == "employment.role"
    )

    assert role["value"].lower() == "business analyst"


def test_i_am_a_role_still_extracts_role():
    facts = SF.extract_facts(
        "I am a Software Engineer",
        {},
    )

    role = next(
        x for x in facts
        if x["predicate"] == "employment.role"
    )

    assert role["value"].lower() == "software engineer"

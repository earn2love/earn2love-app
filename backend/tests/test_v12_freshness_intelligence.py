from ai_engine import freshness_intelligence as F


def test_version():
    assert F.FRESHNESS_VERSION == 12


def test_current_cm_requires_live():
    d = F.assess_freshness(
        "Who is CM of Tamil Nadu?"
    )

    assert d.classification == F.LIVE_REQUIRED
    assert d.requires_live_retrieval is True
    assert d.historical is False


def test_current_chief_minister_requires_live():
    d = F.assess_freshness(
        "Who is the chief minister of Tamil Nadu?"
    )

    assert d.classification == F.LIVE_REQUIRED
    assert d.requires_live_retrieval is True


def test_current_pm_requires_live():
    d = F.assess_freshness(
        "Who is the current UK prime minister?"
    )

    assert d.classification == F.LIVE_REQUIRED
    assert d.requires_live_retrieval is True


def test_current_ceo_requires_live():
    d = F.assess_freshness(
        "Who is the CEO of Microsoft now?"
    )

    assert d.classification == F.LIVE_REQUIRED
    assert d.requires_live_retrieval is True


def test_today_gold_price_requires_live():
    d = F.assess_freshness(
        "What is today's gold price?"
    )

    assert d.classification == F.LIVE_REQUIRED
    assert d.requires_live_retrieval is True


def test_weather_requires_live():
    d = F.assess_freshness(
        "What's the weather in London?"
    )

    assert d.classification == F.LIVE_REQUIRED
    assert d.requires_live_retrieval is True


def test_latest_news_requires_live():
    d = F.assess_freshness(
        "Tell me the latest UK news"
    )

    assert d.classification == F.LIVE_REQUIRED
    assert d.requires_live_retrieval is True


def test_yesterday_winner_requires_live():
    d = F.assess_freshness(
        "Who won yesterday?"
    )

    assert d.classification == F.LIVE_REQUIRED
    assert d.requires_live_retrieval is True


def test_historical_cm_2025_is_historical():
    d = F.assess_freshness(
        "Who was CM of Tamil Nadu in 2025?"
    )

    assert d.classification == F.HISTORICAL_LOOKUP
    assert d.requires_live_retrieval is True
    assert d.historical is True


def test_historical_president_year():
    d = F.assess_freshness(
        "Who was president in 1995?"
    )

    assert d.classification == F.HISTORICAL_LOOKUP
    assert d.historical is True


def test_photosynthesis_does_not_require_live():
    d = F.assess_freshness(
        "What is photosynthesis?"
    )

    assert d.classification == F.STABLE_KNOWLEDGE
    assert d.requires_live_retrieval is False


def test_gravity_does_not_require_live():
    assert (
        F.requires_live_retrieval(
            "Explain gravity"
        )
        is False
    )


def test_greeting_does_not_require_live():
    d = F.assess_freshness(
        "hi"
    )

    assert d.classification == F.CONVERSATIONAL
    assert d.requires_live_retrieval is False


def test_telugu_english_chat_does_not_require_live():
    d = F.assess_freshness(
        "em chestunnav"
    )

    assert d.classification == F.CONVERSATIONAL
    assert d.requires_live_retrieval is False


def test_personal_memory_not_live():
    d = F.assess_freshness(
        "naa peru enti gurthunda?"
    )

    assert d.classification == F.CONVERSATIONAL
    assert d.requires_live_retrieval is False


def test_food_memory_not_live():
    d = F.assess_freshness(
        "what food do I like?"
    )

    assert d.classification == F.CONVERSATIONAL
    assert d.requires_live_retrieval is False


def test_guidance_live():
    g = F.build_freshness_guidance(
        "Who is CM of Tamil Nadu now?"
    )

    assert g["decision"]["requires_live_retrieval"] is True
    assert g["decision"]["version"] == 12
    assert "current evidence" in g["directive"]


def test_guidance_stable():
    g = F.build_freshness_guidance(
        "Explain gravity"
    )

    assert g["decision"]["requires_live_retrieval"] is False
    assert "normal Earn2Love intelligence stack" in g["directive"]

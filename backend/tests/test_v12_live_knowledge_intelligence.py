from datetime import datetime, timezone, timedelta

from ai_engine import live_knowledge_intelligence as LK


NOW = datetime(
    2026,
    8,
    28,
    16,
    0,
    tzinfo=timezone.utc,
)


def gov_result():
    return {
        "title": "Chief Minister - Government",
        "url": "https://example.gov.in/chief-minister",
        "snippet": (
            "Official government page naming the current "
            "Chief Minister."
        ),
    }


def normal_result():
    return {
        "title": "Current political leadership",
        "url": "https://example-news.test/current-leadership",
        "snippet": (
            "Article discussing the current Chief Minister "
            "of Tamil Nadu."
        ),
    }


def test_version():
    assert LK.LIVE_KNOWLEDGE_VERSION == 12


def test_normalize_valid_result():
    item = LK.normalize_evidence(
        gov_result(),
        retrieved_at=NOW.isoformat(),
    )

    assert item is not None
    assert item.source_domain == "example.gov.in"
    assert item.authoritative is True


def test_reject_invalid_url():
    item = LK.normalize_evidence(
        {
            "title": "Bad",
            "url": "javascript:alert(1)",
            "snippet": "bad source",
        },
        retrieved_at=NOW.isoformat(),
    )

    assert item is None


def test_authoritative_packet_verified():
    packet = LK.build_live_knowledge_packet(
        "Who is the current Chief Minister?",
        [gov_result()],
        now=NOW,
    )

    assert packet.can_answer is True
    assert packet.status == LK.STATUS_VERIFIED
    assert packet.confidence > 0.7


def test_non_authoritative_packet_partial():
    packet = LK.build_live_knowledge_packet(
        "Who is the current Chief Minister?",
        [normal_result()],
        now=NOW,
    )

    assert packet.can_answer is True
    assert packet.status == LK.STATUS_PARTIAL


def test_missing_live_evidence_blocks_stale_answer():
    packet = LK.build_live_knowledge_packet(
        "Who is CM of Tamil Nadu?",
        [],
        requires_live_retrieval=True,
        now=NOW,
    )

    assert packet.can_answer is False
    assert packet.status == LK.STATUS_UNAVAILABLE
    assert "stale model knowledge" in packet.reason


def test_missing_optional_evidence_does_not_force_failure():
    packet = LK.build_live_knowledge_packet(
        "Explain gravity",
        [],
        requires_live_retrieval=False,
        now=NOW,
    )

    assert packet.can_answer is True


def test_duplicate_urls_removed():
    result = gov_result()

    packet = LK.build_live_knowledge_packet(
        "Who is Chief Minister?",
        [
            result,
            dict(result),
        ],
        now=NOW,
    )

    assert len(packet.evidence) == 1


def test_grounding_context_contains_source():
    packet = LK.build_live_knowledge_packet(
        "Who is Chief Minister?",
        [gov_result()],
        now=NOW,
    )

    context = LK.build_grounding_context(
        packet
    )

    assert "LIVE KNOWLEDGE EVIDENCE" in context
    assert "[SOURCE 1]" in context
    assert "example.gov.in" in context


def test_unavailable_grounding_forbids_guessing():
    packet = LK.build_live_knowledge_packet(
        "Who is Chief Minister?",
        [],
        now=NOW,
    )

    context = LK.build_grounding_context(
        packet
    )

    assert "Do NOT guess" in context
    assert "stale model knowledge" in context


def test_public_facts_are_ephemeral():
    policy = LK.public_knowledge_memory_policy()

    assert policy["persistToUserMemory"] is False
    assert policy["persistToCharacterMemory"] is False
    assert policy["ephemeralContextOnly"] is True


def test_multiple_sources_preserved():
    packet = LK.build_live_knowledge_packet(
        "Who is Chief Minister?",
        [
            gov_result(),
            normal_result(),
        ],
        now=NOW,
    )

    assert len(packet.evidence) == 2


def test_invalid_results_are_removed():
    packet = LK.build_live_knowledge_packet(
        "Who is Chief Minister?",
        [
            {
                "title": "",
                "url": "",
                "snippet": "",
            },
            gov_result(),
        ],
        now=NOW,
    )

    assert len(packet.evidence) == 1


def test_packet_serialization():
    packet = LK.build_live_knowledge_packet(
        "Who is Chief Minister?",
        [gov_result()],
        now=NOW,
    )

    data = packet.to_dict()

    assert data["version"] == 12
    assert data["canAnswer"] is True
    assert len(data["evidence"]) == 1


def test_score_is_bounded():
    packet = LK.build_live_knowledge_packet(
        "Who is the current Chief Minister?",
        [gov_result()],
        now=NOW,
    )

    assert 0.0 <= packet.evidence[0].score <= 1.0


def test_retrieval_timestamp_present():
    packet = LK.build_live_knowledge_packet(
        "Who is Chief Minister?",
        [gov_result()],
        now=NOW,
    )

    assert packet.retrieved_at.endswith("Z")


def test_minimum_evidence_requirement():
    packet = LK.build_live_knowledge_packet(
        "Who is Chief Minister?",
        [gov_result()],
        minimum_evidence=2,
        now=NOW,
    )

    assert packet.status == LK.STATUS_UNAVAILABLE
    assert packet.can_answer is False


def test_mapping_results_supported():
    packet = LK.build_live_knowledge_packet(
        "Who is Chief Minister?",
        {
            "results": [
                gov_result()
            ]
        },
        now=NOW,
    )

    assert packet.can_answer is True
    assert len(packet.evidence) == 1


def test_future_timestamp_rejected():
    future = (
        NOW
        + timedelta(
            hours=2
        )
    )

    raw = gov_result()
    raw["retrievedAt"] = future.isoformat()

    item = LK.normalize_evidence(
        raw,
        retrieved_at=future.isoformat(),
    )

    assert item is not None

    # Packet creation stamps results at actual retrieval time
    # supplied by the orchestration layer, preventing arbitrary
    # source timestamps from controlling freshness.
    packet = LK.build_live_knowledge_packet(
        "Who is Chief Minister?",
        [raw],
        now=NOW,
    )

    assert packet.can_answer is True

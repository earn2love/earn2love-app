import asyncio

from ai_engine import live_knowledge_provider as LP


class FakeResponse:
    def __init__(self):
        self.id = "resp_test"
        self.output_text = (
            "The official government source confirms "
            "the current office holder."
        )

    def model_dump(self):
        return {
            "id": self.id,
            "output": [
                {
                    "type": "web_search_call",
                    "action": {
                        "type": "search",
                        "queries": [
                            "current chief minister"
                        ],
                        "sources": [
                            {
                                "type": "url",
                                "url": (
                                    "https://example.gov.in/"
                                    "chief-minister"
                                ),
                            },
                            {
                                "type": "url",
                                "url": (
                                    "https://news.example.test/"
                                    "politics"
                                ),
                            },
                        ],
                    },
                },
                {
                    "type": "message",
                    "content": [
                        {
                            "type": "output_text",
                            "text": self.output_text,
                            "annotations": [
                                {
                                    "type": "url_citation",
                                    "title": (
                                        "Chief Minister - "
                                        "Government"
                                    ),
                                    "url": (
                                        "https://example.gov.in/"
                                        "chief-minister"
                                    ),
                                    "start_index": 0,
                                    "end_index": 20,
                                }
                            ],
                        }
                    ],
                },
            ],
        }


def test_version():
    assert (
        LP.LIVE_KNOWLEDGE_PROVIDER_VERSION
        == 12
    )


def test_extract_output_text():
    response = FakeResponse()

    assert (
        "official government source"
        in LP._extract_output_text(
            response
        )
    )


def test_extract_results():
    response = FakeResponse()

    results = LP.extract_search_results(
        response,
        query="Who is Chief Minister?",
        retrieved_at="2026-08-28T16:00:00Z",
    )

    urls = {
        item["url"]
        for item in results
    }

    assert (
        "https://example.gov.in/chief-minister"
        in urls
    )

    assert (
        "https://news.example.test/politics"
        in urls
    )


def test_citation_title_preserved():
    results = LP.extract_search_results(
        FakeResponse(),
        query="Who is Chief Minister?",
    )

    gov = next(
        item
        for item in results
        if "example.gov.in" in item["url"]
    )

    assert (
        gov["title"]
        == "Chief Minister - Government"
    )


def test_duplicate_citation_and_source_removed():
    results = LP.extract_search_results(
        FakeResponse(),
        query="Who is Chief Minister?",
    )

    urls = [
        item["url"]
        for item in results
    ]

    assert (
        urls.count(
            "https://example.gov.in/chief-minister"
        )
        == 1
    )


def test_invalid_query_safe_failure():
    result = asyncio.run(
        LP.search_live("")
    )

    assert result.ok is False
    assert result.error == "empty_query"


def test_result_serialization():
    result = LP.LiveSearchResult(
        ok=True,
        query="test",
        results=(
            {
                "title": "A",
                "url": "https://example.com",
                "snippet": "Example",
            },
        ),
        answer="Example",
        provider="openai-web-search",
        model="test-model",
        response_id="resp_123",
        retrieved_at="2026-08-28T16:00:00Z",
    )

    data = result.to_dict()

    assert data["version"] == 12
    assert data["ok"] is True
    assert data["responseId"] == "resp_123"


def test_safe_url_rejects_non_http():
    assert (
        LP._safe_url(
            "javascript:alert(1)"
        )
        == ""
    )


def test_model_dump_handles_nested_values():
    payload = LP._model_dump(
        {
            "a": [
                {
                    "b": 1
                }
            ]
        }
    )

    assert payload == {
        "a": [
            {
                "b": 1
            }
        ]
    }

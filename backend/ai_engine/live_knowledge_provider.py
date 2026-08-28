"""
Earn2Love AI Engine V12.3
Live Knowledge Provider

Dedicated external web-search boundary.

Architecture:
- This module performs live public-information retrieval only.
- provider.py remains the sole normal conversational LLM-generation boundary.
- router.py remains model/provider authority for normal CharacterEngine generation.
- No user memory or character state is persisted here.
- Results are ephemeral.
- Public facts must be revalidated on future current-information queries.

OpenAI Responses API is used with its built-in web-search tool.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

from dotenv import load_dotenv
from pathlib import Path


# ai_engine/live_knowledge_provider.py -> backend/.env
_BACKEND_DIR = Path(__file__).resolve().parent.parent
_BACKEND_ENV = _BACKEND_DIR / ".env"

load_dotenv(
    dotenv_path=_BACKEND_ENV,
    override=False,
)


LIVE_KNOWLEDGE_PROVIDER_VERSION = 12

DEFAULT_LIVE_MODEL = os.environ.get(
    "AI_LIVE_KNOWLEDGE_MODEL",
    "gpt-5.6-luna",
)

LIVE_TIMEOUT_SECONDS = float(
    os.environ.get(
        "AI_LIVE_KNOWLEDGE_TIMEOUT",
        "25",
    )
)

LIVE_MAX_OUTPUT_TOKENS = int(
    os.environ.get(
        "AI_LIVE_KNOWLEDGE_MAX_OUTPUT_TOKENS",
        "700",
    )
)


@dataclass(frozen=True)
class LiveSearchResult:
    ok: bool
    query: str
    results: tuple[dict[str, Any], ...]
    answer: str
    provider: str
    model: str
    response_id: str | None
    retrieved_at: str
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "query": self.query,
            "results": [
                dict(item)
                for item in self.results
            ],
            "answer": self.answer,
            "provider": self.provider,
            "model": self.model,
            "responseId": self.response_id,
            "retrievedAt": self.retrieved_at,
            "error": self.error,
            "version": LIVE_KNOWLEDGE_PROVIDER_VERSION,
        }


def _now_iso() -> str:
    return (
        datetime.now(timezone.utc)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _norm(value: Any) -> str:
    return " ".join(
        str(value or "")
        .strip()
        .split()
    )


def _safe_url(value: Any) -> str:
    raw = str(value or "").strip()

    if not raw:
        return ""

    try:
        parsed = urlparse(raw)
    except Exception:
        return ""

    if (
        parsed.scheme not in {
            "http",
            "https",
        }
        or not parsed.netloc
    ):
        return ""

    return raw


def _model_dump(value: Any) -> Any:
    if value is None:
        return None

    if isinstance(
        value,
        (
            str,
            int,
            float,
            bool,
        ),
    ):
        return value

    if isinstance(
        value,
        (list, tuple),
    ):
        return [
            _model_dump(item)
            for item in value
        ]

    if isinstance(
        value,
        dict,
    ):
        return {
            key: _model_dump(item)
            for key, item in value.items()
        }

    method = getattr(
        value,
        "model_dump",
        None,
    )

    if callable(method):
        try:
            return _model_dump(
                method()
            )
        except Exception:
            pass

    data = getattr(
        value,
        "__dict__",
        None,
    )

    if isinstance(
        data,
        dict,
    ):
        return {
            key: _model_dump(item)
            for key, item in data.items()
            if not key.startswith("_")
        }

    return str(value)


def _extract_output_text(
    response: Any,
) -> str:
    direct = getattr(
        response,
        "output_text",
        None,
    )

    if direct:
        return _norm(direct)

    payload = _model_dump(
        response
    )

    if not isinstance(
        payload,
        dict,
    ):
        return ""

    pieces: list[str] = []

    for item in payload.get(
        "output",
        [],
    ) or []:
        if not isinstance(
            item,
            dict,
        ):
            continue

        if item.get("type") != "message":
            continue

        for content in item.get(
            "content",
            [],
        ) or []:
            if not isinstance(
                content,
                dict,
            ):
                continue

            text = (
                content.get("text")
                or content.get("output_text")
            )

            if text:
                pieces.append(
                    str(text)
                )

    return _norm(
        " ".join(pieces)
    )


def _walk(
    value: Any,
):
    if isinstance(
        value,
        dict,
    ):
        yield value

        for item in value.values():
            yield from _walk(
                item
            )

    elif isinstance(
        value,
        list,
    ):
        for item in value:
            yield from _walk(
                item
            )


def _extract_url_citations(
    payload: dict[str, Any],
) -> list[dict[str, str]]:
    citations: list[
        dict[str, str]
    ] = []

    for node in _walk(
        payload
    ):
        node_type = str(
            node.get("type")
            or ""
        ).lower()

        if node_type not in {
            "url_citation",
            "urlcitation",
        }:
            continue

        url = _safe_url(
            node.get("url")
        )

        if not url:
            continue

        title = _norm(
            node.get("title")
            or node.get("name")
            or urlparse(url).hostname
            or "Web source"
        )

        citations.append(
            {
                "url": url,
                "title": title,
            }
        )

    return citations


def _extract_web_action_sources(
    payload: dict[str, Any],
) -> list[dict[str, str]]:
    sources: list[
        dict[str, str]
    ] = []

    for node in _walk(
        payload
    ):
        if (
            str(
                node.get("type")
                or ""
            ).lower()
            != "web_search_call"
        ):
            continue

        action = node.get(
            "action"
        )

        if not isinstance(
            action,
            dict,
        ):
            continue

        for source in (
            action.get("sources")
            or []
        ):
            if not isinstance(
                source,
                dict,
            ):
                continue

            url = _safe_url(
                source.get("url")
            )

            if not url:
                continue

            sources.append(
                {
                    "url": url,
                    "title": _norm(
                        source.get("title")
                        or urlparse(
                            url
                        ).hostname
                        or "Web source"
                    ),
                }
            )

    return sources


def extract_search_results(
    response: Any,
    *,
    query: str,
    retrieved_at: str | None = None,
) -> list[dict[str, Any]]:
    """
    Normalize Responses API web evidence into the V12.2 evidence contract.

    Search-call URLs and output URL citations are accepted.
    Duplicate URLs are removed.
    """

    timestamp = (
        retrieved_at
        or _now_iso()
    )

    payload = _model_dump(
        response
    )

    if not isinstance(
        payload,
        dict,
    ):
        return []

    answer = _extract_output_text(
        response
    )

    candidates = (
        _extract_url_citations(
            payload
        )
        + _extract_web_action_sources(
            payload
        )
    )

    seen: set[str] = set()
    results: list[
        dict[str, Any]
    ] = []

    for source in candidates:
        url = source["url"]

        key = url.lower()

        if key in seen:
            continue

        seen.add(key)

        results.append(
            {
                "title": source["title"],
                "url": url,

                # The Responses web-search result is a grounded synthesis.
                # We deliberately do not invent a page-specific quotation.
                # The synthesized search output is passed as retrieval
                # evidence while the original source URL remains attached.
                "snippet": answer,

                "retrievedAt": timestamp,
            }
        )

    return results



from ai_engine import provider as PROV

async def search_live(
    query: Any,
    *,
    model: str | None = None,
    user_country: str | None = None,
    user_city: str | None = None,
    user_region: str | None = None,
    user_timezone: str | None = None,
) -> LiveSearchResult:
    """
    Retrieve current public information through provider.py.

    This module owns normalization/evidence extraction only.
    It performs no direct external LLM communication and no
    persistence.
    """

    query_text = _norm(
        query
    )

    retrieved_at = _now_iso()

    resolved_model = (
        model
        or DEFAULT_LIVE_MODEL
    )

    if not query_text:
        return LiveSearchResult(
            ok=False,
            query="",
            results=(),
            answer="",
            provider="openai-web-search",
            model=resolved_model,
            response_id=None,
            retrieved_at=retrieved_at,
            error="empty_query",
        )

    provider_result = await PROV.search_web(
        query_text,
        model=resolved_model,
        user_country=user_country,
        user_city=user_city,
        user_region=user_region,
        user_timezone=user_timezone,
        timeout_seconds=LIVE_TIMEOUT_SECONDS,
        max_output_tokens=LIVE_MAX_OUTPUT_TOKENS,
    )

    provider_name = (
        provider_result.get("provider")
        or "openai-web-search"
    )

    provider_model = (
        provider_result.get("model")
        or resolved_model
    )

    if not provider_result.get("ok"):
        return LiveSearchResult(
            ok=False,
            query=query_text,
            results=(),
            answer="",
            provider=provider_name,
            model=provider_model,
            response_id=None,
            retrieved_at=retrieved_at,
            error=(
                provider_result.get("error")
                or "live_search_unavailable"
            ),
        )

    response = provider_result.get(
        "response"
    )

    if response is None:
        return LiveSearchResult(
            ok=False,
            query=query_text,
            results=(),
            answer="",
            provider=provider_name,
            model=provider_model,
            response_id=None,
            retrieved_at=retrieved_at,
            error="missing_provider_response",
        )

    answer = _extract_output_text(
        response
    )

    results = extract_search_results(
        response,
        query=query_text,
        retrieved_at=retrieved_at,
    )

    response_id = getattr(
        response,
        "id",
        None,
    )

    if not results:
        return LiveSearchResult(
            ok=False,
            query=query_text,
            results=(),
            answer=answer,
            provider=provider_name,
            model=provider_model,
            response_id=response_id,
            retrieved_at=retrieved_at,
            error="no_web_evidence",
        )

    return LiveSearchResult(
        ok=True,
        query=query_text,
        results=tuple(
            results
        ),
        answer=answer,
        provider=provider_name,
        model=provider_model,
        response_id=response_id,
        retrieved_at=retrieved_at,
        error=None,
    )

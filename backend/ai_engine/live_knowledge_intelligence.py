"""
Earn2Love AI Engine V12.2
Live Knowledge Evidence Intelligence

Pure evidence-validation and grounding layer.

This module:
- does NOT perform web/network calls;
- does NOT choose an LLM provider/model;
- does NOT persist public facts as user memory;
- does NOT modify personality;
- validates externally retrieved evidence;
- produces safe grounding context for the normal AI engine;
- prevents stale-model fallback when live evidence is required.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone, timedelta
from typing import Any
from urllib.parse import urlparse
import re


LIVE_KNOWLEDGE_VERSION = 12


STATUS_VERIFIED = "VERIFIED"
STATUS_PARTIAL = "PARTIAL"
STATUS_UNAVAILABLE = "UNAVAILABLE"


@dataclass(frozen=True)
class KnowledgeEvidence:
    title: str
    url: str
    snippet: str
    source_domain: str
    retrieved_at: str
    published_at: str | None = None
    authoritative: bool = False
    score: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class LiveKnowledgePacket:
    query: str
    status: str
    can_answer: bool
    confidence: float
    evidence: tuple[KnowledgeEvidence, ...]
    reason: str
    retrieved_at: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": LIVE_KNOWLEDGE_VERSION,
            "query": self.query,
            "status": self.status,
            "canAnswer": self.can_answer,
            "confidence": self.confidence,
            "reason": self.reason,
            "retrievedAt": self.retrieved_at,
            "evidence": [
                item.to_dict()
                for item in self.evidence
            ],
        }


def _norm(value: Any) -> str:
    return " ".join(
        str(value or "")
        .strip()
        .split()
    )


def _now() -> datetime:
    return datetime.now(
        timezone.utc
    )


def _iso(value: datetime) -> str:
    return (
        value
        .astimezone(timezone.utc)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _parse_datetime(
    value: Any,
) -> datetime | None:
    raw = str(value or "").strip()

    if not raw:
        return None

    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"

    try:
        parsed = datetime.fromisoformat(
            raw
        )
    except ValueError:
        return None

    if parsed.tzinfo is None:
        parsed = parsed.replace(
            tzinfo=timezone.utc
        )

    return parsed.astimezone(
        timezone.utc
    )


def _domain(url: Any) -> str:
    raw = str(url or "").strip()

    if not raw:
        return ""

    try:
        host = (
            urlparse(raw)
            .hostname
            or ""
        ).lower()
    except Exception:
        return ""

    if host.startswith("www."):
        host = host[4:]

    return host


def _valid_http_url(
    value: Any,
) -> bool:
    raw = str(value or "").strip()

    try:
        parsed = urlparse(raw)
    except Exception:
        return False

    return (
        parsed.scheme in {
            "http",
            "https",
        }
        and bool(parsed.netloc)
    )


def _looks_authoritative(
    domain: str,
) -> bool:
    value = str(
        domain or ""
    ).lower()

    if not value:
        return False

    authoritative_suffixes = (
        ".gov",
        ".gov.uk",
        ".gov.in",
        ".gov.au",
        ".gov.sg",
        ".edu",
        ".ac.uk",
    )

    if any(
        value.endswith(suffix)
        for suffix in authoritative_suffixes
    ):
        return True

    institutional_domains = (
        "parliament.uk",
        "gov.uk",
        "who.int",
        "un.org",
        "europa.eu",
        "bankofengland.co.uk",
        "ons.gov.uk",
        "nhs.uk",
    )

    return any(
        value == domain_name
        or value.endswith("." + domain_name)
        for domain_name
        in institutional_domains
    )


def normalize_evidence(
    item: Any,
    *,
    retrieved_at: Any = None,
) -> KnowledgeEvidence | None:
    if not isinstance(
        item,
        dict,
    ):
        return None

    title = _norm(
        item.get("title")
        or item.get("name")
    )

    url = _norm(
        item.get("url")
        or item.get("link")
    )

    snippet = _norm(
        item.get("snippet")
        or item.get("text")
        or item.get("content")
        or item.get("description")
    )

    if not title and not snippet:
        return None

    if not _valid_http_url(url):
        return None

    domain = _domain(url)

    when = (
        _parse_datetime(
            retrieved_at
        )
        or _parse_datetime(
            item.get(
                "retrievedAt"
            )
        )
        or _now()
    )

    published = (
        item.get("publishedAt")
        or item.get("published_at")
        or item.get("date")
    )

    authoritative = bool(
        item.get(
            "authoritative",
            False,
        )
    ) or _looks_authoritative(
        domain
    )

    return KnowledgeEvidence(
        title=title,
        url=url,
        snippet=snippet,
        source_domain=domain,
        retrieved_at=_iso(
            when
        ),
        published_at=(
            _norm(published)
            if published
            else None
        ),
        authoritative=authoritative,
        score=0.0,
    )


def _tokenize(
    text: Any,
) -> set[str]:
    return {
        token
        for token in re.findall(
            r"[a-zA-Z0-9]+",
            str(text or "").lower(),
        )
        if len(token) >= 2
    }


def _relevance_score(
    query: str,
    evidence: KnowledgeEvidence,
) -> float:
    query_tokens = _tokenize(
        query
    )

    evidence_tokens = _tokenize(
        evidence.title
        + " "
        + evidence.snippet
    )

    if not query_tokens:
        overlap = 0.0

    else:
        overlap = (
            len(
                query_tokens
                & evidence_tokens
            )
            / len(query_tokens)
        )

    score = (
        0.25
        + min(
            0.55,
            overlap * 0.75,
        )
    )

    if evidence.authoritative:
        score += 0.15

    return round(
        min(score, 1.0),
        3,
    )


def _deduplicate(
    evidence: list[KnowledgeEvidence],
) -> list[KnowledgeEvidence]:
    seen_urls: set[str] = set()
    output: list[
        KnowledgeEvidence
    ] = []

    for item in evidence:
        key = item.url.lower()

        if key in seen_urls:
            continue

        seen_urls.add(key)
        output.append(item)

    return output


def _retrieval_is_recent(
    evidence: KnowledgeEvidence,
    *,
    max_age_hours: int,
    now: datetime,
) -> bool:
    retrieved = _parse_datetime(
        evidence.retrieved_at
    )

    if retrieved is None:
        return False

    if retrieved > (
        now
        + timedelta(minutes=5)
    ):
        return False

    age = (
        now
        - retrieved
    )

    return age <= timedelta(
        hours=max_age_hours
    )


def build_live_knowledge_packet(
    query: Any,
    raw_results: Any,
    *,
    requires_live_retrieval: bool = True,
    max_age_hours: int = 24,
    now: datetime | None = None,
    minimum_evidence: int = 1,
) -> LiveKnowledgePacket:
    query_text = _norm(
        query
    )

    clock = (
        now
        or _now()
    ).astimezone(
        timezone.utc
    )

    if not query_text:
        return LiveKnowledgePacket(
            query="",
            status=STATUS_UNAVAILABLE,
            can_answer=False,
            confidence=0.0,
            evidence=(),
            reason="empty live-knowledge query",
            retrieved_at=_iso(clock),
        )

    if isinstance(
        raw_results,
        dict,
    ):
        candidates = (
            raw_results.get("results")
            or raw_results.get("items")
            or raw_results.get("evidence")
            or []
        )

    elif isinstance(
        raw_results,
        (list, tuple),
    ):
        candidates = raw_results

    else:
        candidates = []

    normalized: list[
        KnowledgeEvidence
    ] = []

    for raw in candidates:
        item = normalize_evidence(
            raw,
            retrieved_at=_iso(
                clock
            ),
        )

        if item is None:
            continue

        score = _relevance_score(
            query_text,
            item,
        )

        item = KnowledgeEvidence(
            title=item.title,
            url=item.url,
            snippet=item.snippet,
            source_domain=item.source_domain,
            retrieved_at=item.retrieved_at,
            published_at=item.published_at,
            authoritative=item.authoritative,
            score=score,
        )

        normalized.append(
            item
        )

    normalized = _deduplicate(
        normalized
    )

    normalized = [
        item
        for item in normalized
        if _retrieval_is_recent(
            item,
            max_age_hours=max_age_hours,
            now=clock,
        )
    ]

    normalized.sort(
        key=lambda item: (
            item.authoritative,
            item.score,
        ),
        reverse=True,
    )

    if len(normalized) < minimum_evidence:
        return LiveKnowledgePacket(
            query=query_text,
            status=STATUS_UNAVAILABLE,
            can_answer=(
                not requires_live_retrieval
            ),
            confidence=0.0,
            evidence=tuple(
                normalized
            ),
            reason=(
                "live evidence unavailable; "
                "stale model knowledge must not be presented "
                "as a verified current fact"
                if requires_live_retrieval
                else
                "no external evidence available"
            ),
            retrieved_at=_iso(clock),
        )

    authoritative_count = sum(
        1
        for item in normalized
        if item.authoritative
    )

    top_score = max(
        (
            item.score
            for item in normalized
        ),
        default=0.0,
    )

    if (
        authoritative_count >= 1
        and top_score >= 0.45
    ):
        status = STATUS_VERIFIED
        confidence = min(
            0.98,
            0.72
            + (
                authoritative_count
                * 0.08
            )
            + (
                top_score
                * 0.15
            ),
        )

        reason = (
            "recent relevant evidence includes "
            "an authoritative source"
        )

    else:
        status = STATUS_PARTIAL
        confidence = min(
            0.84,
            0.45
            + (
                top_score
                * 0.35
            )
            + (
                min(
                    len(normalized),
                    3,
                )
                * 0.04
            ),
        )

        reason = (
            "recent evidence is available but "
            "authoritative verification is limited"
        )

    return LiveKnowledgePacket(
        query=query_text,
        status=status,
        can_answer=True,
        confidence=round(
            confidence,
            3,
        ),
        evidence=tuple(
            normalized[:8]
        ),
        reason=reason,
        retrieved_at=_iso(clock),
    )


def build_grounding_context(
    packet: LiveKnowledgePacket,
) -> str:
    """
    Build safe external-knowledge context for the LLM.

    This output is ephemeral prompt context only.
    It must never be written into user-memory collections.
    """

    if not packet.can_answer:
        return (
            "LIVE KNOWLEDGE STATUS: UNAVAILABLE.\n"
            "The user's question requires current or externally "
            "verified information, but sufficient live evidence "
            "was not retrieved.\n"
            "Do NOT guess. Do NOT rely on possibly stale model "
            "knowledge as if it were current. Tell the user briefly "
            "that the current fact could not be verified right now."
        )

    lines = [
        "LIVE KNOWLEDGE EVIDENCE",
        f"Query: {packet.query}",
        f"Verification status: {packet.status}",
        f"Confidence: {packet.confidence:.3f}",
        "",
        "Use the evidence below for current factual claims.",
        "Do not invent facts not supported by this evidence.",
        "If sources disagree, acknowledge the uncertainty.",
        "",
    ]

    for index, item in enumerate(
        packet.evidence,
        start=1,
    ):
        lines.extend(
            [
                f"[SOURCE {index}]",
                f"Title: {item.title}",
                f"URL: {item.url}",
                f"Domain: {item.source_domain}",
                (
                    "Authoritative: yes"
                    if item.authoritative
                    else
                    "Authoritative: not established"
                ),
                (
                    f"Published: {item.published_at}"
                    if item.published_at
                    else
                    "Published: unknown"
                ),
                f"Evidence: {item.snippet}",
                "",
            ]
        )

    lines.extend(
        [
            "ANSWERING RULE:",
            "Answer naturally in the user's conversational language. "
            "Use these sources as factual grounding, but do not dump "
            "internal scoring or retrieval mechanics into the reply.",
        ]
    )

    return "\n".join(
        lines
    )


def public_knowledge_memory_policy() -> dict[str, Any]:
    """
    Explicit boundary for V11 memory integration.

    Public live facts belong to retrieval context, not user memory.
    """

    return {
        "version": LIVE_KNOWLEDGE_VERSION,
        "persistToUserMemory": False,
        "persistToCharacterMemory": False,
        "ephemeralContextOnly": True,
        "reason": (
            "public live facts may change and must be "
            "re-verified instead of becoming durable user memory"
        ),
    }

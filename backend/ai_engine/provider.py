"""Earn2Love provider-independent LLM adapter.

This is the ONLY AI-engine module allowed to communicate directly with
external LLM providers.

Supported providers are routed through LiteLLM so the Character Engine,
memory, relationship model, planner, safety system and conversation logic
remain independent of any hosting platform.

Environment examples:

AI_ENGINE_PROVIDER=openai
AI_ENGINE_MODEL=gpt-5.6-sol
OPENAI_API_KEY=...

or:

AI_ENGINE_PROVIDER=anthropic
AI_ENGINE_MODEL=claude-sonnet-5
ANTHROPIC_API_KEY=...

Provider/model values are configuration and may be changed without
rewriting the Character Engine.
"""

import os
import time
import asyncio
import logging

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

DEFAULT_PROVIDER = os.environ.get("AI_ENGINE_PROVIDER", "openai")
DEFAULT_MODEL = os.environ.get("AI_ENGINE_MODEL", "gpt-5.6-sol")
TIMEOUT_SECONDS = float(os.environ.get("AI_ENGINE_TIMEOUT", "40"))


class ProviderResult(dict):
    pass


def _resolve_model(provider: str, model: str) -> str:
    provider = (provider or "").strip().lower()
    model = (model or "").strip()

    if not model:
        raise ValueError("AI model is not configured")

    # LiteLLM generally accepts provider/model.
    # Do not duplicate provider if already supplied.
    if "/" in model:
        return model

    if provider:
        return f"{provider}/{model}"

    return model


async def generate(
    system_message,
    user_prompt,
    session_id="char",
    provider=None,
    model=None,
):
    """Normalized provider contract.

    Returns:
        {
            ok,
            text,
            provider,
            model,
            latencyMs,
            usage,
            error
        }
    """

    provider = provider or DEFAULT_PROVIDER
    model = model or DEFAULT_MODEL

    started = time.time()

    try:
        from litellm import acompletion

        resolved_model = _resolve_model(provider, model)

        response = await asyncio.wait_for(
            acompletion(
                model=resolved_model,
                messages=[
                    {
                        "role": "system",
                        "content": system_message,
                    },
                    {
                        "role": "user",
                        "content": user_prompt,
                    },
                ],
            ),
            timeout=TIMEOUT_SECONDS,
        )

        text = ""

        if response and getattr(response, "choices", None):
            message = response.choices[0].message
            text = getattr(message, "content", "") or ""

        usage = {}

        raw_usage = getattr(response, "usage", None)

        if raw_usage:
            try:
                if hasattr(raw_usage, "model_dump"):
                    usage = raw_usage.model_dump()
                elif isinstance(raw_usage, dict):
                    usage = raw_usage
                else:
                    usage = {
                        "prompt_tokens": getattr(
                            raw_usage,
                            "prompt_tokens",
                            None,
                        ),
                        "completion_tokens": getattr(
                            raw_usage,
                            "completion_tokens",
                            None,
                        ),
                        "total_tokens": getattr(
                            raw_usage,
                            "total_tokens",
                            None,
                        ),
                    }
            except Exception:
                usage = {}

        latency = int((time.time() - started) * 1000)

        return ProviderResult(
            ok=True,
            text=text.strip(),
            provider=provider,
            model=model,
            latencyMs=latency,
            usage=usage,
            error=None,
        )

    except asyncio.TimeoutError:
        return ProviderResult(
            ok=False,
            text="",
            provider=provider,
            model=model,
            latencyMs=int((time.time() - started) * 1000),
            usage={},
            error="provider_timeout",
        )

    except Exception as exc:
        logger.warning(
            "LLM provider error: %s: %s",
            type(exc).__name__,
            exc,
        )

        return ProviderResult(
            ok=False,
            text="",
            provider=provider,
            model=model,
            latencyMs=int((time.time() - started) * 1000),
            usage={},
            error=f"provider_error:{type(exc).__name__}",
        )


# ============================================================
# V12 LIVE KNOWLEDGE PROVIDER BOUNDARY
# ============================================================

async def search_web(
    query,
    *,
    model=None,
    user_country=None,
    user_city=None,
    user_region=None,
    user_timezone=None,
    timeout_seconds=None,
    max_output_tokens=None,
):
    """
    Perform OpenAI Responses API web search.

    IMPORTANT:
    provider.py remains the only AI-engine module that directly
    communicates with external LLM providers.

    This function performs no persistence.
    """

    query = " ".join(
        str(query or "").strip().split()
    )

    resolved_model = (
        model
        or os.environ.get(
            "AI_LIVE_KNOWLEDGE_MODEL",
            "gpt-5.6-luna",
        )
    )

    timeout = float(
        timeout_seconds
        if timeout_seconds is not None
        else os.environ.get(
            "AI_LIVE_KNOWLEDGE_TIMEOUT",
            "25",
        )
    )

    max_tokens = int(
        max_output_tokens
        if max_output_tokens is not None
        else os.environ.get(
            "AI_LIVE_KNOWLEDGE_MAX_OUTPUT_TOKENS",
            "700",
        )
    )

    if not query:
        return ProviderResult(
            ok=False,
            response=None,
            provider="openai-web-search",
            model=resolved_model,
            error="empty_query",
        )

    api_key = os.environ.get(
        "OPENAI_API_KEY",
        "",
    ).strip()

    if not api_key:
        return ProviderResult(
            ok=False,
            response=None,
            provider="openai-web-search",
            model=resolved_model,
            error="missing_openai_api_key",
        )

    try:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(
            api_key=api_key
        )

        web_tool = {
            "type": "web_search_preview",
            "search_context_size": "medium",
        }

        location = {}

        if user_country:
            location["country"] = str(
                user_country
            ).upper()

        if user_city:
            location["city"] = str(
                user_city
            ).strip()

        if user_region:
            location["region"] = str(
                user_region
            ).strip()

        if user_timezone:
            location["timezone"] = str(
                user_timezone
            ).strip()

        if location:
            location["type"] = "approximate"
            web_tool["user_location"] = location

        instructions = (
            "You are a live public-information retrieval component. "
            "Use web search for the supplied query. "
            "Return only a concise factual synthesis supported by the "
            "web sources you actually inspected. "
            "Prioritize official government, institutional, primary, "
            "or otherwise authoritative sources when available. "
            "For a current office-holder, current law, current event, "
            "price, result, weather, company leader or other changing "
            "fact, verify the present or requested date context. "
            "Do not rely on model memory when web evidence differs. "
            "Do not discuss internal reasoning."
        )

        response = await asyncio.wait_for(
            client.responses.create(
                model=resolved_model,
                instructions=instructions,
                input=query,
                tools=[
                    web_tool
                ],
                tool_choice="required",
                include=[
                    "web_search_call.action.sources"
                ],
                max_output_tokens=max_tokens,
                store=False,
            ),
            timeout=timeout,
        )

        return ProviderResult(
            ok=True,
            response=response,
            provider="openai-web-search",
            model=resolved_model,
            error=None,
        )

    except asyncio.TimeoutError:
        return ProviderResult(
            ok=False,
            response=None,
            provider="openai-web-search",
            model=resolved_model,
            error="live_search_timeout",
        )

    except Exception as exc:
        logger.warning(
            "Live knowledge provider error: %s: %s",
            type(exc).__name__,
            exc,
        )

        return ProviderResult(
            ok=False,
            response=None,
            provider="openai-web-search",
            model=resolved_model,
            error=(
                "live_search_error:"
                + type(exc).__name__
            ),
        )

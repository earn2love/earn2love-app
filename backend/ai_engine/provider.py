"""Provider-agnostic model layer.

`generate(...)` is the ONLY place that talks to an LLM. The engine never imports a
specific provider SDK, so providers swap via env without rewriting character logic.
Uses the Emergent Universal LLM Key via emergentintegrations (OpenAI/Anthropic/Gemini).
Non-streaming: the guarded pipeline needs the full response to validate + regenerate.
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


async def generate(system_message, user_prompt, session_id="char", provider=None, model=None):
    """Normalized contract. Returns {ok, text, provider, model, latencyMs, usage, error}."""
    provider = provider or DEFAULT_PROVIDER
    model = model or DEFAULT_MODEL
    key = os.environ.get("EMERGENT_LLM_KEY")
    started = time.time()
    if not key:
        return ProviderResult(ok=False, text="", provider=provider, model=model,
                              latencyMs=0, usage={}, error="EMERGENT_LLM_KEY not configured")
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
        chat = LlmChat(api_key=key, session_id=session_id, system_message=system_message).with_model(provider, model)
        text = await asyncio.wait_for(chat.send_message(UserMessage(text=user_prompt)), timeout=TIMEOUT_SECONDS)
        latency = int((time.time() - started) * 1000)
        return ProviderResult(ok=True, text=(text or "").strip(), provider=provider, model=model,
                              latencyMs=latency, usage={}, error=None)
    except asyncio.TimeoutError:
        return ProviderResult(ok=False, text="", provider=provider, model=model,
                              latencyMs=int((time.time() - started) * 1000), usage={}, error="provider_timeout")
    except Exception as e:
        logger.warning(f"provider error: {type(e).__name__}: {e}")
        return ProviderResult(ok=False, text="", provider=provider, model=model,
                              latencyMs=int((time.time() - started) * 1000), usage={},
                              error=f"provider_error:{type(e).__name__}")

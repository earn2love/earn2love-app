"""Model router — pick the right model per message instead of one model for everything.

Deterministic routing from the (already-computed) understanding + plan signals, so it
adds ZERO extra LLM cost. Fast/cheap models for social chatter; the strong reasoner for
deep decisions and memory-heavy callbacks. Fully env-configurable and feature-flagged.
"""
import os
import logging

logger = logging.getLogger(__name__)

# Routing categories
FAST_SOCIAL = "FAST_SOCIAL"
STANDARD_SOCIAL = "STANDARD_SOCIAL"
DEEP_REASONING = "DEEP_REASONING"
MEMORY_HEAVY = "MEMORY_HEAVY"
STRUCTURED_ACTION = "STRUCTURED_ACTION"

DEFAULT_MODEL = os.environ.get("AI_ENGINE_MODEL", "gpt-5.6-sol")

# (provider, model) per category — override any via env.
TIERS = {
    FAST_SOCIAL:       ("openai", os.environ.get("AI_MODEL_FAST", "gpt-5.4-mini")),
    STANDARD_SOCIAL:   ("openai", os.environ.get("AI_MODEL_STANDARD", "gpt-5.4")),
    DEEP_REASONING:    ("openai", os.environ.get("AI_MODEL_DEEP", DEFAULT_MODEL)),
    MEMORY_HEAVY:      ("openai", os.environ.get("AI_MODEL_MEMORY", DEFAULT_MODEL)),
    STRUCTURED_ACTION: ("openai", os.environ.get("AI_MODEL_STRUCTURED", "gpt-5.4")),
}

ENABLED = os.environ.get("AI_ROUTER_ENABLED", "1") not in ("0", "false", "False")


def classify(u, plan, memories):
    """Return (category, reason) from deterministic conversation signals."""
    mode = u.get("conversationalMode")
    serious = u.get("seriousnessLevel") == "high"
    if u.get("userReferencedPast") or len(memories or []) >= 3:
        return MEMORY_HEAVY, "old-context callback / memory-rich"
    if serious or u.get("userNeedsAdvice"):
        return DEEP_REASONING, "serious topic / advice requested"
    if mode == "greeting" or u.get("replyShouldBeShort"):
        return FAST_SOCIAL, "greeting / very short social reply"
    if mode in ("casual", "banter"):
        return STANDARD_SOCIAL, f"{mode} conversation"
    return STANDARD_SOCIAL, "default social"


def route(u, plan, memories, *, category_override=None, enabled_override=None):
    enabled = ENABLED if enabled_override is None else enabled_override
    if category_override:
        cat = category_override
        reason = "explicit category"
    elif not enabled:
        cat = DEEP_REASONING
        reason = "router disabled — using strong model"
    else:
        cat, reason = classify(u, plan, memories)
    provider, model = TIERS.get(cat, ("openai", DEFAULT_MODEL))
    return {"category": cat, "provider": provider, "model": model, "reason": reason}


def repair_model():
    """Model to use for a quality-repair regeneration — always the strong reasoner."""
    return TIERS[DEEP_REASONING]

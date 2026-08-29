"""
V16.2C3 verified buffered-stream orchestration.

Internal orchestration bridge. CharacterEngine remains the semantic
authority. Raw provider deltas are buffered before engine verification.
"""

from . import buffered_streaming_generation as BSG16

V16_2_VERIFIED_STREAMING_ORCHESTRATION = True


async def respond_with_buffered_stream(
    engine,
    character_id,
    user_id,
    user_text,
    *,
    sandbox=False,
    language_override=None,
    relationship_override=None,
    history_fixture=None,
    feature_flags=None,
    conversation_id="default",
    multimodal_context=None,
):
    if engine is None:
        raise ValueError("engine_required")

    respond = getattr(engine, "respond", None)

    if not callable(respond):
        raise ValueError("engine_respond_required")

    return await respond(
        character_id,
        user_id,
        user_text,
        sandbox=sandbox,
        language_override=language_override,
        relationship_override=relationship_override,
        history_fixture=history_fixture,
        feature_flags=feature_flags,
        conversation_id=conversation_id,
        multimodal_context=multimodal_context,
        _generation_callable=BSG16.generate_buffered_stream,
    )

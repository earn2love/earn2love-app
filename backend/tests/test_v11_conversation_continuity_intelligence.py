from ai_engine import conversation_continuity_intelligence as CC11


def thread(
    thread_id,
    topic,
    summary,
    *,
    unresolved=True,
    commitment="",
    status="active",
    turn_count=3,
    last_turn_index=5,
):
    return {
        "threadId": thread_id,
        "topic": topic,
        "summary": summary,
        "unresolved": unresolved,
        "commitment": commitment,
        "status": status,
        "turnCount": turn_count,
        "lastTurnIndex": last_turn_index,
    }


def test_version():
    assert CC11.CONTINUITY_VERSION == 11


def test_detect_resume():
    assert CC11.detect_explicit_resume(
        "Let's continue from where we stopped"
    )


def test_detect_return():
    assert CC11.detect_explicit_return(
        "Going back to the payment issue"
    )


def test_detect_completion():
    assert CC11.detect_completion(
        "That's complete now"
    )


def test_detect_abandon():
    assert CC11.detect_abandon(
        "Drop this topic"
    )


def test_unresolved_detection():
    assert CC11.detect_unresolved(
        "We still need to fix checkout"
    )


def test_complete_text_not_unresolved():
    assert not CC11.detect_unresolved(
        "Checkout is fixed now"
    )


def test_commitment_detection():
    result = CC11.extract_commitment(
        "We need to finish the Firebase integration"
    )

    assert result


def test_no_commitment():
    assert (
        CC11.extract_commitment(
            "The app looks good"
        )
        == ""
    )


def test_normalize_thread():
    result = CC11.normalize_thread(
        thread(
            "t1",
            "checkout",
            "Need to fix checkout",
        )
    )

    assert result.thread_id == "t1"
    assert result.topic == "checkout"


def test_topic_similarity():
    score = CC11.topic_similarity(
        "Let's fix the checkout issue",
        "checkout",
        "Basket checkout bug",
    )

    assert score > 0


def test_unrelated_topic_similarity_zero():
    assert (
        CC11.topic_similarity(
            "Tell me about Firebase",
            "checkout",
            "Basket issue",
        )
        == 0
    )


def test_choose_matching_thread():
    threads = [
        thread(
            "t1",
            "checkout",
            "Need to fix checkout bug",
        ),
        thread(
            "t2",
            "firebase",
            "Need to connect Firebase",
        ),
    ]

    result = CC11.choose_thread(
        "Let's fix Firebase",
        threads,
    )

    assert result
    assert result.thread_id == "t2"


def test_explicit_resume_prefers_active_thread():
    threads = [
        thread(
            "t1",
            "checkout",
            "Need to fix checkout",
        ),
        thread(
            "t2",
            "firebase",
            "Need to connect Firebase",
        ),
    ]

    result = CC11.choose_thread(
        "Let's continue",
        threads,
        active_thread_id="t1",
    )

    assert result
    assert result.thread_id == "t1"


def test_completed_thread_not_selected():
    threads = [
        thread(
            "t1",
            "checkout",
            "Checkout fixed",
            status="completed",
        )
    ]

    result = CC11.choose_thread(
        "Let's continue checkout",
        threads,
    )

    assert result is None


def test_new_topic_when_no_thread_matches():
    result = CC11.analyze_continuity(
        "Tell me about movies",
        [
            thread(
                "t1",
                "checkout",
                "Need to fix checkout",
            )
        ],
        active_thread_id="",
        current_topic="movies",
    )

    assert result.mode == CC11.MODE_NEW


def test_continue_active_thread():
    result = CC11.analyze_continuity(
        "The checkout button is still broken",
        [
            thread(
                "t1",
                "checkout",
                "Need to fix checkout",
            )
        ],
        active_thread_id="t1",
    )

    assert result.mode == CC11.MODE_CONTINUE
    assert result.selected_thread_id == "t1"


def test_return_to_prior_thread():
    result = CC11.analyze_continuity(
        "Let's fix Firebase now",
        [
            thread(
                "t1",
                "checkout",
                "Need to fix checkout",
                last_turn_index=10,
            ),
            thread(
                "t2",
                "firebase",
                "Need to connect Firebase",
                last_turn_index=4,
            ),
        ],
        active_thread_id="t1",
    )

    assert result.mode == CC11.MODE_RETURN
    assert result.selected_thread_id == "t2"


def test_explicit_resume():
    result = CC11.analyze_continuity(
        "Where were we? Let's continue",
        [
            thread(
                "t1",
                "checkout",
                "Need to fix checkout",
            )
        ],
        active_thread_id="t1",
    )

    assert result.mode == CC11.MODE_RESUME


def test_explicit_completion():
    result = CC11.analyze_continuity(
        "That's completed now",
        [
            thread(
                "t1",
                "checkout",
                "Need to fix checkout",
            )
        ],
        active_thread_id="t1",
    )

    assert result.mode == CC11.MODE_COMPLETE
    assert result.selected_thread_id == "t1"


def test_explicit_abandon():
    result = CC11.analyze_continuity(
        "Drop this topic",
        [
            thread(
                "t1",
                "checkout",
                "Need to fix checkout",
            )
        ],
        active_thread_id="t1",
    )

    assert result.mode == CC11.MODE_ABANDON


def test_build_thread_detects_unresolved():
    result = CC11.build_thread_candidate(
        thread_id="t1",
        topic="firebase",
        summary="We still need to connect Firebase",
        turn_count=4,
        last_turn_index=9,
    )

    assert result.unresolved


def test_build_thread_detects_commitment():
    result = CC11.build_thread_candidate(
        thread_id="t1",
        topic="firebase",
        summary="We need to connect Firebase",
        turn_count=4,
        last_turn_index=9,
    )

    assert result.commitment


def test_build_thread_complete_summary_not_unresolved():
    result = CC11.build_thread_candidate(
        thread_id="t1",
        topic="checkout",
        summary="Checkout is fixed now",
        turn_count=8,
        last_turn_index=20,
    )

    assert not result.unresolved


def test_analysis_is_deterministic():
    threads = [
        thread(
            "t1",
            "firebase",
            "Need to connect Firebase",
        )
    ]

    first = CC11.analyze_continuity(
        "Let's continue Firebase",
        threads,
        active_thread_id="t1",
    )

    second = CC11.analyze_continuity(
        "Let's continue Firebase",
        threads,
        active_thread_id="t1",
    )

    assert first == second


def test_no_mutation():
    threads = [
        thread(
            "t1",
            "firebase",
            "Need to connect Firebase",
        )
    ]

    before = [
        dict(item)
        for item in threads
    ]

    CC11.analyze_continuity(
        "Let's continue Firebase",
        threads,
        active_thread_id="t1",
    )

    assert threads == before


def test_safe_copy_no_private_reasoning():
    result = CC11.analyze_continuity(
        "Let's continue",
        [
            thread(
                "t1",
                "firebase",
                "Need to connect Firebase",
            )
        ],
        active_thread_id="t1",
    )

    safe = CC11.safe_continuity_copy(
        result
    )

    text = str(
        safe
    )

    assert "chainOfThought" not in text
    assert "hiddenReasoning" not in text
    assert "reasoningTrace" not in text


def test_abandon_beats_resume():
    result = CC11.analyze_continuity(
        "Don't continue, drop this topic",
        [
            thread(
                "t1",
                "firebase",
                "Need to connect Firebase",
            )
        ],
        active_thread_id="t1",
    )

    assert result.mode == CC11.MODE_ABANDON


def test_completion_beats_resume():
    result = CC11.analyze_continuity(
        "We're done, no need to continue",
        [
            thread(
                "t1",
                "firebase",
                "Need to connect Firebase",
            )
        ],
        active_thread_id="t1",
    )

    assert result.mode == CC11.MODE_COMPLETE


def test_recent_thread_used_for_ambiguous_resume():
    threads = [
        thread(
            "t1",
            "checkout",
            "Need checkout fix",
            last_turn_index=4,
        ),
        thread(
            "t2",
            "firebase",
            "Need Firebase fix",
            last_turn_index=20,
        ),
    ]

    result = CC11.choose_thread(
        "Let's continue",
        threads,
    )

    assert result
    assert result.thread_id == "t2"


def test_explicit_return_reason():
    result = CC11.analyze_continuity(
        "Going back to Firebase",
        [
            thread(
                "t1",
                "firebase",
                "Need to connect Firebase",
            )
        ],
    )

    assert result.mode == CC11.MODE_RETURN
    assert result.reason == "explicit_topic_return"


def test_confidence_bounded():
    result = CC11.analyze_continuity(
        "Let's continue",
        [],
    )

    assert 0.0 <= result.confidence <= 1.0


def test_direct_topic_match_beats_generic_summary_word():
    checkout = CC11.topic_similarity(
        "Let's fix Firebase",
        "checkout",
        "Need to fix checkout bug",
    )

    firebase = CC11.topic_similarity(
        "Let's fix Firebase",
        "firebase",
        "Need to connect Firebase",
    )

    assert firebase > checkout


def test_direct_topic_match_beats_more_recent_unrelated_thread():
    threads = [
        thread(
            "checkout",
            "checkout",
            "Need to fix checkout bug",
            last_turn_index=100,
        ),
        thread(
            "firebase",
            "firebase",
            "Need to connect Firebase",
            last_turn_index=5,
        ),
    ]

    selected = CC11.choose_thread(
        "Let's fix Firebase",
        threads,
    )

    assert selected
    assert selected.thread_id == "firebase"


def test_summary_match_still_supports_natural_continuation():
    score = CC11.topic_similarity(
        "The blank page is still happening",
        "checkout",
        "Checkout has a blank page issue",
    )

    assert score > 0


def test_unrelated_summary_remains_zero():
    score = CC11.topic_similarity(
        "Let's connect Firebase",
        "checkout",
        "Basket payment problem",
    )

    assert score == 0.0



def test_not_done_is_not_completion():
    assert not CC11.detect_completion(
        "This is not done yet"
    )

    assert CC11.detect_unresolved(
        "This is not done yet"
    )


def test_not_fixed_is_not_completion():
    assert not CC11.detect_completion(
        "The checkout is not fixed now"
    )


def test_actual_completion_still_detected():
    assert CC11.detect_completion(
        "That's done"
    )


def test_dont_stop_is_not_abandonment():
    assert not CC11.detect_abandon(
        "Don't stop this, continue"
    )


def test_actual_abandonment_still_detected():
    assert CC11.detect_abandon(
        "Drop this issue"
    )


def test_dont_continue_is_not_resume():
    assert not CC11.detect_explicit_resume(
        "Don't continue this"
    )


def test_positive_resume_still_works():
    assert CC11.detect_explicit_resume(
        "Continue where we left off"
    )

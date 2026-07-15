"""Focused unit tests — FLOW_LIVE_TURN_STABILITY_V1 lifecycle accounting."""
import sys, json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from flow_turn_lifecycle import TurnLifecycle


def make(log_lines=None):
    lines = log_lines if log_lines is not None else []
    return TurnLifecycle("sess1-1", "cidA", capture_duration_ms=1234.5,
                         log_fn=lines.append), lines


def test_normal_turn_invariants():
    """Cases A/B: normal turn — 1 STT, 1 translation, 1 TTS, clean summary."""
    tl, lines = make()
    tl.transition("PROCESSING", "orb_released")
    tl.stt_started()
    tl.translation_started()
    tl.tts_requested()
    tl.transition("SPEAKING", "tts_start")
    tl.complete("ok")
    s = tl.finalize()
    assert s["stt_count"] == 1 and s["translation_count"] == 1
    assert s["tts_request_count"] == 1
    assert all(s["invariants"].values()), s["invariants"]
    assert s["completion_status"] == "ok" and s["cleanup_status"] == "complete"


def test_skipped_turn_no_tts():
    """Cases D/E: skip (no speech / incomplete) — zero TTS, invariants hold."""
    tl, _ = make()
    tl.transition("PROCESSING", "orb_released")
    tl.stt_started()
    tl.complete("skipped:incomplete_thought")
    s = tl.finalize()
    assert s["tts_request_count"] == 0
    assert all(s["invariants"].values())


def test_retry_success_counts():
    """Case F: noop retry succeeds — retry counted, final translation still ≤1."""
    tl, _ = make()
    tl.transition("PROCESSING", "orb_released")
    tl.stt_started()
    tl.translation_started()
    tl.retry(); tl.translation_started()      # bounded retry pass
    tl.tts_requested()
    tl.transition("SPEAKING", "tts_start")
    tl.complete("ok")
    s = tl.finalize()
    assert s["retry_count"] == 1 and s["translation_count"] == 2
    assert s["invariants"]["translation_le_1"]          # 2 - 1 retry = 1 final
    assert all(s["invariants"].values())


def test_retry_fail_produces_no_speech():
    """Case G: retry fails — failed turn must have zero TTS requests."""
    tl, _ = make()
    tl.transition("PROCESSING", "orb_released")
    tl.stt_started()
    tl.translation_started()
    tl.retry(); tl.translation_started()
    tl.complete("failed:translation_language_lock_failed")
    s = tl.finalize()
    assert s["tts_request_count"] == 0
    assert s["invariants"]["tts_eq_0_on_failure"]
    assert all(s["invariants"].values())


def test_disconnect_marks_incomplete_ownership_cleared():
    """Cases H/I/J: disconnect mid-turn — summary still emitted, status recorded."""
    tl, lines = make()
    tl.transition("PROCESSING", "orb_released")
    tl.stt_started()
    s = tl.finalize()                          # finally-path with no complete()
    assert s["completion_status"] == "disconnected"
    assert s["cleanup_status"] == "complete"
    assert sum(1 for l in lines if l.startswith("TURN_SUMMARY")) == 1


def test_summary_idempotent():
    """Case N (duplicate signals): double finalize emits exactly one summary."""
    tl, lines = make()
    tl.complete("skipped:release_no_speech")
    tl.finalize(); tl.finalize()
    assert sum(1 for l in lines if l.startswith("TURN_SUMMARY")) == 1


def test_tts_delivery_failure_not_flagged():
    """TTS requested from approved payload but delivery failed (client gone):
    not a validation violation — speech was legitimately authorized."""
    tl, _ = make()
    tl.stt_started(); tl.translation_started(); tl.tts_requested()
    tl.transition("SPEAKING", "approved_payload_tts")
    tl.complete("failed:tts_no_audio")
    s = tl.finalize()
    assert s["invariants"]["tts_eq_0_on_failure"] is True
    assert all(s["invariants"].values())


def test_invariant_violation_visible():
    """A defective double-TTS turn must be flagged, not hidden."""
    tl, _ = make()
    tl.stt_started(); tl.translation_started()
    tl.tts_requested(); tl.tts_requested()     # defect
    tl.complete("ok")
    s = tl.finalize()
    assert s["invariants"]["tts_eq_1_on_success"] is False


def test_transition_lines_bounded_fields():
    """Every transition line carries exactly the bounded evidence fields."""
    tl, lines = make()
    tl.transition("PROCESSING", "orb_released")
    rec = json.loads(lines[-1].split("TURN_LIFECYCLE: ", 1)[1])
    assert set(rec) == {"turn_id", "client_id", "state_from", "state_to", "transition_reason"}
    assert rec["state_from"] == "LISTENING" and rec["state_to"] == "PROCESSING"


if __name__ == "__main__":
    fails = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            try:
                fn()
                print(f"PASS {name}")
            except AssertionError as e:
                fails += 1
                print(f"FAIL {name}: {e}")
    sys.exit(1 if fails else 0)

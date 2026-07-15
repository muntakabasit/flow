"""
FLOW_LIVE_TURN_STABILITY_V1 — canonical turn lifecycle accounting.

One TurnLifecycle instance per committed turn. Pure bookkeeping: no I/O
beyond the injected log function, no model or network dependencies, so it
is unit-testable in isolation and inherited unchanged by future languages
and speech-recognition engines.

Canonical states:
    IDLE → LISTENING → PROCESSING → SPEAKING → TURN_COMPLETE → IDLE

Bounded evidence per transition (one JSON log line):
    turn_id, client_id, state_from, state_to, transition_reason

Bounded summary per turn (one JSON log line, emitted exactly once):
    turn_id, client_id, capture_duration_ms, stt_count, translation_count,
    retry_count, tts_request_count, completion_status, cleanup_status,
    invariants {…: bool}
"""

import json

CANONICAL_STATES = ("IDLE", "LISTENING", "PROCESSING", "SPEAKING", "TURN_COMPLETE")


class TurnLifecycle:
    def __init__(self, turn_id: str, client_id: str, capture_duration_ms: float = 0.0, log_fn=None):
        self.turn_id = turn_id
        self.client_id = client_id
        self.capture_duration_ms = round(capture_duration_ms)
        self._log = log_fn or (lambda s: None)
        self.state = "LISTENING"     # a committed turn begins from an observed capture
        self.stt_count = 0
        self.translation_count = 0
        self.retry_count = 0
        self.tts_request_count = 0
        self.completion_status = "open"   # ok | skipped:<reason> | failed:<reason> | disconnected
        self.cleanup_status = "pending"   # complete | incomplete
        self._summary_emitted = False

    # ── transitions ──────────────────────────────────────────────────────────
    def transition(self, to_state: str, reason: str) -> None:
        if to_state not in CANONICAL_STATES:
            raise ValueError(f"non-canonical state: {to_state}")
        line = {
            "turn_id": self.turn_id,
            "client_id": self.client_id,
            "state_from": self.state,
            "state_to": to_state,
            "transition_reason": reason,
        }
        self.state = to_state
        self._log("TURN_LIFECYCLE: " + json.dumps(line, ensure_ascii=False))

    # ── stage counters ───────────────────────────────────────────────────────
    def stt_started(self):          self.stt_count += 1
    def translation_started(self):  self.translation_count += 1
    def retry(self):                self.retry_count += 1
    def tts_requested(self):        self.tts_request_count += 1

    # ── completion ───────────────────────────────────────────────────────────
    def complete(self, status: str) -> None:
        """status: 'ok' or 'skipped:<reason>' or 'failed:<reason>' or 'disconnected'."""
        self.completion_status = status
        self.transition("TURN_COMPLETE", status)

    def invariants(self) -> dict:
        ok = self.completion_status == "ok"
        return {
            # one committed turn → at most one primary STT stage
            "stt_le_1": self.stt_count <= 1,
            # one committed turn → at most one final translation stage
            # (bounded noop/lang-lock retries are counted in retry_count)
            "translation_le_1": self.translation_count - self.retry_count <= 1,
            # successful turn → exactly one approved TTS request;
            # failed/skipped turn → zero TTS requests, EXCEPT when the failure
            # is the TTS delivery itself (failed:tts_*) — speech was legitimately
            # requested from an approved payload and delivery failed downstream
            "tts_eq_1_on_success": (self.tts_request_count == 1) if ok else True,
            "tts_eq_0_on_failure": (
                True if ok or self.completion_status.startswith("failed:tts")
                else self.tts_request_count == 0
            ),
            "cleanup_complete": self.cleanup_status == "complete",
        }

    def finalize(self, cleanup_complete: bool = True) -> dict:
        """Emit the single bounded turn summary. Idempotent."""
        self.cleanup_status = "complete" if cleanup_complete else "incomplete"
        if self.completion_status == "open":
            # turn never reached an explicit completion — disconnect/cancellation path
            self.completion_status = "disconnected"
        summary = {
            "turn_id": self.turn_id,
            "client_id": self.client_id,
            "capture_duration_ms": self.capture_duration_ms,
            "stt_count": self.stt_count,
            "translation_count": self.translation_count,
            "retry_count": self.retry_count,
            "tts_request_count": self.tts_request_count,
            "completion_status": self.completion_status,
            "cleanup_status": self.cleanup_status,
            "invariants": self.invariants(),
        }
        if not self._summary_emitted:
            self._summary_emitted = True
            self._log("TURN_SUMMARY: " + json.dumps(summary, ensure_ascii=False))
        return summary

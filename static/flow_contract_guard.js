/* ═══════════════════════════════════════════════════════════════
   FlowContractGuard (web)
   Single source of truth for conversation state.
   Enforces legal transitions, mic/TTS mutual exclusivity,
   deferred turn_complete, single tts_playback_done, barge-in.

   Source of truth: FLOW_RUNTIME_CONTRACT.md
   ═══════════════════════════════════════════════════════════════ */
(function () {
  'use strict';

  class FlowContractGuard {
    /**
     * @param {Object} opts
     * @param {Object} opts.legalTransitions  - { state: [allowed targets] }
     * @param {Function} opts.onDiag          - (msg, type) => void
     * @param {Function} opts.onStateChanged  - (newState, prevState, reason) => void
     * @param {boolean}  opts.devFailFast     - throw on violations (dev only)
     * @param {Object}   opts.effects         - side-effect callbacks
     * @param {Function} opts.effects.stopMic
     * @param {Function} opts.effects.stopTTS
     * @param {Function} opts.effects.notifyTTSDone  - sends tts_playback_done to server
     * @param {Function} opts.effects.closeWebSocket
     * @param {Function} opts.isHandsFreeMode - () => boolean
     */
    constructor(opts = {}) {
      this.legalTransitions = opts.legalTransitions || {};
      this.onDiag = opts.onDiag || (() => {});
      this.onStateChanged = opts.onStateChanged || (() => {});
      this.devFailFast = !!opts.devFailFast;
      this.effects = opts.effects || {};
      this.isHandsFreeMode = opts.isHandsFreeMode || (() => true);

      // ── Owned state ──────────────────────────────────
      this._state = 'idle';

      // ── TTS lifecycle flags (guard-owned) ────────────
      this._ttsActive = false;
      this._pendingTurnComplete = false;
      this._ttsDoneNotified = false;

      // ── Mic tracking ─────────────────────────────────
      this._micActive = false;
    }

    // ═════════════════════════════════════════════════════
    // PUBLIC: State accessors (read-only outside guard)
    // ═════════════════════════════════════════════════════
    get state()               { return this._state; }
    get ttsActive()           { return this._ttsActive; }
    get pendingTurnComplete() { return this._pendingTurnComplete; }
    get ttsDoneNotified()     { return this._ttsDoneNotified; }
    get micActive()           { return this._micActive; }

    // ═════════════════════════════════════════════════════
    // CORE: Guarded transition
    // ═════════════════════════════════════════════════════
    transition(to, reason = 'runtime') {
      const from = this._state;

      // No-op on same-state
      if (from === to) return true;

      // Validate legality
      const allowed = this.legalTransitions[from] || [];
      if (!allowed.includes(to)) {
        this._violation(`Illegal transition ${from} -> ${to} [${reason}]`);
        if (!this.devFailFast) {
          this._emergencyRecover(reason);
        }
        return false;
      }

      // ── Pre-transition side effects ──────────────────
      this._applySideEffectsBeforeTransition(from, to, reason);

      // ── Commit state ─────────────────────────────────
      const prev = this._state;
      this._state = to;

      // ── Post-transition side effects ─────────────────
      this._applySideEffectsAfterTransition(prev, to, reason);

      // ── Notify ───────────────────────────────────────
      this._info(`${prev} → ${to} [${reason}]`);
      this.onStateChanged(to, prev, reason);

      // ── Post-transition invariant check ──────────────
      this._checkInvariants(`post:${prev}->${to}`);

      return true;
    }

    // ═════════════════════════════════════════════════════
    // EVENT HOOKS
    // ═════════════════════════════════════════════════════

    // ── TTS lifecycle ──────────────────────────────────
    onTTSStarted() {
      this._event('tts_started');
      this._ttsActive = true;
      this._ttsDoneNotified = false;

      // INVARIANT: mic must not be active during speaking
      if (this._micActive) {
        this._warn('Mic active at TTS start — stopping');
        this._doStopMic();
      }

      this.transition('speaking', 'tts_start');
    }

    onTTSPlaybackFinished() {
      this._event('tts_playback_finished');
      this._ttsActive = false;

      // Send tts_playback_done exactly once
      this._notifyTTSDoneIfNeeded();

      // Deferred turn_complete?
      if (this._pendingTurnComplete) {
        this._pendingTurnComplete = false;
        this._event('deferred_turn_complete_executing');
        this._completeTurnAfterTTS();
      }
    }

    onTTSCancelledByBargeIn() {
      // INVARIANT: barge-in only valid in speaking state
      if (this._state !== 'speaking') {
        this._warn(`Barge-in ignored: not in speaking (current: ${this._state})`);
        return;
      }

      this._event('barge_in');

      // Stop TTS lifecycle
      this._ttsActive = false;
      this._pendingTurnComplete = false;
      this._doStopTTS();

      // Send tts_playback_done exactly once
      this._notifyTTSDoneIfNeeded();

      // Return to listening
      this.transition('listening', 'barge_in');
    }

    // ── Turn ───────────────────────────────────────────
    onTurnComplete() {
      this._event('turn_complete_received');

      if (this._ttsActive) {
        // INVARIANT: defer until TTS playback finishes
        this._pendingTurnComplete = true;
        this._event('turn_complete_deferred', 'tts_active');
        return;
      }

      // TTS not active — complete immediately
      this._completeTurnAfterTTS();
    }

    // ── User OFF ───────────────────────────────────────
    onUserPressedOff() {
      this._event('user_pressed_off');

      // Full cleanup
      this._doStopMic();
      this._doStopTTS();
      this._ttsActive = false;
      this._pendingTurnComplete = false;
      this._ttsDoneNotified = true; // prevent stale done signal

      if (this.effects.closeWebSocket) {
        this.effects.closeWebSocket();
      }

      // Force to idle regardless of current state
      this._forceState('idle', 'user_off');
    }

    // ═════════════════════════════════════════════════════
    // MIC + TTS FLAG MANAGEMENT
    // ═════════════════════════════════════════════════════
    notifyMicStarted() {
      this._micActive = true;
      if (this._state === 'speaking') {
        this._violation('Mic started during speaking — stopping');
        this._doStopMic();
      }
    }

    notifyMicStopped() {
      this._micActive = false;
    }

    markTTSActive() {
      this._ttsActive = true;
      this._ttsDoneNotified = false;
    }

    markTTSInactive() {
      this._ttsActive = false;
    }

    resetTTSFlags() {
      this._ttsActive = false;
      this._pendingTurnComplete = false;
      this._ttsDoneNotified = true;
    }

    // ═════════════════════════════════════════════════════
    // SNAPSHOT (for diagnostics / external checks)
    // ═════════════════════════════════════════════════════
    snapshot() {
      return {
        state: this._state,
        micActive: this._micActive,
        ttsActive: this._ttsActive,
        pendingTurnComplete: this._pendingTurnComplete,
        ttsDoneNotified: this._ttsDoneNotified,
      };
    }

    // ═════════════════════════════════════════════════════
    // PRIVATE: Side effects around transitions
    // ═════════════════════════════════════════════════════
    _applySideEffectsBeforeTransition(from, to, reason) {
      // Entering speaking — mic must be off
      if (to === 'speaking' && this._micActive) {
        this._warn('Stopping mic before entering speaking');
        this._doStopMic();
      }
    }

    _applySideEffectsAfterTransition(prev, to, reason) {
      // Entering offline/failed: stop mic and TTS
      if (to === 'offline' || to === 'failed') {
        this._doStopMic();
        this._doStopTTS();
        this._ttsActive = false;
        this._pendingTurnComplete = false;
      }

      // Entering idle: full cleanup
      if (to === 'idle') {
        this._doStopMic();
        this._doStopTTS();
        this._ttsActive = false;
        this._pendingTurnComplete = false;
        this._ttsDoneNotified = true;
      }
    }

    // ═════════════════════════════════════════════════════
    // PRIVATE: Helpers
    // ═════════════════════════════════════════════════════
    _completeTurnAfterTTS() {
      const nextState = this.isHandsFreeMode() ? 'listening' : 'ready';
      this.transition(nextState, 'turn_complete_after_tts');
    }

    _notifyTTSDoneIfNeeded() {
      if (this._ttsDoneNotified) {
        this._warn('Duplicate tts_playback_done suppressed');
        return;
      }
      this._ttsDoneNotified = true;
      if (this.effects.notifyTTSDone) {
        this.effects.notifyTTSDone();
      }
    }

    _doStopMic() {
      this._micActive = false;
      if (this.effects.stopMic) this.effects.stopMic();
    }

    _doStopTTS() {
      if (this.effects.stopTTS) this.effects.stopTTS();
    }

    _forceState(to, reason) {
      const prev = this._state;
      this._state = to;
      this._info(`FORCE: ${prev} → ${to} [${reason}]`);
      this.onStateChanged(to, prev, reason);
    }

    _emergencyRecover(failedReason) {
      this._warn(`Emergency recover from ${this._state} [failed: ${failedReason}]`);
      this._doStopMic();
      this._doStopTTS();
      this._ttsActive = false;
      this._pendingTurnComplete = false;
      this._ttsDoneNotified = true;
      if (this.effects.closeWebSocket) this.effects.closeWebSocket();
      this._forceState('idle', 'emergency_recover');
    }

    // ═════════════════════════════════════════════════════
    // PRIVATE: Invariant checks
    // ═════════════════════════════════════════════════════
    _checkInvariants(context) {
      // INV-1: Mic must not be active during speaking
      if (this._state === 'speaking' && this._micActive) {
        this._violation(`INV-1: Mic active during speaking [${context}]`);
        this._doStopMic();
      }

      // INV-2: pendingTurnComplete without ttsActive
      if (this._pendingTurnComplete && !this._ttsActive) {
        this._warn(`INV-2: pendingTurnComplete but ttsActive=false [${context}]`);
      }
    }

    // ═════════════════════════════════════════════════════
    // PRIVATE: Logging
    // ═════════════════════════════════════════════════════
    _event(name, detail = '') {
      this.onDiag(`[guard] ${name}${detail ? `: ${detail}` : ''}`, 'info');
    }

    _info(message) {
      this.onDiag(`[guard] ${message}`, 'ok');
    }

    _warn(message) {
      this.onDiag(`[guard] WARN: ${message}`, 'warn');
    }

    _violation(message) {
      this.onDiag(`[guard] VIOLATION: ${message}`, 'err');
      if (this.devFailFast) {
        throw new Error(`[FlowContractGuard] ${message}`);
      }
    }
  }

  window.FlowContractGuard = FlowContractGuard;
})();

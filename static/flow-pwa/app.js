'use strict';

const WIRE_RATE = 24000;
const RECONNECT_DELAYS = [500, 1000, 2000, 4000, 8000, 15000];
const PRECONNECT_CHUNK_LIMIT = 12;
const CAPTURE_MIN_DURATION_MS = 800;
const CAPTURE_TRAILING_GRACE_MS = 150;

// Stable per-tab client identifier — survives page refresh within the same tab,
// resets when the tab is closed (sessionStorage is per-tab, not persisted).
const clientId = (() => {
  const key = 'flow-cid';
  let id = sessionStorage.getItem(key);
  if (!id) {
    id = Math.random().toString(36).slice(2, 10) + Date.now().toString(36);
    sessionStorage.setItem(key, id);
  }
  return id;
})();

// ── DOM refs ──────────────────────────────────────────────────────────────────
if (!document.getElementById('orbBtn')) {
  throw new Error('[Flow] #orbBtn not found — HTML/JS version mismatch. Hard-reload the page.');
}
const orbBtn          = document.getElementById('orbBtn');
const orbPress        = document.getElementById('orbPress');
const orbWrap         = document.getElementById('orbWrap');
const orbIconUse      = document.getElementById('orbIconUse');
const orbLabel        = document.getElementById('orbLabel');
const connDot         = document.getElementById('connDot');
const stateLabel      = document.getElementById('stateLabel');
const dirLabel        = document.getElementById('dirLabel');
const dirOverOrb      = document.getElementById('dirOverOrb');
const panel           = document.getElementById('panel');
const emptyState      = document.getElementById('emptyState');
const turnsList       = document.getElementById('turnsList');
const lastActions     = document.getElementById('lastActions');
const lastSrc         = document.getElementById('lastSrc');
const lastTgt         = document.getElementById('lastTgt');
const copyBtn         = document.getElementById('copyBtn');
const copyIcon        = document.getElementById('copyIcon');
const copyLabel       = document.getElementById('copyLabel');
const shareBtn        = document.getElementById('shareBtn');
const errorText       = document.getElementById('errorText');
const reconnectButton = document.getElementById('reconnectButton');

// ── App state ─────────────────────────────────────────────────────────────────
let appState = 'ready';
let socket = null;
let serverReady = false;
let maintainConnection = false;
let reconnectAttempt = 0;
let reconnectTimer = null;

let captureWanted = false;
let streaming = false;
let captureToken = 0;
let micStream = null;
let micSource = null;
let micProcessor = null;
let audioContext = null;
let preconnectChunks = [];

let audioQueue = [];
let playingAudio = false;
let activeAudioSource = null;
let playbackGeneration = 0;
let playbackSuppressed = false;
let ttsStarted = false;
let ttsDoneSent = false;
let turnComplete = false;
let releaseSignalsSent = new Set();
let sessionReleaseQueued = false;

// ── Tap-toggle capture state ──────────────────────────────────────────────────
let capturePhase = 'idle'; // idle | recording | committing
let captureGeneration = 0;
let captureStartedAt = null;
let captureStopTimer = null;
let captureStopPending = false;
let captureCommitLocked = false;
let suppressKeyboardClick = false;
let keyboardClickResetTimer = null;

// ── Turn management ───────────────────────────────────────────────────────────
let turns = [];
let pendingSource = { text: '', lang: '' };
let pendingTarget = { text: '', lang: '' };
let currentPair = { sourceLang: 'English', targetLang: 'Portuguese', isPortuguese: false };
let lastActionsText = '';

// ── Utilities ─────────────────────────────────────────────────────────────────
function escHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function endpoint() {
  const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
  return `${protocol}//${location.host}/ws?cid=${encodeURIComponent(clientId)}`;
}

function socketOpen() {
  return socket && socket.readyState === WebSocket.OPEN;
}

function monotonicNow() {
  if (typeof performance !== 'undefined' && typeof performance.now === 'function') {
    return performance.now();
  }
  return Date.now();
}

// ── State machine ─────────────────────────────────────────────────────────────
function setState(next, message) {
  appState = next;

  orbWrap.dataset.state = next;

  const iconHref = next === 'processing' ? '#ico-wave'
                 : next === 'speaking'   ? '#ico-speaker'
                 : '#ico-mic';
  orbIconUse.setAttribute('href', iconHref);

  const connState =
    (next === 'ready' || next === 'listening' || next === 'processing' || next === 'speaking')
      ? 'online'
      : (next === 'connecting' || next === 'offline') ? 'reconnecting'
      : 'offline';
  connDot.dataset.conn = connState;
  connDot.classList.toggle('is-active', next !== 'ready' && connState !== 'offline');

  stateLabel.textContent = message || {
    ready: 'Ready', connecting: 'Connecting', listening: 'Listening',
    processing: 'Translating', speaking: 'Speaking',
    offline: 'Offline', error: 'Connection issue'
  }[next] || 'Ready';

  if (next === 'error') {
    dirLabel.textContent = 'OFFLINE';
    dirLabel.className   = 'dir-label is-offline';
  } else if (next === 'connecting' || next === 'offline') {
    dirLabel.textContent = 'RECONNECTING…';
    dirLabel.className   = 'dir-label is-reconnecting';
  } else {
    dirLabel.textContent = 'EN  ·  PT-BR';
    dirLabel.className   = 'dir-label';
  }

  dirOverOrb.classList.toggle('is-visible', next === 'processing');

  if (next !== 'processing' && next !== 'listening') {
    setOrbLabel({
      ready: 'TAP TO RECORD', connecting: 'CONNECTING…', speaking: 'SPEAKING…',
      offline: 'RECONNECTING…', error: 'RECONNECT BELOW'
    }[next] || 'TAP TO RECORD', false);
  } else if (next === 'listening') {
    setOrbLabel('LISTENING…', false);
  }

  if (next === 'ready' && turns.length > 0) {
    lastActions.hidden = false;
  } else if (next !== 'ready') {
    lastActions.hidden = true;
  }

  reconnectButton.hidden = next !== 'error';
}

function setOrbLabel(text, isTranscript) {
  orbLabel.textContent = text;
  orbLabel.classList.toggle('is-transcript', !!isTranscript);
}

function showError(message) {
  errorText.textContent = message || '';
}

// ── Direction ─────────────────────────────────────────────────────────────────
function updateDirection(sourceLanguage) {
  const isPortuguese = (sourceLanguage || '').toLowerCase().startsWith('pt');
  currentPair = {
    sourceLang: isPortuguese ? 'Portuguese' : 'English',
    targetLang: isPortuguese ? 'English'    : 'Portuguese',
    isPortuguese
  };
  dirOverOrb.textContent = isPortuguese
    ? 'TRANSLATING → ENGLISH'
    : 'TRANSLATING → PORTUGUÊS';
}

// ── Turn cards ────────────────────────────────────────────────────────────────
function addTurnCard(source, target) {
  const turn = {
    id:         Date.now(),
    sourceLang: source.lang || currentPair.sourceLang,
    sourceText: source.text || '',
    targetLang: target.lang || currentPair.targetLang,
    targetText: target.text || ''
  };
  turns.unshift(turn);
  if (turns.length > 6) turns.pop();
  renderTurns();
  lastSrc.textContent = `${turn.sourceLang}: ${turn.sourceText}`;
  lastTgt.textContent = `${turn.targetLang}: ${turn.targetText}`;
  lastActionsText = `${turn.sourceLang}: ${turn.sourceText}\n${turn.targetLang}: ${turn.targetText}`;
}

function renderTurns() {
  if (turns.length === 0) {
    emptyState.hidden = false;
    turnsList.innerHTML = '';
    return;
  }
  emptyState.hidden = true;
  turnsList.innerHTML = '';
  for (let i = 0; i < turns.length; i++) {
    const t = turns[i];
    const card = document.createElement('div');
    card.className = 'turn-card' + (i > 0 ? ' is-older' : '');
    card.innerHTML =
      `<div class="turn-lang">${escHtml(t.sourceLang)}</div>` +
      `<p class="turn-source">${escHtml(t.sourceText)}</p>` +
      `<div class="turn-divider"></div>` +
      `<div class="turn-lang">${escHtml(t.targetLang)}</div>` +
      `<p class="turn-target">${escHtml(t.targetText)}</p>`;
    turnsList.appendChild(card);
  }
  panel.scrollTop = 0;
}

// ── AudioContext ──────────────────────────────────────────────────────────────
function getAudioContext() {
  if (!audioContext || audioContext.state === 'closed') {
    audioContext = new (window.AudioContext || window.webkitAudioContext)();
  }
  if (audioContext.state === 'suspended') audioContext.resume().catch(() => {});
  return audioContext;
}

// ── Interaction sounds ────────────────────────────────────────────────────────
// Subtle programmatic tones — no audio files required.
// All at low gain (0.06) so they sit well below speech volume.

function _playTone({ freq = 440, endFreq, duration = 0.10, gain = 0.06, type = 'sine', fadeOut = true } = {}) {
  try {
    const ctx = getAudioContext();
    const osc = ctx.createOscillator();
    const env = ctx.createGain();
    osc.type = type;
    osc.frequency.setValueAtTime(freq, ctx.currentTime);
    if (endFreq !== undefined) {
      osc.frequency.exponentialRampToValueAtTime(endFreq, ctx.currentTime + duration);
    }
    env.gain.setValueAtTime(gain, ctx.currentTime);
    if (fadeOut) env.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + duration);
    osc.connect(env);
    env.connect(ctx.destination);
    osc.start(ctx.currentTime);
    osc.stop(ctx.currentTime + duration + 0.01);
  } catch {}
}

function soundOrbPress()    { _playTone({ freq: 320, endFreq: 220, duration: 0.08, gain: 0.05 }); }
function soundOrbRelease()  { _playTone({ freq: 220, endFreq: 440, duration: 0.10, gain: 0.05 }); }
function soundConnected()   {
  _playTone({ freq: 528, duration: 0.12, gain: 0.04 });
  setTimeout(() => _playTone({ freq: 792, duration: 0.10, gain: 0.04 }), 110);
}

// ── WebSocket ─────────────────────────────────────────────────────────────────
function connect() {
  if (socket && (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING)) {
    return;
  }
  clearTimeout(reconnectTimer);
  reconnectTimer = null;
  serverReady = false;
  setState('connecting');

  try {
    socket = new WebSocket(endpoint());
  } catch (error) {
    scheduleReconnect(`Could not create WebSocket: ${error.message}`);
    return;
  }

  socket.onopen = () => {
    reconnectAttempt = 0;
    sessionReleaseQueued = false;
    releaseSignalsSent.clear();
    showError('');
    send({ type: 'mode_preference', mode: 'stable' });
  };

  socket.onmessage = event => {
    try {
      handleMessage(JSON.parse(event.data));
    } catch {
      showError('Flow received an unreadable server message.');
    }
  };

  socket.onerror = () => {
    showError('Connection interrupted. Retrying when possible.');
  };

  socket.onclose = event => {
    socket = null;
    serverReady = false;
    streaming = false;
    if (captureWanted) {
      captureWanted = false;
      captureToken += 1;
      stopMicrophone();
    }
    resetCaptureControl({ invalidateGeneration: true });
    if (event.code === 4000) {
      // Another device holds an active session — do not auto-reconnect.
      maintainConnection = false;
      setState('error');
      showError('Flow is active on another device.');
      return;
    }
    if (maintainConnection && document.visibilityState === 'visible') {
      scheduleReconnect('Connection lost.');
    } else {
      setState('offline');
    }
  };
}

function scheduleReconnect(message) {
  if (!maintainConnection) {
    setState('offline', message);
    return;
  }
  if (reconnectAttempt >= RECONNECT_DELAYS.length) {
    setState('error', 'Reconnect paused');
    showError('Flow could not reconnect. Tap Reconnect to try again.');
    return;
  }
  const delay = RECONNECT_DELAYS[reconnectAttempt++];
  setState('offline', `${message} Retrying…`);
  clearTimeout(reconnectTimer);
  reconnectTimer = setTimeout(connect, delay);
}

function send(message) {
  if (!socketOpen()) return false;
  socket.send(JSON.stringify(message));
  return true;
}

function socketStateLabel() {
  if (!socket) return 'none';
  return ['CONNECTING', 'OPEN', 'CLOSING', 'CLOSED'][socket.readyState] || String(socket.readyState);
}

function signalSessionRelease(reason, { closeSocket = false } = {}) {
  const socketState = socketStateLabel();
  console.info(`[session_release] attempted reason=${reason} socket_state=${socketState}`);

  if (releaseSignalsSent.has(reason)) {
    console.info(`[session_release] queued reason=${reason} duplicate=true`);
  } else {
    releaseSignalsSent.add(reason);
  }

  if (sessionReleaseQueued) {
    console.info(`[session_release] queued reason=${reason} duplicate=true`);
    return true;
  }

  if (!socketOpen()) {
    console.info(`[session_release] skipped reason=socket_not_open socket_state=${socketState}`);
    return false;
  }

  socket.send(JSON.stringify({ type: 'session_release', reason }));
  sessionReleaseQueued = true;
  console.info(`[session_release] queued reason=${reason}`);

  if (closeSocket) {
    const socketToClose = socket;
    setTimeout(() => {
      if (socketToClose && socketToClose.readyState === WebSocket.OPEN) {
        socketToClose.close(1000, reason);
      }
    }, 150);
  }
  return true;
}

function signalPlaybackDone(reason, { playbackWasOwned = false } = {}) {
  if ((!ttsStarted && !playbackWasOwned) || ttsDoneSent || !socketOpen()) return false;
  socket.send(JSON.stringify({ type: 'tts_playback_done', reason }));
  ttsDoneSent = true;
  return true;
}

function cleanupPlaybackForLifecycle(reason) {
  playbackSuppressed = true;
  const playbackWasOwned = Boolean(
    activeAudioSource || playingAudio || audioQueue.length || ttsStarted
  );
  if (!playbackWasOwned) return true;

  ++playbackGeneration;
  const source = activeAudioSource;
  let cleanupConfirmed = true;

  if (source) {
    source.onended = null;
    try {
      source.stop(0);
    } catch (error) {
      cleanupConfirmed = false;
      console.warn(`[tts_playback_cleanup] unconfirmed reason=${reason} error=${error.message}`);
    }
  }

  audioQueue.length = 0;
  playingAudio = false;
  ttsStarted = false;
  activeAudioSource = null;

  if (source) {
    try {
      source.disconnect();
    } catch (error) {
      cleanupConfirmed = false;
      console.warn(`[tts_playback_cleanup] unconfirmed reason=${reason} error=${error.message}`);
    }
  }

  cleanupConfirmed = cleanupConfirmed &&
    activeAudioSource === null &&
    audioQueue.length === 0 &&
    !playingAudio &&
    !ttsStarted;

  if (!cleanupConfirmed) return false;
  signalPlaybackDone(reason, { playbackWasOwned: true });
  return true;
}

function sendAudio(base64) {
  if (!socketOpen() || !streaming) return false;
  socket.send(JSON.stringify({ type: 'audio', audio: base64 }));
  return true;
}

// ── Microphone ────────────────────────────────────────────────────────────────
//
// handleStream receives the streamPromise that was created synchronously inside
// the completed activation handler, so getUserMedia activation is already
// established when this async function runs.

async function handleStream(streamPromise) {
  const token = captureToken;
  const context = getAudioContext();
  try {
    const stream = await streamPromise;
    if (!captureWanted || token !== captureToken) {
      stream.getTracks().forEach(track => track.stop());
      return;
    }
    micStream = stream;
    micSource = context.createMediaStreamSource(stream);
    micProcessor = context.createScriptProcessor(4096, 1, 1);
    micProcessor.onaudioprocess = event => {
      if (!captureWanted) return;
      const pcm = pcm16Base64(resample(event.inputBuffer.getChannelData(0), context.sampleRate, WIRE_RATE));
      if (!streaming) {
        if (preconnectChunks.length < PRECONNECT_CHUNK_LIMIT) preconnectChunks.push(pcm);
        return;
      }
      sendAudio(pcm);
    };
    micSource.connect(micProcessor);
    micProcessor.connect(context.destination);
    maybeStartStreaming();
  } catch (error) {
    if (!captureWanted || token !== captureToken) return;
    captureWanted = false;
    captureToken += 1;
    stopMicrophone();
    resetCaptureControl({ invalidateGeneration: true });
    setState('ready');
    showError(`Microphone unavailable: ${error.message}`);
  }
}

function stopMicrophone() {
  streaming = false;
  preconnectChunks = [];
  if (micProcessor) {
    try { micProcessor.disconnect(); } catch {}
    micProcessor.onaudioprocess = null;
    micProcessor = null;
  }
  if (micSource) {
    try { micSource.disconnect(); } catch {}
    micSource = null;
  }
  if (micStream) {
    micStream.getTracks().forEach(track => track.stop());
    micStream = null;
  }
}

function maybeStartStreaming() {
  if (!captureWanted || !micProcessor || !serverReady || !socketOpen()) return;
  streaming = true;
  setState('listening');
  for (const chunk of preconnectChunks) sendAudio(chunk);
  preconnectChunks = [];
}

// ── Tap-toggle capture control ────────────────────────────────────────────────
//
// The completed button activation is the only normal input boundary. Audio APIs
// still run synchronously in that user gesture so Safari retains activation.

function resetCaptureControl({ invalidateGeneration = false } = {}) {
  clearTimeout(captureStopTimer);
  captureStopTimer = null;
  if (invalidateGeneration) captureGeneration += 1;
  capturePhase = 'idle';
  captureStartedAt = null;
  captureStopPending = false;
  captureCommitLocked = false;
  orbPress.classList.remove('is-pressed');
  orbBtn.setAttribute('aria-pressed', 'false');
}

function startCapture() {
  if (
    capturePhase !== 'idle' ||
    captureStopPending ||
    captureCommitLocked ||
    appState !== 'ready'
  ) {
    return false;
  }

  maintainConnection = true;
  if (!socketOpen() || !serverReady) {
    if (!socketOpen()) connect();
    return false;
  }

  let streamPromise;
  try {
    getAudioContext();
    streamPromise = navigator.mediaDevices.getUserMedia({
      audio: {
        channelCount: 1,
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true
      }
    });
  } catch (err) {
    showError(`Microphone unavailable: ${err.message}`);
    return false;
  }

  captureGeneration += 1;
  capturePhase = 'recording';
  captureStartedAt = monotonicNow();
  captureStopPending = false;
  captureCommitLocked = false;
  captureWanted = true;
  turnComplete = false;
  playbackSuppressed = false;
  ttsStarted = false;
  ttsDoneSent = false;
  pendingSource = { text: '', lang: '' };
  pendingTarget = { text: '', lang: '' };

  // Immediate visual feedback
  soundOrbPress();
  orbPress.classList.add('is-pressed');
  orbBtn.setAttribute('aria-pressed', 'true');
  showError('');
  setState('listening');

  handleStream(streamPromise);
  maybeStartStreaming();
  return true;
}

function commitCapture(generation, { requireStreaming = false } = {}) {
  if (
    generation !== captureGeneration ||
    capturePhase !== 'recording' ||
    !captureStopPending ||
    captureCommitLocked
  ) {
    return false;
  }

  clearTimeout(captureStopTimer);
  captureStopTimer = null;
  captureCommitLocked = true;
  captureStopPending = false;
  capturePhase = 'committing';
  captureWanted = false;
  captureToken += 1;

  soundOrbRelease();
  orbPress.classList.remove('is-pressed');
  orbBtn.setAttribute('aria-pressed', 'false');
  const hadStreaming = streaming;
  stopMicrophone();

  if ((!requireStreaming || hadStreaming) && send({ type: 'orb_released' })) {
    setState('processing');
    return true;
  }

  resetCaptureControl({ invalidateGeneration: true });
  if (serverReady && socketOpen()) setState('ready');
  return false;
}

function requestCaptureStop() {
  if (
    capturePhase !== 'recording' ||
    captureStopPending ||
    captureCommitLocked
  ) {
    return false;
  }

  captureStopPending = true;
  const generation = captureGeneration;
  const elapsedMs = captureStartedAt === null ? 0 : monotonicNow() - captureStartedAt;
  const minimumRemainingMs = Math.max(0, CAPTURE_MIN_DURATION_MS - elapsedMs);

  captureStopTimer = setTimeout(() => {
    if (
      generation !== captureGeneration ||
      capturePhase !== 'recording' ||
      !captureStopPending ||
      captureCommitLocked
    ) {
      return;
    }
    captureStopTimer = setTimeout(() => {
      commitCapture(generation);
    }, CAPTURE_TRAILING_GRACE_MS);
  }, minimumRemainingMs);
  return true;
}

function toggleCapture() {
  if (capturePhase === 'idle') return startCapture();
  if (capturePhase === 'recording') return requestCaptureStop();
  return false;
}

// Lifecycle release remains immediate so existing background behavior is not
// changed by the normal tap-toggle timing contract.
function release() {
  if (capturePhase !== 'recording' || captureCommitLocked) return false;
  clearTimeout(captureStopTimer);
  captureStopTimer = null;
  captureStopPending = true;
  return commitCapture(captureGeneration, { requireStreaming: true });
}

// ── Orb event listeners ───────────────────────────────────────────────────────

orbBtn.addEventListener('click', event => {
  event.preventDefault();
  if (suppressKeyboardClick) {
    suppressKeyboardClick = false;
    return;
  }
  toggleCapture();
});

// Prevent long-press context menu on mobile Safari
orbBtn.addEventListener('contextmenu', e => e.preventDefault());

// Keyboard (accessibility)
orbBtn.addEventListener('keydown', e => {
  if (e.key !== ' ' && e.key !== 'Enter') return;
  e.preventDefault();
  if (e.repeat) return;
  suppressKeyboardClick = true;
  toggleCapture();
});
orbBtn.addEventListener('keyup', e => {
  if (e.key !== ' ' && e.key !== 'Enter') return;
  e.preventDefault();
  clearTimeout(keyboardClickResetTimer);
  keyboardClickResetTimer = setTimeout(() => {
    suppressKeyboardClick = false;
  }, 0);
});

// ── Safety release ────────────────────────────────────────────────────────────
// Incoming call, app-switch, or any reason the window loses focus during capture.

window.addEventListener('blur', () => {
  release();
  signalSessionRelease('app_backgrounded');
});

document.addEventListener('visibilitychange', () => {
  if (document.hidden) {
    release();
    cleanupPlaybackForLifecycle('visibility_hidden');
    signalSessionRelease('visibility_hidden');
  } else {
    playbackSuppressed = false;
    if (maintainConnection && !socketOpen()) {
      reconnectAttempt = 0;
      connect();
    }
  }
});

// ── Last-turn action buttons ──────────────────────────────────────────────────
copyBtn.addEventListener('click', () => {
  if (!lastActionsText) return;
  navigator.clipboard.writeText(lastActionsText).then(() => {
    copyLabel.textContent = 'Copied';
    copyIcon.setAttribute('href', '#ico-check');
    copyBtn.classList.add('is-copied');
    setTimeout(() => {
      copyLabel.textContent = 'Copy';
      copyIcon.setAttribute('href', '#ico-copy');
      copyBtn.classList.remove('is-copied');
    }, 1500);
  }).catch(() => {});
});

shareBtn.addEventListener('click', () => {
  if (!lastActionsText) return;
  if (navigator.share) {
    navigator.share({ text: lastActionsText }).catch(() => {});
  } else {
    navigator.clipboard.writeText(lastActionsText).catch(() => {});
  }
});

// ── Reconnect ─────────────────────────────────────────────────────────────────
reconnectButton.addEventListener('click', () => {
  maintainConnection = true;
  reconnectAttempt = 0;
  sessionReleaseQueued = false;
  releaseSignalsSent.clear();
  showError('');
  connect();
});

// ── Network recovery ──────────────────────────────────────────────────────────
window.addEventListener('online', () => {
  if (maintainConnection && !socketOpen()) {
    reconnectAttempt = 0;
    connect();
  }
});

window.addEventListener('pagehide', () => {
  maintainConnection = false;
  captureWanted = false;
  captureToken += 1;
  clearTimeout(reconnectTimer);
  stopMicrophone();
  cleanupPlaybackForLifecycle('pagehide');
  // Signal before closing so the server can immediately grant the lease
  // to a waiting device rather than waiting for the TCP close to propagate.
  signalSessionRelease('pagehide', { closeSocket: true });
});

window.addEventListener('beforeunload', () => {
  signalSessionRelease('explicit_disconnect');
});

// ── Audio DSP ─────────────────────────────────────────────────────────────────
function resample(input, inputRate, outputRate) {
  if (inputRate === outputRate) return input;
  const ratio = inputRate / outputRate;
  const output = new Float32Array(Math.round(input.length / ratio));
  for (let i = 0; i < output.length; i++) {
    const pos  = i * ratio;
    const low  = Math.floor(pos);
    const high = Math.min(low + 1, input.length - 1);
    output[i]  = input[low] * (1 - (pos - low)) + input[high] * (pos - low);
  }
  return output;
}

function pcm16Base64(samples) {
  const ints = new Int16Array(samples.length);
  for (let i = 0; i < samples.length; i++) {
    const s  = Math.max(-1, Math.min(1, samples[i]));
    ints[i]  = s < 0 ? s * 32768 : s * 32767;
  }
  const bytes = new Uint8Array(ints.buffer);
  let binary = '';
  for (let start = 0; start < bytes.length; start += 8192) {
    binary += String.fromCharCode(...bytes.subarray(start, start + 8192));
  }
  return btoa(binary);
}

// ── TTS playback ──────────────────────────────────────────────────────────────
function enqueueAudio(base64) {
  if (playbackSuppressed) return false;
  ttsStarted = true;
  audioQueue.push(base64);
  if (!playingAudio) playNextAudio();
  return true;
}

function playNextAudio(generation = playbackGeneration) {
  if (generation !== playbackGeneration || playbackSuppressed) return;
  if (!audioQueue.length) {
    activeAudioSource = null;
    playingAudio = false;
    notifyTTSPlaybackDone();
    if (turnComplete) finishTurn();
    return;
  }
  playingAudio = true;
  const binary = atob(audioQueue.shift());
  const bytes  = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
  const pcm     = new Int16Array(bytes.buffer);
  const context = getAudioContext();
  const buffer  = context.createBuffer(1, pcm.length, WIRE_RATE);
  const channel = buffer.getChannelData(0);
  for (let i = 0; i < pcm.length; i++) channel[i] = pcm[i] / 32768;
  const source  = context.createBufferSource();
  source.buffer = buffer;
  source.connect(context.destination);
  activeAudioSource = source;
  source.onended = () => {
    if (activeAudioSource === source) activeAudioSource = null;
    if (generation !== playbackGeneration || playbackSuppressed) return;
    playNextAudio(generation);
  };
  source.start();
}

function notifyTTSPlaybackDone() {
  signalPlaybackDone('playback_complete');
}

function finishTurn() {
  if (pendingSource.text || pendingTarget.text) {
    addTurnCard(pendingSource, pendingTarget);
    pendingSource = { text: '', lang: '' };
    pendingTarget = { text: '', lang: '' };
  }
  turnComplete = false;
  ttsStarted   = false;
  resetCaptureControl();
  if (!captureWanted) setState(serverReady ? 'ready' : 'offline');
}

// ── Message handler ───────────────────────────────────────────────────────────
function handleMessage(message) {
  switch (message.type) {

    case 'flow.ready':
      serverReady = true;
      soundConnected();
      setState('ready');
      maybeStartStreaming();
      break;

    case 'speech_started':
      if (captureWanted) setState('listening');
      break;

    case 'speech_stopped':
      if (!captureWanted) setState('processing');
      break;

    case 'source_transcript': {
      const lang = message.diagnostics?.detected_lang || message.diagnostics?.stable_lang || '';
      updateDirection(lang);
      pendingSource = { text: message.text || '', lang: currentPair.sourceLang };
      if (message.text) {
        const truncated = message.text.length > 52
          ? message.text.slice(0, 52) + '…'
          : message.text;
        setOrbLabel(truncated, true);
      } else {
        setOrbLabel('HEARD YOU', false);
      }
      break;
    }

    case 'translation_done':
      pendingTarget = { text: message.text || '', lang: currentPair.targetLang };
      break;

    case 'tts_start':
      if (playbackSuppressed) break;
      ttsStarted = true;
      ttsDoneSent = false;
      setState('speaking');
      break;

    case 'audio_delta':
      setState('speaking');
      enqueueAudio(message.audio);
      break;

    case 'turn_complete':
      turnComplete = true;
      if (!playingAudio && !audioQueue.length) {
        notifyTTSPlaybackDone();
        finishTurn();
      }
      break;

    case 'ping':
      send({ type: 'pong' });
      break;

    case 'error':
      showError(message.message || 'Flow could not complete this turn.');
      if (!captureWanted && !playingAudio) {
        resetCaptureControl({ invalidateGeneration: true });
        setState('ready');
      }
      break;
  }
}

// ── Service worker ────────────────────────────────────────────────────────────
if ('serviceWorker' in navigator) {
  navigator.serviceWorker.register('/static/flow-pwa/sw.js', { scope: '/static/flow-pwa/' }).catch(() => {});
}

// ── Boot ──────────────────────────────────────────────────────────────────────
setState('ready');

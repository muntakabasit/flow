'use strict';

const WIRE_RATE = 24000;
const RECONNECT_DELAYS = [500, 1000, 2000, 4000, 8000, 15000];
const PRECONNECT_CHUNK_LIMIT = 12;

// ── DOM refs ─────────────────────────────────────────────────────────────────
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

let holdPointerId = null;
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
let ttsStarted = false;
let ttsDoneSent = false;
let turnComplete = false;

// ── Turn management ───────────────────────────────────────────────────────────
let turns = [];
let pendingSource = { text: '', lang: '' };
let pendingTarget = { text: '', lang: '' };
let currentPair = { sourceLang: 'English', targetLang: 'Portuguese', isPortuguese: false };
let lastActionsText = '';

// ── Helpers ───────────────────────────────────────────────────────────────────
function escHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function endpoint() {
  const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
  return `${protocol}//${location.host}/ws`;
}

function socketOpen() {
  return socket && socket.readyState === WebSocket.OPEN;
}

// ── State machine ─────────────────────────────────────────────────────────────
function setState(next, message) {
  appState = next;

  // Orb animation state
  orbWrap.dataset.state = next;

  // Icon
  const iconHref = next === 'processing' ? '#ico-wave'
                 : next === 'speaking'   ? '#ico-speaker'
                 : '#ico-mic';
  orbIconUse.setAttribute('href', iconHref);

  // Connection dot colour + pulse
  const connState = (next === 'ready' || next === 'listening' || next === 'processing' || next === 'speaking')
    ? 'online'
    : (next === 'connecting' || next === 'offline') ? 'reconnecting'
    : 'offline';
  connDot.dataset.conn = connState;
  connDot.classList.toggle('is-active', next !== 'ready' && connState !== 'offline');

  // Trust bar state label
  stateLabel.textContent = message || {
    ready:      'Ready',
    connecting: 'Connecting',
    listening:  'Listening',
    processing: 'Translating',
    speaking:   'Speaking',
    offline:    'Offline',
    error:      'Connection issue'
  }[next] || 'Ready';

  // Trust bar direction label
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

  // Direction over orb — visible during processing only
  dirOverOrb.classList.toggle('is-visible', next === 'processing');

  // Orb label (only set for non-transcript states — transcript updates come from source_transcript)
  if (next !== 'processing' && next !== 'listening') {
    setOrbLabel({
      ready:      'HOLD TO SPEAK',
      connecting: 'CONNECTING…',
      speaking:   'SPEAKING…',
      offline:    'RECONNECTING…',
      error:      'RECONNECT BELOW'
    }[next] || 'HOLD TO SPEAK', false);
  } else if (next === 'listening') {
    setOrbLabel('LISTENING…', false);
  }

  // Last turn actions: show in ready state when turns exist
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

// ── Direction / language pair ─────────────────────────────────────────────────
function updateDirection(sourceLanguage) {
  const isPortuguese = (sourceLanguage || '').toLowerCase().startsWith('pt');
  currentPair = {
    sourceLang:    isPortuguese ? 'Portuguese' : 'English',
    targetLang:    isPortuguese ? 'English'    : 'Portuguese',
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

// ── Audio context ─────────────────────────────────────────────────────────────
function getAudioContext() {
  if (!audioContext || audioContext.state === 'closed') {
    audioContext = new (window.AudioContext || window.webkitAudioContext)();
  }
  if (audioContext.state === 'suspended') audioContext.resume().catch(() => {});
  return audioContext;
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

  socket.onclose = () => {
    socket = null;
    serverReady = false;
    streaming = false;
    if (captureWanted) {
      captureWanted = false;
      captureToken += 1;
      stopMicrophone();
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

function sendAudio(base64) {
  if (!socketOpen() || !streaming) return false;
  socket.send(JSON.stringify({ type: 'audio', audio: base64 }));
  return true;
}

// ── Microphone / capture ──────────────────────────────────────────────────────
async function startCapture() {
  const token = ++captureToken;
  const context = getAudioContext();
  const streamPromise = navigator.mediaDevices.getUserMedia({
    audio: {
      channelCount: 1,
      echoCancellation: true,
      noiseSuppression: true,
      autoGainControl: true
    }
  });

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
    if (token !== captureToken) return;
    captureWanted = false;
    orbPress.classList.remove('is-pressed');
    orbBtn.setAttribute('aria-pressed', 'false');
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

// ── Hold interaction ──────────────────────────────────────────────────────────
function beginHold(event) {
  if (event.pointerType === 'mouse' && event.button !== 0) return;
  event.preventDefault();
  if (captureWanted) return;
  holdPointerId = Number.isInteger(event.pointerId) ? event.pointerId : null;
  if (holdPointerId !== null) orbBtn.setPointerCapture?.(holdPointerId);
  captureWanted = true;
  maintainConnection = true;
  turnComplete = false;
  ttsStarted = false;
  ttsDoneSent = false;
  pendingSource = { text: '', lang: '' };
  pendingTarget = { text: '', lang: '' };
  orbPress.classList.add('is-pressed');
  orbBtn.setAttribute('aria-pressed', 'true');
  showError('');
  setState(serverReady && socketOpen() ? 'listening' : 'connecting');
  startCapture();
  connect();
  maybeStartStreaming();
}

function endHold(event) {
  if (holdPointerId !== null && event.pointerId !== undefined && event.pointerId !== holdPointerId) return;
  if (!captureWanted) return;
  event?.preventDefault?.();
  holdPointerId = null;
  captureWanted = false;
  ++captureToken;
  orbPress.classList.remove('is-pressed');
  orbBtn.setAttribute('aria-pressed', 'false');
  const hadStreaming = streaming;
  stopMicrophone();
  if (hadStreaming && send({ type: 'orb_released' })) {
    setState('processing');
  } else if (serverReady && socketOpen()) {
    setState('ready');
  }
}

// ── Audio DSP ─────────────────────────────────────────────────────────────────
function resample(input, inputRate, outputRate) {
  if (inputRate === outputRate) return input;
  const ratio = inputRate / outputRate;
  const output = new Float32Array(Math.round(input.length / ratio));
  for (let index = 0; index < output.length; index++) {
    const position = index * ratio;
    const low = Math.floor(position);
    const high = Math.min(low + 1, input.length - 1);
    output[index] = input[low] * (1 - (position - low)) + input[high] * (position - low);
  }
  return output;
}

function pcm16Base64(samples) {
  const ints = new Int16Array(samples.length);
  for (let index = 0; index < samples.length; index++) {
    const sample = Math.max(-1, Math.min(1, samples[index]));
    ints[index] = sample < 0 ? sample * 32768 : sample * 32767;
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
  ttsStarted = true;
  ttsDoneSent = false;
  audioQueue.push(base64);
  if (!playingAudio) playNextAudio();
}

function playNextAudio() {
  if (!audioQueue.length) {
    playingAudio = false;
    notifyTTSPlaybackDone();
    if (turnComplete) finishTurn();
    return;
  }
  playingAudio = true;
  const binary = atob(audioQueue.shift());
  const bytes = new Uint8Array(binary.length);
  for (let index = 0; index < binary.length; index++) bytes[index] = binary.charCodeAt(index);
  const pcm = new Int16Array(bytes.buffer);
  const context = getAudioContext();
  const buffer = context.createBuffer(1, pcm.length, WIRE_RATE);
  const channel = buffer.getChannelData(0);
  for (let index = 0; index < pcm.length; index++) channel[index] = pcm[index] / 32768;
  const source = context.createBufferSource();
  source.buffer = buffer;
  source.connect(context.destination);
  source.onended = playNextAudio;
  source.start();
}

function notifyTTSPlaybackDone() {
  if (!ttsStarted || ttsDoneSent) return;
  ttsDoneSent = true;
  send({ type: 'tts_playback_done' });
}

function finishTurn() {
  if (pendingSource.text || pendingTarget.text) {
    addTurnCard(pendingSource, pendingTarget);
    pendingSource = { text: '', lang: '' };
    pendingTarget = { text: '', lang: '' };
  }
  turnComplete = false;
  ttsStarted = false;
  if (!captureWanted) setState(serverReady ? 'ready' : 'offline');
}

// ── Message handler ───────────────────────────────────────────────────────────
function handleMessage(message) {
  switch (message.type) {

    case 'flow.ready':
      serverReady = true;
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
      const sourceLanguage = message.diagnostics?.detected_lang || message.diagnostics?.stable_lang || '';
      updateDirection(sourceLanguage);
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
      ttsStarted = true;
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
      if (!captureWanted && !playingAudio) setState('ready');
      break;
  }
}

// ── Orb event listeners ───────────────────────────────────────────────────────
orbBtn.addEventListener('pointerdown', beginHold);
orbBtn.addEventListener('pointerup', endHold);
orbBtn.addEventListener('pointercancel', endHold);
orbBtn.addEventListener('lostpointercapture', endHold);
orbBtn.addEventListener('contextmenu', event => event.preventDefault());
orbBtn.addEventListener('keydown', event => {
  if ((event.key === ' ' || event.key === 'Enter') && !event.repeat) beginHold(event);
});
orbBtn.addEventListener('keyup', event => {
  if (event.key === ' ' || event.key === 'Enter') endHold(event);
});

// ── Last turn action buttons ──────────────────────────────────────────────────
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

// ── Reconnect button ──────────────────────────────────────────────────────────
reconnectButton.addEventListener('click', () => {
  maintainConnection = true;
  reconnectAttempt = 0;
  showError('');
  connect();
});

// ── Lifecycle ─────────────────────────────────────────────────────────────────
document.addEventListener('visibilitychange', () => {
  if (document.visibilityState === 'visible' && maintainConnection && !socketOpen()) {
    reconnectAttempt = 0;
    connect();
  }
});

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
  if (socketOpen()) socket.close(1000, 'page hidden');
});

// ── Service worker ────────────────────────────────────────────────────────────
if ('serviceWorker' in navigator) {
  navigator.serviceWorker.register('./sw.js', { scope: './' }).catch(() => {});
}

// ── Boot ──────────────────────────────────────────────────────────────────────
setState('ready');

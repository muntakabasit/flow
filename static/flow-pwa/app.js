'use strict';

const WIRE_RATE = 24000;
const RECONNECT_DELAYS = [500, 1000, 2000, 4000, 8000, 15000];
const PRECONNECT_CHUNK_LIMIT = 12;

const holdButton = document.getElementById('holdButton');
const statusDot = document.getElementById('statusDot');
const statusCopy = document.getElementById('statusCopy');
const direction = document.getElementById('direction');
const actionStatus = document.getElementById('actionStatus');
const reconnectButton = document.getElementById('reconnectButton');
const sourceLabel = document.getElementById('sourceLabel');
const sourceText = document.getElementById('sourceText');
const translationLabel = document.getElementById('translationLabel');
const translationText = document.getElementById('translationText');
const errorText = document.getElementById('errorText');

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

function endpoint() {
  const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
  return `${protocol}//${location.host}/ws`;
}

function socketOpen() {
  return socket && socket.readyState === WebSocket.OPEN;
}

function setState(next, message) {
  appState = next;
  holdButton.dataset.state = next;
  statusDot.dataset.state = next;
  const copy = message || {
    ready: 'Ready',
    connecting: 'Connecting',
    listening: 'Listening',
    processing: 'Translating',
    speaking: 'Speaking',
    offline: 'Offline',
    error: 'Connection issue'
  }[next] || 'Ready';
  statusCopy.textContent = copy;
  actionStatus.textContent = {
    ready: 'Press and hold. Release to translate.',
    connecting: 'Keep holding while Flow connects.',
    listening: 'Listening. Release when you finish.',
    processing: 'Translating your final turn.',
    speaking: 'Playing translation.',
    offline: 'Flow will retry a limited number of times.',
    error: 'Tap reconnect, then hold to speak.'
  }[next] || '';
  reconnectButton.hidden = next !== 'error';
}

function showError(message = '') {
  errorText.textContent = message;
}

function setPanelText(element, value, placeholder = false) {
  element.textContent = value;
  element.classList.toggle('placeholder', placeholder);
}

function updateDirection(sourceLanguage) {
  const isPortuguese = (sourceLanguage || '').toLowerCase().startsWith('pt');
  direction.textContent = isPortuguese ? 'PT-BR / EN' : 'EN / PT-BR';
  sourceLabel.textContent = isPortuguese ? 'Portuguese' : 'English';
  translationLabel.textContent = isPortuguese ? 'English' : 'Portuguese';
}

function getAudioContext() {
  if (!audioContext || audioContext.state === 'closed') {
    audioContext = new (window.AudioContext || window.webkitAudioContext)();
  }
  if (audioContext.state === 'suspended') audioContext.resume().catch(() => {});
  return audioContext;
}

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
  setState('offline', `${message} Retrying...`);
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

function beginHold(event) {
  if (event.pointerType === 'mouse' && event.button !== 0) return;
  event.preventDefault();
  if (captureWanted) return;
  holdPointerId = Number.isInteger(event.pointerId) ? event.pointerId : null;
  if (holdPointerId !== null) holdButton.setPointerCapture?.(holdPointerId);
  captureWanted = true;
  maintainConnection = true;
  turnComplete = false;
  ttsStarted = false;
  ttsDoneSent = false;
  setPanelText(sourceText, 'Listening for speech...', true);
  setPanelText(translationText, 'Your final translation appears here.', true);
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
  const hadStreaming = streaming;
  stopMicrophone();
  if (hadStreaming && send({ type: 'orb_released' })) {
    setState('processing');
  } else if (serverReady && socketOpen()) {
    setState('ready');
  }
}

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
  turnComplete = false;
  ttsStarted = false;
  if (!captureWanted) setState(serverReady ? 'ready' : 'offline');
}

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
      setPanelText(sourceText, message.text || 'No source speech received.', !message.text);
      break;
    }
    case 'translation_done':
      setPanelText(translationText, message.text || 'No final translation received.', !message.text);
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

holdButton.addEventListener('pointerdown', beginHold);
holdButton.addEventListener('pointerup', endHold);
holdButton.addEventListener('pointercancel', endHold);
holdButton.addEventListener('lostpointercapture', endHold);
holdButton.addEventListener('contextmenu', event => event.preventDefault());
holdButton.addEventListener('keydown', event => {
  if ((event.key === ' ' || event.key === 'Enter') && !event.repeat) beginHold(event);
});
holdButton.addEventListener('keyup', event => {
  if (event.key === ' ' || event.key === 'Enter') endHold(event);
});

reconnectButton.addEventListener('click', () => {
  maintainConnection = true;
  reconnectAttempt = 0;
  showError('');
  connect();
});

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

if ('serviceWorker' in navigator) {
  navigator.serviceWorker.register('./sw.js', { scope: './' }).catch(() => {});
}

setState('ready');

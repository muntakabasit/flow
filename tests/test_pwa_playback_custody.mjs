import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';

const appSource = fs.readFileSync(
  new URL('../static/flow-pwa/app.js', import.meta.url),
  'utf8'
);

function loadApp({ failSourceStop = false } = {}) {
  class FakeElement {
    constructor() {
      this.dataset = {};
      this.textContent = '';
      this.innerHTML = '';
      this.hidden = false;
      this.listeners = new Map();
      this.classList = { add() {}, remove() {}, toggle() {} };
    }

    addEventListener(type, callback) { this.listeners.set(type, callback); }
    appendChild() {}
    setAttribute() {}
    setPointerCapture() {}
  }

  class FakeAudioSource {
    static instances = [];

    constructor() {
      this.onended = null;
      this.started = false;
      this.stopped = false;
      this.disconnected = false;
      this.stopCalls = 0;
      FakeAudioSource.instances.push(this);
    }

    connect() {}
    start() { this.started = true; }
    stop() {
      ++this.stopCalls;
      if (failSourceStop) throw new Error('stop failed');
      this.stopped = true;
    }
    disconnect() { this.disconnected = true; }
    end() { this.onended?.(); }
  }

  class FakeAudioContext {
    constructor() {
      this.state = 'running';
      this.sampleRate = 48_000;
      this.destination = {};
    }

    resume() { return Promise.resolve(); }
    createBuffer(_, length) {
      return { getChannelData: () => new Float32Array(length) };
    }
    createBufferSource() { return new FakeAudioSource(); }
    createGain() {
      return {
        gain: {
          setValueAtTime() {},
          exponentialRampToValueAtTime() {}
        },
        connect() {}
      };
    }
    createOscillator() {
      return {
        frequency: {
          setValueAtTime() {},
          exponentialRampToValueAtTime() {}
        },
        connect() {},
        start() {},
        stop() {}
      };
    }
  }

  class FakeWebSocket {
    static CONNECTING = 0;
    static OPEN = 1;
    static CLOSING = 2;
    static CLOSED = 3;
    static instances = [];

    constructor(url) {
      this.url = url;
      this.readyState = FakeWebSocket.CONNECTING;
      this.sent = [];
      this.playbackDoneSnapshots = [];
      FakeWebSocket.instances.push(this);
    }

    send(payload) {
      const message = JSON.parse(payload);
      this.sent.push(message);
      if (message.type === 'tts_playback_done') {
        this.playbackDoneSnapshots.push(context.__flowPlaybackTest.state());
      }
    }

    open() {
      this.readyState = FakeWebSocket.OPEN;
      this.onopen?.();
    }

    close() {
      this.readyState = FakeWebSocket.CLOSED;
      this.onclose?.({ code: 1000 });
    }
  }

  const ids = [
    'orbBtn', 'orbPress', 'orbWrap', 'orbIconUse', 'orbLabel', 'connDot',
    'stateLabel', 'dirLabel', 'dirOverOrb', 'panel', 'emptyState', 'turnsList',
    'lastActions', 'lastSrc', 'lastTgt', 'copyBtn', 'copyIcon', 'copyLabel',
    'shareBtn', 'errorText', 'reconnectButton'
  ];
  const elements = new Map(ids.map(id => [id, new FakeElement()]));
  const documentListeners = new Map();
  const windowListeners = new Map();
  const storage = new Map();

  const document = {
    hidden: false,
    visibilityState: 'visible',
    getElementById(id) { return elements.get(id); },
    createElement() { return new FakeElement(); },
    addEventListener(type, callback) { documentListeners.set(type, callback); }
  };

  const context = vm.createContext({
    console,
    WebSocket: FakeWebSocket,
    window: {
      AudioContext: FakeAudioContext,
      webkitAudioContext: FakeAudioContext,
      addEventListener(type, callback) { windowListeners.set(type, callback); }
    },
    document,
    navigator: {
      clipboard: { writeText: () => Promise.resolve() },
      mediaDevices: { getUserMedia: () => Promise.resolve({ getTracks: () => [] }) },
      serviceWorker: { register: () => Promise.resolve() }
    },
    sessionStorage: {
      getItem(key) { return storage.get(key) ?? null; },
      setItem(key, value) { storage.set(key, value); }
    },
    location: { protocol: 'https:', host: 'flow.flowbasit.com' },
    setTimeout: () => 1,
    clearTimeout() {},
    btoa: value => Buffer.from(value, 'binary').toString('base64'),
    atob: value => Buffer.from(value, 'base64').toString('binary'),
    Float32Array,
    Int16Array,
    Uint8Array,
    Math,
    Date,
    JSON,
    String,
    Number
  });

  vm.runInContext(`${appSource}\n;globalThis.__flowPlaybackTest = {
    connect,
    handleMessage,
    state: () => ({
      queueLength: audioQueue.length,
      playingAudio,
      activeAudioSource,
      playbackSuppressed,
      ttsStarted,
      ttsDoneSent
    })
  };`, context, { filename: 'static/flow-pwa/app.js' });

  context.__flowPlaybackTest.connect();
  const socket = FakeWebSocket.instances[0];
  socket.open();

  return {
    api: context.__flowPlaybackTest,
    document,
    documentListeners,
    windowListeners,
    socket,
    sources: FakeAudioSource.instances
  };
}

function audioChunk() {
  return Buffer.alloc(4).toString('base64');
}

function playbackDoneMessages(socket) {
  return socket.sent.filter(message => message.type === 'tts_playback_done');
}

{
  const app = loadApp();
  app.api.handleMessage({ type: 'tts_start' });
  app.api.handleMessage({ type: 'audio_delta', audio: audioChunk() });
  app.api.handleMessage({ type: 'audio_delta', audio: audioChunk() });

  const activeSource = app.sources[0];
  const staleOnended = activeSource.onended;
  assert.equal(app.api.state().queueLength, 1, 'second chunk is queued');

  app.document.hidden = true;
  app.document.visibilityState = 'hidden';
  app.documentListeners.get('visibilitychange')();

  const state = app.api.state();
  assert.equal(activeSource.stopCalls, 1, 'active source is stopped exactly once');
  assert.equal(activeSource.stopped, true, 'active source stop succeeds');
  assert.equal(activeSource.disconnected, true, 'active source is disconnected');
  assert.equal(state.activeAudioSource, null, 'active source custody is cleared');
  assert.equal(state.queueLength, 0, 'queued audio is cleared');
  assert.equal(state.playingAudio, false, 'playing flag is cleared');
  assert.equal(state.ttsStarted, false, 'TTS playback state is cleared');
  assert.equal(state.playbackSuppressed, true, 'late hidden audio is suppressed');

  const done = playbackDoneMessages(app.socket);
  assert.equal(done.length, 1, 'background cleanup reports playback done once');
  assert.equal(done[0].reason, 'visibility_hidden');
  assert.deepEqual(
    app.socket.playbackDoneSnapshots.map(snapshot => ({
      queueLength: snapshot.queueLength,
      playingAudio: snapshot.playingAudio,
      activeAudioSource: snapshot.activeAudioSource,
      ttsStarted: snapshot.ttsStarted
    })),
    [{ queueLength: 0, playingAudio: false, activeAudioSource: null, ttsStarted: false }],
    'playback_done enters the socket only after playback effects are gone'
  );

  staleOnended();
  app.api.handleMessage({ type: 'audio_delta', audio: audioChunk() });
  assert.equal(app.sources.length, 1, 'stale callback and late audio cannot restart playback');

  app.windowListeners.get('pagehide')();
  assert.equal(playbackDoneMessages(app.socket).length, 1, 'pagehide cleanup is idempotent');
}

{
  const app = loadApp({ failSourceStop: true });
  app.api.handleMessage({ type: 'tts_start' });
  app.api.handleMessage({ type: 'audio_delta', audio: audioChunk() });
  app.document.hidden = true;
  app.document.visibilityState = 'hidden';
  app.documentListeners.get('visibilitychange')();

  assert.equal(playbackDoneMessages(app.socket).length, 0,
    'unconfirmed source stop does not release server playback custody');
  assert.equal(app.api.state().queueLength, 0, 'failed cleanup still abandons queued client audio');
  assert.equal(app.api.state().playingAudio, false, 'failed cleanup clears local playing state');
}

{
  const app = loadApp();
  app.api.handleMessage({ type: 'tts_start' });
  app.api.handleMessage({ type: 'audio_delta', audio: audioChunk() });
  app.api.handleMessage({ type: 'audio_delta', audio: audioChunk() });
  app.api.handleMessage({ type: 'turn_complete' });

  app.sources[0].end();
  assert.equal(app.sources.length, 2, 'normal playback advances to queued audio');
  app.sources[1].end();

  assert.equal(playbackDoneMessages(app.socket).length, 1,
    'normal queue drain reports playback completion once');
  assert.equal(playbackDoneMessages(app.socket)[0].reason, 'playback_complete');
  assert.equal(app.api.state().queueLength, 0);
  assert.equal(app.api.state().playingAudio, false);
  assert.equal(app.api.state().activeAudioSource, null);
}

console.log('PASS: lifecycle playback custody and normal drain are deterministic');

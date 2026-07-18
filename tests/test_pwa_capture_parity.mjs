import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';

const appSource = fs.readFileSync(
  new URL('../static/flow-pwa/app.js', import.meta.url),
  'utf8'
);

function createScheduler() {
  let now = 0;
  let nextId = 1;
  const timers = new Map();

  function setTimeout(callback, delay = 0) {
    const id = nextId++;
    timers.set(id, { callback, at: now + Math.max(0, Number(delay) || 0) });
    return id;
  }

  function clearTimeout(id) {
    timers.delete(id);
  }

  function advance(ms) {
    const target = now + ms;
    while (true) {
      const due = [...timers.entries()]
        .filter(([, timer]) => timer.at <= target)
        .sort((a, b) => a[1].at - b[1].at || a[0] - b[0])[0];
      if (!due) break;
      const [id, timer] = due;
      timers.delete(id);
      now = timer.at;
      timer.callback();
    }
    now = target;
  }

  return {
    setTimeout,
    clearTimeout,
    advance,
    now: () => now,
    callbacks: () => [...timers.values()].map(timer => timer.callback)
  };
}

function loadApp() {
  const scheduler = createScheduler();
  let getUserMediaCalls = 0;

  class FakeElement {
    constructor() {
      this.dataset = {};
      this.textContent = '';
      this.innerHTML = '';
      this.hidden = false;
      this.listeners = new Map();
      this.attributes = new Map();
      this.classList = { add() {}, remove() {}, toggle() {} };
    }

    addEventListener(type, callback) { this.listeners.set(type, callback); }
    appendChild() {}
    setAttribute(name, value) { this.attributes.set(name, value); }
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
      FakeWebSocket.instances.push(this);
    }

    send(payload) { this.sent.push(JSON.parse(payload)); }
    open() {
      this.readyState = FakeWebSocket.OPEN;
      this.onopen?.();
    }
    close(code = 1000) {
      this.readyState = FakeWebSocket.CLOSED;
      this.onclose?.({ code });
    }
  }

  const tracks = [];
  const processors = [];

  class FakeAudioContext {
    constructor() {
      this.state = 'running';
      this.sampleRate = 48_000;
      this.currentTime = 0;
      this.destination = {};
    }

    resume() { return Promise.resolve(); }
    createMediaStreamSource() { return { connect() {}, disconnect() {} }; }
    createScriptProcessor() {
      const processor = { connect() {}, disconnect() {}, onaudioprocess: null };
      processors.push(processor);
      return processor;
    }
    createBuffer(_, length) {
      return { getChannelData: () => new Float32Array(length) };
    }
    createBufferSource() {
      return { connect() {}, disconnect() {}, start() {}, stop() {} };
    }
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

  const ids = [
    'orbBtn', 'orbPress', 'orbWrap', 'orbIconUse', 'orbLabel', 'connDot',
    'stateLabel', 'dirLabel', 'dirOverOrb', 'panel', 'emptyState', 'turnsList',
    'lastActions', 'lastSrc', 'lastTgt', 'copyBtn', 'copyIcon', 'copyLabel',
    'shareBtn', 'errorText', 'reconnectButton'
  ];
  const elements = new Map(ids.map(id => [id, new FakeElement()]));
  const storage = new Map();

  const context = vm.createContext({
    console,
    WebSocket: FakeWebSocket,
    window: {
      AudioContext: FakeAudioContext,
      webkitAudioContext: FakeAudioContext,
      addEventListener() {}
    },
    document: {
      hidden: false,
      visibilityState: 'visible',
      getElementById(id) { return elements.get(id); },
      createElement() { return new FakeElement(); },
      addEventListener() {}
    },
    navigator: {
      clipboard: { writeText: () => Promise.resolve() },
      mediaDevices: {
        getUserMedia() {
          getUserMediaCalls += 1;
          const track = { stopped: false, stop() { this.stopped = true; } };
          tracks.push(track);
          return Promise.resolve({ getTracks: () => [track] });
        }
      },
      serviceWorker: { register: () => Promise.resolve() }
    },
    sessionStorage: {
      getItem(key) { return storage.get(key) ?? null; },
      setItem(key, value) { storage.set(key, value); }
    },
    location: { protocol: 'https:', host: 'flow.flowbasit.com' },
    performance: { now: scheduler.now },
    setTimeout: scheduler.setTimeout,
    clearTimeout: scheduler.clearTimeout,
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

  vm.runInContext(`${appSource}\n;globalThis.__flowCaptureTest = {
    connect,
    handleMessage,
    markServerReady: () => { serverReady = true; setState('ready'); },
    state: () => ({
      appState,
      capturePhase,
      captureGeneration,
      captureWanted,
      captureStopPending,
      captureCommitLocked,
      streaming
    })
  };`, context, { filename: 'static/flow-pwa/app.js' });

  const orb = elements.get('orbBtn');
  const event = overrides => ({
    key: '',
    repeat: false,
    preventDefault() {},
    ...overrides
  });

  return {
    api: context.__flowCaptureTest,
    scheduler,
    orb,
    tracks,
    processors,
    sockets: FakeWebSocket.instances,
    getUserMediaCalls: () => getUserMediaCalls,
    click: () => orb.listeners.get('click')(event()),
    keydown: (key, repeat = false) => orb.listeners.get('keydown')(event({ key, repeat })),
    keyup: key => orb.listeners.get('keyup')(event({ key })),
    flush: () => new Promise(resolve => setImmediate(resolve))
  };
}

function readyApp(app) {
  app.api.connect();
  const socket = app.sockets[0];
  socket.open();
  app.api.markServerReady();
  return socket;
}

function messages(socket, type) {
  return socket.sent.filter(message => message.type === type);
}

// FLOW_CAPTURE_001, 002, 003, 004, 005, 007
{
  const app = loadApp();
  const socket = readyApp(app);

  app.click();
  await app.flush();
  assert.equal(app.api.state().capturePhase, 'recording');
  assert.equal(app.api.state().captureWanted, true);
  assert.equal(app.api.state().streaming, true);
  assert.equal(app.api.state().appState, 'listening');
  assert.equal(app.getUserMediaCalls(), 1);

  assert.equal(app.orb.listeners.has('pointerup'), false);
  assert.equal(app.orb.listeners.has('pointercancel'), false);
  assert.equal(app.orb.listeners.has('lostpointercapture'), false);
  assert.equal(messages(socket, 'orb_released').length, 0);

  app.click();
  assert.equal(app.api.state().captureStopPending, true);
  assert.equal(app.api.state().captureWanted, true);
  app.click();
  assert.equal(messages(socket, 'orb_released').length, 0);

  app.scheduler.advance(799);
  assert.equal(app.api.state().captureWanted, true);
  assert.equal(app.tracks[0].stopped, false);
  assert.equal(messages(socket, 'orb_released').length, 0);

  app.scheduler.advance(1);
  assert.equal(messages(socket, 'orb_released').length, 0);
  app.scheduler.advance(149);
  assert.equal(app.tracks[0].stopped, false);
  assert.equal(messages(socket, 'orb_released').length, 0);

  app.scheduler.advance(1);
  assert.equal(app.tracks[0].stopped, true);
  assert.equal(app.api.state().capturePhase, 'committing');
  assert.equal(app.api.state().captureCommitLocked, true);
  assert.equal(app.api.state().appState, 'processing');
  assert.equal(messages(socket, 'orb_released').length, 1);

  app.click();
  assert.equal(app.getUserMediaCalls(), 1);
  assert.equal(messages(socket, 'orb_released').length, 1);
}

// FLOW_CAPTURE_005: a stop requested after the minimum still receives 150 ms grace.
{
  const app = loadApp();
  const socket = readyApp(app);
  app.click();
  await app.flush();
  app.scheduler.advance(1000);
  app.click();
  app.scheduler.advance(149);
  assert.equal(messages(socket, 'orb_released').length, 0);
  assert.equal(app.tracks[0].stopped, false);
  app.scheduler.advance(1);
  assert.equal(messages(socket, 'orb_released').length, 1);
  assert.equal(app.tracks[0].stopped, true);
}

// FLOW_CAPTURE_006: rapid double tap creates one bounded turn and one commit.
{
  const app = loadApp();
  const socket = readyApp(app);
  app.click();
  app.click();
  app.click();
  await app.flush();
  app.scheduler.advance(950);
  app.scheduler.advance(5000);
  assert.equal(messages(socket, 'orb_released').length, 1);
  assert.equal(app.getUserMediaCalls(), 1);
}

// FLOW_CAPTURE_008 and 009: committing, processing, and speaking reject capture.
{
  const app = loadApp();
  const socket = readyApp(app);
  app.click();
  await app.flush();
  app.click();
  app.scheduler.advance(950);
  app.click();
  assert.equal(app.getUserMediaCalls(), 1);
  app.api.handleMessage({ type: 'tts_start' });
  assert.equal(app.api.state().appState, 'speaking');
  app.click();
  assert.equal(app.getUserMediaCalls(), 1);
  assert.equal(messages(socket, 'orb_released').length, 1);
}

// FLOW_CAPTURE_010: keydown toggles; keyup and repeated keydown never submit.
{
  const app = loadApp();
  const socket = readyApp(app);
  app.keydown(' ', false);
  await app.flush();
  app.keydown(' ', true);
  app.keyup(' ');
  assert.equal(app.api.state().capturePhase, 'recording');
  assert.equal(messages(socket, 'orb_released').length, 0);

  app.keydown('Enter', false);
  app.keyup('Enter');
  app.scheduler.advance(950);
  assert.equal(messages(socket, 'orb_released').length, 1);
}

// Capture cannot begin before both the WebSocket and server readiness are true.
{
  const app = loadApp();
  app.click();
  assert.equal(app.api.state().capturePhase, 'idle');
  assert.equal(app.getUserMediaCalls(), 0);
  const socket = app.sockets[0];
  socket.open();
  app.click();
  assert.equal(app.getUserMediaCalls(), 0);
  app.api.markServerReady();
  app.click();
  assert.equal(app.getUserMediaCalls(), 1);
}

// A deferred callback captured before disconnect cannot commit a stale generation.
{
  const app = loadApp();
  const socket = readyApp(app);
  app.click();
  await app.flush();
  app.click();
  const staleMinimumCallback = app.scheduler.callbacks()[0];
  socket.close();
  staleMinimumCallback();
  app.scheduler.advance(1000);
  assert.equal(messages(socket, 'orb_released').length, 0);
  assert.equal(app.api.state().capturePhase, 'idle');
}

console.log('PASS: FLOW_CAPTURE_001 through FLOW_CAPTURE_010');

import Foundation
import AVFoundation
import AudioToolbox
import UIKit
import Network

// MARK: - State Machine (FLOW_SPEC §3) ----------------------------------------
//
// READY → LISTENING → PROCESSING → READY
//
// Linear. No branching. No skipped states. Always returns to READY.
// Server is source of truth for turn boundaries (spec §12).

enum AppState: Equatable {
    case ready
    case listening
    case processing
    case speaking
}

enum ConnStatus: Equatable {
    case online        // WebSocket open
    case reconnecting  // dropped, auto-retry in progress
    case offline       // never connected or permanently dead
}

final class ReleaseFeedback {
    static let shared = ReleaseFeedback()

    private let haptic = UIImpactFeedbackGenerator(style: .light)
    private let player: AVAudioPlayer?

    private init() {
        player = Self.buildPlayer()
        player?.prepareToPlay()
        haptic.prepare()
    }

    func fire() {
        haptic.impactOccurred()
        haptic.prepare()
        guard let player else { return }
        if player.isPlaying { player.stop() }
        player.currentTime = 0
        player.play()
    }

    private static func buildPlayer() -> AVAudioPlayer? {
        let sampleRate = 22_050
        let duration = 0.07
        let sampleCount = Int(Double(sampleRate) * duration)
        let frequency = 820.0
        let fadeIn = Int(Double(sampleRate) * 0.005)
        let fadeOut = Int(Double(sampleRate) * 0.018)

        var pcm = [Int16](repeating: 0, count: sampleCount)
        for i in 0..<sampleCount {
            let t = Double(i) / Double(sampleRate)
            let rampIn = i < fadeIn ? Double(i) / Double(max(fadeIn, 1)) : 1.0
            let rampOutStart = sampleCount - fadeOut
            let rampOut = i >= rampOutStart ? Double(sampleCount - i) / Double(max(fadeOut, 1)) : 1.0
            let envelope = rampIn * rampOut
            let sample = sin(2 * .pi * frequency * t) * 0.22 * envelope
            pcm[i] = Int16(max(-1.0, min(1.0, sample)) * Double(Int16.max))
        }

        let dataBytes = sampleCount * MemoryLayout<Int16>.size
        var wav = Data()

        func u32le(_ value: UInt32) -> [UInt8] {
            withUnsafeBytes(of: value.littleEndian) { Array($0) }
        }

        func u16le(_ value: UInt16) -> [UInt8] {
            withUnsafeBytes(of: value.littleEndian) { Array($0) }
        }

        wav.append(contentsOf: "RIFF".utf8)
        wav.append(contentsOf: u32le(UInt32(dataBytes + 36)))
        wav.append(contentsOf: "WAVE".utf8)
        wav.append(contentsOf: "fmt ".utf8)
        wav.append(contentsOf: u32le(16))
        wav.append(contentsOf: u16le(1))
        wav.append(contentsOf: u16le(1))
        wav.append(contentsOf: u32le(UInt32(sampleRate)))
        wav.append(contentsOf: u32le(UInt32(sampleRate * 2)))
        wav.append(contentsOf: u16le(2))
        wav.append(contentsOf: u16le(16))
        wav.append(contentsOf: "data".utf8)
        wav.append(contentsOf: u32le(UInt32(dataBytes)))

        for sample in pcm {
            wav.append(contentsOf: u16le(UInt16(bitPattern: sample)))
        }

        let player = try? AVAudioPlayer(data: wav)
        player?.volume = 1.0
        return player
    }
}

final class ProcessingFeedback {
    static let shared = ProcessingFeedback()

    private let player: AVAudioPlayer?

    private init() {
        player = Self.buildPlayer()
        player?.prepareToPlay()
    }

    func fire() {
        guard let player else { return }
        if player.isPlaying { player.stop() }
        player.currentTime = 0
        player.play()
    }

    func stop() {
        player?.stop()
    }

    private static func buildPlayer() -> AVAudioPlayer? {
        let sampleRate = 22_050
        let duration = 0.065
        let sampleCount = Int(Double(sampleRate) * duration)
        let frequency = 560.0
        let fadeIn = Int(Double(sampleRate) * 0.008)
        let fadeOut = Int(Double(sampleRate) * 0.026)

        var pcm = [Int16](repeating: 0, count: sampleCount)
        for i in 0..<sampleCount {
            let t = Double(i) / Double(sampleRate)
            let rampIn = i < fadeIn ? Double(i) / Double(max(fadeIn, 1)) : 1.0
            let rampOutStart = sampleCount - fadeOut
            let rampOut = i >= rampOutStart ? Double(sampleCount - i) / Double(max(fadeOut, 1)) : 1.0
            let envelope = rampIn * rampOut
            let sample = sin(2 * .pi * frequency * t) * 0.10 * envelope
            pcm[i] = Int16(max(-1.0, min(1.0, sample)) * Double(Int16.max))
        }

        let dataBytes = sampleCount * MemoryLayout<Int16>.size
        var wav = Data()

        func u32le(_ value: UInt32) -> [UInt8] {
            withUnsafeBytes(of: value.littleEndian) { Array($0) }
        }

        func u16le(_ value: UInt16) -> [UInt8] {
            withUnsafeBytes(of: value.littleEndian) { Array($0) }
        }

        wav.append(contentsOf: "RIFF".utf8)
        wav.append(contentsOf: u32le(UInt32(dataBytes + 36)))
        wav.append(contentsOf: "WAVE".utf8)
        wav.append(contentsOf: "fmt ".utf8)
        wav.append(contentsOf: u32le(16))
        wav.append(contentsOf: u16le(1))
        wav.append(contentsOf: u16le(1))
        wav.append(contentsOf: u32le(UInt32(sampleRate)))
        wav.append(contentsOf: u32le(UInt32(sampleRate * 2)))
        wav.append(contentsOf: u16le(2))
        wav.append(contentsOf: u16le(16))
        wav.append(contentsOf: "data".utf8)
        wav.append(contentsOf: u32le(UInt32(dataBytes)))

        for sample in pcm {
            wav.append(contentsOf: u16le(UInt16(bitPattern: sample)))
        }

        let player = try? AVAudioPlayer(data: wav)
        player?.volume = 1.0
        return player
    }
}

// MARK: - FlowSession ---------------------------------------------------------

final class FlowSession: ObservableObject {

    struct Turn: Identifiable {
        let id        = UUID()
        let sourceText: String
        let sourceLang: String
        let targetText: String
        let targetLang: String
    }

    @Published var state: AppState  = .ready
    @Published var turns: [Turn]    = []
    @Published var liveTranscript   = ""
    @Published var connStatus: ConnStatus = .offline   // SC-01: drives connection dot in TrustBarView
    @Published var skipFlash        = ""               // SC-03: brief "Nothing heard" on VAD idle release

    // Source lang of the in-flight turn. Set by source_transcript, cleared on turn commit.
    @Published var pendingSourceLang: String? = nil

    private let capture = AudioCapture()
    private let tts     = TTSPlayer()
    private let ws      = FlowWSClient()

    // SPEC §4: Only one finalize per turn.
    // True once the server (speech_stopped) or the user (release) has already
    // triggered the turn end — whichever fires first wins; the other is a no-op.
    private var finalizeEmitted = false
    private var hasEverConnected = false   // P0.3: distinguish "never tried" from "dropped"

    // Safety watchdog: if the app is still in .processing after 6s, force returnToReady().
    // Covers AVAudioEngine stalls, missed server messages, and any other stuck-state scenario.
    // Started whenever state enters .processing; cancelled by returnToReady().
    private var watchdog: DispatchWorkItem?
    private var processingPresenceWorkItem: DispatchWorkItem?
    private var processingPresenceArmed = false

    private let light   = UIImpactFeedbackGenerator(style: .light)
    private let success = UINotificationFeedbackGenerator()

    init() {
        capture.prepareSession()
        ws.onMessage    = { [weak self] msg in self?.handleMessage(msg) }
        ws.onDisconnect = { [weak self] in self?.handleDisconnect() }
        ws.onConnect    = { [weak self] in
            self?.hasEverConnected = true
            self?.connStatus = .online
        }
        ws.onGiveUp     = { [weak self] in
            // P0.3: if we were connected before, show reconnecting not offline —
            // offline is reserved for "never successfully connected this session"
            guard let self else { return }
            self.connStatus = self.hasEverConnected ? .reconnecting : .offline
        }
        ws.connect()
    }

    // MARK: Repeat last output (REPEAT_LAST_OUTPUT_V1) -------------------------

    /// Replay the last translated turn's spoken audio without re-speaking.
    /// Server regenerates TTS from its cached last_output.
    /// Guard: only callable when state == .ready and WS is open.
    /// Does NOT add a duplicate turn to history (server sends repeat_done, not translation_done).
    func repeatLast() {
        guard state == .ready else { return }
        guard ws.sendRepeat() else { return }   // WS not open → no-op
        tts.stop()                              // silence any residual audio
        state = .processing
        armProcessingPresenceCue()
        startWatchdog(after: 10)    // P1.5: 10s to first chunk (not 30s — TTS should start fast)
        print("[Session] repeatLast — sent repeat request")
    }

    // MARK: Server URL (runtime-configurable, no rebuild needed) ---------------

    /// The currently active server URL (read from UserDefaults, falls back to default).
    var serverURL: String {
        UserDefaults.standard.string(forKey: FlowWSClient.urlDefaultsKey)
        ?? FlowWSClient.defaultURLString
    }

    /// Update the WebSocket server URL and immediately reconnect.
    /// Triggered by the long-press URL editor in the status bar.
    func setServerURL(_ urlString: String) {
        ws.setURL(urlString)
    }

    // MARK: Press / Release (spec §4) -----------------------------------------

    func pressDown() {
        // Block new press if turn is still resolving (spec §10 — no state corruption).
        guard state == .ready else { return }
        // Block if socket is not live — mic must not start while reconnecting/offline.
        // Tap while reconnecting bypasses the retry timer for immediate attempt.
        guard connStatus == .online else { ws.reconnectNow(); return }

        finalizeEmitted = false
        liveTranscript  = ""
        pendingSourceLang = nil

        tts.stop()          // barge-in: silence any speaking TTS from prior turn
        state = .listening
        light.impactOccurred()
        light.prepare()
        ws.connectIfNeeded()
        capture.start { [weak self] pcm in self?.ws.sendAudio(pcm) }
    }

    func pressUp() {
        print("RELEASE FIRED")
        capture.stop()
        // Only send end_of_utterance if server hasn't already ended the turn.
        // spec §4: "Only ONE finalize per turn"
        guard !finalizeEmitted else { return }
        guard state == .listening else { return }
        finalizeEmitted = true
        playReleaseTone()          // immediate non-verbal cue: fires exactly once per valid release
        guard ws.sendEndOfUtterance() else {
            // WS not open — finalize couldn't be sent, server doesn't know turn ended.
            // Fall back to .ready so the user can press again once connected.
            print("[Session] pressUp — WS not open, resetting to ready")
            returnToReady()
            return
        }
        state = .processing
        armProcessingPresenceCue()
        startWatchdog()
    }

    // MARK: Server message handler (spec §6) ----------------------------------

    private func handleMessage(_ msg: [String: Any]) {
        guard let type = msg["type"] as? String else { return }

        switch type {

        case "speech_started":
            // Server confirms it heard audio — no state change needed.
            // Client is already .listening from pressDown().
            break

        case "speech_stopped":
            // Server hit the 60s hard cap. Normal turn end is via pressUp() only.
            // Stop capture immediately. Mark finalize as done so pressUp() is a no-op.
            capture.stop()
            if !finalizeEmitted {
                finalizeEmitted = true
                playCapHitTone()   // cap-hit only — tells user "limit reached, translating now"
                if state == .listening {
                    state = .processing
                    startWatchdog()
                }
            }

        case "source_transcript":
            // server_local.py sends {"type":"source_transcript","text":"...","diagnostics":{...}}
            // active_lang is the canonical normalized language (en / pt-BR).
            let text = msg["text"] as? String ?? ""
            liveTranscript = text
            if let diag = msg["diagnostics"] as? [String: Any],
               let lang = diag["active_lang"] as? String {
                pendingSourceLang = lang
            }

        case "translation_delta":
            // Streaming delta — no state change needed.
            break

        case "translation_done":
            // Server finished translating. Collect final text and queued TTS.
            cancelProcessingPresenceCue()
            let translation = msg["text"] as? String ?? ""
            let source      = liveTranscript
            let srcLang     = pendingSourceLang ?? "en"

            // Commit turn to history (even if empty — server guarantees valid turns).
            if !source.isEmpty || !translation.isEmpty {
                commitTurn(source: source, sourceLang: srcLang, translation: translation)
            }

            // Wait for TTS queue to drain, then return to READY.
            // If no audio chunks were enqueued, drains immediately.
            // sendTTSPlaybackDone() is called inside returnToReady() — covers all exit paths.
            tts.signalDone { [weak self] in
                DispatchQueue.main.async {
                    guard let self else { return }
                    // Handoff signal: light haptic exactly when TTS finishes and the turn
                    // is clean. Fires only on this path (normal completion) — not on
                    // watchdog / error / skip_turn exits so there's no confusing phantom tap.
                    // Person B feels this and knows: "my turn — press now."
                    self.light.impactOccurred()
                    self.cancelProcessingPresenceCue()
                    playReadyTone()    // distinct from release tone; fires once per completed playback cycle
                    self.returnToReady()
                }
            }

        case "tts_start":
            // Pipeline confirmed working — TTS is about to play.
            // Reset watchdog from 6s (pipeline timeout) to 30s (TTS playback timeout).
            // Without this, the watchdog fires mid-TTS for any response > ~3s of speech.
            startWatchdog(after: 30)
            // Pre-start the audio engine now so it is warm when first audio_delta arrives.
            // Saves ~20–50ms of engine cold-start from the first perceived sound.
            tts.prime()

        case "audio_delta":
            // server_local.py sends {"type":"audio_delta","audio":"<base64 PCM16>"}
            if let b64 = msg["audio"] as? String,
               let pcm = Data(base64Encoded: b64) {
                cancelProcessingPresenceCue()
                // Reset the 30s watchdog on every arriving chunk.
                // Without this, a response whose audio stream spans > 30s total
                // (long Portuguese passages, many sentences) trips the watchdog
                // mid-playback and silently kills the remaining audio.
                startWatchdog(after: 30)
                tts.enqueue(pcm)
            }

        case "repeat_done":
            // Server finished streaming the repeat TTS.
            // Two paths:
            //   a. skip_reason present → no cached output on server, return to ready immediately.
            //   b. normal → wait for TTS queue to drain exactly like translation_done,
            //      but do NOT call commitTurn() — this is a replay, not a new turn.
            cancelProcessingPresenceCue()
            if let reason = msg["skip_reason"] as? String {
                print("[Session] repeat not available — \(reason)")
                returnToReady()
                break
            }
            tts.signalDone { [weak self] in
                DispatchQueue.main.async {
                    guard let self else { return }
                    self.light.impactOccurred()
                    self.cancelProcessingPresenceCue()
                    playReadyTone()
                    self.returnToReady()
                }
            }

        case "ping":
            // Server keepalive — respond so server can track liveness.
            ws.sendPong()

        case "turn_complete":
            // Server skipped the turn (no speech / VAD idle / short sound / STT error).
            // skip_reason is always present on skipped turns; absent on normal turns.
            // Normal turns return to READY via the TTS drain callback in translation_done —
            // do not reset here for those or TTS playback would be cut short.
            if let reason = msg["skip_reason"] as? String {
                print("[FLOW][TURN] Skipped — reason: \(reason)")
                light.impactOccurred()     // SC-03: subtle haptic confirms release was registered
                // Brief label flash so user knows silence was intentional, not a bug.
                let isNoSpeech = ["release_no_speech", "short_sound",
                                  "no_audio_received", "short_segment"].contains(reason)
                if isNoSpeech {
                    skipFlash = "Nothing heard"
                    DispatchQueue.main.asyncAfter(deadline: .now() + 1.5) { [weak self] in
                        self?.skipFlash = ""
                    }
                }
                returnToReady()
            }

        case "error":
            // Server-reported error — unblock processing and return to READY.
            // spec §13: client must never crash on missing events.
            let errMsg = msg["message"] as? String ?? "unknown error"
            print("[FLOW][ERROR] Server error: \(errMsg)")
            returnToReady()

        default:
            break
        }
    }

    // MARK: Disconnect handler (spec §7) --------------------------------------

    private func handleDisconnect() {
        // Client must reset to READY and not crash. spec §7.
        print("[FLOW][ERROR] WebSocket disconnected — reconnecting")
        connStatus = .reconnecting
        capture.stop()
        returnToReady()
    }

    // MARK: Helpers -----------------------------------------------------------

    // Always called on main thread (handleMessage is dispatched to main by FlowWSClient).
    private func commitTurn(source: String, sourceLang: String, translation: String) {
        let srcLabel = sourceLang.hasPrefix("pt") ? "PT-BR" : "EN"
        let tgtLabel = sourceLang.hasPrefix("pt") ? "EN" : "PT-BR"
        turns.insert(Turn(sourceText: source, sourceLang: srcLabel,
                          targetText: translation, targetLang: tgtLabel), at: 0)
        liveTranscript    = ""
        pendingSourceLang = nil
        success.notificationOccurred(.success)
    }

    private func startWatchdog(after seconds: Double = 6) {
        watchdog?.cancel()
        let item = DispatchWorkItem { [weak self] in
            guard let self, self.state == .processing else { return }
            print("[Session] watchdog fired (\(Int(seconds))s) — forcing recovery")
            self.tts.stop()     // clear any stalled audio engine state before reset
            self.returnToReady()
        }
        watchdog = item
        DispatchQueue.main.asyncAfter(deadline: .now() + seconds, execute: item)
    }

    private func armProcessingPresenceCue() {
        processingPresenceArmed = true
        processingPresenceWorkItem?.cancel()
        scheduleProcessingPresenceCue(after: 1.0)
    }

    private func scheduleProcessingPresenceCue(after delay: TimeInterval) {
        let item = DispatchWorkItem { [weak self] in
            guard let self, self.processingPresenceArmed, self.state == .processing else { return }
            ProcessingFeedback.shared.fire()
            self.scheduleProcessingPresenceCue(after: 1.5)
        }
        processingPresenceWorkItem = item
        DispatchQueue.main.asyncAfter(deadline: .now() + delay, execute: item)
    }

    private func cancelProcessingPresenceCue() {
        processingPresenceArmed = false
        processingPresenceWorkItem?.cancel()
        processingPresenceWorkItem = nil
        ProcessingFeedback.shared.stop()
    }

    private func returnToReady() {
        // Always returns to .ready — spec §3 golden rule.
        // sendTTSPlaybackDone() here covers ALL exit paths:
        //   normal drain, watchdog, disconnect, skip-turn, error.
        // Without this, watchdog/error paths leave server stuck with is_playing_tts=True.
        cancelProcessingPresenceCue()
        watchdog?.cancel()
        watchdog = nil
        finalizeEmitted = false
        liveTranscript   = ""
        pendingSourceLang = nil
        ws.sendTTSPlaybackDone()   // always clear server echo-suppression state
        state = .ready
    }
}

// Fires system sound 1104 (key_press_click) immediately on valid button release.
// No async, no state dependency, no server round-trip required.
private func playReleaseTone() {
    AudioServicesPlaySystemSound(1104)
}

// Fires when the 60s hard cap is hit and translation begins automatically.
// Double pulse (100ms gap) + medium haptic — perceptually distinct from the single-fire
// release (1104) and ready (1117) tones. Signals "something stopped me / system took over"
// without requiring the user to look at the screen.
// Only fires on the cap-hit path (speech_stopped with !finalizeEmitted).
private func playCapHitTone() {
    let h = UIImpactFeedbackGenerator(style: .medium)
    h.impactOccurred()                                              // stronger than release (.light)
    AudioServicesPlaySystemSound(1057)                              // first pulse — immediate
    DispatchQueue.main.asyncAfter(deadline: .now() + 0.10) {
        AudioServicesPlaySystemSound(1057)                          // second pulse — 100ms later
    }
}

// Fires system sound 1117 (short positive chime) when TTS fully drains and the
// turn is complete. Signals "your turn now" to the waiting speaker.
// Only called from the tts.signalDone path — not from watchdog / error / skip exits.
private func playReadyTone() {
    AudioServicesPlaySystemSound(1117)
}

// MARK: - AudioCapture --------------------------------------------------------
//
// Captures mic at device native rate, resamples to 24 kHz PCM-16 mono.
// spec §8: Input = PCM → base64 JSON, consistent sample rate.

final class AudioCapture {

    private let avSession = AVAudioSession.sharedInstance()
    private let engine    = AVAudioEngine()
    private var nativeHz: Double = 44_100
    private var running   = false
    private var sessionOK = false

    func prepareSession() {
        guard !sessionOK else { return }
        do {
            try avSession.setCategory(.playAndRecord, mode: .voiceChat,
                                      options: [.defaultToSpeaker, .allowBluetoothHFP])
            try avSession.setActive(true)
            sessionOK = true
        } catch {
            print("[Capture] session prepare error: \(error)")
        }
    }

    func start(onBuffer: @escaping (Data) -> Void) {
        guard !running else { return }
        if !sessionOK { prepareSession() }
        running = true

        let input = engine.inputNode
        let fmt   = input.outputFormat(forBus: 0)
        nativeHz  = fmt.sampleRate

        input.removeTap(onBus: 0)
        input.installTap(onBus: 0, bufferSize: 1_024, format: fmt) { [weak self] buf, _ in
            guard let self, let ch = buf.floatChannelData?[0] else { return }
            onBuffer(self.resample(ch, count: Int(buf.frameLength)))
        }

        if !engine.isRunning {
            do { try engine.start() } catch {
                print("[Capture] engine start error: \(error)")
                input.removeTap(onBus: 0)
                running = false
            }
        }
    }

    func stop() {
        guard running else { return }
        running = false
        engine.inputNode.removeTap(onBus: 0)
    }

    // Linear-interpolation resample: native Hz → 24 kHz, float32 → int16.
    private func resample(_ src: UnsafePointer<Float>, count n: Int) -> Data {
        let ratio    = nativeHz / 24_000.0
        let outCount = max(1, Int(Double(n) / ratio))
        var out      = Data(count: outCount * 2)
        out.withUnsafeMutableBytes { ptr in
            guard let dst = ptr.bindMemory(to: Int16.self).baseAddress else { return }
            for i in 0..<outCount {
                let s    = Double(i) * ratio
                let lo   = Int(s); let hi = min(lo + 1, n - 1)
                let frac = Float(s - Double(lo))
                let v    = src[lo] * (1 - frac) + src[hi] * frac
                dst[i]   = Int16(max(-1, min(1, v)) * Float(Int16.max))
            }
        }
        return out
    }
}

// MARK: - TTSPlayer -----------------------------------------------------------
//
// Streams PCM-16 24 kHz mono chunks into AVAudioPlayerNode.
// spec §8: streaming audio chunks allowed, must not crash if missing.

final class TTSPlayer {

    private let fmt  = AVAudioFormat(commonFormat: .pcmFormatFloat32,
                                     sampleRate: 24_000, channels: 1,
                                     interleaved: false)!
    private let engine = AVAudioEngine()
    private let node   = AVAudioPlayerNode()
    private let q      = DispatchQueue(label: "flow.tts", qos: .userInteractive)

    private var pending = 0
    private var allIn   = false
    private var drainCB: (() -> Void)?

    init() {
        engine.attach(node)
        engine.connect(node, to: engine.mainMixerNode, format: fmt)
    }

    // Prime the audio engine when tts_start arrives (~1ms before first audio_delta).
    // Removes engine cold-start cost (~20–50ms) from first perceived audio delay.
    func prime() {
        q.async { [weak self] in
            guard let self else { return }
            guard !self.engine.isRunning else {
                // If engine is running but node is stopped here, the checkDrain bug
                // would have caused silent audio. Log it so we can confirm the fix holds.
                if !self.node.isPlaying {
                    print("[TTS] prime: engine running, node stopped — restarting node")
                    self.node.play()
                }
                return
            }
            do { try self.engine.start(); self.node.play() } catch {
                print("[TTS] prime error: \(error)")
            }
        }
    }

    func enqueue(_ pcm16: Data) {
        let frames = pcm16.count / 2
        guard frames > 0,
              let buf = AVAudioPCMBuffer(pcmFormat: fmt,
                                         frameCapacity: AVAudioFrameCount(frames)),
              let ch  = buf.floatChannelData?[0] else { return }

        buf.frameLength = AVAudioFrameCount(frames)
        pcm16.withUnsafeBytes { raw in
            guard let src = raw.bindMemory(to: Int16.self).baseAddress else { return }
            for i in 0..<frames { ch[i] = Float(src[i]) / 32_768.0 }
        }

        // Start engine if prime() wasn't called or failed (safe fallback).
        if !engine.isRunning {
            do { try engine.start(); node.play() } catch {
                print("[TTS] engine start error: \(error)"); return
            }
        }

        q.async { [weak self] in
            guard let self else { return }
            // Defensive: if engine is running but node was stopped (e.g. checkDrain
            // raced with a rapid second turn before engine.stop() queued), restart node
            // so scheduled buffers actually play.
            if self.engine.isRunning && !self.node.isPlaying {
                print("[TTS] enqueue: engine running but node stopped — restarting node")
                self.node.play()
            }
            self.pending += 1
            self.node.scheduleBuffer(buf) {
                self.q.async { self.pending -= 1; self.checkDrain() }
            }
        }
    }

    // Call after translation_done — fires drainCB when last buffer plays.
    func signalDone(onDrain cb: @escaping () -> Void) {
        q.async { [weak self] in
            guard let self else { return }
            self.drainCB = cb
            self.allIn   = true
            self.checkDrain()
        }
    }

    // Hard stop for barge-in or session reset.
    func stop() {
        q.async { [weak self] in
            guard let self else { return }
            self.pending = 0; self.allIn = false; self.drainCB = nil
            self.node.stop()
            self.engine.stop()
        }
    }

    private func checkDrain() {
        guard allIn && pending == 0 else { return }
        allIn = false
        let cb = drainCB; drainCB = nil
        node.stop()
        engine.stop()   // FIX: match stop() — without this, prime()/enqueue() see
                        // engine.isRunning=true on next turn and skip node.play(),
                        // scheduling buffers on a dead node → silent audio every
                        // second turn.
        print("[TTS] checkDrain: engine stopped, ready for next turn")
        DispatchQueue.main.async { cb?() }
    }
}

// MARK: - FlowWSClient --------------------------------------------------------
//
// WebSocket client strictly per FLOW_SPEC §6 wire protocol.
//
// Uses Network.framework (NWConnection) instead of URLSession so we can force
// HTTP/1.1 in the TLS ALPN negotiation. iOS URLSession advertises h2 by default;
// Cloudflare/ngrok tunnels negotiate HTTP/2, which breaks the WebSocket upgrade
// handshake (101 Switching Protocols is HTTP/1.1-only). Forcing ALPN = http/1.1
// matches what Python's websockets library does, which connects successfully.
//
// Client → Server:
//   {"type":"audio","audio":"<base64>"}
//   {"type":"speech_stopped"}
//   {"type":"tts_playback_done"}
//
// Server → Client:
//   speech_started | speech_stopped | source_transcript | translation_delta |
//   translation_done | tts_start | audio_delta | turn_complete | error

final class FlowWSClient {

    // Active tunnel endpoint.
    // Stored in UserDefaults under key "flow.serverURL" so it can be updated
    // at runtime (long-press the status bar in the app) without a Xcode rebuild.
    // Falls back to the hardcoded default below when UserDefaults has no value.
    static let defaultURLString = "wss://flow.flowbasit.com/ws"
    static let urlDefaultsKey   = "flow.serverURL"

    private var url: URL {
        let stored = UserDefaults.standard.string(forKey: Self.urlDefaultsKey)
                     ?? Self.defaultURLString
        return URL(string: stored) ?? URL(string: Self.defaultURLString)!
    }

    var onMessage:    (([String: Any]) -> Void)?
    var onDisconnect: (() -> Void)?
    var onConnect:    (() -> Void)?
    var onGiveUp:     (() -> Void)?

    private enum ConnState { case idle, connecting, open, dead }
    private var connState: ConnState = .idle
    private var conn: NWConnection?

    private var audioQueue: [Data] = []

    private var retryCount    = 0
    private var retryWorkItem: DispatchWorkItem?
    // Fast window (attempts 1-5): tight retries for server restarts / brief drops.
    // Slow window (attempts 6+): exponential back-off for unstable networks.
    private static let fastDelays: [Double] = [0.5, 1.0, 1.0, 2.0, 2.0]
    private static let maxRetries = 9    // fast(5) + slow(4) before saturation → 30s

    func connect() {
        guard connState == .idle || connState == .dead else { return }
        retryWorkItem?.cancel()
        retryWorkItem = nil
        connState = .connecting
        print("[WS] connecting → \(url)")
        print("Connecting to WebSocket:", url.absoluteString)

        // Force HTTP/1.1 in TLS ALPN — prevents HTTP/2 negotiation which breaks
        // WebSocket handshake through Cloudflare tunnels.
        let tlsOpts = NWProtocolTLS.Options()
        sec_protocol_options_add_tls_application_protocol(
            tlsOpts.securityProtocolOptions, "http/1.1"
        )

        let wsOpts = NWProtocolWebSocket.Options()
        wsOpts.autoReplyPing = true

        let params = NWParameters(tls: tlsOpts)
        params.defaultProtocolStack.applicationProtocols.insert(wsOpts, at: 0)

        conn = NWConnection(to: NWEndpoint.url(url), using: params)
        conn?.stateUpdateHandler = { [weak self] state in
            DispatchQueue.main.async { self?.handleState(state) }
        }
        conn?.start(queue: .main)
        receive()
    }

    func connectIfNeeded() {
        if connState == .idle || connState == .dead { connect() }
    }

    /// Call this to change the server URL at runtime (no rebuild needed).
    /// Cancels any in-flight connection and immediately reconnects with the new URL.
    func setURL(_ urlString: String) {
        UserDefaults.standard.set(urlString, forKey: Self.urlDefaultsKey)
        // Cancel current connection and all pending retries, then reconnect.
        retryWorkItem?.cancel()
        retryWorkItem = nil
        retryCount    = 0
        conn?.cancel()
        conn          = nil
        connState     = .dead
        connect()
    }

    func sendAudio(_ pcm16: Data) {
        DispatchQueue.main.async { [weak self] in
            guard let self else { return }
            if self.connState == .open {
                self.transmitAudio(pcm16)
            } else {
                self.audioQueue.append(pcm16)
            }
        }
    }

    @discardableResult
    func sendEndOfUtterance() -> Bool {
        guard connState == .open else {
            print("[WS] sendEndOfUtterance — not open (state=\(connState)), dropping")
            return false
        }
        send(["type": "speech_stopped"])
        return true
    }

    func sendTTSPlaybackDone() {
        guard connState == .open else { return }
        send(["type": "tts_playback_done"])
    }

    func sendPong() {
        guard connState == .open else { return }
        send(["type": "pong"])
    }

    @discardableResult
    func sendRepeat() -> Bool {
        guard connState == .open else {
            print("[WS] sendRepeat — not open, dropping")
            return false
        }
        send(["type": "repeat"])
        return true
    }

    // MARK: Private

    private func handleState(_ state: NWConnection.State) {
        switch state {
        case .ready:
            connState = .open
            retryCount = 0
            retryWorkItem?.cancel()
            retryWorkItem = nil
            print("[FLOW] Server connected — ready")
            onConnect?()
            let q = audioQueue; audioQueue = []
            q.forEach { transmitAudio($0) }
        case .failed(let err):
            print("[WS] connection failed: \(err.localizedDescription)")
            handleDrop()
        case .cancelled:
            if connState != .dead { handleDrop() }
        default:
            break
        }
    }

    private func handleDrop() {
        guard connState != .dead else { return }
        if connState == .connecting {
            print("[WS] failed to connect")
        } else {
            print("[WS] disconnected")
        }
        connState = .dead
        conn = nil
        audioQueue.removeAll()
        onDisconnect?()
        retryCount += 1
        if retryCount > Self.maxRetries {
            // Backoff saturated — keep retrying at 30s forever (self-healing).
            // onGiveUp updates UI once; loop continues below without returning.
            retryCount = Self.maxRetries
            onGiveUp?()
        }
        let delay = Self.retryDelay(for: retryCount)
        print("[WS] retry \(retryCount) in \(delay)s")
        let item = DispatchWorkItem { [weak self] in
            guard let self, self.connState == .dead else { return }
            self.connect()
        }
        retryWorkItem = item
        DispatchQueue.main.asyncAfter(deadline: .now() + delay, execute: item)
    }

    private static func retryDelay(for attempt: Int) -> Double {
        if attempt <= fastDelays.count {
            return fastDelays[attempt - 1]                          // fast window
        }
        let slowIndex = attempt - fastDelays.count                  // 1, 2, 3, 4…
        return min(30.0, pow(2.0, Double(slowIndex + 1)))           // 4, 8, 16, 30
    }

    /// Cancel pending retry and reconnect immediately.
    /// Called when user taps mic while reconnecting — bypasses timer.
    func reconnectNow() {
        retryWorkItem?.cancel()
        retryWorkItem = nil
        guard connState == .dead else { return }
        connect()
    }

    private func receive() {
        conn?.receiveMessage { [weak self] data, context, _, error in
            DispatchQueue.main.async {
                guard let self else { return }
                if let error = error {
                    print("[WS] receive error: \(error.localizedDescription)")
                    self.handleDrop()
                    return
                }
                if let data = data,
                   let meta = context?.protocolMetadata(
                       definition: NWProtocolWebSocket.definition
                   ) as? NWProtocolWebSocket.Metadata,
                   meta.opcode == .text,
                   let text = String(data: data, encoding: .utf8) {
                    self.dispatch(text)
                }
                self.receive()
            }
        }
    }

    private func transmitAudio(_ pcm16: Data) {
        sendRaw("{\"type\":\"audio\",\"audio\":\"\(pcm16.base64EncodedString())\"}")
    }

    private func send(_ dict: [String: Any]) {
        guard connState == .open,
              let data = try? JSONSerialization.data(withJSONObject: dict),
              let str  = String(data: data, encoding: .utf8) else { return }
        sendRaw(str)
    }

    private func sendRaw(_ text: String) {
        guard connState == .open, let data = text.data(using: .utf8) else { return }
        let meta = NWProtocolWebSocket.Metadata(opcode: .text)
        let ctx  = NWConnection.ContentContext(identifier: "ws", metadata: [meta])
        conn?.send(content: data, contentContext: ctx, isComplete: true,
                   completion: .idempotent)
    }

    private func dispatch(_ raw: String) {
        guard let data = raw.data(using: .utf8),
              let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any]
        else { return }
        onMessage?(json)
    }
}

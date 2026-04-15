"""
FLOW LOCAL — Live Bilingual Interpreter (100% Local)
No cloud calls. Whisper + Ollama + Piper TTS on-device.

Hold-to-talk pipeline (sentence-level TTS overlap):
  Press → audio capture starts → Release → force_finalize → mlx-whisper STT (Apple Silicon ANE)
    → Ollama LLM streams tokens → detect sentence boundary
    → Piper TTS per sentence → audio_delta sent immediately
    (LLM continues generating while TTS plays previous sentence)
  VAD role: speech onset detection + hard-cap safety only (not turn authority)

Key optimizations:
  - Single-pass STT with stable_lang hint (skips 3× dual-transcription)
  - Streaming LLM → sentence-level TTS (overlaps generation with synthesis)
  - Persistent httpx connection pooling for Ollama
  - Barge-in cancels remaining TTS sentences
  - Energy pre-filter + hallucination guard
  - Echo suppression (post-TTS 600ms silence window + VAD reset)
  - Per-turn METRICS logging (tts_first_audio_ms for P50/P95)
"""

import asyncio
import json
import os
import sys
import io
import wave
import base64
import time
import traceback
import re
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from enum import Enum

import numpy as np
import httpx
import onnxruntime
import mlx_whisper
from piper import PiperVoice
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from websockets.exceptions import ConnectionClosedError
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware


# Error codes for structured error handling
class ErrorCode(str, Enum):
    STT_FAILED = "STT_FAILED"
    STT_TIMEOUT = "STT_TIMEOUT"
    LLM_FAILED = "LLM_FAILED"
    LLM_TIMEOUT = "LLM_TIMEOUT"
    LLM_UNAVAILABLE = "LLM_UNAVAILABLE"
    TTS_FAILED = "TTS_FAILED"
    AUDIO_ENCODING_ERROR = "AUDIO_ENCODING_ERROR"
    VAD_ERROR = "VAD_ERROR"
    UNKNOWN = "UNKNOWN"

    def user_message(self):
        messages = {
            "STT_FAILED": "Could not understand speech. Please try again.",
            "STT_TIMEOUT": "Speech processing took too long. Try speaking shorter phrases.",
            "LLM_FAILED": "Translation service encountered an error. Retrying...",
            "LLM_TIMEOUT": "Translation is slow. Please wait or try a shorter phrase.",
            "LLM_UNAVAILABLE": "Translator offline. Make sure Ollama is running.",
            "TTS_FAILED": "Could not generate audio response.",
            "AUDIO_ENCODING_ERROR": "Audio encoding failed. Check microphone.",
            "VAD_ERROR": "Speech detection error.",
            "UNKNOWN": "Unknown error occurred.",
        }
        return messages.get(self.value, messages["UNKNOWN"])


# ---------------------------------------------------------------------------
# Logging (unbuffered)
# ---------------------------------------------------------------------------

def log(msg):
    print(msg, flush=True)


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

FLOW_DIR = Path(__file__).resolve().parent
PIPER_MODELS_DIR = FLOW_DIR / "models" / "piper"

# Whisper — mlx-whisper runs on Apple Silicon ANE/Metal (~940ms on M4 vs ~2300ms CPU)
# medium: 941ms, best accuracy for accent/diacritic robustness (EN + PT-BR)
# large-v3-turbo: 1534ms, marginal quality gain; tiny: 59ms, low diacritic accuracy
MLX_WHISPER_MODEL = "mlx-community/whisper-medium"

# Ollama
OLLAMA_URL = "http://localhost:11434/api/chat"
OLLAMA_MODEL = "gemma3:4b"
OLLAMA_TIMEOUT = 30.0             # seconds per translation request (increased for stability)
OLLAMA_RETRIES = 3                # retry count on failure (increased for resilience)

# Audio
INPUT_SAMPLE_RATE = 24000         # from browser
VAD_SAMPLE_RATE = 16000           # silero requires 16kHz
WHISPER_SAMPLE_RATE = 16000       # whisper requires 16kHz

# VAD
VAD_THRESHOLD = 0.5
VAD_NEG_THRESHOLD = 0.35
SILENCE_DURATION_MS = 700         # trailing silence trimmed from buffer on release — not used for auto-end
MIN_SPEECH_MS = 350               # allow shorter natural turns without feeling delayed
MAX_SPEECH_S = 60                 # safety hard cap — user controls end via button release; 60s covers longest natural turns
AUDIO_TIMEOUT_MS = 60000          # 60s — covers cold LLM+TTS on first turn; client sends no audio during processing
VAD_WINDOW = 512                  # silero window size in samples
VAD_CONTEXT = 64                  # silero context size

# Energy pre-filter: skip segments quieter than this RMS.
# Applied as peak windowed RMS (see transcribe_segment), not global RMS.
# Global RMS dilutes long quiet turns: 6s of soft speech over 30s of audio averages
# close to threshold even though the speech windows are clearly above it.
MIN_ENERGY_RMS        = 0.002    # minimum peak-window RMS — below this = silence/ambient noise
ENERGY_WINDOW_SAMPLES = 8000     # 0.5s at 16kHz — one window must exceed threshold to pass

# ---------------------------------------------------------------------------
# Language Stability Contract (CRITICAL)
# ---------------------------------------------------------------------------

ALLOWED_LANGS = ["en", "pt"]      # ONLY English and Portuguese (PT includes all pt variants)
LANGUAGE_SWITCH_HYSTERESIS = 3    # require 3 consecutive same-language detections before stable switch (prevents single-turn flicker)
LANGUAGE_SWITCH_COOLDOWN = 0      # no cooldown — interpreter must switch every turn
MIN_CONFIDENCE_STT = 0.55         # ASCII rescue gate (kept for rescue chain guard)
MIN_CONFIDENCE_SWITCH = 0.70      # minimum confidence to start/advance language switch hysteresis
                                   # Lowered from 0.90 — switch allowed when detected_lang != current
                                   # lang with confidence >= 0.70.
CONF_LOW_CONFIDENCE_FLOOR = 0.60  # below this: low-quality signal — skip if short, log if long
# 3-lane gate thresholds (spec-exact)
CONF_STRONG_EN  = 0.55            # Lane A/B boundary — English
CONF_STRONG_PT  = 0.45            # Lane A/B boundary — Portuguese (Whisper PT scores lower)
CONF_WEAK_FLOOR = 0.30            # Lane B/C boundary — all languages; below → repeat-request

# Reliability Modes — Default Configuration
DEFAULT_RELIABILITY_MODE = "stable"   # reliability-first baseline

# ---------------------------------------------------------------------------
# Phase 1 Accent Hardening — instrumentation + guarded EN retry
# ---------------------------------------------------------------------------
ACCENT_LOG_PATH = "accent_failures.jsonl"   # append-only; one JSON object per line
SOURCE_TAG      = "live"                     # override to "tiktok_test" during clip testing

# Words that are unambiguously English and rare as standalone tokens in PT/FR/ES.
# "do" excluded (Portuguese preposition). Single-letter tokens excluded (noise).
_EN_DISCRIMINATING_WORDS = frozenset({
    "the", "is", "are", "you", "what", "where", "when", "how",
    "my", "your", "can", "please", "thank",
    "i'm", "don't", "can't", "i'll", "we're", "they're",
    "okay", "yeah", "was", "were", "have", "has",
    "could", "would", "should", "this", "that", "there",
    "here", "they", "she", "he", "we", "with", "about",
})

# Mode-specific parameters (per-session, not hardcoded)
MODE_CONFIG = {
    "stable": {
        "SILENCE_DURATION_MS": 1300,    # trailing silence trimmed from buffer on release
        "KEEPALIVE_INTERVAL": 20,       # seconds
        "KEEPALIVE_TIMEOUT": 90000,     # 90s timeout
    },
    "fast": {
        "SILENCE_DURATION_MS": 650,     # trailing silence trimmed from buffer on release
        "KEEPALIVE_INTERVAL": 20,       # seconds
        "KEEPALIVE_TIMEOUT": 45000,     # 45s timeout
    }
}

# Session-level keepalive defaults — overridden per-session by MODE_CONFIG above.
KEEPALIVE_INTERVAL = MODE_CONFIG[DEFAULT_RELIABILITY_MODE]["KEEPALIVE_INTERVAL"]
KEEPALIVE_TIMEOUT = MODE_CONFIG[DEFAULT_RELIABILITY_MODE]["KEEPALIVE_TIMEOUT"]

# Whisper hallucination guard — only patterns that NO real user would intentionally say
# as a genuine interpreter utterance. Greetings, yes/no, thanks are NOT hallucinations
# in an interpreter context — they are legitimate phrases that must be translated.
HALLUCINATION_PATTERNS = {
    # English — YouTube/subtitle artifacts (never said in a live meeting)
    "thank you for watching", "thanks for watching", "thanks for viewing",
    "like and subscribe", "subscribe", "if you like this",
    "thanks for listening", "subtitles by",
    # Single-phoneme noise blobs that are never meaningful
    "you", "oh", "um", "uh", "hmm", "ah", "so",
    "the end", "one", "two", "three",
    # Portuguese — YouTube/subtitle artifacts
    "obrigado por assistir", "obrigado por ver", "obrigado por ouvir",
    "se inscreva", "legendas pela comunidade", "amara.org",
    "legendas pela comunidade amara.org",
}
MIN_TRANSCRIPTION_CHARS = 2       # ignore 1-char transcriptions
MIN_SPEECH_SEGMENT_MS = 350       # skip micro-segments/noise before STT
MIN_DUAL_CANDIDATE_CONF = 0.40    # dual-transcription: discard candidates below this confidence
                                   # prevents a long uncertain transcript from outscoring a
                                   # short confident one via the len*0.02 term in scoring
STABLE_LANG_BIAS    = 0.10        # score bonus for candidates matching the session stable_lang
                                   # tiebreaker only — won't override a clearly better candidate
                                   # (~5 chars or ~0.10 conf difference overrides the bias)

# ---------------------------------------------------------------------------
# ConversationContext — lightweight session frame  (CONTROLLED_CONTEXT_V1)
# ---------------------------------------------------------------------------
#
# Stores exactly five deterministic fields describing the conversational frame.
# Updated only after a valid, clean, high-confidence turn (Lane A or B).
# NEVER stores raw STT text. NEVER stores full turn history.
#
# Purpose: give the LLM a single-turn anchor so pronoun references ("say it
# to her", "the same thing") resolve correctly across turns, and so direction
# is preserved even when the LLM's context window is otherwise empty.
#
# Lifetime: one instance per WebSocket session; reset on disconnect.

import dataclasses as _dc

@_dc.dataclass
class ConversationContext:
    # 1. Language pair (always EN↔PT-BR for Flow; explicit for prompt clarity)
    language_pair: str = "EN↔PT-BR"
    # 2. Last confirmed translation direction ("en→pt-BR" | "pt-BR→en" | "unknown")
    direction: str = "unknown"
    # 3. Source/target role labels for the last clean turn
    #    {"source": "en", "target": "pt-BR"}  — derived from active_lang
    speaker_roles: dict = _dc.field(default_factory=dict)
    # 4. Language we're currently translating INTO (tracks side of conversation)
    current_target: str = ""
    # 5. Cleaned source-language text of the LAST VALID TURN — post-rescue-chain,
    #    pre-translation. Max 80 chars. Never raw STT. Never target-language text.
    last_clean_meaning: str = ""

    # Maximum characters to store in last_clean_meaning.
    # Long enough to resolve pronouns/topics; short enough to add no latency.
    MAX_MEANING_CHARS: int = _dc.field(default=80, init=False, repr=False)

    def update(
        self,
        active_lang: str,
        target_lang: str,
        interpretation: str,
    ) -> None:
        """
        Commit a completed clean turn into the context frame.
        Called ONLY after Lane A/B translation with a non-empty result.
        interpretation = post-rescue-chain source text (NEVER raw STT).
        """
        self.language_pair   = "EN↔PT-BR"
        self.direction       = f"{active_lang}→{target_lang}"
        self.speaker_roles   = {"source": active_lang, "target": target_lang}
        self.current_target  = target_lang
        # Truncate cleanly at a word boundary so we don't store a mid-word fragment
        meaning = interpretation.strip()
        if len(meaning) > self.MAX_MEANING_CHARS:
            truncated = meaning[: self.MAX_MEANING_CHARS]
            last_space = truncated.rfind(" ")
            meaning = truncated[:last_space] if last_space > 0 else truncated
        self.last_clean_meaning = meaning

    def anchor_line(self) -> str:
        """
        Returns a single-line LLM context hint or empty string.
        Empty string → caller must NOT append anything to the prompt.
        Only populated after the first valid turn in the session.
        """
        if not self.last_clean_meaning:
            return ""
        return (
            f"Prior utterance (reference only — resolve pronouns/topics from this): "
            f'"{self.last_clean_meaning}"'
        )


# Thread pool for blocking inference calls (3 workers: STT + TTS can overlap)
EXECUTOR = ThreadPoolExecutor(max_workers=3)

# STT execution lock — mlx-whisper uses Metal; concurrent invocations produce
# "A command encoder is already encoding to this command buffer" assertion.
# All transcribe_segment calls (primary + EN-retry) must hold this lock.
# It is an asyncio.Lock so it serialises at the coroutine level without
# blocking the event loop between polls.
stt_lock = asyncio.Lock()

# Persistent httpx client for Ollama (connection pooling, avoids TCP reconnect)
_ollama_client: httpx.AsyncClient | None = None

async def get_ollama_client() -> httpx.AsyncClient:
    global _ollama_client
    if _ollama_client is None or _ollama_client.is_closed:
        _ollama_client = httpx.AsyncClient(
            timeout=httpx.Timeout(OLLAMA_TIMEOUT, connect=5.0),
            limits=httpx.Limits(max_connections=2, max_keepalive_connections=1),
        )
    return _ollama_client

# Sentence boundary for streaming TTS — split on .!?; followed by whitespace or end-of-string
SENTENCE_BOUNDARY_RE = re.compile(r'[.!?;]\s+|[.!?;]$')

# ---------------------------------------------------------------------------
# System prompt — interpreter behavior (text mode)
# ---------------------------------------------------------------------------

INTERPRETER_PROMPT = (
    "You are FLOW, a real-time interpreter robot. You ONLY translate.\n"
    "You have NO other purpose. You do not chat, explain, or improvise.\n\n"
    "Your ONLY task:\n"
    "1. Read the [SOURCE LANGUAGE → TARGET LANGUAGE] direction indicator\n"
    "2. Translate the text that follows into the TARGET LANGUAGE\n"
    "3. Output ONLY the translation — nothing else\n\n"
    "MANDATORY RULES — never break these:\n"
    "- OUTPUT MUST BE in the TARGET language — always, without exception\n"
    "- NEVER output the source text unchanged — even single words must be translated\n"
    "- NEVER echo or repeat the source language\n"
    "- Preserve tone and register exactly (formal stays formal, casual stays casual)\n"
    "- Translate MEANING and INTENT — not words. Reconstruct what the speaker meant.\n"
    "- Do NOT add, remove, or rephrase content beyond what natural expression requires\n"
    "- Do NOT add acknowledgments, commentary, or explanations\n"
)


# ---------------------------------------------------------------------------
# Model loading (at startup)
# ---------------------------------------------------------------------------

log("[flow-local] Warming up mlx-whisper (downloads model on first run, ~200MB)…")
# Use low-amplitude noise (not silence) so Whisper runs the full decoder path
# and compiles all Metal shaders at startup rather than during the first user turn.
_warmup_audio = (np.random.default_rng(0).standard_normal(16000 * 2)
                 .astype(np.float32) * 0.05)
mlx_whisper.transcribe(_warmup_audio, path_or_hf_repo=MLX_WHISPER_MODEL, verbose=False,
                       condition_on_previous_text=False)
log(f"[flow-local] mlx-whisper '{MLX_WHISPER_MODEL}' ready (Apple ANE)")

log("[flow-local] Loading Piper voices...")
piper_voice_en = PiperVoice.load(str(PIPER_MODELS_DIR / "en_US-lessac-high.onnx"))
piper_voice_pt = PiperVoice.load(str(PIPER_MODELS_DIR / "pt_BR-faber-medium.onnx"))
PIPER_RATE_EN = piper_voice_en.config.sample_rate
PIPER_RATE_PT = piper_voice_pt.config.sample_rate
log(f"[flow-local] Piper voices loaded (EN={PIPER_RATE_EN}Hz, PT={PIPER_RATE_PT}Hz)")

log("[flow-local] Loading Silero VAD...")
VAD_ONNX_PATH = str(
    Path(onnxruntime.__file__).parent.parent
    / "faster_whisper" / "assets" / "silero_vad_v6.onnx"
)
# Verify it exists, fall back to finding it
if not Path(VAD_ONNX_PATH).exists():
    from faster_whisper.vad import get_assets_path
    VAD_ONNX_PATH = str(Path(get_assets_path()) / "silero_vad_v6.onnx")
log(f"[flow-local] Silero VAD at: {VAD_ONNX_PATH}")

# Pre-create a single shared ONNX InferenceSession for Silero VAD.
# Creating it per-connection (inside websocket_handler) is a synchronous blocking call
# that takes 7–9 seconds on first use, because onnxruntime must load the model from disk,
# parse the ONNX graph, and compile a CPU execution plan — all on the asyncio event loop.
# One session is safe to share: InferenceSession.Run() is thread-safe, and the LSTM state
# (h, c, context) lives on each StreamingVAD instance, not inside the session object.
_vad_opts = onnxruntime.SessionOptions()
_vad_opts.inter_op_num_threads = 1
_vad_opts.intra_op_num_threads = 1
_VAD_SESSION = onnxruntime.InferenceSession(
    VAD_ONNX_PATH,
    providers=["CPUExecutionProvider"],
    sess_options=_vad_opts,
)
log("[flow-local] Silero VAD ONNX session ready (shared across connections)")


# ---------------------------------------------------------------------------
# Audio utilities
# ---------------------------------------------------------------------------

def resample(audio, input_rate, output_rate):
    """Linear interpolation resampler."""
    if input_rate == output_rate:
        return audio
    ratio = input_rate / output_rate
    output_len = int(len(audio) / ratio)
    indices = np.arange(output_len) * ratio
    low = np.floor(indices).astype(int)
    high = np.minimum(low + 1, len(audio) - 1)
    frac = (indices - low).astype(np.float32)
    return audio[low] * (1 - frac) + audio[high] * frac


def decode_browser_audio(b64_pcm16):
    """Decode base64 PCM16 24kHz from browser → float32 numpy array."""
    raw = base64.b64decode(b64_pcm16)
    int16 = np.frombuffer(raw, dtype=np.int16)
    return int16.astype(np.float32) / 32768.0


def float32_to_pcm16_b64(audio_float32):
    """Float32 numpy → PCM16 → base64 string."""
    int16 = np.clip(audio_float32 * 32767, -32768, 32767).astype(np.int16)
    raw = int16.tobytes()
    return base64.b64encode(raw).decode("ascii")


# ---------------------------------------------------------------------------
# Streaming Silero VAD
# ---------------------------------------------------------------------------

class StreamingVAD:
    """
    Processes audio in real-time, detects speech boundaries.
    Calls ONNX Silero VAD directly with persistent LSTM state.
    """

    def __init__(
        self,
        threshold=VAD_THRESHOLD,
        neg_threshold=VAD_NEG_THRESHOLD,
        silence_ms=SILENCE_DURATION_MS,
        min_speech_ms=MIN_SPEECH_MS,
        max_speech_s=MAX_SPEECH_S,
        sample_rate=VAD_SAMPLE_RATE,
        session=None,   # pre-created InferenceSession; creates its own if None (test use)
    ):
        self.threshold = threshold
        self.neg_threshold = neg_threshold
        self.silence_samples = int(silence_ms * sample_rate / 1000)
        self.min_speech_samples = int(min_speech_ms * sample_rate / 1000)
        self.max_speech_samples = int(max_speech_s * sample_rate)
        self.sample_rate = sample_rate

        # ONNX session — reuse the global pre-created session when provided.
        # InferenceSession.Run() is thread-safe; LSTM state (h, c, context) is per-instance.
        if session is not None:
            self.session = session
        else:
            opts = onnxruntime.SessionOptions()
            opts.inter_op_num_threads = 1
            opts.intra_op_num_threads = 1
            self.session = onnxruntime.InferenceSession(
                VAD_ONNX_PATH,
                providers=["CPUExecutionProvider"],
                sess_options=opts,
            )

        # Persistent LSTM state
        self.h = np.zeros((1, 1, 128), dtype="float32")
        self.c = np.zeros((1, 1, 128), dtype="float32")
        self.context = np.zeros(VAD_CONTEXT, dtype="float32")

        # State machine
        self.is_speaking = False
        self.silence_counter = 0
        self.speech_buffer = []  # list of float32 arrays
        self.speech_samples_count = 0
        self.pending = np.array([], dtype="float32")  # incomplete window buffer

    def reset_state(self):
        """Reset LSTM state for new session."""
        self.h = np.zeros((1, 1, 128), dtype="float32")
        self.c = np.zeros((1, 1, 128), dtype="float32")
        self.context = np.zeros(VAD_CONTEXT, dtype="float32")

    def reset_full(self):
        """Full reset: LSTM state + speech detection state machine.
        Call after TTS playback to prevent echo-triggered false speech detection."""
        self.reset_state()
        self.is_speaking = False
        self.silence_counter = 0
        self.speech_buffer = []
        self.speech_samples_count = 0
        self.pending = np.array([], dtype="float32")

    def force_finalize(self):
        """Called when client sends explicit speech_stopped (orb released).
        Immediately emits speech_stopped with the accumulated buffer — skips the
        silence wait entirely. Safe no-op if VAD is not mid-speech."""
        if not self.is_speaking or not self.speech_buffer:
            return []
        self.is_speaking = False
        # Do NOT trim trailing silence — button release is the explicit boundary.
        # Trimming would remove valid speech content when the user pauses before releasing.
        # Include any partial VAD window in pending so no audio is lost at utterance end.
        buffers = self.speech_buffer
        if len(self.pending) > 0:
            buffers = buffers + [self.pending]
        segment = np.concatenate(buffers)
        self.speech_buffer = []
        self.speech_samples_count = 0
        self.silence_counter = 0
        self.pending = np.array([], dtype="float32")
        if len(segment) >= self.min_speech_samples:
            return [("speech_stopped", segment)]
        return [("speech_stopped_short",)]

    def _run_vad_window(self, window_512):
        """Run VAD on a single 512-sample window. Returns speech probability."""
        # Prepend context
        input_frame = np.concatenate([self.context, window_512])
        input_frame = input_frame.reshape(1, -1)  # (1, 576)

        output, self.h, self.c = self.session.run(
            None,
            {"input": input_frame, "h": self.h, "c": self.c},
        )

        # Update context
        self.context = window_512[-VAD_CONTEXT:]

        # output shape is (1,) — single probability value
        return float(output[0])

    def process_chunk(self, audio_16k):
        """
        Process a chunk of 16kHz float32 audio.
        Returns list of events: [("speech_started",), ("speech_stopped", audio_segment)]
        """
        events = []

        # Append to pending buffer
        self.pending = np.concatenate([self.pending, audio_16k])

        # Process all complete 512-sample windows
        while len(self.pending) >= VAD_WINDOW:
            window = self.pending[:VAD_WINDOW]
            self.pending = self.pending[VAD_WINDOW:]

            prob = self._run_vad_window(window)

            if not self.is_speaking:
                # Currently idle — check if speech starts
                if prob >= self.threshold:
                    self.is_speaking = True
                    self.silence_counter = 0
                    self.speech_buffer = [window]
                    self.speech_samples_count = VAD_WINDOW
                    events.append(("speech_started",))
            else:
                # Currently speaking — accumulate audio
                self.speech_buffer.append(window)
                self.speech_samples_count += VAD_WINDOW

                if prob < self.neg_threshold:
                    self.silence_counter += VAD_WINDOW
                else:
                    self.silence_counter = 0

                # Hard cap only — silence threshold deliberately suppressed.
                # Turn end is controlled exclusively by button release (force_finalize).
                # User can pause naturally while holding without being cut off.
                force_stop = self.speech_samples_count >= self.max_speech_samples
                if force_stop:
                    log(f"[flow-local] VAD: hard cap ({MAX_SPEECH_S}s) hit, forcing segment end")
                    self.is_speaking = False

                    if self.speech_samples_count >= self.min_speech_samples:
                        segment = np.concatenate(self.speech_buffer)
                        events.append(("speech_stopped", segment))
                    else:
                        events.append(("speech_stopped_short",))

                    self.speech_buffer = []
                    self.speech_samples_count = 0
                    self.silence_counter = 0

        return events


# ---------------------------------------------------------------------------
# STT: faster-whisper transcription
# ---------------------------------------------------------------------------

def compute_rms(audio):
    """Compute RMS energy of an audio segment."""
    return float(np.sqrt(np.mean(audio ** 2)))


def normalize_lang(raw_lang):
    """
    Normalize detected language to canonical form.

    Returns:
        "en" or "pt-BR" (normalized)
        Converts pt, pt-pt, pt-br variants → pt-BR
        Converts other languages to last stable lang fallback
    """
    if not raw_lang:
        return None

    raw_lower = raw_lang.lower().strip()

    # English
    if raw_lower == "en" or raw_lower.startswith("en-"):
        return "en"

    # Portuguese (all variants normalize to pt-BR)
    if raw_lower.startswith("pt"):
        return "pt-BR"

    # Unsupported language detected (ru, it, sq, etc.)
    return None


def is_gibberish(text):
    """Detect noise/gibberish: repeated chars, no vowels, too short, unbalanced tokens."""
    t = text.strip()
    if len(t) < 3:
        return True

    # Check for excessive repeated characters (aaaaaa, bbbbb = noise)
    for char in set(t.lower()):
        if char.isalpha() and t.lower().count(char) > len(t) * 0.5:  # >50% same char
            return True

    # Check vowel/consonant balance (gibberish has almost no vowels)
    vowels = sum(1 for c in t.lower() if c in 'aeiouáéíóú')
    if len(t) > 5 and vowels < len(t) * 0.2:  # <20% vowels = unnatural
        return True

    return False

def _clean_repetition_hallucinations(text: str) -> str:
    """
    Collapse Whisper repetition artifacts that condition_on_previous_text=False
    may not fully prevent.

    Two passes:
    1. Single token repeated >3 times in a row → 1 occurrence
       e.g. "yes yes yes yes yes" → "yes"
    2. Short phrase (2–6 words) repeated 3+ times in a row → 1 occurrence
       e.g. "I don't know I don't know I don't know" → "I don't know"
    """
    # Pass 1: same word 4+ times consecutively
    text = re.sub(r'\b(\w+)(?:\s+\1){3,}', r'\1', text, flags=re.IGNORECASE)
    # Pass 2: same 2–6 word phrase 3+ times consecutively
    text = re.sub(r'\b(\w+(?:\s+\w+){1,5})(?:\s+\1){2,}', r'\1', text, flags=re.IGNORECASE)
    return text


def is_hallucination(text):
    """Check if Whisper output is a known hallucination pattern."""
    # First check for gibberish
    if is_gibberish(text):
        return True

    t = text.strip().lower().rstrip(".").rstrip("!")
    if len(t) < MIN_TRANSCRIPTION_CHARS:
        return True
    # Exact match for known patterns
    if t in HALLUCINATION_PATTERNS:
        return True
    # Partial match for obvious cases (subscribe, thank you, bye, etc.)
    hallucination_keywords = ["subscribe", "thank you", "bye", "like and subscribe", "for watching"]
    if any(keyword in t for keyword in hallucination_keywords):
        # But allow if it's clearly part of a longer meaningful phrase
        if len(t) > len(hallucination_keywords[0]) + 5:
            return False  # Likely part of a longer phrase
        return True
    return False


def transcribe_segment(audio_16k, forced_source_language=None, skip_dual=False, stable_lang=None):
    """
    Transcribe a speech segment using mlx-whisper (Apple Silicon ANE).
    Returns (text, language, confidence).

    Args:
        forced_source_language: Manual user preference only (from UI settings).
            NOT stable_lang — that would force Whisper to transcribe echo as wrong language.
        skip_dual: When True, skip the expensive 3-pass dual-transcription retry.
            Set to True when stable_lang is known (language already established).
        stable_lang: The session's established language ("en" or "pt-BR"), or None on cold start.
            Used to add a small score bias toward the session language in dual-transcription
            candidate selection — prevents random language flips on misdetection recovery.

    Robust strategy:
    - Use optional source-language hint when provided.
    - If auto-detect returns unsupported/misdetected language, retry with PT and EN forced.
    - Prefer non-hallucinated, longer candidate text.
    """
    # Peak-window energy check.
    # Slide non-overlapping ENERGY_WINDOW_SAMPLES windows and take the maximum RMS.
    # Rationale: global RMS (mean across all samples) under-reports energy for long
    # turns where speech is surrounded by natural pauses — the silence samples drag
    # the mean below MIN_ENERGY_RMS even when speech windows are clearly audible.
    # Peak-window RMS asks "is there ANY 0.5s window with speech?" which is the right
    # question. Truly silent turns still fail: all windows stay at ambient ~0.0003-0.001.
    n = len(audio_16k)
    if n <= ENERGY_WINDOW_SAMPLES:
        peak_rms = compute_rms(audio_16k)
    else:
        peak_rms = max(
            compute_rms(audio_16k[i : i + ENERGY_WINDOW_SAMPLES])
            for i in range(0, n - ENERGY_WINDOW_SAMPLES + 1, ENERGY_WINDOW_SAMPLES)
        )
    if peak_rms < MIN_ENERGY_RMS:
        log(f"[flow-local] Energy too low (peak_rms={peak_rms:.5f}), skipping")
        return "", "unknown", 0.0

    def transcribe_once(lang_hint=None):
        # initial_prompt biases Whisper toward correct transcription:
        # - Portuguese: seeds diacritics (ã, ç, é, ô) so decoder favors accented chars
        # - English: seeds West African / Caribbean accent awareness + food vocabulary
        #   so the decoder resolves "rice and peach" → "rice and peas" at inference time
        #   (Whisper treats the prompt as prior decoded text, shifting next-token probs)
        if lang_hint == "pt":
            prompt = "Transcrição de áudio em português brasileiro. Atenção às acentuações: ã, õ, ç, é, ê, ó, ô, á, à, ú, í."
        elif lang_hint == "en":
            prompt = (
                "Transcription of English with West African and Caribbean accents. "
                "Common food terms: rice and peas, plantain, jollof, fufu, egusi, suya. "
                # Financial and everyday vocabulary that accent-sensitive speakers commonly
                # have misheard: money/Manny, budget/buggy, building/billing, people/poiple.
                # Listing them as prior context shifts Whisper's next-token probabilities
                # toward these forms without overriding clear audio evidence.
                "Financial terms: money, payment, budget, transfer, funds, account, income, cost, price, business. "
                "Common words: people, building, really, actually, something, everything, going, today."
            )
        else:
            # Auto-detect pass: minimal vocabulary hint only — no language label that could
            # bias language detection. Adds financial domain context for accent-sensitive
            # word resolution on the main (non-retry) transcription path.
            prompt = (
                "money, payment, budget, people, building, really, actually, something, today."
            )
        # mlx-whisper only supports greedy decoding; beam_size > 1 raises NotImplementedError
        log(f"[flow-local] STT decode: model={MLX_WHISPER_MODEL} lang={lang_hint!r} "
            f"mode=greedy prompt={'yes' if prompt else 'no'}")
        result = mlx_whisper.transcribe(
            audio_16k,
            path_or_hf_repo=MLX_WHISPER_MODEL,
            language=lang_hint,
            initial_prompt=prompt,
            verbose=False,
            condition_on_previous_text=False,
        )
        raw_lang = result.get("language") or lang_hint or "unknown"
        segs = result.get("segments", [])
        if segs:
            avg_nsp = sum(s.get("no_speech_prob", 0.1) for s in segs) / len(segs)
            conf = max(0.0, min(1.0, 1.0 - avg_nsp))
        else:
            conf = 0.5  # no segment metadata → neutral (was 0.8, falsely confident)
        txt = result.get("text", "").strip()
        # language_probs is only populated on auto-detect pass (language=None).
        # Callers store this to gate which forced language to try for recovery.
        lp = result.get("language_probs") or {}
        return txt, raw_lang, conf, lp

    # Optional source-language hint from client settings
    whisper_lang = None
    if forced_source_language:
        f = forced_source_language.lower()
        if f.startswith("pt"):
            whisper_lang = "pt"
        elif f.startswith("en"):
            whisper_lang = "en"

    text, raw_lang, confidence, auto_lp = transcribe_once(whisper_lang)

    # Dual-transcription for short segments OR unsupported languages:
    # Short Portuguese words ("Olá", "Obrigado") often get misdetected as other languages.
    # Always try both PT and EN forced transcription and pick the best result.
    duration_s = len(audio_16k) / 16000
    supported = (raw_lang == "en" or str(raw_lang).startswith("pt"))
    # Retry only when:
    #  - auto-detect returned an unsupported language (must try PT/EN to find correct one), OR
    #  - segment is short AND confidence is genuinely ambiguous (below MIN_DUAL_CANDIDATE_CONF).
    # Do NOT retry when auto-detect already returned a supported language with adequate
    # confidence — retrying then risks a longer but uncertain forced-EN output overriding
    # a correct PT detection, flipping the translation direction.
    #
    # skip_dual is an optimization for established sessions: skips the expensive retry when
    # the language is already known and supported. It does NOT apply to unsupported-language
    # detections (e.g. Yoruba, Igbo) — those always need a retry because they have no other
    # recovery path; without retry they silently return an empty transcript.
    needs_retry = (whisper_lang is None) and (
        not supported                   # unsupported lang: always retry regardless of skip_dual
        or (not skip_dual and duration_s < 2.0 and confidence < MIN_DUAL_CANDIDATE_CONF)
    )

    if needs_retry:
        if not supported and skip_dual:
            log(f"[flow-local] ⚠️ Dual-transcription forced: unsupported lang '{raw_lang}' detected in established session (skip_dual override)")
        reason = "unsupported_lang" if not supported else "short_segment"
        log(f"[flow-local] Dual-transcription ({reason}): auto='{raw_lang}' text='{text}' dur={duration_s:.1f}s")
        candidates = []
        # Normalize stable_lang once for bias comparisons below.
        _stable_norm = normalize_lang(stable_lang) if stable_lang else None

        # Length coefficient for candidate scoring.
        # Unsupported-lang recovery: use 0.005 so confidence dominates.
        #   Whisper is genuinely more confident on the correct source language, making
        #   confidence the right signal. The full 0.02 would let a translated PT string
        #   (longer) beat a short high-confidence EN transcription.
        # Short-segment retry: keep 0.02 — length is meaningful for distinguishing
        #   real PT phrases from EN hallucinations on ambiguous audio.
        _len_coef = 0.005 if not supported else 0.02

        # Keep auto-detect result if it's supported, non-hallucinated, and confident enough.
        # The confidence gate prevents a longer but uncertain transcript winning via
        # the len*0.02 term when we're genuinely unsure what was said.
        if supported and text and not is_hallucination(text) and confidence >= MIN_DUAL_CANDIDATE_CONF:
            score = (len(text) * _len_coef) + confidence
            if _stable_norm and normalize_lang(raw_lang) == _stable_norm:
                score += STABLE_LANG_BIAS   # prefer session language on recovery turns
            candidates.append((score, text, raw_lang, confidence))
        # Try forced language pass(es).
        # Priority order for choosing which forced language(s) to run:
        #
        # 1. Session-lock (established session + unsupported detect):
        #    Only try the session's stable language — prevents direction flip.
        #
        # 2. LP-gate (cold-start + unsupported detect):
        #    Use Whisper's language_probs from the auto-detect pass as an oracle.
        #    language_probs is computed by Whisper's encoder BEFORE decoding, so it
        #    reflects the actual language of the audio regardless of the detected label.
        #    Example: English audio misdetected as "yo" → lp["en"]=0.42, lp["pt"]=0.04.
        #    If |lp_en - lp_pt| > LP_GATE_MIN_DELTA, only run the more probable language.
        #    This eliminates the "translated candidate wins" problem: Whisper can generate
        #    fluent PT text from English audio with similar confidence, so score-based
        #    selection is unreliable when both candidates are in the running.
        #    Fall back to both if probs are genuinely ambiguous (< LP_GATE_MIN_DELTA apart).
        #
        # 3. Short-ambiguous-segment retry: always try both PT and EN.
        LP_GATE_MIN_DELTA = 0.05   # minimum |lp_en - lp_pt| to trust the oracle
        if _stable_norm and not supported:
            _hints = [(h, c) for h, c in (("pt", "pt"), ("en", "en"))
                      if normalize_lang(c) == _stable_norm]
            log(f"[flow-local] Session-lock: unsupported lang in established session — only trying '{stable_lang}' candidate")
        elif not supported and auto_lp:
            # LP-gate: Whisper already knows which language this audio is most likely in.
            lp_en = auto_lp.get("en", 0.0)
            lp_pt = max((v for k, v in auto_lp.items() if k.startswith("pt")), default=0.0)
            if abs(lp_en - lp_pt) > LP_GATE_MIN_DELTA:
                _oracle = "en" if lp_en > lp_pt else "pt"
                _hints = [(_oracle, _oracle)]
                log(f"[flow-local] LP-gate: lp_en={lp_en:.3f} lp_pt={lp_pt:.3f} → only trying '{_oracle}'")
            else:
                _hints = [("pt", "pt"), ("en", "en")]
                log(f"[flow-local] LP-gate: lp_en={lp_en:.3f} lp_pt={lp_pt:.3f} — ambiguous, trying both")
        else:
            _hints = [("pt", "pt"), ("en", "en")]
        for hint, canon in _hints:
            t2, l2, c2, _ = transcribe_once(hint)
            if t2 and not is_hallucination(t2) and c2 >= MIN_DUAL_CANDIDATE_CONF:
                score = (len(t2) * _len_coef) + c2
                if _stable_norm and normalize_lang(l2 or canon) == _stable_norm:
                    score += STABLE_LANG_BIAS   # prefer session language on recovery turns
                candidates.append((score, t2, l2 or canon, c2))

        if candidates:
            candidates.sort(key=lambda x: x[0], reverse=True)
            _, text, raw_lang, confidence = candidates[0]
            log(f"[flow-local] Dual-transcription picked: lang={raw_lang} conf={confidence:.2f} text='{text}'")
        elif not supported:
            return "", raw_lang, confidence

    # If forced source language is set, trust it as final language family
    if whisper_lang == "pt":
        lang = "pt-BR"
    elif whisper_lang == "en":
        lang = "en"
    elif raw_lang == "en" or str(raw_lang).startswith("pt"):
        lang = raw_lang
    else:
        # Unsupported language detected (e.g. "yo" Yoruba, "ig" Igbo for Nigerian Pidgin).
        # If the text is ASCII-dominant it is almost certainly Latin-script Pidgin/creole,
        # not a genuinely foreign language — rescue it as English rather than discarding.
        alpha = [c for c in text if c.isalpha()]
        if alpha and text and not is_hallucination(text) and \
                confidence >= MIN_CONFIDENCE_STT and \
                sum(1 for c in alpha if ord(c) < 128) / len(alpha) >= 0.85:
            log(f"[flow-local] Unsupported lang '{raw_lang}' but text is ASCII-dominant — rescued as 'en' (conf={confidence:.2f})")
            lang = "en"
        else:
            return "", raw_lang, confidence

    # Hallucination guard
    if is_hallucination(text):
        log(f"[flow-local] Hallucination filtered: '{text}'")
        return "", lang, confidence

    return text, lang, confidence


# ---------------------------------------------------------------------------
# Pass 1 — Phonetic confusion rescue  (STT mistranscription correction)
# ---------------------------------------------------------------------------
#
# Corrects high-confidence phonetic near-misses before the slang/shorthand
# layer runs. Must stay conservative: phrase-level or sentence-position-
# anchored patterns only — never single ambiguous words.
#
# Run ORDER: phonetic (pass 1) → slang/shorthand (pass 2).
# This matters because phonetic rescue produces canonical Pidgin forms
# ("picking" → "pikin") that the slang layer then normalises ("pikin" → "child").

_PHONETIC_EN: list[tuple[re.Pattern, str]] = [
    # "no feet" → "no fit"  (phonetic: feet/fit; Pidgin for "can't")
    # "no feet" is not a standard English idiom — safe to replace.
    (re.compile(r"\bno\s+feet\b",                re.IGNORECASE), "no fit"),
    # "my picking" → "my pikin"  (possessive collapses the gerund reading)
    (re.compile(r"\bmy\s+picking\b",              re.IGNORECASE), "my pikin"),
    # "picking dem" → "pikin dem"  (Pidgin plural — never standard English)
    (re.compile(r"\bpicking\s+dem\b",             re.IGNORECASE), "pikin dem"),
    # "a bag" / "a beg" at sentence start → "Abeg"  (please — Pidgin interjection)
    # Anchored to string-start so "I need a bag" is untouched.
    (re.compile(r"^a\s+(?:bag|beg)\b",            re.IGNORECASE), "Abeg"),
    # "good mourning" → "good morning"  ("mourning" = bereavement; never a greeting)
    (re.compile(r"\bgood\s+mourning\b",           re.IGNORECASE), "good morning"),
    # "tank you" → "thank you"  (th/t voicing; very common for non-native speakers)
    (re.compile(r"\btank\s+you\b",                re.IGNORECASE), "thank you"),

    # ── Food vocabulary (West African / Caribbean speech) ──────────────────
    # "rice and peach" → "rice and peas"  ("rice and peas" is the Caribbean dish;
    # "rice and peach" is not a real food dish; peas/peach = /z/ → /tʃ/ confusion)
    # Negative lookahead blocks known compound-food follow-words (peach cobbler, peach cake etc.)
    # but allows normal sentence continuations (please, for, is, at, …)
    (re.compile(
        r"\brice\s+and\s+peach(?:es)?\b(?!\s+(?:cobbler|cake|pie|tart|crumble|crisp|pudding|jam|galette|sorbet|mousse))",
        re.IGNORECASE,
    ), "rice and peas"),

    # ── Phrase-level STT confusion fixes ──────────────────────────────────
    # "view head of" → "you heard of"
    # Whisper hears accented /juː/ as /vjuː/ ("view") and drops the rhotic on "heard"
    # → "head".  "view head of" is not a valid English phrase; safe to rescue.
    (re.compile(r"\bview\s+head\s+of\b",          re.IGNORECASE), "you heard of"),
]

_PHONETIC_PT: list[tuple[re.Pattern, str]] = [
    # "duente" → "doente"  ("duente" is not a Portuguese word; "doente" = sick)
    (re.compile(r"\bduente\b",   re.IGNORECASE), "doente"),
    # Gerund nasal drop: -ndo → -no (fast speech; STT transcribes informal form)
    # None of the "-no" forms are valid PT-BR words, so false-positive risk = zero.
    (re.compile(r"\bfazeno\b",   re.IGNORECASE), "fazendo"),
    (re.compile(r"\bcomeno\b",   re.IGNORECASE), "comendo"),
    (re.compile(r"\bfalano\b",   re.IGNORECASE), "falando"),
    (re.compile(r"\bbebeno\b",   re.IGNORECASE), "bebendo"),   # drinking
    (re.compile(r"\bandano\b",   re.IGNORECASE), "andando"),   # walking / going
    (re.compile(r"\bdormino\b",  re.IGNORECASE), "dormindo"),  # sleeping
]


def phonetic_rescue(raw: str, lang: str) -> str:
    """
    Pass 1: correct known STT phonetic confusions.

    Patterns are phrase-level or string-position-anchored — no single-word
    substitutions that could hit legitimate vocabulary.
    Output is fed into rescue_transcript() (pass 2) for slang normalisation.
    """
    if not raw or not raw.strip():
        return raw
    rescued = raw.strip()
    patterns = _PHONETIC_EN if lang == "en" else _PHONETIC_PT if lang == "pt-BR" else []
    for pattern, replacement in patterns:
        rescued = pattern.sub(replacement, rescued)
    # Re-capitalise sentence start when the original opened with a capital
    if raw and raw[0].isupper() and rescued and rescued[0].islower():
        rescued = rescued[0].upper() + rescued[1:]
    return rescued


# ---------------------------------------------------------------------------
# Pass 2 — Slang / shorthand rescue  (internal only — raw shown to user)
# ---------------------------------------------------------------------------

# Nigerian Pidgin / West African English idiomatic forms → semantic equivalents.
# Longer phrases listed first to prevent partial matches (e.g. "my pikin dem"
# must be tried before the shorter "pikin dem" or "pikin").
_RESCUE_EN: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\babeg\b",              re.IGNORECASE), "please"),
    (re.compile(r"\bno\s+fit\b",          re.IGNORECASE), "can't"),
    (re.compile(r"\bmy\s+pikin\s+dem\b",  re.IGNORECASE), "my children"),
    (re.compile(r"\bpikin\s+dem\b",       re.IGNORECASE), "children"),
    (re.compile(r"\bmy\s+pikin\b",        re.IGNORECASE), "my child"),
    (re.compile(r"\bpikin\b",             re.IGNORECASE), "child"),
    (re.compile(r"\bno\s+wahala\b",       re.IGNORECASE), "no problem"),
    (re.compile(r"\bwahala\b",            re.IGNORECASE), "trouble"),
]

# Brazilian Portuguese informal contractions that STT commonly transcribes
# without diacritics. Word-boundary anchored — safe against mid-word hits.
_RESCUE_PT: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\bnao\b",  re.IGNORECASE), "não"),
    (re.compile(r"\bvc\b",   re.IGNORECASE), "você"),
    (re.compile(r"\bpra\b",  re.IGNORECASE), "para"),
    (re.compile(r"\bta\b",   re.IGNORECASE), "tá"),
]


def rescue_transcript(raw: str, lang: str) -> str:
    """
    Lightweight rule-based rescue for diaspora / accented / informal speech.

    Returns a version of the transcript better suited for LLM translation.
    This output goes to the LLM only — the raw STT text is always shown to
    the user unchanged.

    Philosophy:
      - Resolve unambiguous lexical gaps (Pidgin vocabulary the LLM won't know)
      - Restore diacritics the STT may have dropped (PT-BR informal forms)
      - Preserve register and tone — no grammatical rewriting
      - Conservative: only high-confidence, unambiguous substitutions
    """
    if not raw or not raw.strip():
        return raw

    rescued = raw.strip()
    patterns = _RESCUE_EN if lang == "en" else _RESCUE_PT if lang == "pt-BR" else []
    for pattern, replacement in patterns:
        rescued = pattern.sub(replacement, rescued)

    # Re-capitalise sentence start when the original opened with a capital letter
    if raw and raw[0].isupper() and rescued and rescued[0].islower():
        rescued = rescued[0].upper() + rescued[1:]

    return rescued


# ---------------------------------------------------------------------------
# 3-Lane Gate — helpers
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Accent normalization — EN only, evidence-gated.
# Rules are added ONLY after checkpoint evidence (N≥5 real failures).
# Keep this block narrow. False negatives are safer than false positives.
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Compiled accent-normalization patterns — EN only.
# Each regex is compiled once at import time (zero per-turn overhead).
# Rules require real failure evidence before addition.
# ---------------------------------------------------------------------------

# "axed" → "asked": ax/ask metathesis (African + AAVE English).
# Fires only when followed by personal pronoun or question complement.
# Does NOT fire on: "got axed", "axed the project", "axed his budget".
_ACCENT_AX_RE = re.compile(
    r'\baxed\b(?=\s+(?:me|him|her|them|us|you|if|whether|what|where|when|why|how|about)\b)',
    re.IGNORECASE,
)

# "seat down" → "sat down": vowel tensing /æ/ → /iː/ ("sat" heard as "seat").
# Pronoun guard required — fires only when a subject pronoun directly precedes
# "seat down", so "take a seat down here" (noun phrase) is never touched.
_ACCENT_SEAT_DOWN_RE = re.compile(
    r'\b(I|he|she|they|we|you)\s+seat\s+down\b',
    re.IGNORECASE,
)

# "[modal] of" → "[modal] have": contracted "have" ('v) sounds like "of".
# "would of / could of / should of / must of / might of" are never grammatically
# correct in any English variety.
# Negative lookahead excludes "of course" — the one common false-positive risk.
_ACCENT_MODAL_OF_RE = re.compile(
    r'\b(would|could|should|must|might)\s+of\b(?!\s+course\b)',
    re.IGNORECASE,
)


def _normalize_accent_en(text: str) -> str:
    """
    Pass 3 of the rescue chain — evidence-backed EN accent normalization.

    Called after phonetic_rescue (pass 1) and rescue_transcript (pass 2),
    EN-only gated, so changes are captured in rescue_changed_count and
    logged automatically in accent_failures.jsonl.

    Rules are intentionally narrow. Each rule must have checkpoint evidence.
    Candidates without evidence yet (suppose-to, use-to, tense agreement)
    are documented above and must NOT be added speculatively.
    """
    # ax/ask metathesis
    text = _ACCENT_AX_RE.sub('asked', text)
    # vowel tensing: [pronoun] seat down → [pronoun] sat down
    text = _ACCENT_SEAT_DOWN_RE.sub(r'\1 sat down', text)
    # modal + "of" → modal + "have"
    text = _ACCENT_MODAL_OF_RE.sub(r'\1 have', text)
    return text


def _count_rescue_changes(original: str, rescued: str) -> int:
    """
    Word-level edit distance between raw STT text and post-rescue text.
    Counts substituted words + length delta. Used as a brokenness signal:
    0–1 changes → probably fine; 2+ → original was too uncertain.
    """
    orig = original.lower().split()
    resc = rescued.lower().split()
    diff = sum(1 for a, b in zip(orig, resc) if a != b)
    diff += abs(len(orig) - len(resc))
    return diff


# ---------------------------------------------------------------------------
# Phase 1 accent-hardening helpers
# ---------------------------------------------------------------------------

def _looks_like_english(text: str) -> bool:
    """True if the transcript contains at least one unambiguous English function word."""
    words = set(re.sub(r"[^\w'\s]", "", text.lower()).split())
    return bool(words & _EN_DISCRIMINATING_WORDS)


def _english_plausible_from_state(stable_lang: str | None, active_lang: str) -> bool:
    """True if the session is currently oriented toward English turns."""
    norm = normalize_lang(stable_lang) if stable_lang else None
    if norm is not None:
        return norm.startswith("en")
    return active_lang.startswith("en")


def _should_retry_as_english(
    detected_lang: str,
    text: str,
    stable_lang: str | None,
    active_lang: str,
) -> bool:
    """
    Three-gate guard for forced-EN retry on unknown-lang drops.
    All three must pass — prevents catching PT/FR/ES clips.
    """
    if normalize_lang(detected_lang) is not None:
        return False                               # lang is known — no retry needed
    if not _looks_like_english(text):
        return False                               # no English signal in transcript
    if not _english_plausible_from_state(stable_lang, active_lang):
        return False                               # session not oriented toward English
    return True


def _write_accent_log(entry: dict) -> None:
    """Append one JSON line to the accent failure log. Silent on I/O error."""
    try:
        with open(ACCENT_LOG_PATH, 'a') as f:
            f.write(json.dumps(entry) + '\n')
    except Exception as e:
        log(f"[flow-local] accent_log write failed: {e}")


def _classify_turn_lane(
    text: str,
    detected_lang: str,
    stt_confidence: float,
    rescue_changed_count: int,
    stable_lang: str | None,
) -> tuple[str, str]:
    """
    Classify a turn into Lane A (direct translate), B (clarify then translate),
    or C (fail safely / request repeat).

    Returns (lane: 'A'|'B'|'C', reason: str).

    Priority order (first match wins):
      1. Unknown / unsupported language → C
      2. Confidence below weak floor → C
      3. High brokenness (≥2 signals) → C
      4. Below strong threshold OR any brokenness → B
      5. Otherwise → A
    """
    norm = normalize_lang(detected_lang)
    if norm is None:
        return 'C', f'unknown_lang ({detected_lang})'

    strong = CONF_STRONG_PT if norm.startswith("pt") else CONF_STRONG_EN

    if stt_confidence < CONF_WEAK_FLOOR:
        return 'C', f'below_floor ({stt_confidence:.2f}<{CONF_WEAK_FLOOR})'

    # Count brokenness signals — text-quality only, not session-state.
    # Lang-flip during bilingual switching is expected; the stability system handles it.
    brokenness = 0
    if len(text.strip().split()) < 2:            # single word — too short to infer meaning
        brokenness += 1
    if rescue_changed_count >= 2:                # rescue rewrote 2+ words — original was uncertain
        brokenness += 1

    # Routing is confidence-only. Brokenness is informational — logged but does not
    # independently trigger Lane B. Rationale:
    #   - A confident single word ("yes", conf=0.92) needs no clarification.
    #   - PT informal speech with 2+ rescue changes is correctly handled by the rescue
    #     chain; routing it to Lane B risks register-changing clarification on turns
    #     that Whisper understood fine.
    #   - Only low confidence predicts "the LLM might improve this."
    # Fast Lane C at CONF_WEAK_FLOOR=0.30 is the hard floor for truly bad input.
    if stt_confidence < strong:
        return 'B', f'conf={stt_confidence:.2f} strong={strong} brokenness={brokenness}'

    return 'A', f'conf={stt_confidence:.2f} brokenness={brokenness}'


# ---------------------------------------------------------------------------
# Pass 3 — Clarification layer (architecture stub — disabled by default)
# ---------------------------------------------------------------------------
#
# When CLARIFICATION_ENABLED = True (future), this pass sends the rescued
# transcript through a fast LLM prompt that:
#   - preserves source language (does NOT translate)
#   - preserves tone, register, urgency, and informality
#   - resolves genuinely ambiguous phrasing before the main translation
#
# Only runs on turns that reach this point (energy, confidence, gibberish
# guards have already passed), so the extra latency only hits real speech.
#
# Rationale for keeping disabled:
#   - Adds ~200–400ms latency per turn (a second Ollama round-trip)
#   - Direction + confidence fixes resolve the majority of current failures
#   - The phonetic + slang rescue chain covers the primary text-quality cases
#   - Activate after direction/confidence are stable and text quality is
#     confirmed to still be the bottleneck in live session metrics.

CLARIFICATION_ENABLED = False   # toggle to True to activate Lane B clarification

CLARIFICATION_PROMPT = (
    "Rewrite this utterance in the same language so the intended meaning is clear. "
    "Preserve tone, urgency, politeness, and informality. "
    "Do not translate. Do not explain. Output only the clarified utterance."
)


async def clarify_transcript(text: str, source_lang: str) -> str:
    """
    Lane B clarification pass: send the rescued transcript through a fast Ollama
    prompt that resolves ambiguous phrasing without translating.

    Pass-through when CLARIFICATION_ENABLED=False (default).
    Flip CLARIFICATION_ENABLED=True to activate after direction/confidence are stable.
    """
    if not CLARIFICATION_ENABLED or not text.strip():
        return text
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                OLLAMA_URL,
                json={
                    "model": OLLAMA_MODEL,
                    "messages": [
                        {"role": "system", "content": CLARIFICATION_PROMPT},
                        {"role": "user",   "content": text},
                    ],
                    "stream": False,
                    "options": {"temperature": 0.1, "num_predict": 150},
                },
            )
            data = resp.json()
            clarified = data.get("message", {}).get("content", "").strip()
            if clarified and not is_hallucination(clarified):
                log(f"[flow-local] Lane B clarification: '{text}' → '{clarified}'")
                return clarified
    except Exception as e:
        log(f"[flow-local] Clarification failed ({type(e).__name__}) — using original")
    return text


# ---------------------------------------------------------------------------
# Translation: Ollama streaming
# ---------------------------------------------------------------------------

def _norm_lang(lang):
    if not lang:
        return None
    l = str(lang).lower()
    if l.startswith("pt"):
        return "pt-BR"
    if l.startswith("en"):
        return "en"
    return l


# Portuguese stopwords used for post-LLM output validation.
# If an EN→PT-BR translation contains none of these, the LLM likely returned
# English text unchanged — treat as a translation failure.
_PT_STOPWORDS = frozenset({
    "de", "que", "e", "o", "a", "do", "da", "em", "um", "uma",
    "os", "as", "para", "com", "por", "se", "no", "na", "não",
    "é", "isso", "está", "são", "eu", "você", "nós", "ele", "ela",
    "mas", "mais", "muito", "bem", "quando", "como", "já",
})

def _looks_like_portuguese(text: str) -> bool:
    """Return True if text plausibly contains Portuguese.

    Short outputs (< 4 words) are given a pass — single-word translations
    like "OK" or "Sim" are valid without stopwords.
    """
    words = [w.strip(".,!?;:\"'").lower() for w in text.split()]
    if len(words) < 4:
        return True   # too short to judge — don't false-positive on valid short translations
    hits = sum(1 for w in words if w in _PT_STOPWORDS)
    return hits >= 1


# ---------------------------------------------------------------------------
# Pre-translation semantic cleanup  (hardened v2 + guardrails patch)
# ---------------------------------------------------------------------------
#
# GUARDRAIL LAW: Clean structure, not content. Never sanitize meaning.
#
#   Permitted removals:
#     - hesitation noise (um/uh/hmm) — zero semantic content, any position
#     - leading filler/discourse chains — ^ anchored, prefix only
#     - discourse glue ("I mean", "you know") — positionally safe anywhere
#     - consecutive word repetitions — collapses stutter, keeps one instance
#
#   NEVER removed or altered:
#     - explicit / strong language  ("f*ck", "damn", "merda", etc.)
#     - emotional wording           ("I hate", "I love", "I'm scared")
#     - raw intent words            verbs of desire/refusal/instruction
#     - mid-sentence content words  only ^ anchored patterns touch leading text
#
# Over-clean guard: _is_overcleaned(original, cleaned) → bool
#   If cleanup removed > 40% of word-count, the result is discarded and
#   the original is returned unchanged. Prevents cascade-removal on short
#   turns where fillers dominate (e.g. "like, um, yeah" → "" → fallback).
#
# Short-turn bypass in context store: turns < 5 words skip cleanup for
#   ctx storage and store the rescue-chain interpretation directly, ensuring
#   emotionally loaded short phrases are never silently stripped.

import re as _re

# Layer 1: collapse N consecutive identical words (with optional comma-spaces)
#   Matches: "like like like", "like, like, like", "so so"
#   Replaces with the single captured word.
_CONSEC_REPEAT = _re.compile(r'\b(\w+)(\s*,?\s+\1)+\b', _re.IGNORECASE)

# Layer 2: pure noise — safe to remove ANYWHERE (no semantic content ever)
_EN_NOISE = _re.compile(r'\b(um+|uh+|er+|hmm+|hm+)\b', _re.IGNORECASE)
_PT_NOISE = _re.compile(r'\b(hmm+|hm+|uh+|um+)\b',     _re.IGNORECASE)

# Layer 3a: discourse markers — safe anywhere (discourse glue, not content)
_EN_DISCOURSE = _re.compile(
    r'\b(you know what i mean|you know|i mean)\b',
    _re.IGNORECASE,
)
# "né" is unambiguously a PT-BR discourse tag; "sabe" could mean "knows" mid-sentence
# so we only handle it in the leading-chain pattern below.
_PT_DISCOURSE = _re.compile(r'\bné\b', _re.IGNORECASE)

# Layer 3b: LEADING filler chains — ^ anchored: only at start of string
#   Matches one or more filler words followed by comma/space, greedily.
#   "Like, so, yeah, basically what I..." → removes "Like, so, yeah, basically "
#   "I like this" — SAFE: no ^ match.
_EN_LEADING = _re.compile(
    r'^(?:(?:yeah|yep|yup|ah+|so|like|well|okay|ok|right|'
    r'basically|literally|actually)[,\s]*)+',
    _re.IGNORECASE,
)
_PT_LEADING = _re.compile(
    r'^(?:(?:tipo|assim|então|sabe|ah+)[,\s]*)+',
    _re.IGNORECASE,
)

_MULTI_SPACE = _re.compile(r' {2,}')
_LEAD_PUNCT  = _re.compile(r'^[,.\s]+')

# Over-clean threshold: if cleanup removes more than this fraction of the
# original word-count, it is considered overcleaned and the original is returned.
_OVERCLEAN_MAX_WORD_LOSS = 0.40   # 40% — conservative; most turns lose < 15%


def _is_overcleaned(original: str, cleaned: str) -> bool:
    """Return True if cleanup removed too many words from the original.

    Guard against cascade-removal on short turns where fillers dominate.
    Example: "like, um, yeah" (3 words) → "" is 100% loss → overcleaned.
    Example: "like, um, I need help" (5 words) → "I need help" (3) = 40% loss → boundary.

    GUARDRAIL: Clean structure, not content. Never sanitize meaning.
    """
    orig_words = original.split()
    if not orig_words:
        return False   # empty original — nothing to protect
    clean_words = cleaned.split()
    loss = (len(orig_words) - len(clean_words)) / len(orig_words)
    return loss > _OVERCLEAN_MAX_WORD_LOSS


# ---------------------------------------------------------------------------
# No-op translation guard — detect LLM output in same language as source
# ---------------------------------------------------------------------------
# Words that are UNIQUE to English (never appear in normal PT-BR text).
_EN_UNIQUE: frozenset = frozenset([
    "the", "is", "are", "was", "were", "have", "has", "had",
    "will", "would", "could", "should", "this", "that", "these",
    "those", "there", "their", "they", "with", "what", "when",
    "where", "which", "been", "being", "does", "did",
])
# Words/tokens unique to Portuguese (accented or structurally distinct).
_PT_UNIQUE: frozenset = frozenset([
    "é", "está", "são", "estão", "não", "você", "isso", "mais",
    "também", "aqui", "porque", "então", "muito", "mas", "bem",
    "meu", "minha", "nosso", "nossa", "dela", "dele", "agora",
    "ainda", "já", "vou", "vai", "foi", "ser", "ter", "fazer",
])


def _is_noop_output(input_text: str, output_text: str, source_lang: str, target_lang: str) -> bool:
    """Return True if LLM output is a no-op (wrong language or structurally identical to input).

    Three detection strategies (any one triggers no-op):
      1. Lexical similarity  — token-overlap ratio >= 0.8 vs input (LLM echoed the source).
      2. Direction mismatch  — output contains language markers belonging to source, not target.
      3. Short-sentence trap — < 3 output tokens but >= 2 shared with input (tiny echo).
    """
    out_words = re.findall(r"\b\w+\b", output_text.lower())
    inp_words = re.findall(r"\b\w+\b", input_text.lower())

    if not out_words:
        return False

    out_set = set(out_words)
    inp_set = set(inp_words)

    # Strategy 1: lexical similarity — Jaccard-like ratio on token sets
    if inp_set:
        overlap_ratio = len(out_set & inp_set) / max(len(out_set), len(inp_set))
        if overlap_ratio >= 0.8:
            return True

    # Strategy 3: short sentence — fewer than 3 tokens but 2+ shared with input
    if len(out_words) < 3 and len(out_set & inp_set) >= 2:
        return True

    # Strategy 2: direction mismatch — output language markers contradict target
    if target_lang.startswith("pt") and len(out_set & _EN_UNIQUE) >= 2:
        return True   # expected PT, output contains EN markers
    if target_lang.startswith("en") and len(out_set & _PT_UNIQUE) >= 1:
        return True   # expected EN, output contains PT markers

    return False


def _clean_input_text(text: str, source_lang: str = "en") -> str:
    """Strip speech fillers and collapse repeated words before translation.

    GUARDRAIL: Clean structure, not content. Never sanitize meaning.
    Permitted: hesitation noise, leading filler prefix, discourse glue.
    Forbidden: explicit language, emotional wording, raw intent.

    Passes (in order):
      1. Collapse consecutive repeated words: "like like like" → "like"
      2. Remove pure noise (um/uh/hmm) from anywhere
      3. Remove discourse markers ("I mean", "you know") from anywhere
      4. Strip LEADING filler chains ("Like, so, basically, …" prefix)
      5. Normalise whitespace + leading punctuation
      6. Over-clean guard: if > 40% of words removed → return original

    Rule-based only — no external libraries.
    Falls back to the original string if cleanup produces an empty result
    or triggers the over-clean guard.
    """
    original = text.strip()
    cleaned  = original

    # Pass 1: collapse consecutive identical words (loop until stable)
    # One re.sub pass reduces "like like like" → "like like" (only first pair).
    # The while-loop ensures full collapse regardless of repetition count.
    prev = None
    while prev != cleaned:
        prev = cleaned
        cleaned = _CONSEC_REPEAT.sub(r'\1', cleaned)

    # Passes 2-4: language-specific
    if source_lang.startswith("en"):
        cleaned = _EN_NOISE.sub("", cleaned)      # um/uh/hmm anywhere
        cleaned = _EN_DISCOURSE.sub("", cleaned)  # "I mean" / "you know" anywhere
        cleaned = _EN_LEADING.sub("", cleaned)    # leading filler chain only
    elif source_lang.startswith("pt"):
        cleaned = _PT_NOISE.sub("", cleaned)      # hmm/uh anywhere
        cleaned = _PT_DISCOURSE.sub("", cleaned)  # né anywhere
        cleaned = _PT_LEADING.sub("", cleaned)    # leading filler chain only

    # Pass 5: normalise whitespace + leading punctuation artifacts
    cleaned = _MULTI_SPACE.sub(" ", cleaned).strip()
    cleaned = _LEAD_PUNCT.sub("", cleaned).strip()

    # Pass 6: over-clean guard — discard result if too many words lost
    if not cleaned:
        return original   # empty result → always return original
    if _is_overcleaned(original, cleaned):
        log(f"[flow-local] [cleanup] overcleaned guard fired — returning original: '{original}'")
        return original

    return cleaned


def _clean_intent_text(text: str, source_lang: str = "en") -> str:
    """Pre-translation intent cleaner — strips fillers before LLM sees the text.

    Runs the same regex passes as _clean_input_text but with an independent
    70% over-clean guard (vs. 40%). Called explicitly in the websocket handler
    so the cleaned form is visible in logs and used as the translation input.

    Falls back to original if result is empty or > 70% of words were removed.
    Rule-based only — no external libraries.
    """
    original = text.strip()
    cleaned  = original

    # Pass 1: collapse consecutive repeated words (loop until stable)
    prev = None
    while prev != cleaned:
        prev = cleaned
        cleaned = _CONSEC_REPEAT.sub(r'\1', cleaned)

    # Passes 2–4: language-specific noise, discourse markers, leading fillers
    if source_lang.startswith("en"):
        cleaned = _EN_NOISE.sub("", cleaned)
        cleaned = _EN_DISCOURSE.sub("", cleaned)
        cleaned = _EN_LEADING.sub("", cleaned)
    elif source_lang.startswith("pt"):
        cleaned = _PT_NOISE.sub("", cleaned)
        cleaned = _PT_DISCOURSE.sub("", cleaned)
        cleaned = _PT_LEADING.sub("", cleaned)

    # Pass 5: normalise whitespace + leading punctuation artifacts
    cleaned = _MULTI_SPACE.sub(" ", cleaned).strip()
    cleaned = _LEAD_PUNCT.sub("", cleaned).strip()

    if not cleaned:
        return original   # empty result → always return original

    # 70% over-clean guard — stricter than _clean_input_text's 40% threshold.
    # Protects short turns where fillers dominate ("so like yeah" → "" would be 100% loss).
    orig_words  = original.split()
    clean_words = cleaned.split()
    if orig_words and (len(orig_words) - len(clean_words)) / len(orig_words) > 0.70:
        return original

    return cleaned


def _choose_translation_direction(source_language, forced_target_language=None):
    """Return (source_norm, target_lang, direction_hint, no_op)."""
    source_norm = _norm_lang(source_language) or "en"
    forced_norm = _norm_lang(forced_target_language)

    # Pair mode default: auto opposite target
    auto_target = "en" if source_norm.startswith("pt") else "pt-BR"
    chosen_target = forced_norm or auto_target

    # Hard block: EN→PT-BR is NEVER a no-op regardless of normalisation edge-cases.
    # Belt-and-suspenders: if the direction is explicitly cross-language, force the
    # translation path before the equality check below can fire.
    if source_norm == "en" and (chosen_target or "").startswith("pt"):
        return source_norm, chosen_target, "[English → Brazilian Portuguese] ", False
    if source_norm.startswith("pt") and chosen_target == "en":
        return source_norm, chosen_target, "[Portuguese → English] ", False

    # Guard: never translate source->same source when target is forced same
    if chosen_target == source_norm:
        return source_norm, chosen_target, None, True

    if source_norm.startswith("pt") and chosen_target == "en":
        return source_norm, chosen_target, "[Portuguese → English] ", False

    if source_norm == "en" and chosen_target.startswith("pt"):
        return source_norm, chosen_target, "[English → Brazilian Portuguese] ", False

    # Fallback to auto opposite target if forced target contradicts source
    chosen_target = auto_target
    if source_norm.startswith("pt"):
        return source_norm, chosen_target, "[Portuguese → English] ", False
    return source_norm, chosen_target, "[English → Brazilian Portuguese] ", False



# ---------------------------------------------------------------------------
# TTS: Piper synthesis → PCM16 24kHz → base64 chunks
# ---------------------------------------------------------------------------

def synthesize_audio(text, target_lang):
    """
    Synthesize text to PCM16 24kHz float32 array.
    Runs in thread pool (blocking).
    Returns float32 numpy array at 24kHz, or None on failure.
    """
    try:
        voice = piper_voice_pt if target_lang == "pt-BR" else piper_voice_en
        native_rate = PIPER_RATE_PT if target_lang == "pt-BR" else PIPER_RATE_EN

        # Synthesize — returns AudioChunk objects (one per sentence)
        chunks = []
        for audio_chunk in voice.synthesize(text):
            chunks.append(audio_chunk.audio_float_array)

        if not chunks:
            return None

        # Concatenate all sentence audio
        audio = np.concatenate(chunks)

        # Resample to 24kHz if needed
        if native_rate != INPUT_SAMPLE_RATE:
            audio = resample(audio, native_rate, INPUT_SAMPLE_RATE)

        return audio

    except Exception as e:
        log(f"[flow-local] TTS error: {e}")
        traceback.print_exc()
        return None


async def safe_send(ws, payload: dict) -> bool:
    """
    Send JSON to client, silently absorbing disconnect exceptions.
    Returns True on success, False if the connection is already gone.
    Spec §7 / §13: disconnect = normal exit, not exception.
    """
    try:
        await ws.send_json(payload)
        return True
    except (WebSocketDisconnect, ConnectionClosedError):
        return False
    except RuntimeError:
        # FastAPI raises RuntimeError("WebSocket is not connected") if
        # send is attempted after the transport has already closed.
        return False


async def synthesize_and_send(text, target_lang, client_ws):
    """Synthesize and stream audio chunks to browser."""
    loop = asyncio.get_event_loop()

    try:
        # Run TTS in thread pool to avoid blocking
        audio = await loop.run_in_executor(
            EXECUTOR,
            synthesize_audio,
            text,
            target_lang,
        )

        if audio is None or len(audio) == 0:
            log("[flow-local] ❌ TTS returned empty audio")
            await safe_send(client_ws, {"type": "error", "code": "TTS_FAILED", "message": "Could not generate audio response"})
            return

        # Chunk into ~2048 samples (~85ms at 24kHz) and send - reduced for lower perceived latency
        chunk_size = 2048
        for i in range(0, len(audio), chunk_size):
            chunk = audio[i : i + chunk_size]
            b64 = float32_to_pcm16_b64(chunk)
            if not await safe_send(client_ws, {"type": "audio_delta", "audio": b64}):
                return  # client gone — stop sending
    except Exception as e:
        log(f"[flow-local] ❌ TTS EXCEPTION: {type(e).__name__}: {e}")
        import traceback
        log(f"[flow-local] TTS Traceback:\n{traceback.format_exc()}")
        await safe_send(client_ws, {"type": "error", "code": "TTS_FAILED", "message": "Could not generate audio response"})


# ---------------------------------------------------------------------------
# Streaming pipeline: LLM translation → sentence-level TTS → audio chunks
# ---------------------------------------------------------------------------

async def translate_and_stream_tts(
    text: str,
    source_language: str,
    target_lang_override: str | None,
    client_ws: WebSocket,
    loop: asyncio.AbstractEventLoop,
    turn_id: int,
    barge_in_event: asyncio.Event,
    conv_ctx: "ConversationContext | None" = None,
    extra_instruction: str = "",             # injected on no-op retry; empty = normal call
) -> tuple[str, str, float, float, float]:
    """
    Streaming pipeline: LLM translation → sentence-level TTS → audio chunks.

    As the LLM generates tokens, we detect sentence boundaries and immediately
    synthesize + send each sentence. This overlaps LLM generation with TTS.

    conv_ctx: optional ConversationContext — if present and has a last_clean_meaning,
    its anchor_line() is appended to the system prompt to enable pronoun/topic
    resolution across turns. Zero latency cost — it's a string append before the
    first LLM call. No anchor → prompt is identical to baseline.

    Returns: (full_translation, target_lang, llm_ms, tts_first_audio_ms, tts_total_ms, llm_ttft_ms)
    """
    # INTENT CLEAN — choke-point: every translation path passes through here.
    # Runs before direction choice, prompt build, or any streaming logic.
    _intent_cleaned = _clean_intent_text(text, source_language)
    if _intent_cleaned != text:
        log(f"[intent_clean] raw='{text}' → cleaned='{_intent_cleaned}'")
    text = _intent_cleaned

    source_norm, target_lang, direction_hint, no_op = _choose_translation_direction(
        source_language, target_lang_override
    )

    log(f"[flow-local] Streaming pipeline: source={source_norm} target={target_lang} hint={direction_hint} no_op={no_op}")

    if no_op:
        await safe_send(client_ws, {"type": "translation_done", "text": text})
        return text, target_lang, 0.0, 0.0, 0.0, 0.0

    # Semantic cleanup: strip fillers, collapse repeats before sending to LLM.
    # SC-01: cleaner input → cleaner translation.
    # SC-02: falls back to original if cleanup empties the string.
    _raw_for_log = text
    text = _clean_input_text(text, source_norm)
    if text != _raw_for_log:
        log(f"[flow-local] Semantic cleanup: raw='{_raw_for_log}' cleaned='{text}'")

    log(f"[flow-local] Translating: '{text}'")

    llm_start = time.monotonic()
    llm_ttft_ms: float = 0.0          # time-to-first-token: llm_start → first delta
    llm_ttft_logged = False
    tts_first_audio_time = None
    tts_total_start = None
    full_text = ""
    pending_sentence = ""
    sentence_queue: asyncio.Queue = asyncio.Queue()
    tts_started = False
    sentences_sent = 0

    # Background task: consume sentence_queue, synthesize, send audio
    async def tts_consumer():
        nonlocal tts_first_audio_time, tts_total_start, tts_started, sentences_sent
        while True:
            item = await sentence_queue.get()
            if item is None:  # sentinel: LLM done
                break

            sentence_text, sentence_idx = item
            if not sentence_text.strip():
                continue

            # Check barge-in before each sentence
            if barge_in_event.is_set():
                log(f"[flow-local] Barge-in: skipping remaining TTS sentences")
                # Drain remaining queue
                while not sentence_queue.empty():
                    try:
                        sentence_queue.get_nowait()
                    except asyncio.QueueEmpty:
                        break
                break

            if tts_total_start is None:
                tts_total_start = time.monotonic()

            # Synthesize in thread pool
            t_synth = time.monotonic()
            try:
                audio = await loop.run_in_executor(
                    EXECUTOR, synthesize_audio, sentence_text, target_lang,
                )
                if sentence_idx == 0:
                    log(f"[flow-local] ⏱ tts_synth[0]={(time.monotonic()-t_synth)*1000:.0f}ms  text='{sentence_text[:40]}'")
            except Exception as e:
                log(f"[flow-local] TTS sentence {sentence_idx} error: {e}")
                continue

            if audio is None or len(audio) == 0:
                log(f"[flow-local] TTS sentence {sentence_idx} empty, skipping")
                continue

            # Send tts_start before first audio
            if not tts_started:
                tts_started = True
                if not await safe_send(client_ws, {"type": "tts_start"}):
                    return  # client gone
                tts_first_audio_time = time.monotonic()

            # Stream audio chunks (~85ms each at 24kHz)
            chunk_size = 2048
            chunk_n = 0
            for i in range(0, len(audio), chunk_size):
                if barge_in_event.is_set():
                    break
                chunk = audio[i : i + chunk_size]
                b64 = float32_to_pcm16_b64(chunk)
                if not await safe_send(client_ws, {"type": "audio_delta", "audio": b64}):
                    return  # client gone — stop sending
                if sentence_idx == 0 and chunk_n == 0:
                    t_wire = time.monotonic()
                    log(f"[flow-local] ⏱ first audio_delta sent  wire_delay={(t_wire - tts_first_audio_time)*1000:.1f}ms")
                chunk_n += 1

            sentences_sent += 1

    # Start TTS consumer as background task
    tts_task = asyncio.create_task(tts_consumer())
    sentence_idx = 0

    # Build the system prompt — base prompt + optional context anchor.
    # anchor_line() returns "" when this is the first turn or context has nothing
    # useful, so the prompt falls back to identical-to-baseline behavior.
    _anchor = conv_ctx.anchor_line() if conv_ctx else ""
    _system_prompt = INTERPRETER_PROMPT + ("\n" + _anchor if _anchor else "")
    if extra_instruction:
        _system_prompt += "\n" + extra_instruction   # no-op retry: stronger language enforcement
    if _anchor:
        log(f"[flow-local] [ctx] anchor injected: '{_anchor}'")

    # Stream LLM translation
    last_error = None
    for attempt in range(1, OLLAMA_RETRIES + 1):
        full_text = ""
        pending_sentence = ""
        try:
            client = await get_ollama_client()
            async with client.stream(
                "POST",
                OLLAMA_URL,
                json={
                    "model": OLLAMA_MODEL,
                    "messages": [
                        {"role": "system", "content": _system_prompt},
                        {"role": "user", "content": direction_hint + text},
                    ],
                    "stream": True,
                    "keep_alive": -1,          # keep model pinned; prevents eviction between sessions
                    "options": {"temperature": 0.1, "num_predict": 200},
                },
            ) as response:
                async for line in response.aiter_lines():
                    if not line.strip():
                        continue
                    try:
                        chunk = json.loads(line)
                        delta = chunk.get("message", {}).get("content", "")
                        if delta:
                            if not llm_ttft_logged:
                                llm_ttft_ms = (time.monotonic() - llm_start) * 1000
                                llm_ttft_logged = True
                            full_text += delta
                            pending_sentence += delta

                            # Check for sentence boundary
                            match = SENTENCE_BOUNDARY_RE.search(pending_sentence)
                            if match:
                                end_pos = match.end()
                                complete = pending_sentence[:end_pos].strip()
                                pending_sentence = pending_sentence[end_pos:]

                                if complete:
                                    # Stream text to client for progressive display
                                    await safe_send(client_ws, {
                                        "type": "translation_delta",
                                        "text": complete + " ",
                                    })
                                    # Queue for TTS
                                    await sentence_queue.put((complete, sentence_idx))
                                    sentence_idx += 1
                    except json.JSONDecodeError:
                        continue

            # LLM done — flush remaining text
            if pending_sentence.strip():
                await safe_send(client_ws, {
                    "type": "translation_delta",
                    "text": pending_sentence.strip(),
                })
                await sentence_queue.put((pending_sentence.strip(), sentence_idx))
                sentence_idx += 1

            # Signal TTS consumer to stop
            await sentence_queue.put(None)
            llm_ms = (time.monotonic() - llm_start) * 1000

            # Wait for TTS to finish
            await tts_task

            tts_first_ms = ((tts_first_audio_time - llm_start) * 1000) if tts_first_audio_time else 0
            tts_total_ms = ((time.monotonic() - tts_total_start) * 1000) if tts_total_start else 0

            log(f"[flow-local] LLM raw: '{full_text.strip()}'")
            log(f"[flow-local] Streaming done: LLM={llm_ms:.0f}ms TTFT={llm_ttft_ms:.0f}ms first_audio={tts_first_ms:.0f}ms tts_total={tts_total_ms:.0f}ms sentences={sentences_sent}")

            # ── Post-LLM translation validation — BOTH directions ──────────────
            # If the model returned the wrong language, catch it here and do ONE
            # non-streaming retry with a stronger explicit prompt.
            # TTS for this turn has already played; corrected text is returned
            # so the client transcript panel shows the right output.
            #
            # EN → PT-BR: output must look like Portuguese.
            # PT → EN:    output must look like English.
            # Max 1 retry per direction (SC-01/SC-02/SC-03 compliance).
            final_text = full_text.strip()

            # ── Direction A: EN → PT-BR ────────────────────────────────────────
            if source_norm == "en" and target_lang.startswith("pt") and not _looks_like_portuguese(final_text):
                log(f"[flow-local] ⚠️ EN→PT mismatch — output looks English ('{final_text[:60]}') — retrying")
                _retry_prompt = (
                    "Translate the following text from English to Brazilian Portuguese. "
                    "Do NOT repeat the original language. "
                    "Output ONLY the translated Portuguese sentence."
                )
                try:
                    _client = await get_ollama_client()
                    _retry_resp = await _client.post(
                        OLLAMA_URL,
                        json={
                            "model": OLLAMA_MODEL,
                            "messages": [
                                {"role": "system", "content": _retry_prompt},
                                {"role": "user",   "content": text},
                            ],
                            "stream": False,
                            "keep_alive": -1,
                            "options": {"temperature": 0.05, "num_predict": 200},
                        },
                    )
                    _retry_resp.raise_for_status()
                    _corrected = (_retry_resp.json()
                                  .get("message", {})
                                  .get("content", "")
                                  .strip())
                    if _corrected and _looks_like_portuguese(_corrected):
                        log(f"[flow-local] ✅ EN→PT retry produced valid PT-BR: '{_corrected[:60]}'")
                        final_text = _corrected
                    else:
                        log(f"[flow-local] ⚠️ EN→PT retry also failed PT-BR check: '{_corrected[:60]}' — keeping original")
                except Exception as _retry_err:
                    log(f"[flow-local] ⚠️ EN→PT retry request failed: {_retry_err}")

            # ── Direction B: PT → EN ───────────────────────────────────────────
            elif source_norm.startswith("pt") and target_lang == "en" and not _looks_like_english(final_text):
                log(f"[flow-local] ⚠️ PT→EN mismatch — output looks Portuguese ('{final_text[:60]}') — retrying")
                _retry_prompt = (
                    "Translate the following text from Brazilian Portuguese to English. "
                    "Do NOT repeat the original language. "
                    "Output ONLY the translated English sentence."
                )
                try:
                    _client = await get_ollama_client()
                    _retry_resp = await _client.post(
                        OLLAMA_URL,
                        json={
                            "model": OLLAMA_MODEL,
                            "messages": [
                                {"role": "system", "content": _retry_prompt},
                                {"role": "user",   "content": text},
                            ],
                            "stream": False,
                            "keep_alive": -1,
                            "options": {"temperature": 0.05, "num_predict": 200},
                        },
                    )
                    _retry_resp.raise_for_status()
                    _corrected = (_retry_resp.json()
                                  .get("message", {})
                                  .get("content", "")
                                  .strip())
                    if _corrected and _looks_like_english(_corrected):
                        log(f"[flow-local] ✅ PT→EN retry produced valid English: '{_corrected[:60]}'")
                        final_text = _corrected
                    else:
                        log(f"[flow-local] ⚠️ PT→EN retry also failed EN check: '{_corrected[:60]}' — keeping original")
                except Exception as _retry_err:
                    log(f"[flow-local] ⚠️ PT→EN retry request failed: {_retry_err}")

            return final_text, target_lang, llm_ms, tts_first_ms, tts_total_ms, llm_ttft_ms

        except httpx.ConnectError:
            last_error = ErrorCode.LLM_UNAVAILABLE
            log(f"[flow-local] Ollama connect failed (attempt {attempt}/{OLLAMA_RETRIES})")
        except (httpx.ReadTimeout, httpx.WriteTimeout, asyncio.TimeoutError):
            last_error = ErrorCode.LLM_TIMEOUT
            log(f"[flow-local] Ollama timeout (attempt {attempt}/{OLLAMA_RETRIES})")
        except Exception as e:
            last_error = ErrorCode.LLM_FAILED
            log(f"[flow-local] Translation error (attempt {attempt}/{OLLAMA_RETRIES}): {e}")

        if attempt < OLLAMA_RETRIES:
            await asyncio.sleep(0.5)

    # All retries failed — clean up TTS task
    await sentence_queue.put(None)
    await tts_task

    await safe_send(client_ws, {
        "type": "error",
        "error_code": last_error.value,
        "message": last_error.user_message(),
    })
    return full_text.strip(), target_lang, 0, 0, 0


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

app = FastAPI(title="Flow Local Interpreter")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

STATIC_DIR = FLOW_DIR / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
async def index():
    return FileResponse(
        str(STATIC_DIR / "index.html"),
        headers={"Cache-Control": "no-cache, no-store, must-revalidate"},
    )


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "flow-local-interpreter",
        "whisper": MLX_WHISPER_MODEL,
        "ollama_model": OLLAMA_MODEL,
        "tts": "piper",
    }


# ---------------------------------------------------------------------------
# Prewarm helpers — run in executor thread pool, not main thread
# ---------------------------------------------------------------------------
#
# WHY EXECUTOR-SPECIFIC:
#   All inference calls (STT + TTS) run via loop.run_in_executor(EXECUTOR, ...).
#   Main-thread warmup (the module-level mlx_whisper.transcribe call) primes the
#   main thread only — the 3 EXECUTOR worker threads remain cold.
#   Running prewarm through run_in_executor ensures the actual worker threads
#   have compiled Metal shaders and warm ONNX state before the first user turn.
#
# WHY NOISE NOT SILENCE:
#   mlx-whisper detects silence and early-exits the decoder loop.
#   The full Metal compute graph (attention, cross-attention, beam search)
#   is only compiled on the first real speech call. Using low-amplitude
#   noise forces the full decoder path and compiles all Metal shaders at
#   prewarm time instead of during the user's first turn.

def _prewarm_whisper():
    """Prime Whisper ANE/Metal kernels in an executor worker thread."""
    _audio = (np.random.default_rng(42).standard_normal(16000 * 2)
              .astype(np.float32) * 0.05)
    mlx_whisper.transcribe(
        _audio,
        path_or_hf_repo=MLX_WHISPER_MODEL,
        verbose=False,
        condition_on_previous_text=False,
    )


def _prewarm_tts():
    """Prime Piper ONNX JIT for both voices in an executor worker thread."""
    synthesize_audio("Hello.", "en")
    synthesize_audio("Olá.", "pt-BR")


# ---------------------------------------------------------------------------
# WebSocket handler — the main pipeline
# ---------------------------------------------------------------------------

# HARD SINGLE SESSION — only one active WebSocket at a time.
# Second connection is rejected cleanly with code 4000.
# Future: surface this state in client UI instead of silent reconnect.
_active_ws: "WebSocket | None" = None
_ws_lock = asyncio.Lock()


@app.websocket("/ws")
async def websocket_handler(client_ws: WebSocket):
    global _active_ws
    async with _ws_lock:
        if _active_ws is not None:
            await client_ws.close(code=4000, reason="single-session: another client is active")
            log("[flow-local] Rejected duplicate connection (4000)")
            return
        _active_ws = client_ws
    await client_ws.accept()
    log("[flow-local] Client connected")

    # Per-session mode configuration (FIRST — before VAD creation)
    session_reliability_mode = DEFAULT_RELIABILITY_MODE  # will be overridden by client
    session_config = MODE_CONFIG[session_reliability_mode]
    session_silence_duration_ms = session_config["SILENCE_DURATION_MS"]
    session_keepalive_interval = session_config["KEEPALIVE_INTERVAL"]
    session_keepalive_timeout = session_config["KEEPALIVE_TIMEOUT"]

    # Per-session state (VAD created AFTER session config is set).
    # Pass _VAD_SESSION to avoid re-initializing ONNX on every connection (~7–9s blocking call).
    vad = StreamingVAD(silence_ms=session_silence_duration_ms, session=_VAD_SESSION)
    chunks_received = 0
    loop = asyncio.get_event_loop()
    is_playing_tts = False          # echo suppression flag
    tts_done_time = 0.0             # monotonic timestamp when TTS playback ended
    POST_TTS_SILENCE_MS = 300       # discard mic audio for 300ms after TTS ends
                                    # — covers phone speaker echo decay (<50ms) + room reverb tail (50–200ms)
                                    # — 1200ms was sized for laptop speakers; phone has hardware AEC + short speaker-mic path
                                    # — hold-to-talk: vad.reset_full() already clears LSTM echo; this window is just trailing-reverb guard
    turn_count = 0                  # for latency logging
    keepalive_task = None           # background keepalive ping
    last_audio_time = time.monotonic()  # Track audio timeout
    barge_in_event = asyncio.Event()    # signal streaming TTS to stop on barge-in

    # Language stability state
    stable_lang = None              # current stable language (None = not yet detected, normalized to "en" or "pt-BR")
    lang_switch_counter = 0         # consecutive detections of a candidate language
    candidate_lang = None           # language we're considering switching to
    turns_since_switch = 0          # cooldown counter after language switch

    # Controlled conversational context (CONTROLLED_CONTEXT_V1)
    # One instance per session; updated only after valid clean turns.
    # Gives the LLM a pronoun/topic anchor across turns — no full memory.
    conv_ctx = ConversationContext()

    # REPEAT_LAST_OUTPUT_V1 — last successful turn cache.
    # Stores the minimum data needed to replay translated output on demand.
    # Updated on same eligibility gate as conv_ctx (Lane A/B, conf ≥ 0.60).
    # NEVER stores raw STT. NEVER stores more than one turn.
    last_output: dict | None = None   # {"text", "target_lang", "source_text", "direction"}

    # Phase 1 accent hardening — unique ID for this WS session (used in failure log)
    import uuid as _uuid
    session_id = _uuid.uuid4().hex[:8]

    # Optional language preferences from client UI
    preferred_source_lang = None    # "en" | "pt-BR" | None(auto)
    preferred_target_lang = None    # "en" | "pt-BR" | None(auto)
    lock_target_lang = False        # when true, force target language; default pair-mode auto

    # Send ready (wait for client to send mode preference)
    await client_ws.send_json({
        "type": "flow.ready",
        "message": "Local interpreter active. Speak naturally.",
        "reliability_mode": session_reliability_mode,
        "keepalive_timeout_ms": session_keepalive_timeout,
    })

    # Per-session prewarm: re-warm executor threads immediately on connect.
    # Between sessions the OS may deprioritize idle executor threads; the first
    # real STT/TTS call would pay the re-warm cost (~2-4s) during the user's turn.
    # Firing here in background completes (~300ms on warm server) before user first press.
    async def _session_prewarm():
        t0 = time.monotonic()
        try:
            await asyncio.gather(
                loop.run_in_executor(EXECUTOR, _prewarm_whisper),
                loop.run_in_executor(EXECUTOR, _prewarm_tts),
            )
            log(f"[flow-local] Session prewarm complete ({(time.monotonic()-t0)*1000:.0f}ms)")
        except Exception as e:
            log(f"[flow-local] Session prewarm error (non-fatal): {e}")

    asyncio.create_task(_session_prewarm())

    # Keepalive: ping at interval to detect stale connections
    async def keepalive():
        try:
            ping_count = 0
            while True:
                # Use session-specific interval (20-25s per mode config)
                await asyncio.sleep(session_keepalive_interval)
                if client_ws.application_state.value == "connected":
                    try:
                        ping_count += 1
                        await client_ws.send_json({"type": "ping"})
                        if ping_count % 3 == 0:
                            log(f"[flow-local] Keepalive ping #{ping_count} sent (mode: {session_reliability_mode})")
                    except Exception as e:
                        log(f"[flow-local] Keepalive ping failed: {e}")
                        break
        except asyncio.CancelledError:
            log("[flow-local] Keepalive task cancelled")
            pass

    keepalive_task = asyncio.create_task(keepalive())

    try:
        while True:
            raw = await client_ws.receive()
            if raw.get("type") == "websocket.disconnect":
                log("[flow-local] Client disconnected")
                break

            msg = None
            msg_type = None
            audio_bytes = None

            if raw.get("type") == "websocket.receive":
                if "text" in raw and raw["text"] is not None:
                    msg = json.loads(raw["text"])
                    msg_type = msg.get("type")

            if msg_type is None:
                continue

            # Mode preference: client requests reliability mode
            if msg_type == "mode_preference":
                requested_mode = msg.get("mode", DEFAULT_RELIABILITY_MODE)
                if requested_mode in MODE_CONFIG:
                    session_reliability_mode = requested_mode
                    session_config = MODE_CONFIG[session_reliability_mode]
                    session_silence_duration_ms = session_config["SILENCE_DURATION_MS"]
                    session_keepalive_interval = session_config["KEEPALIVE_INTERVAL"]
                    session_keepalive_timeout = session_config["KEEPALIVE_TIMEOUT"]

                    # CRITICAL: Recreate VAD with new silence duration
                    vad = StreamingVAD(silence_ms=session_silence_duration_ms, session=_VAD_SESSION)

                    log(f"[flow-local] Mode switched to {session_reliability_mode} (silence: {session_silence_duration_ms}ms, keepalive: {session_keepalive_timeout}ms, VAD recreated)")
                    # Echo back confirmation
                    await client_ws.send_json({
                        "type": "mode_confirmed",
                        "reliability_mode": session_reliability_mode,
                        "keepalive_timeout_ms": session_keepalive_timeout,
                    })
                continue

            # Language preference from client settings (optional override)
            if msg_type == "language_config":
                src = (msg.get("source_language") or "").strip().lower()
                tgt = (msg.get("target_language") or "").strip().lower()

                preferred_source_lang = _norm_lang(src)
                preferred_target_lang = _norm_lang(tgt)

                # Pair mode default: target auto-switches opposite of detected source.
                # Only force target when explicit lock_target=true is provided.
                lock_target_lang = bool(msg.get("lock_target", False))

                log(
                    f"[flow-local] Language config updated: "
                    f"source={preferred_source_lang or 'auto'} "
                    f"target={preferred_target_lang or 'auto'} "
                    f"lock_target={lock_target_lang}"
                )
                continue

            # Echo suppression: browser tells us when TTS playback ends
            if msg_type == "tts_playback_done":
                is_playing_tts = False
                tts_done_time = time.monotonic()
                barge_in_event.set()  # signal streaming TTS to stop
                vad.reset_full()  # Clear LSTM state that accumulated TTS energy
                log(f"[flow-local] TTS done → VAD reset, {POST_TTS_SILENCE_MS}ms silence window started")
                continue

            # Keepalive messages: respond immediately
            if msg_type == "keepalive_ping":
                try:
                    await client_ws.send_json({"type": "keepalive_pong"})
                except Exception:
                    pass
                continue

            if msg_type == "pong":
                # client responded to our ping, no action needed
                continue

            # REPEAT_LAST_OUTPUT_V1 — replay last clean translated output.
            # Client sends {"type": "repeat"} only when state == .ready.
            # Server regenerates TTS from cached text — no stored audio bytes.
            # Uses new message type "repeat_done" so iOS does NOT commit a
            # duplicate turn to history; echo suppression (is_playing_tts) applies.
            if msg_type == "repeat":
                if not last_output:
                    log("[flow-local] [repeat] requested but no output cached yet")
                    await safe_send(client_ws, {
                        "type": "repeat_done",
                        "skip_reason": "no_repeat_available",
                    })
                    continue

                _rep_text    = last_output["text"]
                _rep_lang    = last_output["target_lang"]
                _rep_dir     = last_output["direction"]
                _rep_src     = last_output["source_text"]
                log(f"[flow-local] [repeat] replaying: dir={_rep_dir} text='{_rep_text[:60]}'")

                await safe_send(client_ws, {"type": "tts_start"})
                is_playing_tts = True
                barge_in_event.clear()

                try:
                    _rep_audio = await loop.run_in_executor(
                        EXECUTOR, synthesize_audio, _rep_text, _rep_lang,
                    )
                    if _rep_audio is not None and len(_rep_audio) > 0:
                        _chunk_size = 2048
                        for _i in range(0, len(_rep_audio), _chunk_size):
                            _chunk = _rep_audio[_i : _i + _chunk_size]
                            _b64   = float32_to_pcm16_b64(_chunk)
                            if not await safe_send(client_ws, {"type": "audio_delta", "audio": _b64}):
                                break  # client gone
                    else:
                        log("[flow-local] [repeat] TTS produced no audio")
                except Exception as _rep_err:
                    log(f"[flow-local] [repeat] TTS error: {_rep_err}")

                await safe_send(client_ws, {
                    "type":        "repeat_done",
                    "text":        _rep_text,
                    "source_text": _rep_src,
                    "direction":   _rep_dir,
                })
                continue

            # Three-way dispatch: release signal | unknown | audio
            events = []
            if msg_type == "speech_stopped":
                # Guard: ignore release before any audio has arrived this session.
                # Happens when client sends speech_stopped during WS handshake before
                # the session is fully settled (flow.ready → mode_confirmed → first chunk).
                if chunks_received == 0:
                    log("[flow-local] ⚠️ Zero-chunk release — no audio yet, session not ready (ignored)")
                    await client_ws.send_json({
                        "type": "turn_complete",
                        "skip_reason": "no_audio_received",
                    })
                    continue

                # Client released orb — finalize immediately, no silence wait
                last_audio_time = time.monotonic()
                events = vad.force_finalize()

                # Guard: release arrived but VAD was never in speaking state
                # (orb released before VAD detected speech onset, e.g. very quick tap).
                if not events:
                    log("[flow-local] ⚠️ Release with VAD idle — no speech detected, turn skipped")
                    await client_ws.send_json({
                        "type": "turn_complete",
                        "skip_reason": "release_no_speech",
                    })
                    continue
                log(f"[flow-local] Release msg → force_finalize ({len(events)} event(s))")
            elif msg_type != "audio":
                continue
            else:
                # Update audio timeout counter
                last_audio_time = time.monotonic()

                chunks_received += 1
                if chunks_received == 1:
                    log("[flow-local] First audio chunk received")

                # Echo suppression: discard mic audio while TTS is playing
                if is_playing_tts:
                    continue
                # Post-TTS cooldown: discard mic audio for 600ms after TTS ends
                # Prevents echo loop (mic picks up lingering TTS from speaker)
                elapsed_since_tts = (time.monotonic() - tts_done_time) * 1000
                if elapsed_since_tts < POST_TTS_SILENCE_MS:
                    continue

                # Decode browser audio (24kHz float32)
                audio_24k = decode_browser_audio(msg["audio"])

                # Resample to 16kHz for VAD + Whisper
                audio_16k = resample(audio_24k, INPUT_SAMPLE_RATE, VAD_SAMPLE_RATE)

                # Run VAD
                events = vad.process_chunk(audio_16k)

            for event in events:
                if event[0] == "speech_started":
                    speech_start_time = time.monotonic()
                    log("[flow-local] Speech started")
                    await client_ws.send_json({"type": "speech_started"})

                elif event[0] == "speech_stopped":
                    speech_stop_time = time.monotonic()
                    # Segment duration: from VAD speech_started to stop event (release or hard cap).
                    segment_duration_ms = (speech_stop_time - speech_start_time) * 1000 if 'speech_start_time' in locals() else 0
                    log(f"[flow-local] Speech stopped — segment {segment_duration_ms:.0f}ms")
                    await client_ws.send_json({"type": "speech_stopped"})
                    turn_start = time.monotonic()

                    speech_audio = event[1]  # float32 16kHz
                    duration_s = len(speech_audio) / VAD_SAMPLE_RATE
                    segment_ms = int(duration_s * 1000)
                    log(f"[flow-local] Speech segment: {duration_s:.1f}s ({len(speech_audio)} samples)")

                    # Guard: skip tiny segments that are usually noise/trailing breaths
                    if segment_ms < MIN_SPEECH_SEGMENT_MS:
                        log(f"[flow-local] Turn skipped: short_segment ({segment_ms}ms < {MIN_SPEECH_SEGMENT_MS}ms)")
                        await client_ws.send_json({"type": "turn_complete", "skip_reason": "short_segment"})
                        continue

                    # 1. Transcribe (in thread pool — blocking)
                    #    Only pass manual user preference as Whisper language hint.
                    #    Do NOT pass stable_lang as forced_source_language — it would force-transcribe
                    #    echo as wrong language. Pass it separately for dual-transcription scoring bias.
                    #
                    # P3.4 TURN RESET: each fresh PTT segment is evaluated without session-language
                    # bias so Whisper picks the language of THIS audio, not the prior session.
                    # stable_lang is cleared from the bias slot (passed as None) while skip_dual
                    # retains the performance optimization (True when session is established).
                    # The session variable stable_lang is NOT modified — memory lives on.
                    log(f"[turn_reset] prior_session_lang={stable_lang or 'none'} new_segment_started=1")
                    stt_start = time.monotonic()
                    pre_stt_ms = (stt_start - turn_start) * 1000
                    try:
                        async with stt_lock:   # serialise Metal GPU — only one Whisper at a time
                            text, detected_lang, stt_confidence = await loop.run_in_executor(
                                EXECUTOR,
                                transcribe_segment,
                                speech_audio,
                                preferred_source_lang,       # manual preference only (or None)
                                stable_lang is not None,     # skip_dual: True when session established
                                None,                        # bias=None: no session tilt per fresh turn
                            )
                        stt_ms = (time.monotonic() - stt_start) * 1000
                        log(f"[segment_detect] detected={detected_lang} conf={stt_confidence:.2f} prior_session={stable_lang or 'none'}")
                        log(f"[flow-local] STT ({stt_ms:.0f}ms): [{detected_lang}] confidence={stt_confidence:.2f} text='{text}'")
                    except Exception as e:
                        stt_ms = (time.monotonic() - stt_start) * 1000
                        log(f"[flow-local] ❌ STT EXCEPTION ({stt_ms:.0f}ms): {type(e).__name__}: {e}")
                        import traceback
                        log(f"[flow-local] STT Traceback:\n{traceback.format_exc()}")
                        await client_ws.send_json({"type": "error", "code": "STT_FAILED", "message": "Could not understand speech"})
                        await client_ws.send_json({"type": "turn_complete", "skip_reason": "stt_exception"})
                        continue

                    # ── 3-lane gate: fast Lane C ────────────────────────────
                    # Cheap checks that don't need the rescue chain.
                    # Empty / floor / unknown-lang / gibberish → repeat-request.
                    # unknown_lang gets a guarded EN retry before dropping.
                    raw_text = text   # preserve pre-rescue text for logging
                    _cleaned = _clean_repetition_hallucinations(text)
                    if _cleaned != text:
                        log(f"[flow-local] Hallucination cleaned: '{text}' -> '{_cleaned}'")
                        text = _cleaned
                    _fast_c_reason = None
                    if not text.strip():
                        _fast_c_reason = "empty_transcript"
                    elif stt_confidence < CONF_WEAK_FLOOR:
                        _fast_c_reason = f"below_floor ({stt_confidence:.2f})"
                    elif normalize_lang(detected_lang) is None:
                        # Guarded EN retry — three-gate check before attempting
                        if _should_retry_as_english(detected_lang, text, stable_lang, preferred_source_lang or ""):
                            log(f"[flow-local] unknown_lang '{detected_lang}' — EN retry gate passed, retrying")
                            try:
                                async with stt_lock:   # serialise Metal GPU — same lock as primary STT
                                    _retry_text, _retry_lang, _retry_conf = await loop.run_in_executor(
                                        EXECUTOR,
                                        transcribe_segment,
                                        speech_audio,
                                        "en",   # forced English
                                        True,   # skip_dual — we already spent one pass
                                    )
                                # Log the retry event (phase=fast_retry — no final lane yet)
                                _write_accent_log({
                                    "ts": time.time(), "session_id": session_id,
                                    "source_tag": SOURCE_TAG,
                                    "phase": "fast_retry",
                                    "raw_stt": text, "rescued_text": None,
                                    "rescue_changed": None,
                                    "stt_conf": stt_confidence, "detected_lang": detected_lang,
                                    "normalized_lang": None,
                                    "stable_lang": stable_lang,
                                    "lane": None, "lane_reason": f"unknown_lang ({detected_lang})",
                                    "en_retry_fired": True,
                                    "en_retry_conf": _retry_conf,
                                    "en_retry_text": _retry_text,
                                    "translation_out": None,
                                    "annotated_intended": None,
                                    "failure_category": None, "audio_quality": None,
                                })
                                if _retry_conf >= CONF_WEAK_FLOOR:
                                    log(f"[flow-local] EN retry recovered: conf={_retry_conf:.2f} text='{_retry_text}'")
                                    text           = _retry_text
                                    detected_lang  = _retry_lang
                                    stt_confidence = _retry_conf
                                    # fall through — no _fast_c_reason, processing continues
                                else:
                                    log(f"[flow-local] EN retry insufficient: conf={_retry_conf:.2f} — dropping")
                                    _fast_c_reason = f"unknown_lang ({detected_lang}) en_retry_conf={_retry_conf:.2f}"
                            except Exception as _e:
                                log(f"[flow-local] EN retry exception: {_e} — dropping")
                                _fast_c_reason = f"unknown_lang ({detected_lang}) en_retry_error"
                        else:
                            _fast_c_reason = f"unknown_lang ({detected_lang})"
                    elif is_gibberish(text):
                        _fast_c_reason = f"gibberish"
                    if _fast_c_reason:
                        log(f"[flow-local] Turn → Lane C ({_fast_c_reason}): text='{text}'")
                        _write_accent_log({
                            "ts": time.time(), "session_id": session_id,
                            "source_tag": SOURCE_TAG,
                            "phase": "turn",
                            "raw_stt": raw_text, "rescued_text": None,
                            "rescue_changed": None,
                            "stt_conf": stt_confidence, "detected_lang": detected_lang,
                            "normalized_lang": normalize_lang(detected_lang),
                            "stable_lang": stable_lang,
                            "lane": "C", "lane_reason": _fast_c_reason,
                            "en_retry_fired": False,
                            "en_retry_conf": None, "en_retry_text": None,
                            "translation_out": None,
                            "annotated_intended": None,
                            "failure_category": None, "audio_quality": None,
                        })
                        await client_ws.send_json({
                            "type": "turn_complete",
                            "skip_reason": "repeat_requested",
                            "lane": "C",
                            "reason": _fast_c_reason,
                        })
                        turns_since_switch += 1
                        continue
                    # ────────────────────────────────────────────────────────

                    # ── Low-confidence guard ────────────────────────────────────
                    # STT confidence < CONF_LOW_CONFIDENCE_FLOOR (0.60):
                    #   • Short text (< 3 words): skip — likely noise, not speech.
                    #     Prevents a mumble or ambient sound from generating a
                    #     garbled translation that confuses the conversation.
                    #   • Longer text: let it through but log clearly.
                    #     Could be genuine low-energy speech; rescue chain handles it.
                    # This sits above the hard Lane-C floor (CONF_WEAK_FLOOR=0.30)
                    # and adds a graduated quality gate without killing real speech.
                    if stt_confidence < CONF_LOW_CONFIDENCE_FLOOR:
                        _word_count = len(text.strip().split())
                        if _word_count < 3:
                            log(f"[flow-local] ⚠️ Low-conf short turn: conf={stt_confidence:.2f} words={_word_count} text='{text}' — skipping")
                            await client_ws.send_json({
                                "type": "turn_complete",
                                "skip_reason": "low_confidence_short",
                                "stt_confidence": round(stt_confidence, 2),
                            })
                            turns_since_switch += 1
                            continue
                        else:
                            log(f"[flow-local] ⚠️ Low-conf turn: conf={stt_confidence:.2f} words={_word_count} text='{text}' — proceeding with caution")
                    # ────────────────────────────────────────────────────────────

                    # LANGUAGE STABILITY: Apply hysteresis and cooldown
                    # Normalize detected language to canonical form (en or pt-BR)
                    normalized_lang = normalize_lang(detected_lang)

                    switch_reason = None
                    active_lang = stable_lang if stable_lang else normalized_lang

                    # First detection: initialize stable language (normalized)
                    if stable_lang is None:
                        if normalized_lang:  # Only set if it's a supported language
                            stable_lang = normalized_lang
                            active_lang = normalized_lang
                            switch_reason = "initial_detection"
                            log(f"[flow-local] Language initialized: {stable_lang} (detected: {detected_lang})")
                        else:
                            # Unsupported language on first detection
                            log(f"[flow-local] Unsupported language on first detection: {detected_lang}, waiting for supported lang")
                            switch_reason = "unsupported_initial"
                            active_lang = normalized_lang or "pt-BR"  # fallback
                            await client_ws.send_json({"type": "turn_complete"})
                            turns_since_switch += 1
                            continue

                    # Language switch logic with hysteresis (only for supported languages)
                    elif normalized_lang and normalized_lang != stable_lang:
                        # Reset hysteresis if candidate language changes
                        if normalized_lang != candidate_lang:
                            candidate_lang = normalized_lang
                            # HARDENED: only start accumulating if this first detection
                            # already meets the confidence bar. A single noisy detection
                            # of a different language must not start the switch clock.
                            if stt_confidence >= MIN_CONFIDENCE_SWITCH:
                                lang_switch_counter = 1
                                active_lang = normalized_lang
                                switch_reason = "language_candidate_detected"
                                log(f"[lang_switch] from={stable_lang} to={normalized_lang} conf={stt_confidence:.2f}")
                            else:
                                lang_switch_counter = 0  # don't start counter on low-conf
                                active_lang = stable_lang
                                switch_reason = f"language_candidate_rejected_low_conf ({stt_confidence:.2f}<{MIN_CONFIDENCE_SWITCH})"
                            log(f"[flow-local] Language candidate: {candidate_lang} (detected={detected_lang}, conf={stt_confidence:.2f}, counter={lang_switch_counter})")
                        else:
                            # HARDENED: only advance the counter on HIGH-confidence
                            # detections. A low-confidence turn that happens to match
                            # the candidate cannot accumulate toward a switch.
                            if stt_confidence >= MIN_CONFIDENCE_SWITCH:
                                lang_switch_counter += 1
                            else:
                                switch_reason = f"hysteresis_not_advanced_low_conf ({stt_confidence:.2f}<{MIN_CONFIDENCE_SWITCH})"
                                active_lang = stable_lang
                                log(f"[flow-local] Language candidate {candidate_lang}: low conf {stt_confidence:.2f} — counter stays at {lang_switch_counter}/{LANGUAGE_SWITCH_HYSTERESIS}")
                            log(f"[flow-local] Language candidate {candidate_lang}: count={lang_switch_counter}/{LANGUAGE_SWITCH_HYSTERESIS}")

                            # Check if we have enough consecutive detections to switch
                            if lang_switch_counter >= LANGUAGE_SWITCH_HYSTERESIS:
                                # Check cooldown: allow very high confidence to override
                                if turns_since_switch >= LANGUAGE_SWITCH_COOLDOWN or stt_confidence >= 0.95:
                                    _prev_stable = stable_lang
                                    stable_lang = normalized_lang
                                    active_lang = normalized_lang
                                    candidate_lang = None
                                    lang_switch_counter = 0
                                    turns_since_switch = 0
                                    switch_reason = "hysteresis_satisfied"
                                    log(f"[lang_switch] from={_prev_stable} to={stable_lang} conf={stt_confidence:.2f}")
                                    log(f"[flow-local] Language switched to {stable_lang} (cooldown ok)")
                                else:
                                    # Still in cooldown period
                                    active_lang = stable_lang
                                    switch_reason = f"cooldown_active ({turns_since_switch}/{LANGUAGE_SWITCH_COOLDOWN})"
                                    log(f"[flow-local] Language switch blocked by cooldown: {switch_reason}")
                            else:
                                # Not enough consecutive detections yet.
                                # Gate direction flip on MIN_CONFIDENCE_SWITCH — same rule
                                # as first-detection: confident signal flips immediately,
                                # uncertain signal holds stable direction until hysteresis done.
                                if stt_confidence >= MIN_CONFIDENCE_SWITCH:
                                    active_lang = normalized_lang
                                    log(f"[lang_switch] from={stable_lang} to={normalized_lang} conf={stt_confidence:.2f}")
                                else:
                                    active_lang = stable_lang
                                switch_reason = f"hysteresis_pending ({lang_switch_counter}/{LANGUAGE_SWITCH_HYSTERESIS})"
                    elif normalized_lang and normalized_lang == stable_lang:
                        # Same language detected again — reset hysteresis
                        candidate_lang = None
                        lang_switch_counter = 0
                        active_lang = stable_lang
                        switch_reason = "confirmed_language"
                    else:
                        # Unsupported language detected while stable lang exists
                        active_lang = stable_lang  # Ignore unsupported detection
                        switch_reason = f"unsupported_lang_ignored ({detected_lang})"
                        log(
                            f"[flow-local] [lang_lock] detected={detected_lang} kept={active_lang}"
                            f" reason={switch_reason} text={text[:40]!r}"
                        )

                    # P1.8: unified lock log — fires whenever the stability system uses a
                    # different (supported) language than what the detector returned this turn.
                    # Covers: low-conf rejection, cooldown block, hysteresis pending.
                    # Unsupported-lang case is already logged in the else branch above.
                    if normalized_lang and normalized_lang != active_lang:
                        log(
                            f"[flow-local] [lang_lock] detected={detected_lang} kept={active_lang}"
                            f" reason={switch_reason} text={text[:40]!r}"
                        )

                    # TURN OWNERSHIP LOCK — P3.3
                    # The session stability system above resolves active_lang using hysteresis
                    # and cooldown. That is correct for session-level memory, but in push-to-talk
                    # use each segment is its own speech act and should own its language when
                    # the detection is confident.
                    #
                    # Rule: if this segment's detected language differs from what the session
                    # system chose AND confidence >= MIN_CONFIDENCE_SWITCH, override active_lang
                    # for this turn only. stable_lang / candidate_lang / hysteresis state are
                    # NOT modified — session memory evolves at its own pace.
                    _session_chosen = active_lang
                    if (
                        normalized_lang
                        and normalized_lang != active_lang
                        and stt_confidence >= MIN_CONFIDENCE_SWITCH
                    ):
                        active_lang = normalized_lang
                    log(
                        f"[turn_owner] segment_lang={normalized_lang or detected_lang}"
                        f" session_lang={_session_chosen} chosen={active_lang}"
                        f" conf={stt_confidence:.2f}"
                    )

                    # Optional manual source override from client settings
                    if preferred_source_lang:
                        log(
                            f"[flow-local] lang_override: stability={active_lang} → override={preferred_source_lang}"
                            f" text={text[:40]!r}"
                        )
                        active_lang = preferred_source_lang
                        switch_reason = f"manual_source_override ({preferred_source_lang})"

                    # 1b. Three-pass rescue chain (internal).
                    #     Pass 1: phonetic confusion  e.g. "no feet" → "no fit"
                    #     Pass 2: slang/shorthand      e.g. "no fit"  → "can't"
                    #     Pass 3: accent normalization e.g. "axed me" → "asked me"  [EN only]
                    phonetic = phonetic_rescue(text, active_lang)
                    interpretation = rescue_transcript(phonetic, active_lang)
                    if active_lang and active_lang.startswith("en"):
                        interpretation = _normalize_accent_en(interpretation)
                    rescue_changed_count = _count_rescue_changes(text, interpretation)
                    log(
                        f"[flow-local] 📝 raw='{text}'"
                        f" | phonetic='{phonetic}' [{'changed' if phonetic != text else 'clean'}]"
                        f" | rescued='{interpretation}' [{'changed' if interpretation != phonetic else 'clean'}]"
                        f" | rescue_changes={rescue_changed_count} src={active_lang}"
                    )

                    # Send post-rescue transcript — this is what translation actually operated on.
                    # For clean audio rescue is a no-op (interpretation == text); for noisy audio
                    # the user sees the corrected text, which is honest.
                    await client_ws.send_json({
                        "type": "source_transcript",
                        "text": interpretation,
                        "diagnostics": {
                            "detected_lang": detected_lang,
                            "stt_confidence": stt_confidence,
                            "stable_lang": stable_lang,
                            "active_lang": active_lang,
                            "switch_reason": switch_reason,
                            "segment_ms": segment_ms,
                        }
                    })

                    # 1c. Full 3-lane classification (rescue_changed_count + stable_lang now available)
                    turn_lane, lane_reason = _classify_turn_lane(
                        text, detected_lang, stt_confidence, rescue_changed_count, stable_lang
                    )
                    log(f"[flow-local] Turn → Lane {turn_lane}: {lane_reason}")

                    # Phase 1 turn-level log: write when lane=C, heavy rescue, or borderline conf
                    if turn_lane == 'C' or rescue_changed_count >= 2 or stt_confidence < 0.65:
                        _write_accent_log({
                            "ts": time.time(), "session_id": session_id,
                            "source_tag": SOURCE_TAG,
                            "phase": "turn",
                            "raw_stt": raw_text, "rescued_text": interpretation,
                            "rescue_changed": rescue_changed_count,
                            "stt_conf": stt_confidence, "detected_lang": detected_lang,
                            "normalized_lang": normalize_lang(detected_lang),
                            "stable_lang": stable_lang,
                            "lane": turn_lane, "lane_reason": lane_reason,
                            "en_retry_fired": False,
                            "en_retry_conf": None, "en_retry_text": None,
                            "translation_out": None,   # filled after translation below
                            "annotated_intended": None,
                            "failure_category": None, "audio_quality": None,
                        })

                    if turn_lane == 'C':
                        await client_ws.send_json({
                            "type": "turn_complete",
                            "skip_reason": "repeat_requested",
                            "lane": "C",
                            "reason": lane_reason,
                        })
                        turns_since_switch += 1
                        continue

                    # Lane B: run clarification (no-op while CLARIFICATION_ENABLED=False)
                    if turn_lane == 'B':
                        interpretation = await clarify_transcript(interpretation, active_lang)

                    # 2+3. Streaming translate + TTS (overlapped)
                    # Intent cleaning runs inside translate_and_stream_tts (choke-point).
                    barge_in_event.clear()
                    is_playing_tts = True
                    full_translation, target_lang, llm_ms, tts_first_ms, tts_total_ms, llm_ttft_ms = \
                        await translate_and_stream_tts(
                            interpretation, active_lang,   # rescued text — intent-cleaned inside
                            preferred_target_lang if lock_target_lang else None,
                            client_ws, loop, turn_count, barge_in_event,
                            conv_ctx,   # CONTROLLED_CONTEXT_V1: pronoun/topic anchor
                        )

                    # NO-OP GUARD: ensure LLM output is in target language, not source.
                    # The LLM can ignore direction hints and echo source text despite a
                    # correct prompt — this guard catches and corrects that failure.
                    if full_translation.strip() and _is_noop_output(
                        interpretation, full_translation, active_lang, target_lang
                    ):
                        _tgt_name = "Portuguese" if active_lang.startswith("en") else "English"
                        _src_name = "English"    if active_lang.startswith("en") else "Portuguese"
                        log(f"[translation_guard] noop_detected → retry text=\"{full_translation.strip()[:80]}\"")
                        _retry_instr = (
                            f"Translate strictly into {_tgt_name}. "
                            f"Do NOT repeat input. Output must be natural and fluent."
                        )
                        full_translation, target_lang, *_ = await translate_and_stream_tts(
                            interpretation, active_lang,
                            preferred_target_lang if lock_target_lang else None,
                            client_ws, loop, turn_count, barge_in_event,
                            conv_ctx,
                            extra_instruction=_retry_instr,
                        )
                        if _is_noop_output(interpretation, full_translation, active_lang, target_lang):
                            log(f"[translation_guard] noop_detected → dropped text=\"{full_translation.strip()[:80]}\"")
                            full_translation = ""   # blocks translation_done + ctx update

                    # 4. Send final text (voice-first: text after audio started)
                    if full_translation.strip():
                        await client_ws.send_json({
                            "type": "translation_done",
                            "text": full_translation.strip(),
                        })

                    # CONTROLLED_CONTEXT_V1 — update conversational frame.
                    # Gates: Lane A or B (turn_lane), confidence above low-conf floor,
                    # supported language, non-empty translation.
                    # Stores interpretation (post-rescue-chain source text) — NOT raw STT,
                    # NOT the translation output. Anchors the NEXT turn's LLM prompt.
                    _ctx_eligible = (
                        turn_lane in ('A', 'B')
                        and stt_confidence >= CONF_LOW_CONFIDENCE_FLOOR
                        and normalize_lang(detected_lang) is not None
                        and bool(full_translation.strip())
                        and bool(interpretation.strip())
                    )
                    if _ctx_eligible:
                        # Store interpretation directly — it is already the rescue-chain
                        # output (phonetic + slang + accent passes). Re-cleaning it would
                        # corrupt short emotionally-loaded turns ("I hate this", "merda!").
                        _ctx_meaning = interpretation
                        conv_ctx.update(active_lang, target_lang, _ctx_meaning)
                        log(f"[flow-local] [ctx] updated: dir={conv_ctx.direction} meaning='{conv_ctx.last_clean_meaning}'")
                        # REPEAT_LAST_OUTPUT_V1 — cache this turn's output for replay.
                        # Uses same gate as conv_ctx — never stores noisy/low-conf turns.
                        last_output = {
                            "text":        full_translation.strip(),
                            "target_lang": target_lang,
                            "source_text": interpretation,   # post-rescue, not raw STT
                            "direction":   f"{active_lang}→{target_lang}",
                        }
                        log(f"[flow-local] [repeat] cached: dir={last_output['direction']} text='{last_output['text'][:60]}'")
                    else:
                        log(f"[flow-local] [ctx] NOT updated: lane={turn_lane} conf={stt_confidence:.2f} eligible={_ctx_eligible}")

                    # Turn complete — log with streaming metrics
                    turn_ms = (time.monotonic() - turn_start) * 1000
                    turn_count += 1
                    turns_since_switch += 1
                    if turn_count == 1:
                        log("[flow-local] ✅ First usable turn complete — session fully ready")
                    await client_ws.send_json({"type": "turn_complete"})

                    # Per-turn instrumentation
                    metrics = {
                        "turn_id": turn_count,
                        "speech_duration_ms": round(segment_ms),
                        "pre_stt_ms": round(pre_stt_ms),
                        "stt_ms": round(stt_ms),
                        "llm_ttft_ms": round(llm_ttft_ms),
                        "llm_ms": round(llm_ms),
                        "tts_first_audio_ms": round(tts_first_ms),
                        "tts_total_ms": round(tts_total_ms),
                        "total_ms": round(turn_ms),
                        "source_lang": active_lang,
                        "target_lang": target_lang,
                    }
                    log(f"[flow-local] METRICS: {json.dumps(metrics)}")
                    # Per-stage durations (each stage in isolation)
                    log(f"[flow-local] ⏱ PIPELINE  pre_stt={pre_stt_ms:.0f}ms | stt={stt_ms:.0f}ms | llm_ttft={llm_ttft_ms:.0f}ms | llm={llm_ms:.0f}ms | tts_first={tts_first_ms:.0f}ms | total={turn_ms:.0f}ms")
                    # Cumulative timestamps from turn_start=0 (shows when user hears each stage)
                    _t_stt_done  = pre_stt_ms + stt_ms
                    _t_llm_tok   = _t_stt_done + llm_ttft_ms
                    _t_tts_ready = _t_stt_done + tts_first_ms   # tts_first_ms anchored to llm_start≈stt_done
                    log(f"[flow-local] ⏱ BREAKDOWN"
                        f"  t0=0(stop_rx)"
                        f"  t1={pre_stt_ms:.0f}(stt_start)"
                        f"  t2={_t_stt_done:.0f}(stt_done)"
                        f"  t3={_t_llm_tok:.0f}(llm_1st_tok)"
                        f"  t4={_t_tts_ready:.0f}(audio_ready)"
                        f"  t5={turn_ms:.0f}(done)"
                        f"  — slowest={max(('pre_stt',pre_stt_ms),('stt',stt_ms),('llm_ttft',llm_ttft_ms),('llm',llm_ms),('tts_first',tts_first_ms),key=lambda x:x[1])[0]}")

                elif event[0] == "speech_stopped_short":
                    log("[flow-local] Short sound ignored — returning client to ready")
                    await safe_send(client_ws, {
                        "type": "turn_complete",
                        "skip_reason": "short_sound",
                    })

            if chunks_received > 0 and chunks_received % 100 == 0:
                log(f"[flow-local] Audio chunks: {chunks_received}")

            # Safety timeout: no audio received for AUDIO_TIMEOUT_MS (60s).
            # Normal during processing — client sends no audio while awaiting translation.
            # Fires only if client truly disconnected without a clean WebSocket close.
            time_since_audio = (time.monotonic() - last_audio_time) * 1000
            if time_since_audio > AUDIO_TIMEOUT_MS:
                log(f"[flow-local] Audio safety timeout ({time_since_audio:.0f}ms) — closing session")
                break

    except WebSocketDisconnect:
        log("[flow-local] Client disconnected")
    except ConnectionClosedError as e:
        # websockets transport-level close (e.g. keepalive ping timeout, network drop).
        # This is NOT a crash — log cleanly and let finally block run.
        log(f"[flow-local] Transport closed: {e}")
    except Exception as e:
        import traceback as tb
        log(f"[flow-local] ❌ UNHANDLED EXCEPTION: {type(e).__name__}: {e}")
        log(f"[flow-local] Full traceback:\n{tb.format_exc()}")
        try:
            await client_ws.send_json({
                "type": "error",
                "code": "UNKNOWN",
                "message": f"Server error: {type(e).__name__}",
            })
        except Exception as close_err:
            log(f"[flow-local] Could not send error message: {close_err}")
    finally:
        if keepalive_task:
            keepalive_task.cancel()
        async with _ws_lock:
            if _active_ws is client_ws:
                _active_ws = None
    log("[flow-local] Session ended")


# ---------------------------------------------------------------------------
# Lightweight regression tests (direction logic)
# ---------------------------------------------------------------------------

def _run_direction_logic_tests():
    cases = [
        ("pt-BR", "pt-BR", True, "pt-BR"),  # pt speech + forced pt -> no-op
        ("pt-BR", "en", False, "en"),       # pt speech + forced en -> pt->en
        ("en", "pt-BR", False, "pt-BR"),   # en speech + forced pt -> en->pt
        ("en", "en", True, "en"),          # en speech + forced en -> no-op
    ]
    for src, forced, expect_noop, expect_target in cases:
        s, t, _, no_op = _choose_translation_direction(src, forced)
        assert no_op == expect_noop, f"no_op mismatch for src={src} forced={forced}"
        assert t == expect_target, f"target mismatch for src={src} forced={forced}: got {t}"


# ---------------------------------------------------------------------------
# Ollama warmup
# ---------------------------------------------------------------------------

async def warmup_ollama():
    """
    Warm up Ollama: load model into GPU memory and prime the KV cache with
    the system prompt so the first real translation call is fast.

    Critical: the message format here MUST exactly match what
    translate_pipeline_streaming() sends.  llama.cpp re-uses the cached
    KV state only when the token prefix is identical, so using the same
    INTERPRETER_PROMPT here means the 150-token system message is already
    encoded before the first user turn arrives.

    keep_alive: -1 tells Ollama never to evict the model while the
    process is running (default is 5 min, which causes a cold-reload
    penalty on sessions that start more than 5 min after warmup).
    """
    log(f"[flow-local] Warming up Ollama ({OLLAMA_MODEL})...")
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                OLLAMA_URL,
                json={
                    "model": OLLAMA_MODEL,
                    "messages": [
                        {"role": "system", "content": INTERPRETER_PROMPT},
                        {"role": "user", "content": "[English → Brazilian Portuguese] Hello."},
                    ],
                    "stream": False,
                    "keep_alive": -1,          # pin model in GPU memory indefinitely
                    "options": {"num_predict": 5},
                },
            )
            data = resp.json()
            result = data.get("message", {}).get("content", "")
            log(f"[flow-local] Ollama warm (KV primed): '{result}'")
    except Exception as e:
        log(f"[flow-local] Ollama warmup failed: {e}")
        log("[flow-local] Make sure Ollama is running: ollama serve")


@app.on_event("startup")
async def startup():
    _run_direction_logic_tests()
    await warmup_ollama()
    # Warm EXECUTOR worker threads (STT + TTS).
    # The module-level mlx_whisper.transcribe() call above primes the main thread only.
    # Actual inference runs on EXECUTOR threads via run_in_executor — they must be
    # warmed separately so the first real user turn does not pay the Metal/ONNX cold cost.
    loop = asyncio.get_event_loop()
    t0 = time.monotonic()
    await asyncio.gather(
        loop.run_in_executor(EXECUTOR, _prewarm_whisper),
        loop.run_in_executor(EXECUTOR, _prewarm_tts),
    )
    log(f"[flow-local] Executor prewarm complete ({(time.monotonic()-t0)*1000:.0f}ms) — first turn should be fast")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    log("")
    log("  ╔══════════════════════════════════════╗")
    log("  ║   FLOW LOCAL — Bilingual Interpreter ║")
    log("  ║   English ↔ Brazilian Portuguese      ║")
    log("  ║   100% LOCAL — No cloud calls         ║")
    log("  ║   http://localhost:8765               ║")
    log("  ╚══════════════════════════════════════╝")
    log("")
    uvicorn.run(app, host="0.0.0.0", port=8765)

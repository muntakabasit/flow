#!/usr/bin/env python3
"""
report_latency.py — FLOW_LATENCY_BASELINE_V1

Measurement-only latency baseline from existing Flow server logs.
Parses the per-turn METRICS JSON lines that server_local.py already emits —
no server, client, model, or config changes.

Per-turn source line (server_local.py ~line 2899):
  [flow-local] METRICS: {"turn_id": 1, "speech_duration_ms": ..., "pre_stt_ms": ...,
                         "stt_ms": ..., "llm_ttft_ms": ..., "llm_ms": ...,
                         "tts_first_audio_ms": ..., "tts_total_ms": ..., "total_ms": ...,
                         "source_lang": "...", "target_lang": "..."}

Event lines counted for hit rates:
  [flow-local] Dual-transcription (<reason>): ...     (transcribe_segment retry path)
  [flow-local] Lane B clarification: ...              (clarify_transcript round-trip)

release_to_first_audio_ms = pre_stt_ms + stt_ms + tts_first_audio_ms
  (tts_first_audio_ms is measured from llm_start, so it already contains llm_ttft
   plus sentence-boundary wait plus first Piper synth — do not add llm_ttft again.)

Usage:
  python3 scripts/report_latency.py [logfile ...]
  Default logfile: ~/.flow/server.stdout.log
  On the Mac Mini (runtime):
    python3 scripts/report_latency.py /Users/kulturestudios/.flow/server.stdout.log
"""

import json
import re
import statistics
import sys
from pathlib import Path

METRICS_RE = re.compile(r"\[flow-local\] METRICS: (\{.*\})")
# Only the trigger line — 'Dual-transcription (<reason>):'. The same event also
# logs 'Dual-transcription picked:'/'forced:' lines; counting those would double-count.
DUAL_RE    = re.compile(r"\[flow-local\] Dual-transcription \(")
LANE_B_RE  = re.compile(r"\[flow-local\] Lane B clarification:")

# Serial pipeline stages compared to name the dominant bottleneck.
# llm_ms excluded: it overlaps TTS (streaming) so it is not a serial cost.
STAGES = ["pre_stt_ms", "stt_ms", "llm_ttft_ms", "tts_first_after_llm_ms"]


def parse_logs(paths):
    turns, dual_hits, lane_b_hits = [], 0, 0
    for path in paths:
        with open(path, errors="replace") as f:
            for line in f:
                m = METRICS_RE.search(line)
                if m:
                    try:
                        turns.append(json.loads(m.group(1)))
                    except json.JSONDecodeError:
                        pass
                    continue
                if DUAL_RE.search(line):
                    dual_hits += 1
                elif LANE_B_RE.search(line):
                    lane_b_hits += 1
    return turns, dual_hits, lane_b_hits


def enrich(turn):
    pre  = turn.get("pre_stt_ms", 0)
    stt  = turn.get("stt_ms", 0)
    tf   = turn.get("tts_first_audio_ms", 0)
    ttft = turn.get("llm_ttft_ms", 0)
    turn["release_to_first_audio_ms"] = pre + stt + tf
    # Portion of first-audio wait that is TTS/sentence-wait, after the LLM's first token
    turn["tts_first_after_llm_ms"] = max(0, tf - ttft)
    return turn


def stats_row(name, values):
    if not values:
        return f"  {name:<28} —"
    return (f"  {name:<28} "
            f"avg={statistics.mean(values):>7.0f}  "
            f"med={statistics.median(values):>7.0f}  "
            f"max={max(values):>7.0f}  "
            f"n={len(values)}")


def main():
    paths = [Path(p).expanduser() for p in (sys.argv[1:] or ["~/.flow/server.stdout.log"])]
    missing = [p for p in paths if not p.is_file()]
    if missing:
        for p in missing:
            print(f"error: log file not found: {p}", file=sys.stderr)
        sys.exit(1)

    turns, dual_hits, lane_b_hits = parse_logs(paths)
    if not turns:
        print("No METRICS lines found — no completed turns in these logs.")
        sys.exit(0)

    turns = [enrich(t) for t in turns]
    n = len(turns)

    fields = [
        ("stt_ms",                     "STT"),
        ("llm_ttft_ms",                "LLM time-to-first-token"),
        ("llm_ms",                     "LLM total (overlaps TTS)"),
        ("tts_first_audio_ms",         "First audio (from llm_start)"),
        ("tts_total_ms",               "TTS total"),
        ("release_to_first_audio_ms",  "Release → first audio"),
    ]

    print()
    print(f"FLOW LATENCY BASELINE — {n} turns from {', '.join(str(p) for p in paths)}")
    print("=" * 78)
    for key, label in fields:
        print(stats_row(label, [t[key] for t in turns if key in t]))

    print()
    print(f"  Dual-transcription hit rate:  {dual_hits}/{n} turns  ({100*dual_hits/n:.0f}%)")
    print(f"  Lane B clarify hit rate:      {lane_b_hits}/{n} turns  ({100*lane_b_hits/n:.0f}%)")

    print()
    print("  WORST 5 TURNS by release → first audio")
    print(f"  {'turn':>5} {'rel→audio':>10} {'pre_stt':>8} {'stt':>7} {'ttft':>7} {'llm':>7} {'tts1st':>7}  lang")
    for t in sorted(turns, key=lambda t: t["release_to_first_audio_ms"], reverse=True)[:5]:
        print(f"  {t.get('turn_id','?'):>5} "
              f"{t['release_to_first_audio_ms']:>9.0f}ms "
              f"{t.get('pre_stt_ms',0):>7.0f} "
              f"{t.get('stt_ms',0):>7.0f} "
              f"{t.get('llm_ttft_ms',0):>7.0f} "
              f"{t.get('llm_ms',0):>7.0f} "
              f"{t.get('tts_first_audio_ms',0):>7.0f}  "
              f"{t.get('source_lang','?')}→{t.get('target_lang','?')}")

    # Dominant bottleneck: which serial stage has the largest median
    medians = {s: statistics.median([t.get(s, 0) for t in turns]) for s in STAGES}
    dominant = max(medians, key=medians.get)
    labels = {
        "pre_stt_ms":             "pre-STT (commit/segment handling)",
        "stt_ms":                 "STT (mlx-whisper)",
        "llm_ttft_ms":            "LLM time-to-first-token (Ollama)",
        "tts_first_after_llm_ms": "sentence wait + first TTS synth (Piper)",
    }
    print()
    print("  DOMINANT BOTTLENECK (median serial cost per stage)")
    for s in STAGES:
        marker = "◀ dominant" if s == dominant else ""
        print(f"    {labels[s]:<42} {medians[s]:>7.0f}ms  {marker}")
    print()


if __name__ == "__main__":
    main()

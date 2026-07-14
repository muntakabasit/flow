#!/usr/bin/env python3
"""
FLOW_SUDANESE_ARABIC_STT_FEASIBILITY_GATE_V1 — offline STT probe.

Runs mlx-whisper (the SAME model Flow uses: mlx-community/whisper-medium)
against each recorded sample, twice:
  pass A: auto-detect language  (what Flow's cold-start path would see)
  pass B: forced language="ar"  (best-case Arabic decode)

Custody law:
  - raw output is APPENDED to raw_whisper_output.jsonl — never overwritten
  - human references are read from manifest.csv — never modified
  - evidence.csv is generated with judgment columns left EMPTY for humans

Runs standalone. Does not import or modify server_local.py.
Requires: mlx_whisper, ffmpeg (for m4a/mp3 decode via whisper's loader).
"""

import csv
import json
import sys
import time
from pathlib import Path

MODEL = "mlx-community/whisper-medium"   # must match server_local.py MLX_WHISPER_MODEL
KIT = Path(__file__).resolve().parent
MANIFEST = KIT / "manifest.csv"
RAW_LOG = KIT / "raw_whisper_output.jsonl"
EVIDENCE = KIT / "evidence.csv"

JUDGMENT_COLS = [
    "meaning_preserved",        # yes / partial / no
    "dialect_words_preserved",  # yes / partial / no / n-a
    "code_switch_preserved",    # yes / partial / no / n-a
    "names_places_preserved",   # yes / partial / no / n-a
    "uncertainty_notes",
    "speaker_judgment",         # faithful / partly / unfaithful
]


def main():
    try:
        import mlx_whisper
    except ImportError:
        sys.exit("mlx_whisper not available — run this on the Mac Mini Flow runtime.")

    if EVIDENCE.exists():
        sys.exit(f"{EVIDENCE.name} already exists — refusing to overwrite a judged run. "
                 f"Move it aside to start a fresh run (custody law).")

    rows = list(csv.DictReader(open(MANIFEST, encoding="utf-8")))
    missing = [r["sample_id"] for r in rows if not (KIT / r["audio_file"]).exists()]
    if missing:
        sys.exit(f"Missing audio files for: {', '.join(missing)} — record them first (see README).")

    run_ts = time.strftime("%Y-%m-%dT%H:%M:%S")
    evidence_rows = []

    with open(RAW_LOG, "a", encoding="utf-8") as raw:
        for r in rows:
            path = str(KIT / r["audio_file"])
            sid = r["sample_id"]
            print(f"[{sid}] {r['scenario']} …", flush=True)

            results = {}
            for pass_name, lang in (("auto", None), ("forced_ar", "ar")):
                t0 = time.monotonic()
                kwargs = dict(path_or_hf_repo=MODEL, verbose=False, temperature=0.0,
                              no_speech_threshold=0.45)
                if lang:
                    kwargs["language"] = lang
                out = mlx_whisper.transcribe(path, **kwargs)
                elapsed = round((time.monotonic() - t0) * 1000)
                segs = out.get("segments", [])
                avg_nsp = (sum(s.get("no_speech_prob", 0) for s in segs) / len(segs)) if segs else None
                results[pass_name] = {
                    "text": out.get("text", "").strip(),
                    "detected_language": out.get("language"),
                    "avg_no_speech_prob": round(avg_nsp, 3) if avg_nsp is not None else None,
                    "stt_ms": elapsed,
                }
                # Custody: append raw record immediately, before any judgment exists.
                raw.write(json.dumps({
                    "run_ts": run_ts, "model": MODEL, "sample_id": sid,
                    "audio_file": r["audio_file"], "dialect_label": r["dialect_label"],
                    "scenario": r["scenario"], "pass": pass_name, **results[pass_name],
                }, ensure_ascii=False) + "\n")
                raw.flush()

            evidence_rows.append({
                "sample_id": sid,
                "audio_file": r["audio_file"],
                "dialect_label": r["dialect_label"],
                "scenario": r["scenario"],
                "human_reference_transcription": r["human_reference_transcription"],
                "raw_whisper_auto": results["auto"]["text"],
                "auto_detected_lang": results["auto"]["detected_language"],
                "raw_whisper_forced_ar": results["forced_ar"]["text"],
                **{c: "" for c in JUDGMENT_COLS},
            })

    with open(EVIDENCE, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(evidence_rows[0].keys()))
        w.writeheader()
        w.writerows(evidence_rows)

    print(f"\nDone. Raw custody log: {RAW_LOG.name} (append-only)")
    print(f"Judgment sheet:        {EVIDENCE.name} — fill judgment columns with the speaker.")


if __name__ == "__main__":
    main()

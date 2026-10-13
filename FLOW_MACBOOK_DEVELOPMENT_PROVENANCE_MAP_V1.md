# FLOW_MACBOOK_DEVELOPMENT_PROVENANCE_MAP_V1

```text
MODE:     READ-ONLY ARCHAEOLOGICAL PROVENANCE RETRIEVAL
PRODUCED: 2026-10-13
MUTATION: NONE (this report file only)
REPAIRS:  NONE
DEPLOYS:  NONE
```

---

## 1. MACBOOK MACHINE IDENTITY

```text
HOSTNAME:      Abduls-MacBook-Pro.local
USER:          abdulbasitmuntaka
OS:            macOS 26.3.1 (Build 25D771280a)
PRIMARY CWD:   /Users/abdulbasitmuntaka/flow  (NOT a git repository)
VOLUMES:
  /dev/disk3s3s1  →  /           (APFS sealed, read-only, local)
  /dev/disk3s1    →  /System/Volumes/Data  (APFS local, journaled, protect)
  /dev/disk3s7    →  /Volumes/jango  (APFS local, journaled — external volume)
  CoreSimulator/  →  iOS 23B86, watchOS 23S36 (sealed simulators)
```

---

## 2. DISCOVERED FLOW ROOTS / REPOSITORIES

| ID | Path | Git | Earliest commit | Latest commit | Remote |
|---|---|---|---|---|---|
| R-01 | `/Users/abdulbasitmuntaka/flow` | NO | — | — | — |
| R-02 | `/Users/abdulbasitmuntaka/projects/flow` | YES | 2025-12-30 "baseline" | 2025-12-30 | none |
| R-03 | `/Users/abdulbasitmuntaka/projects/flow-ios` | YES | 2025-12-18 "Init iOS app shell" | 2025-12-18 | none |
| R-04 | `/Users/abdulbasitmuntaka/projects/flow translator` | YES | 2025-12-18 "Initial Commit" | 2025-12-18 | none |
| R-05 | `/Users/abdulbasitmuntaka/BelawuOS/flow` | YES (nested in BelawuOS) | 2026-02-14 | 2026-03-17 | https://github.com/muntakabasit/BelawuOS.git |
| R-06 | `/Users/abdulbasitmuntaka/BelawuOS/flow-interpreter` | YES | 2026-02-23 | 2026-02-23 | https://github.com/muntakabasit/floow.git |
| R-07 | `/Users/abdulbasitmuntaka/BelawuOS/flow/flow-interpreter` | YES (nested within R-05) | 2026-02-23 | 2026-02-23 | https://github.com/muntakabasit/floow.git |
| R-08 | `/Users/abdulbasitmuntaka/ofa_jack_agent/projects/flow` | YES | 2026-04-09 | 2026-07-24 | https://github.com/muntakabasit/flow.git |

**R-01 `/Users/abdulbasitmuntaka/flow` — NOT a git repository.**
Contains only one subdirectory: `FlowiOS/` (Xcode project, mtime Mar 20 2026). This is NOT a deployable server root. This MacBook's primary working directory for the Claude Code session points here, but all Flow source, history, and documentation live in R-08.

**R-08 is the canonical MacBook build path** per `docs/FLOW_STABILIZATION_FREEZE_V1.md`:
```
BUILD_PATH:   /Users/abdulbasitmuntaka/ofa_jack_agent/projects/flow
RUNTIME_PATH: /Users/kulturestudios/ofa_jack_agent/projects/flow  (Mac Mini)
```

---

## 3. SOURCE RESERVOIR INVENTORY

| ID | Path | Type | Date class | What it contains |
|---|---|---|---|---|
| SR-01 | `projects/flow/` (R-02) | HTTP API + layer-based architecture + iOS Swift app spec | Dec 2025 (filesystem mtime) | Ollama-backed HTTP interpreter, layer contracts (Rhythm/Transcription/Semantic/Rendering/TTS), 7-language support spec, test suite |
| SR-02 | `projects/flow-ios/` (R-03) | Xcode iOS project shell | Dec 2025 | `FlowiOS/` only — no implementation |
| SR-03 | `projects/flow translator/` (R-04) | Unknown (single initial commit) | Dec 2025 | Not inspected in depth — single "Initial Commit" |
| SR-04 | `BelawuOS/flow/` (R-05) | WebSocket + Silero VAD + faster-whisper server | Feb–Mar 2026 | First working browser interpreter; 48 commits |
| SR-05 | `BelawuOS/flow-interpreter/` (R-06, R-07) | Fly.io deployment configuration | Feb 2026 | 4 commits, Fly.io cloud deployment files |
| SR-06 | `BelawuOS/flow-km/` | Knowledge management / governance decisions | Mar 2026 | Decisions log, atlas builder |
| SR-07 | `ofa_jack_agent/projects/flow/` (R-08) | Current canonical build | Apr–Jul 2026 | 77 commits, server_local.py, FlowiOS Xcode project, PWA, reports, docs, evidence |
| SR-08 | `ofa_jack_agent/projects/flow/accent_failures.jsonl` | Live per-turn JSONL ledger | Mar 16–26 2026 | 159 records, 43 sessions, real EN↔PT-BR conversations |
| SR-09 | `ofa_jack_agent/projects/flow/logs/` | Server startup logs | Feb 28 2026 | `flow-20260228-103254.log` — startup only, 16 lines |
| SR-10 | `ofa_jack_agent/projects/flow/surrogate_assets/v1/` | 12 WAV audio assets (A-01–A-12) | Aug 13 2026 (mtime) | Frozen surrogate test stimulus set |
| SR-11 | `ofa_jack_agent/projects/flow/reports/live-evidence/` | Live evidence captures | Aug 18–21 2026 | Multiple Cell A runs, runtime identity, server logs |
| SR-12 | `ofa_jack_agent/projects/flow/FLOW_SURROGATE_E_*_EVIDENCE_V1.md` | Surrogate encounter evidence | Aug 17–18 2026 | E-04 through E-13, mixed COMPLETE/INCOMPLETE/PARTIAL |
| SR-13 | `projects/flow/.zen/audit.jsonl` | Agent session audit trail | Dec 2025 | Zencoder agent session log, DESIGN/IMPLEMENT phases |
| SR-14 | `flow.flowbasit.com.har` | Browser HAR capture | Aug 18 2026 (mtime) | Network trace of flow.flowbasit.com — 77KB |
| SR-15 | `Downloads/flow_spec_*.sh` | Spec freeze shell scripts | Unknown | `flow_spec_freeze_v1.sh`, `flow_spec_review_rev2.sh`, etc. |
| SR-16 | `Downloads/flowx.jpg` | Screenshot/image | Apr 2 2026 | Flow UI image (not inspected) |
| SR-17 | `BelawuOS/flow/accent_failures.jsonl` | Earlier accent failure JSONL | Earlier version | 108 records — strict prefix of SR-08 (94 of 159 records) |

---

## 4. GIT LINEAGES

### L-01: `projects/flow` (R-02) — HTTP/Layer architecture baseline

```text
COMMITS:     1
RANGE:       2025-12-30
REMOTE:      none
BRANCH:      master
HEAD:        22909cb  "baseline"
DIRTY:       yes (.DS_Store, .aider.chat.history.md, pyproject.toml modified; tests deleted)
AUTHOR:      theangryafrican <muntakabasit@gmail.com>
TOOLS USED:  aider AI coding assistant (.aider.chat.history.md, .aider.input.history present)
ZENCODER:    yes (.zen/audit.jsonl shows session from 2025-12-16)
```

This is the oldest recoverable source reservoir. Key architectural facts from the commit:
- Pure HTTP, not WebSocket. Endpoint: `POST /interpret`.
- Port 8088. Backend: Ollama (`llama3:latest`).
- Layer contracts: `RhythmLayer`, `TranscriptionLayer`, `SemanticLayer`, `RenderingLayer`, `TTSLayer`.
- State machine: `LISTENING → CAPTURING → PROCESSING → SPEAKING → ERROR`.
- 7 languages: EN, TW (Twi), GA (Ga), HA (Hausa), PT, ES, FR.
- `PROJECT_STATUS.md` internal date: 2026-01-05. Status: "MVP Foundation Complete."
- Zencoder audit shows session started 2025-12-16; DESIGN phase entered, IMPLEMENT phase entered.
- No VAD. No WebSocket. No microphone capture in server.

**The `PROJECT_STATUS.md` date (2026-01-05) is later than the git commit date (2025-12-30), suggesting continued development without commits after the single baseline commit.**

### L-02: `BelawuOS/flow` (R-05) — WebSocket/VAD browser interpreter

```text
COMMITS:      48
RANGE:        2026-02-14 → 2026-03-17
REMOTE:       https://github.com/muntakabasit/BelawuOS.git
BRANCH:       main
BRANCHES:     main, claude/adversarial-proof-execution-8b8f1b, claude/stupefied-brahmagupta
REMOTE_BRANCH: origin/flow (Fly.io related)
DIRTY:        yes (parent BelawuOS files modified: .dockerignore, .gitignore, __init__.py, agents/)
FIRST COMMIT AUTHOR: kulturestudios <kulturestudios@kultures-Mac-mini.local>
```

This repository was **authored on the Mac Mini**, not on this MacBook. First commit author is `kulturestudios@kultures-Mac-mini.local`. This is critical provenance: Flow's WebSocket/VAD architecture originated on the Mac Mini and was pushed to the BelawuOS remote, then pulled to the MacBook.

Commit 8fc11dc (Feb 14, "Flow web interpreter: wired engine + all bug fixes") includes in body:
```
State machine, WebSocket reconnect, mic capture, client-side RMS/VAD endpointing,
TTS playback with barge-in, auto-connect.
```
This commit already contained both VAD mode AND hold-to-talk as a toggleable option:
```javascript
let holdToTalkMode = localStorage.getItem('holdToTalkMode') === 'true';
```
Default was auto (false). Hold-to-talk was user-selectable via a checkbox.

Key milestones in this lineage:
- Feb 14: First working WebSocket browser interpreter (Mac Mini authored)
- Feb 17: Client-side VAD gate removed; all audio streamed to server; server Silero VAD becomes sole authority
- Feb 22: Streaming pipeline + Fly.io deployment config
- Feb 23: Fly.io deployment files (floow.git remote — note double 'o')
- Mar 7: **HOLD-only mode hardcoded** (`holdToTalkMode = true`, never from localStorage)
- Mar 9: `release ends turn immediately via speech_stopped`
- Mar 11: `guard zero-chunk release, fix spurious log, wire speech_stopped from hold-end`
- Mar 17: Last commit — 3 stability bugs fixed

**The Mar 7 commit ("Force HOLD-only mode") is the earliest documented forced removal of the auto/VAD path from the client UI.** The commit message: "Conversation mode: HOLD-only build — always true, never restored from localStorage."

### L-03: `BelawuOS/flow-interpreter` (R-06, R-07) — Fly.io deployment attempt

```text
COMMITS:  4
RANGE:    2026-02-23
REMOTE:   https://github.com/muntakabasit/floow.git  (note: "floow")
```

Same commits and SHA in both R-06 and R-07 locations. Fly.io configuration for cloud deployment. No further development.

### L-04: `projects/flow-ios` (R-03) — iOS shell only

```text
COMMITS:  1
RANGE:    2025-12-18
BRANCH:   master
```

`Init iOS app shell`. Only `FlowiOS/` directory. No implementation beyond shell structure.

### L-05: `ofa_jack_agent/projects/flow` (R-08) — Canonical current build path

```text
COMMITS:  77
RANGE:    2026-04-09 → 2026-07-24
REMOTE:   https://github.com/muntakabasit/flow.git
BRANCH:   main
HEAD:     dbf0bd7  "chore(pwa): activate repeat playback assets"  (2026-07-24)
DIRTY:    yes — materially significant uncommitted changes:
            M server_local.py        (504 insertions, 137 deletions)
            M static/flow-pwa/app.js
            M FlowiOS/FlowiOS.xcodeproj/project.pbxproj
            M FlowiOS/FlowiOS/FlowSession.swift
            M FlowiOS/FlowiOS/Info.plist
            M .claude/launch.json
            M __pycache__/server_local.cpython-314.pyc
```

**The uncommitted `server_local.py` is the MacBook build version (SHA: `fc5ddc14...`) that was present during the Aug 2026 reconciliation but has NOT been deployed to the Mac Mini.**

The Mac Mini was running `ad67f3fe...` (dated July 26 on the Mini) during all Aug 2026 evidence activity.

Commit `f8dbb79 2026-04-09 "Flow — clean initial commit (large model files excluded)"` is the base of this repository. It does not contain model weights; those remain on the Mac Mini runtime.

Notable commit clusters:
- Apr 9–12: Server hardening (lang lock, translation guards, launchd, iOS reconnect)
- Apr 15: Turn language ownership lock (P3.3)
- Jul 9: FLOW_REPAIR_PHRASE_FIDELITY_V1 (frozen, runtime-validated)
- Jul 10: PWA public cutover, session handoff, iPad compatibility repair
- Jul 15: Canonical turn lifecycle + invariant evidence; Amharic/Tigrinya/Sudanese-Arabic STT probes
- Jul 16: PWA playback custody repair; root cutover
- Jul 18: Tap-toggle capture (canonical)
- Jul 24: Repeat playback parity (HEAD)

---

## 5. NON-GIT HISTORICAL EVIDENCE

### NG-01: `accent_failures.jsonl` (R-08 root, 159 records)

```text
DATE RANGE:    2026-03-16T16:27:22Z → 2026-03-26T07:08:57Z
TYPE:          Live per-turn JSONL ledger
EVIDENCE CLASS: DIRECT OBSERVATION RECORD — real human encounters
SESSIONS:      43
TURNS:         159
LANGUAGES:     en (91), pt-BR (60), null (8)
LANES:         A (46), B (48), C (65)
TRANSLATION:   null in all 159 records (translation_out never populated in this log)
```

This is the **strongest real-human historical source on this MacBook** for EN↔PT-BR interpretation. Contains recognisably real bilingual conversation, including PT-BR passages about travel. Does not contain audio, timing, or turn-boundary (press/release) evidence.

Session counts: "43 sessions, 159 turns" — this is the source of the "159 turns / 43 sessions" figure referenced in recovery context.

### NG-02: `flow-20260228-103254.log` (16 lines)

```text
DATE:          2026-02-28 (filename)
TYPE:          Server startup log
EVIDENCE CLASS: DIRECT ARTIFACT — server startup only
CONTENT:       Startup sequence: Whisper 'small' loaded, Piper EN/PT loaded, Silero VAD loaded,
               Ollama warm with gemma3:4b. Shows server ready at localhost:8765.
               No turns recorded. Only 16 lines.
```

This log file exists on the MacBook at `logs/flow-20260228-103254.log`. It documents Flow running locally at localhost:8765 on Feb 28, 2026 with Whisper small, Piper TTS, Silero VAD, Ollama gemma3:4b. This is a MacBook-local startup, not the Mac Mini.

**Significance:** Feb 28 is the date associated with Abdul's "decision about inconsistent auto behaviour" in the recovery hypothesis. This log does not contain any turns or behavioral evidence — only startup. If that decision was made through observation, the observation evidence was not preserved in this log.

### NG-03: Surrogate audio assets `surrogate_assets/v1/A-01.wav` through `A-12.wav`

```text
DATE:          Filesystem mtime 2026-08-13
TYPE:          WAV audio files for surrogate testing
EVIDENCE CLASS: DIRECT ARTIFACT — frozen test stimuli
TOTAL:         12 files, ~2.4MB combined
SHA-256:       Per-file hashes frozen in FLOW_SURROGATE_FIXTURE_ASSET_SET_FREEZE_RECORD_V1.md
COMPOSITE:     7234f0dadb1b712c1e99049065d801b5b2a958d0def69fdf4754decf2b900e9c
```

### NG-04: `reports/live-evidence/` tree — Aug 2026 bounded evidence runs

```text
DATE RANGE:    2026-08-18 → 2026-08-21
TYPE:          Live server log captures, runtime identity, operator evidence
EVIDENCE CLASS: DIRECT OBSERVATION RECORD (server-side); DIRECT ARTIFACT (captured bytes)
RUNS:          7 timestamped subdirectories:
               20260818-174432Z, 20260818-180939Z, 20260818-183707Z
               20260821-125236Z, 20260821-130933Z, 20260821-155519Z
               20260821-162426Z  (V6, consumed/closed)
```

The Aug 18 run `20260818-174432Z` captured Mac Mini runtime identity:
- Hostname: `kultures-Mac-mini.local`
- Process started: Mon Jul 27 17:06:04 2026 (running 22 days by Aug 18)
- `server_local.py` mtime on Mac Mini: `2026-07-26T19:18:15+0100`
- `server_local.py` SHA on Mac Mini: `ad67f3fe42203ca57017c0a49d9440fb5386eb9baea8d896e336ee0b18576926`
- Server health: `whisper: mlx-community/whisper-medium, ollama: gemma3:4b, tts: piper`
- Metrics at that time: successful_turns_total=61, failed_turns_total=7, rejected_sessions_total=66
- Log markers at time of gate: 571 TURN_LIFECYCLE, 209 TURN_SUMMARY, 410 [segment_detect]

V6 (20260821-162426Z) was run and closed as CELL_A_INCONCLUSIVE — a reconnect stop condition triggered.

### NG-05: `BelawuOS/flow-km/decisions/` tree

```text
DATE RANGE:    2026-03-01 → 2026-04-17
TYPE:          Dated decision records
EVIDENCE CLASS: HUMAN-AUTHORED CLAIM (short notes, not structured evidence)
NOTABLE:
  2026-03-07: "Investigate long-running conversations", "Review queue management mechanism"
  2026-04-17: "No clear decision made due to model discovery failure, no alternative actions taken"
```

These are brief notes, not structured evidence. The Mar 7 note correlates with the same-date git commit forcing HOLD-only mode in BelawuOS/flow.

### NG-06: `BelawuOS/flow/CHANGES_SUMMARY_2026_02_14.md`

```text
DATE:          2026-02-14 (internal, filesystem)
EVIDENCE CLASS: DERIVED REPORT — describes changes made
KEY CLAIM:     Author path listed as /Users/kulturestudios/BelawuOS/flow/static/index.html
               Confirms the Feb 14 commit was authored on Mac Mini (kulturestudios user)
CONTENT:       Auto-start listening restored (sessionWanted=true); auto-resume after TTS added
```

This document confirms that early BelawuOS/flow development occurred on the Mac Mini. The MacBook received commits via git pull from the BelawuOS remote.

### NG-07: `flow.flowbasit.com.har` (77KB, Aug 18 mtime)

```text
DATE:          2026-08-18 (filesystem mtime)
EVIDENCE CLASS: DIRECT ARTIFACT — network trace of flow.flowbasit.com
NOT INSPECTED: Content not read during this retrieval pass
```

---

## 6. EVIDENCE-BACKED DEVELOPMENT TIMELINE

Evidence quality labels:
- **PROVES**: direct artifact/observation, no competing explanation
- **SUPPORTS**: consistent but not ruled-out alternatives
- **WORKER_CLAIM**: from a report/document, not a direct observation
- **NOT_ESTABLISHED**: no evidence on this MacBook addresses this claim

### Window 1: Nov–Dec 2025 — Founding design and HTTP prototype

| What | Evidence | Class |
|---|---|---|
| Flow project began with HTTP API + layer architecture (7 languages) | R-02, SR-01: `projects/flow/api/server.py` — `GET /health, POST /interpret`, port 8088, Ollama llama3:latest | PROVES |
| Zencoder AI used to build initial implementation | SR-13: `.zen/audit.jsonl` shows DESIGN→IMPLEMENT session starting 2025-12-16 | PROVES |
| Aider AI coding tool used | `.aider.chat.history.md`, `.aider.input.history` present in R-02 | PROVES |
| iOS app concept existed from start | R-03 `projects/flow-ios` (Dec 18 2025), R-02 PROJECT_STATUS.md describes iOS app | PROVES |
| 7-language design (EN, TW, GA, HA, PT, ES, FR) | R-02 PROJECT_STATUS.md | SUPPORTS (file date Jan 5 2026; git commit Dec 30) |
| Semantic layer contract existed | R-02 `flow/layers/contracts.py` — `SemanticLayer`, `RenderingLayer` etc. defined | PROVES |
| No WebSocket, no browser mic capture at this stage | R-02 `api/server.py` — pure HTTP, no asyncio WS | PROVES |

### Window 2: Feb 2026 — WebSocket + VAD browser interpreter (Mac Mini origin)

| What | Evidence | Class |
|---|---|---|
| First working WebSocket + VAD Flow created Feb 14 2026 | R-05 commit `8fc11dc` authored by `kulturestudios@kultures-Mac-mini.local` | PROVES (for Mac Mini; inferred MacBook received via BelawuOS pull) |
| Both auto-VAD and hold-to-talk available in first WebSocket build | R-05 commit `8fc11dc` contains `holdToTalkMode = localStorage.getItem('holdToTalkMode') === 'true'` with checkbox UI | PROVES |
| Default was auto/VAD mode (holdToTalkMode=false unless set) | R-05 commit `8fc11dc` localStorage default = null → `=== 'true'` evaluates false | PROVES (implementation default) |
| Client-side VAD was gating audio stream in first build, then changed Feb 17 | R-05 commits `8fc11dc` → `ab4bac3` diff: "Stream audio only when VAD says speaking" removed | PROVES |
| Server-side Silero VAD present from first build | R-05 commit `8fc11dc`: `VAD_THRESHOLD`, `StreamingVAD` class, `silero_vad_v6.onnx` | PROVES |
| Fly.io cloud deployment attempted Feb 23 | R-06/R-07, `floow.git` remote, 4 commits | PROVES |
| Flow running locally on MacBook Feb 28 2026 | SR-09 `flow-20260228-103254.log`: startup log, Whisper 'small', localhost:8765 | PROVES |
| Feb 28 "decision about inconsistent auto behaviour" | NOT ESTABLISHED — log has startup only, no turns, no decision record found on MacBook |

### Window 3: Mar 2026 — Hold-only lock and real field encounters

| What | Evidence | Class |
|---|---|---|
| HOLD-only mode forced on Mar 7 by Abdul | R-05 commit `c7110b3`: `holdToTalkMode = true` hardcoded | PROVES |
| March 7 force was a deliberate UX decision, not a fix | Commit message: "Force HOLD-only mode: hardcode holdToTalkMode, block auto path" | SUPPORTS (intent from message) |
| Real bilingual conversations Mar 16–26 | SR-08 `accent_failures.jsonl`: 159 records, 43 sessions, source_tag="live" | PROVES |
| Conversations occurred during BelawuOS/flow era | SR-08 timestamps converted: ~2026-03-16 | PROVES |
| EN and PT-BR both spoken (real speakers) | SR-08: stable_lang "en" 91 times, "pt-BR" 60 times | PROVES |
| Audio was NOT preserved from these sessions | SR-08: no audio field in JSONL; confirmed in evidence recovery | PROVES (structural absence) |
| 3-lane routing (A/B/C) was live during these sessions | SR-08: `lane_reason` fields reference confidence thresholds | PROVES |
| Translation_out is null for all 159 records | SR-08: translation_out=null in all records | PROVES (translation logging was not implemented at this time) |

### Window 4: Apr 2026 — Clean repo import and iOS/ops hardening

| What | Evidence | Class |
|---|---|---|
| New dedicated Flow git repo created Apr 9 | R-08 commit `f8dbb79`: "Flow — clean initial commit (large model files excluded)" | PROVES |
| This was a clean import from existing code, not a from-scratch start | Commit message says "large model files excluded" — implies source was pre-existing | SUPPORTS |
| iOS reconnect, lang ownership, launchd autostart all in Apr commits | R-08 commits Apr 10–15 | PROVES |
| Explicit orb release / tap-to-speak architecture introduced Apr 15-16 | R-08 context from prior sessions; commit series around P3.x | SUPPORTS (prior session evidence, not re-verified here) |
| Language ownership "turn-segment takes priority over session" Apr 15 | R-08 commit `52a3592` | PROVES |
| `flow.flowbasit.com` domain in use by Apr 11 | R-08 commit `3447327`: "iOS: permanent endpoint — flow.flowbasit.com" | PROVES |

### Window 5: Jul 2026 — PWA stabilisation, tap-toggle, turn lifecycle freeze

| What | Evidence | Class |
|---|---|---|
| PWA public cutover Jul 10 | R-08 commit `619653a` | PROVES |
| Canonical tap-toggle capture build Jul 18 | R-08 commit `2266dd0` | PROVES |
| Turn lifecycle canonical freeze Jul 15 (FLOW_LIVE_TURN_STABILITY_V1) | R-08 commit `75882e0` | PROVES |
| Amharic, Tigrinya, Arabic STT probes Jul 15 | R-08 commits `ee65cf1`, `903f525`, `be3a2bf` | PROVES |
| Mac Mini server started Jul 27 and ran without restart through Aug 21 | SR-11 `IDENTITY_RUNTIME.txt`: `ps` output shows start date Jul 27 17:06:04 2026 | PROVES |
| Mac Mini was running server_local.py dated Jul 26 | SR-11: `mtime=2026-07-26T19:18:15+0100` on Mac Mini server_local.py | PROVES |
| MacBook build had 504-insertion uncommitted delta vs Mac Mini deployed version | `FLOW_RUNTIME_SOURCE_IDENTITY_RECONCILIATION_V1.md`: MacBook `fc5ddc14` ≠ Mac Mini `ad67f3fe` | PROVES |

### Window 6: Aug 2026 — Surrogate baseline testing and evidence capture

| What | Evidence | Class |
|---|---|---|
| Fixture spec frozen Aug 12–13 | SR-12 file dates; `FLOW_ONE_DEVICE_INTERPRETER_FIXTURE_V1.md` frozen UTC 2026-08-13T06:57:08Z | PROVES |
| Surrogate audio assets created Aug 13 | SR-10 filesystem mtime 2026-08-13 | PROVES |
| E-01 through E-13 surrogate encounters attempted Aug 13–18 | SR-12 evidence files, dates Aug 17–18 | PROVES |
| 3 breaks observed: BC-2 (non-yield during TTS), BC-4 (correction swallowed), BC-6 (consecutive direction fail) | `FLOW_CONTROL_BREAK_CAPABILITY_PRESSURE_CHARACTERISATION_V1.md` | PROVES (surrogate evidence — not field evidence) |
| Surrogate results are surrogate only — not equivalent to real bilingual field use | Fixture law: "Simulation earns engineering confidence. Humans earn conversation confidence. SURROGATE PASS ≠ FIELD PASS" | PROVES (structural) |
| Runtime gate blocked Aug 14 — Mac Mini unreachable via public key | `FLOW_SURROGATE_CURRENT_FLOW_BASELINE_V1_RUNTIME_GATE_BLOCKED.md` | PROVES |
| Mac Mini was reachable Aug 18–21 via operator session | SR-11 live evidence runs | PROVES |
| Mac Mini running 571 TURN_LIFECYCLE cycles by Aug 18 | SR-11 `IDENTITY_RUNTIME.txt`: MARKER_COUNT | PROVES |
| V6 Cell A Aug 21 was inconclusive (reconnect, not capture/interpretation failure) | `FLOW_BOUND_EVIDENCE_CAPTURE_CELL_A_PWA_EXECUTION_V6_CLOSURE_RECORD_V1.md`: CELL_A_INCONCLUSIVE, REASON: RECONNECT_STOP_CONDITION | PROVES |
| A setup turn DID work on Aug 21 before reconnect: "I moved here from Manchester about three years ago" → PT-BR | SR-11 `CELL_A_SERVER_EVIDENCE.md` | PROVES |
| August 21 is last date of evidence activity on MacBook | File modification dates in R-08 — last file Aug 21 17:56 | PROVES |
| What "Flow degraded" means is NOT established in a single Aug 21 document | No single document on this MacBook records a "degraded" verdict on Aug 21 — the V6 closure records INCONCLUSIVE | NOT_ESTABLISHED as stated |

---

## 7. INTERACTION / UX EVOLUTION

| Period | Interaction model | Evidence |
|---|---|---|
| Dec 2025 | HTTP POST only; no browser mic; iOS app spec with auto silence detection | R-02 server.py |
| Feb 14 2026 | WebSocket; auto-VAD (default) + hold-to-talk (toggleable via UI checkbox) | R-05 first commit |
| Feb 17 2026 | Client-side VAD gate removed; all audio streams continuously to server; server Silero VAD sole authority | R-05 commit `ab4bac3` |
| Feb 22 2026 | "Streaming pipeline + UI redesign + accent/echo fixes" | R-05 commit `1cf3365` |
| Mar 6 2026 | "Restore Virgil UI + mobile Safari AudioContext fix"; "release ends turn immediately via speech_stopped" | R-05 commits |
| Mar 7 2026 | **HOLD-only mode hardcoded.** Auto/VAD path blocked in client. `holdToTalkMode = true` always. | R-05 commit `c7110b3` |
| Mar 9 2026 | Release = turn boundary (killMic + silence flush + immediate TRANSLATING) | R-05 commit `e49c9f5` |
| Apr 2026 | Explicit orb release / tap-toggle architecture in ofa_jack Flow | R-08 commit series |
| Jul 2026 | Canonical tap-toggle capture; turn lifecycle freeze; PWA parity | R-08 Jul commits |

**The VAD-to-hold transition is documented at Mar 7 2026 in R-05.** The forced HOLD was a deliberate commit by Abdul, not a gradual change. Prior state (Feb 14–Mar 6) had hold-to-talk as toggleable with auto-VAD as default.

**What is not established:** Whether Abdul's experience with auto-VAD in live sessions caused the Mar 7 force. The `flow-km` decision for Mar 7 reads: "Investigate long-running conversations / Review queue management mechanism." The git commit message says "block auto path, guard foreground restart." These are consistent with a decision driven by auto-VAD misbehavior in long conversations, but the decision record itself is only a 2-line note.

---

## 8. SPEECH / STT / TRANSLATION / TTS EVOLUTION

| Period | STT | Translation | TTS |
|---|---|---|---|
| Dec 2025 | None in server (HTTP only; client records audio separately) | Ollama `llama3:latest` via HTTP | Not implemented |
| Feb 14 2026 | faster-whisper `small` (server-side) | Ollama `gemma3:4b` | Piper (EN=22050Hz, PT=22050Hz) |
| Feb 28 2026 | faster-whisper `small` (confirmed in startup log) | Ollama `gemma3:4b` | Piper |
| Mar 10 2026 | mlx-whisper Apple ANE (replaced faster-whisper CPU) | Ollama | Piper |
| Mar 16 2026 | `condition_on_previous_text=False` added; repetition cleaner | Ollama | Piper |
| Aug 18 2026 (Mac Mini) | `mlx-community/whisper-medium` (confirmed in health endpoint) | Ollama `gemma3:4b` | Piper |
| Jul–Aug 2026 (MacBook build) | Current server_local.py (uncommitted) — not fully inspected | Ollama | Piper |

Accent normalization / rescue chain: Introduced Mar 11–16 2026 in R-05. Present in R-08 from earliest commit.

Language direction EN→PT-BR and PT-BR→EN both operated. Language ownership lock ("turn-segment language takes priority over session language") added Apr 15 2026.

---

## 9. RUNTIME / DEVICE / DEPLOYMENT EVOLUTION

| Period | Runtime location | Identity |
|---|---|---|
| Dec 2025 | MacBook localhost:8088 | R-02, HTTP only |
| Feb 2026 | Mac Mini (`kulturestudios@kultures-Mac-mini.local`) | R-05 origin; BelawuOS repo |
| Feb 28 2026 | MacBook localhost:8765 | SR-09 startup log |
| Apr–Jul 2026 | Mac Mini `localhost:8765` behind Cloudflare tunnel → `flow.flowbasit.com` | R-08; launchd daemon `com.flow.server` |
| Aug 18 2026 | Mac Mini: server started Jul 27, running 22+ days | SR-11 ps output |
| Aug 18–21 2026 | Mac Mini branch: `repo-hygiene-v1`, HEAD `94092edf...` | `FLOW_SURROGATE_CURRENT_FLOW_BASELINE_CLOSEOUT_V1.md` |

**Mac Mini runtime truth (as of Aug 2026):**
- Host: `kultures-Mac-mini.local`
- User: `kulturestudios`
- Project root: `/Users/kulturestudios/ofa_jack_agent/projects/flow`
- Branch: `repo-hygiene-v1`
- HEAD: `94092edf460073353760597d9ffa386ca3ddacd1`
- `server_local.py` SHA: `ad67f3fe42203ca57017c0a49d9440fb5386eb9baea8d896e336ee0b18576926`
- Started: Jul 27 2026
- Daemon: `com.flow.server` (system LaunchDaemon, not LaunchAgent)
- stdout log: `/Users/kulturestudios/.flow/server.stdout.log`
- stderr log: `/Users/kulturestudios/.flow/server.stderr.log`

**The Mac Mini branch `repo-hygiene-v1` (HEAD `94092edf`) is NOT the same as the MacBook build HEAD `dbf0bd7`. The MacBook build was also ahead of the Mini by 504 insertion uncommitted changes.**

The MacBook can see `d25a31f repo hygiene: ignore Xcode/agent/scratch noise...` in R-08 git log, which is likely the commit that corresponds to the Mac Mini's `repo-hygiene-v1` branch origin. But the exact merge relationship was not established in this retrieval.

---

## 10. VALIDATION / FAILURE / RECOVERY EVOLUTION

| Period | What happened | Evidence class |
|---|---|---|
| Mar 16–26 2026 | 159 real turns, 43 sessions — live EN↔PT-BR | PROVES (JSONL) |
| Mar 2026 | Accent rescue chain for diaspora speech introduced | PROVES (git) |
| Apr 2026 | Portuguese live acceptance packet | `reports/FLOW_PORTUGUESE_LIVE_ACCEPTANCE_PACKET_V1.md` (not read in depth) |
| Jul 15 2026 | FLOW_LIVE_TURN_STABILITY_V1 canonical fixture | R-08 commit |
| Aug 12–13 2026 | Fixture spec frozen; surrogate audio assets created | SR-10, SR-12 |
| Aug 13–18 2026 | E-01 through E-13 surrogate encounters | SR-12 |
| Aug 14 2026 | Runtime gate BLOCKED — Mac Mini not reachable via key auth | NG-04 |
| Aug 18 2026 | Source identity reconciliation: MacBook build ≠ Mac Mini deployed | PROVES |
| Aug 18 2026 | Surrogate baseline closeout: E-05/E-08 breaks confirmed (BC-4/BC-2) | `FLOW_SURROGATE_CURRENT_FLOW_BASELINE_CLOSEOUT_V1.md` |
| Aug 18 2026 | 3 cell A runs same day; earlier runs blocked on runtime identity (CELL_A_SOURCE_MISMATCH) | SR-11 |
| Aug 21 2026 | V6 Cell A: one physical attempt; setup turn worked; reconnect stop triggered; INCONCLUSIVE | SR-11 |
| Aug 21 2026 | V6 consumed, closed, not reusable. Cell B closed. | `FLOW_BOUND_EVIDENCE_CAPTURE_CELL_A_PWA_EXECUTION_V6_CLOSURE_RECORD_V1.md` |
| Post Aug 21 | No further evidence activity found on MacBook | File dates |

---

## 11. PRIMARY-EVIDENCE RECOVERY TARGET RESULTS

| Target | Result |
|---|---|
| A. Original early visual/interface Flow | NOT RECOVERED on this MacBook as a distinct artifact. SR-01 (Dec 2025) is HTTP/API only. R-05 index.html first appears Feb 14. No screenshots of the original Dec 2025 interface found. |
| B. Earliest browser/FastAPI implementation | RECOVERED. R-05 commit `8fc11dc` (Feb 14 2026) is the earliest WebSocket+browser Flow source on this MacBook. Note: it was authored on the Mac Mini, not the MacBook. |
| C. Automatic/VAD interaction before HOLD-only | RECOVERED. R-05 commit `8fc11dc` contains auto-VAD as default (`holdToTalkMode=false`). Client-side VAD gate was in `8fc11dc`, removed Feb 17. Server-side Silero VAD present throughout. |
| D. Abdul's 28 Feb decision about inconsistent auto behaviour | NOT RECOVERED. Feb 28 startup log exists but has no turns, no decision record. The forced HOLD-only is at Mar 7, not Feb 28. Gap between Feb 28 log and Mar 7 commit is unaccounted for on MacBook. |
| E. Actual HOLD/orb interaction implementation | RECOVERED. R-05 commit `c7110b3` (Mar 7): `holdToTalkMode = true` hardcoded. R-05 commit `e49c9f5` (Mar 9): "Make release the turn boundary." R-08 Apr onward: explicit orb release architecture. |
| F. Live March conversation records | RECOVERED. SR-08: 159 turns, 43 sessions, Mar 16–26 2026. Audio not preserved. |
| G. Source of "159 turns / 43 sessions" | RECOVERED. This count comes directly from `accent_failures.jsonl` in R-08 root (counted: wc -l=159, unique session_ids: 43). |
| H. Audio recordings from March sessions | NOT RECOVERED on this MacBook. SR-08 has no audio field. No separate audio files found matching those sessions. |
| I. April explicit-release/VAD boundary | RECOVERED (via R-08 commits and prior session context). April confirms `orb_released` vs `speech_stopped` distinction. Exact commit series not re-read in this pass. |
| J. Transition from HOLD to tap-toggle | RECOVERED. R-08 commits Jul 18: "fix(pwa): restore canonical tap-toggle capture" — named explicitly. |
| K. July physical Safari/PWA evidence | RECOVERED (partial). `FLOW_CANONICAL_IOS_PWA_V1_BUILD_VALIDATION.md` (docs, Jul 10 mtime). Details not read in depth. |
| L. Earliest evidence of degraded audio-route/STT state | NOT RECOVERED as a distinct "degraded" verdict. Aug 18 Cell A was blocked by source identity mismatch, not degradation. Aug 21 V6 was INCONCLUSIVE (reconnect). BC-2/BC-4/BC-6 from surrogate evidence are the closest characterisation. |
| M. Last genuinely field-proven sustained conversation state | RECOVERED (partial). SR-08 JSONL (Mar 2026) is the last direct field evidence on MacBook. Server metrics Aug 18 show 61 successful turns since Jul 27 start — but the underlying turn content is in Mac Mini logs, not this MacBook. |
| N. Exact failure specimen that later governance preserved | NOT RECOVERED on this MacBook as a named artifact. The Aug 21 V6 closure is INCONCLUSIVE. The surrogate break evidence is the documented capability pressure, not a specific field failure specimen. |
| O. Historical six-field semantic contract | RECOVERED (partial). R-02 `flow/layers/contracts.py` defines 5 layer contracts. Dec 2025 `PROJECT_STATUS.md` mentions 5 components. No document named "six-field semantic contract" found on MacBook. |
| P. Screenshots/video showing interface evolution | PARTIAL. `Downloads/flowx.jpg` (Apr 2 2026), `Downloads/FLOW.jpg` and `FLOW BACKGROUND.jpg` (Mar 28 2026) exist but were not viewed in this pass. |
| Q. ChatGPT/Claude/Codex conversation exports explaining technical mutations | PARTIAL. `.aider.chat.history.md` present in R-02 (Dec 2025). Claude Code session JSONL files at `~/.claude/projects/-Users-abdulbasitmuntaka-flow/*.jsonl`. Codex archived sessions at `~/.codex/archived_sessions/`. Not read in depth. |

---

## 12. CONFLICTS / CONTRADICTIONS

### C-01: Session primary working directory has no git history

The Claude Code session opened at `/Users/abdulbasitmuntaka/flow`, but this directory has no `.git`. The actual source is in R-08 (`ofa_jack_agent/projects/flow`). The `flow` directory at home root contains only `FlowiOS/` — an empty Xcode project directory. This is NOT a deployment root or a historical source.

### C-02: BelawuOS/flow was authored on the Mac Mini

The first BelawuOS/flow commit (`8fc11dc`) was authored by `kulturestudios@kultures-Mac-mini.local`, not by `abdulbasitmuntaka` on the MacBook. The Mac Mini is both the historical development origin of the WebSocket version AND the current runtime. The MacBook received this work via BelawuOS git push/pull, not via direct creation.

### C-03: Mac Mini branch not in MacBook git history

The Mac Mini's `repo-hygiene-v1` branch (HEAD `94092edf`) does not appear in R-08's git log as a commit reachable from `main`. The MacBook has a commit `d25a31f "repo hygiene:..."` which is likely the base of that branch, but the Mac Mini branch and its HEAD are not verified to be in R-08's reachable history.

### C-04: The "August 21 governing decision marks Flow degraded" claim

The Belawu context states: "21 August 2026 — The latest recovered governing decision marks Flow degraded." On this MacBook, the last Aug 21 document is `FLOW_BOUND_EVIDENCE_CAPTURE_CELL_A_PWA_EXECUTION_V6_CLOSURE_RECORD_V1.md`, which records `CELL_A_INCONCLUSIVE`, not an explicit degraded verdict. The surrogate closeout (Aug 18) records BC-2/BC-4/BC-6 breaks without a "degraded" declaration. The "degraded" language may have originated in a conversation/governance artifact not present in git-tracked documents, or may refer to the implication of unresolved breaks rather than an explicit artifact.

### C-05: `[turn_cleanup]=0` in Aug 18 metrics

The Aug 18 runtime gate shows `MARKER_COUNT[[turn_cleanup]]=0` while showing 571 TURN_LIFECYCLE markers. This is notable — turn cleanup never ran despite 571 turn lifecycle events and 61 successful turns. This is not characterised here as a failure; it may be a naming change. It is a potential signal worth comparing against Mac Mini source.

---

## 13. UNKNOWN / NOT ESTABLISHED

- **MacBook was the primary development machine** — NOT ESTABLISHED. First BelawuOS/flow commits are Mac Mini authored. Dec 2025 projects are MacBook (abdulbasitmuntaka author). There were two development locations.
- **When the MacBook became the primary build path** — NOT ESTABLISHED from git history alone. R-08 "clean initial commit" Apr 9 says "large model files excluded" — models remained on Mac Mini.
- **What the Feb 28 MacBook server session produced or observed** — NOT ESTABLISHED. Log file has startup only.
- **Whether the Mar 7 HOLD-only decision was driven by direct observation of auto-VAD failure** — SUPPORTED but NOT PROVED.
- **Content of the 571 turns run on Mac Mini between Jul 27 and Aug 18** — NOT RECOVERABLE from MacBook. In Mac Mini logs only.
- **What caused BC-6 (consecutive direction fail) at the implementation level** — NOT ESTABLISHED. Pressure characterisation names it as mechanical; cause not diagnosed.
- **The exact "August degradation specimen" for Flow hold** — NOT ESTABLISHED on this MacBook.

---

## 14. MACBOOK-ONLY EVIDENCE TO COMPARE WITH MAC MINI

The following evidence exists only on this MacBook and should be compared against Mac Mini findings when the Mac Mini is independently examined:

| MacBook artifact | What to compare |
|---|---|
| R-02 `projects/flow/` (Dec 2025 HTTP architecture) | Does Mac Mini have any corresponding HTTP-era source or deployment? |
| R-05 `BelawuOS/flow/` (Feb–Mar 2026 WebSocket) | Mac Mini has the same remote. Were there unpushed commits on Mac Mini that predate Feb 14? |
| SR-08 `accent_failures.jsonl` (159 records) | Does Mac Mini have a corresponding file? Mac Mini R-05 repo has 108 records (confirmed prefix). |
| SR-09 `flow-20260228-103254.log` | Was this generated on MacBook or copied from Mac Mini? (Path says local startup — MacBook) |
| Aug 21 running `server_local.py` (`ad67f3fe`) | This is the Mac Mini's deployed version; MacBook does NOT have an exact copy (MacBook current = `fc5ddc14`) |
| `FLOW_RUNTIME_SOURCE_IDENTITY_RECONCILIATION_V1.md` diff | Full unified diff of Mac Mini vs MacBook server_local.py — preserved locally in this report directory |
| Uncommitted server_local.py changes on MacBook (504 insertions) | These represent post-Jul-24 candidate work not yet committed; compare against Mac Mini |

---

## 15. HIGH-VALUE ARTIFACTS TO PRESERVE BEFORE ANY CLEANUP

The following should be preserved (or their state confirmed) before any reset, checkout, or cleanup:

1. **`server_local.py` (current uncommitted)** — SHA `fc5ddc14...` — 504-insertion delta vs HEAD `dbf0bd7`. This is the only copy of this candidate build state. Not committed. Not on Mac Mini. Risk: `git checkout` or stash would overwrite.

2. **`static/flow-pwa/app.js` (uncommitted)** — PWA candidate changes, also not committed.

3. **`FlowiOS/` uncommitted Xcode changes** — `FlowSession.swift`, `Info.plist`, `project.pbxproj`.

4. **`surrogate_assets/v1/*.wav` (A-01–A-12)** — frozen test stimuli with verified SHA-256 hashes. Not in git. If deleted, 12 WAV files are lost.

5. **`reports/live-evidence/` tree** — Aug 2026 bounded server log captures. Not in git. Contains runtime identity of Mac Mini at multiple points. Not replaceable.

6. **`accent_failures.jsonl` (159 records)** — Only copy of live Mar 2026 bilingual conversation data. Not audio, but irreplaceable transcript/language routing evidence.

7. **`R-02 projects/flow/`** — Dec 2025 HTTP architecture baseline. Not in git (1 commit, no remote). Contains `.venv/` which may include dependencies not easily reproducible.

8. **`BelawuOS/flow/` (R-05) branch `claude/adversarial-proof-execution-8b8f1b`** — unknown content; not inspected. Preserve before any cleanup of BelawuOS.

---

## RETURN

```text
RESULT:         PARTIAL

SUBSTANTIAL RECOVERY:
  - MacBook machine identity established
  - 8 Flow repositories discovered and characterised
  - 5 distinct git lineages traced
  - Development timeline from Dec 2025 to Aug 2026 reconstructed from evidence
  - VAD→hold transition confirmed at Mar 7 2026 commit level
  - March 2026 real bilingual sessions confirmed (159 turns, 43 sessions)
  - August 2026 surrogate testing characterised
  - Mac Mini runtime identity at Aug 2026 established from captured reports
  - Source identity divergence between MacBook build and Mac Mini runtime proved

NAMED INACCESSIBLE GAPS:
  - Feb 28 2026 decision record (log exists, no turns, no decision text)
  - Audio from March 2026 live sessions (not preserved on MacBook)
  - Mac Mini logs from Jul 27 – Aug 18 (571 turns) — on Mac Mini only
  - Exact "degraded" verdict artifact (may exist only in conversation/governance export)
  - Dec 2025 interface screenshots
  - Mac Mini pre-Feb-14 source history (if any)
```

---

*Produced by FLOW_MACBOOK_HISTORY_PROVENANCE_RETRIEVAL_001 / 2026-10-13 / READ-ONLY / No Flow mutation.*

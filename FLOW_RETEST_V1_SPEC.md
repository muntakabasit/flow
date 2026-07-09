# FLOW_RETEST_V1_SPEC

**Purpose:** Turn the Flow V2 architecture question from reasoning into data.
Run ONE real conversation with one real person. Measure where the latency
actually lives. Confirm or refute the industry finding that discomfort comes
from end-of-turn detection, not the TTS layer.

**This is not a build. It is a measured observation of the existing Flow.**

---

## THE ONE HYPOTHESIS BEING TESTED

> Industry data (2026) says: in a voice pipeline, most felt discomfort comes
> from **end-of-turn detection + LLM time**, NOT from TTS speed.
>
> Flow prediction: the user gets pulled out of the conversation at the
> **turn gap** — the silence between "I stopped talking" and "the translation
> starts" — not because the voice quality is poor.

If true → the governor is the lever, not a faster TTS engine (don't chase Miso One).
If false → something else is the problem, and now you know what.

---

## SETUP (keep it small)

- One real person. A real conversation that needs translation — not a demo.
- Phone or laptop recording the whole session (screen + audio) so you can
  review timing afterward. The recording IS the instrument.
- No new code required for V1. Observation first.

---

## THE FOUR TIMESTAMPS TO CAPTURE

For 5–10 real turns, you are looking for four moments per turn. You do not
need millisecond precision. You need to know WHICH GAP is the long one.

```
T1  speaker stops talking          (end of their speech)
T2  system shows it has decided     (transcription appears / "thinking")
    the turn is over
T3  translation output begins        (first audio / first text out)
T4  output finishes                  (ready for next turn)
```

The three gaps that matter:

```
GAP A = T2 - T1   END-OF-TURN DETECTION
        How long after they stop does the system realise they're done?
        (Industry says: this is usually the painful one.)

GAP B = T3 - T2   PROCESSING (STT finalise + translate + TTS start)
        How long from "turn is over" to "output begins"?

GAP C = T4 - T3   OUTPUT DELIVERY
        How long does the output itself take to play?
```

---

## HOW TO MEASURE WITHOUT BUILDING ANYTHING

V1 = review the recording afterward. Scrub the timeline. For each turn, note
roughly how many seconds each gap took. You are not after a number. You are
after a PATTERN: which gap is consistently the long one.

Optional V1.1 (only if the recording review is ambiguous): add console
timestamp logs at the four points in the existing Flow code. One log line each.
No architecture change. Just `print(time, "T1_speech_end")` etc.

---

## WHAT TO WATCH (the human half)

The numbers tell you WHERE. The watching tells you WHAT IT COSTS.

At each moment the user gets pulled out of the conversation, note:
- What had just happened? (a long gap? a wrong translation? an awkward overlap?)
- Did they look at the device or at the person?
- Did they repeat themselves, wait, or talk over the system?

The locked Flow principle is **confidence continuity: never let the user wonder
what the system is doing.** So the real failure event is not "slow" — it is the
moment the user shifts from *being in the conversation* to *managing the system*.
Mark every one of those moments and which gap caused it.

---

## WHAT THIS TEST IS NOT

- Not a redesign
- Not a model swap
- Not a TTS upgrade (resist Miso One until this test says TTS is the problem)
- Not push-to-talk vs continuous (that's a later question; first find the gap)
- Not a multi-turn architecture rebuild

One conversation. Four timestamps. Find the long gap. Watch the human.

---

## DECISION RULE (what you do with the result)

```
IF the long gap is GAP A (end-of-turn detection)
   -> the governor is the lever. Tune turn-detection timing.
      This is the industry-predicted result and the cheapest fix.

IF the long gap is GAP B (processing)
   -> STT/translate/TTS pipeline timing. THEN a faster component
      (incl. possibly Miso One / Moshi-class) becomes justified.

IF the long gap is GAP C (output delivery)
   -> the TTS engine itself. Only here does a TTS swap make sense.

IF discomfort happened with NO long gap
   -> it's not latency at all. It's translation MEANING / accuracy /
      the confidence-continuity signal. Different problem entirely.
```

---

## ONE-LINE LOCK

Flow is a multilingual conversation continuity engine. The next move is not to
rebuild it — it is to measure one real conversation and find which gap pulls the
user out, before changing a single component.

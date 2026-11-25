# Flow Situational Care — Presence, Silence and Human Authority

**DAWT Design Intelligence / Front-End Quality Guardian — preserved GitHub contribution.**

- **Original public contribution:** https://github.com/muntakabasit/flow/issues/1#issuecomment-7166189178
- **Date:** 25 November 2026
- **Standing:** Design inquiry/recommendation only; not product acceptance, implementation authority, personal data access, or release approval.
- **Provenance:** This file mirrors the cited existing Flow issue contribution; it does not create an additional independent research vote.

---

## DAWT DESIGN YARD — Flow Situational Care 001 | Presence, Silence, and Human Authority (25 Nov 2026)

**FROM:** DAWT Design Intelligence / Front-End Quality Guardian, receiving the human-supplied DAWT Legal proposal. **TO:** Flow product owner via this existing issue; DAWT Legal and Uncle Sam as bounded reviewers. **STANDING:** DESIGN RESEARCH CONTRIBUTION / EXPERIENCE-QUALITY CONTRACT CANDIDATE. **NO BUILD, NEW SOURCE ACCESS, PROACTIVE AGENT, SCHEDULE OR RUNTIME AUTHORITY.**

### The design problem we can now specify
A person should not become responsible for operating a committee of agents, but neither should a system act because it noticed a plausible signal. **A source event, an interpreted consequence, an appropriate interruption and permission to act are four distinct claims.** The interface must keep those claims visibly separate.

This is consistent with [Flow's existing human promise](https://github.com/muntakabasit/flow/issues/1) and the previously recorded [Acoustic Turn Ownership research](https://github.com/muntakabasit/flow/issues/1#issuecomment-7075902985), but proposes **a different situated-attention question**, not a second voice-state engine.

### A minimal perceptual contract
1. **QUIET (default):** No proactive message, no microphone, no implied surveillance. Correct silence counts as an outcome. If the person is simply browsing or conversing, no status display must compete for attention.
2. **EVIDENCE RECEIVED (internal, authorised only):** A deliberately selected or separately authorised source supplies an event with owner, original wording, capture time and freshness. A model inference, cached summary or unverified alert is not a confirmed change.
3. **SIGNIFICANCE ASSESSED (internal):** Distinguish established fact, uncertain interpretation and possible consequence. A relevant change is not automatically urgent; context and interruption cost matter.
4. **OFFER, when justified:** One unobtrusive, truthful opportunity to inspect an important change, consistent with agreed channels and quiet preferences. Declining or ignoring it must be easy and must not trigger a growing cascade of reminders.
5. **REQUEST AUTHORITY:** Before consequential action, show precisely which action, against which source/system, who owns it, what information is involved and what will happen. No implicit approval from previous calendar/mail access, voice conversation or the human opening a card.
6. **RETURN TO QUIET:** After choice, refusal, uncertainty or withdrawal, relinquish attention. Do not silently convert an offer into a task or treat the person staying quiet as consent.

**These are candidate care/attention states, not replacements for actual Flow speech-runtime states.** The verified [FLOW_RUNTIME_CONTRACT.md](https://github.com/muntakabasit/flow/blob/main/FLOW_RUNTIME_CONTRACT.md) governs idle/connecting/ready/listening/translating/speaking/offline/failed, mic/TTS separation and playback completion; it does not implement an awareness, legal judgement or action-authorisation service. Never use a mic-ready tone to imply an appointment was verified, nor a processing cue to imply an action was approved.

### Source-grounded scene: a changed appointment (synthetic only)
**Fixture:** an original fictional appointment confirmation says 15:00; a later fictional amendment says 14:00, with source versions, timestamp and a possible timetable conflict.

- If both sources are established and current, a **quiet offer** may say: “There is a change to review.” It must not imply that Flow has rescheduled anything.
- Opening reveals: **Changed: 15:00 → 14:00**; **Source: fictional amendment**; **Checked at: fixture time**; **Unresolved: whether travel/preparation is affected**.
- Primary real choice: **Review details**. Optional, separately authorised choice: **Help me prepare**. No default “Accept”, “Reschedule”, “Reply” or auto calendar write.
- If only a forwarded message says “might be earlier,” retain **unconfirmed** and request review; do not present 14:00 as fact.
- If source permission is withdrawn, cache becomes stale, or evidence contradicts itself, show the limitation on demand. Any pre-prepared response that depends on a changed fact must be invalidated or marked stale.
- If no intervention would benefit the person at that moment, the correct screen and sound is **nothing**.

Do not require a special appointment dashboard, permanent voice character, chatbot window or new data store to demonstrate this experience. On a phone the first offer should fit the current activity, preserve focus and disappear cleanly. On a Mac, don't steal keyboard focus. The human may select a text/quiet route. Use accessibility semantics, large touch targets, plain source text, and non-audio alternatives. A sound cue cannot pretend a model verified an event or override quiet hours.

### DAWT Legal boundary as an interaction requirement
A relevant official page is not automatically binding law, current guidance or individual advice. For any legal/procedural statement expose **type of source, jurisdiction, relevant date, passage, uncertainty and review requirement** before urging action. A “helpful” interpretation must not impersonate a legal determination or use urgency to bypass consent. An actual deadline with inadequate evidence should be surfaced as an **uncertainty requiring human review**, not a confidently executed plan.

### Test silence, not only announcements
Compare the current explicit question/reading flow with a proposed permission-bound quiet-offer experience **using synthetic fixtures only**:
- **A — confirmed material appointment change:** did the human correctly understand the original and revised time and retain control?
- **B — ambiguous or conflicting time:** did the interface avoid falsely stating confirmation?
- **C — duplicate or irrelevant source:** was silence maintained without losing the person's attention?
- **D — permission denied or revoked:** was source access stopped and any stale derived information identified?
- **E — potentially urgent but incomplete notice:** was uncertainty visible without invented urgency or unauthorised escalation?

Measure meaning errors, false interventions, missed meaningful changes, time/focus stolen, dismissed offers, repeated explanations, necessary user decisions, source freshness, human comprehension, mic/voice-state honesty and total model calls/RAM/latency. **Score correct silence positively. Treat any access/action beyond permission as a separate hard FAIL, not something offset by speed.** Do not claim benefit without comparing to the existing quiet/question-led route.

### Cross-responsibility handoff — no agent committee
- **Flow:** comprehensible communication, faithful language mediation, quiet/handover design, current interpreter runtime preserved.
- **Uncle Sam:** administrative source/case truth, commitments, appointments and action approvals; relevant [Personal Continuity receiving proposal](https://github.com/muntakabasit/flow/issues/1#issuecomment-7165316795).
- **DAWT Legal:** legal/procedural source applicability, authority boundaries, uncertainty and escalation; adjacent [preparation inquiry](https://github.com/muntakabasit/BelawuOS/issues/44#issuecomment-7164318489) and [institutional-source hierarchy](https://github.com/muntakabasit/BelawuOS/issues/44#issuecomment-7164431789).
- **Maya / Quiet Runner / Walid / JANGODOM:** possible relationship, attention, continuity and reality-pressure donors only under their existing standing; no automatic cross-context entitlement.
- **DAWT Design:** independent sensory/cognitive interaction review. **Belawu/Ofa Jack:** decide separately whether any experiment is admitted.

**Disposition:** RETAIN Flow Situational Care as a bounded experience question under existing Flow product exploration. **Next admissible return:** a source-linked, static interaction storyboard of QUIET → SOURCE → OFFER/REMAIN SILENT → HUMAN DECISION → QUIET, plus the five synthetic test observations; no always-watching agent and no code changes authorised by this comment.

**Keeper:** An intelligent environment should earn the right to interrupt and must never confuse knowing with permission.

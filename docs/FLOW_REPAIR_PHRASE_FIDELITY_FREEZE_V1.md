# FLOW_REPAIR_PHRASE_FIDELITY_FREEZE_V1

STATUS: FROZEN  
DATE: 2026-07-09  
SCOPE: Repair phrase translation fidelity only

## Running truth

Flow runtime is healthy after restart.

Health check result:

- com.flow.server daemon: PASS
- com.flow.tunnel daemon: PASS
- localhost:8765 listening: PASS
- public WebSocket handshake: PASS
- overall health: PASS

Runtime server PID observed: 41888

## Problem

PT-BR repair phrases were being softened or dropped by the translation model.

Pre-patch evidence:

STT captured:

Não entendi. Repete, por favor. Não tô te ouvindo. Peraí...

LLM incorrectly produced:

No, not yet. I understand now. Explain it to me better...

This weakened actionable repair commands needed for conversation continuity.

## Cause

The failure was confirmed as LLM translation behavior, not STT.

STT captured the repair phrase faithfully.  
The LLM compressed or softened the repair commands.

## Patch

Patched server_local.py only.

Updated INTERPRETER_PROMPT to preserve repair, command, and request phrases as actionable sentences.

No iOS change.  
No STT change.  
No model swap.  
No glossary architecture.  
No second LLM pass.  
No launchd/tunnel change.

## Runtime validation

Post-patch runtime evidence:

STT:

Entendi. Repete, por favor. Não tô te ouvindo. Peraí...

LLM raw:

I understand. Repeat, please. I can’t hear you. Wait. I didn’t understand. Explain it better to me...

Verdict:

FLOW_REPAIR_PHRASE_FIDELITY_V1 = RUNTIME VALIDATED

## Healthcheck reconciliation

Earlier WebSocket 403 was caused by the hard single-session rule colliding with active/stale client state.

After restart and warmup, check_flow_health.sh returned OVERALL PASS.

No healthcheck patch required for this freeze.

## Freeze boundary

This freeze applies only to repair phrase fidelity behavior.

It does not freeze:

- full source tree
- all uncommitted MacBook changes
- iOS state
- healthcheck semantics
- STT latency
- AirPods/Bluetooth
- model routing
- future short-turn optimization

## Final ruling

FLOW_REPAIR_PHRASE_FIDELITY_V1 is frozen as a validated runtime behavior layer.

FULL REPO = NOT FROZEN

STOP.

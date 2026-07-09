# FLOW_STABILIZATION_FREEZE_V1

## Runtime Truth

- BUILD_PATH: `/Users/abdulbasitmuntaka/ofa_jack_agent/projects/flow`
- RUNTIME_PATH: `/Users/kulturestudios/ofa_jack_agent/projects/flow`
- Runtime host: Mac Mini
- Runtime service: system LaunchDaemon, not LaunchAgent
- Server daemon: `com.flow.server`
- Tunnel daemon: `com.flow.tunnel`
- Health check:

```bash
ssh -t kulturestudios@100.93.82.113 'cd /Users/kulturestudios/ofa_jack_agent/projects/flow && bash check_flow_health.sh'
```

- Healthy state requires: server daemon running, tunnel daemon running, `localhost:8765` listening, WebSocket handshake PASS, OVERALL PASS

## Grounding Truth

- CONFIG_PATH: null / not_externalized
- DATA_PATH: null / not_centralized
- ADMIN_ACCESS_METHOD: SSH to Mac Mini + launchctl / health script
- RUNNING_STATUS_METHOD: Mac Mini health check, not build-side assumption

## Product / Runtime State

- iPhone mic path works
- Solo retest passed
- Conversation continuity passed
- AirPods/Bluetooth reliability deferred
- Flow is stable enough for controlled real-world testing

## UX State

- FLOW_ERROR_SURFACE_V1 completed
- Connection lost remains top errorText
- No-speech duplicate removed
- No speech / nothing heard feedback now belongs to orb/skipFlash only

## Deferred / Parked Layers

- FLOW_REAL_USER_RETEST_V1 pending
- FLOW_COMPREHENSIBLE_INPUT_NOTE_V1 held / not build
- FLOW_DATA_SURFACE_CLEANUP_V1 parked
- AirPods/Bluetooth support deferred

## Warnings

- Build-side launchd templates may not reflect live Mac Mini daemon configuration
- Live runtime truth beats templates
- Do not re-open AirPods work without a fresh bounded spec
- Do not build comprehensible-input/adaptive learning features until real-user retest

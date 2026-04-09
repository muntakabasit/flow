# Flow Shared Design Tokens + SwiftUI Parity Map

This file defines UI tokens used in `flow/static/index.html` and the intended SwiftUI equivalents.

## Color Tokens

- `--bg` → `Color("FlowBg")` / `Color(red: 0.031, green: 0.035, blue: 0.047)`
- `--surface` → `Color("FlowSurface")`
- `--surface2` → `Color("FlowSurface2")`
- `--surface3` → `Color("FlowSurface3")`
- `--border` → `Color("FlowBorder")`
- `--border-hi` → `Color("FlowBorderHi")`
- `--text` → `Color("FlowTextPrimary")`
- `--text-2` → `Color("FlowTextSecondary")`
- `--text-3` → `Color("FlowTextTertiary")`
- `--accent` → `Color("FlowAccent")`
- `--green` → `Color("FlowStateListening")`
- `--amber` → `Color("FlowStateConnecting")`
- `--red` → `Color("FlowStateOffline")`

## Spacing Scale

- `--space-1` (4) → `4`
- `--space-2` (8) → `8`
- `--space-3` (12) → `12`
- `--space-4` (16) → `16`
- `--space-5` (20) → `20`
- `--space-6` (24) → `24`
- `--space-8` (32) → `32`

Use as `padding(.horizontal, 16)`, `VStack(spacing: 16)`, etc.

## Corner Radius

- `--radius-sm` (8) → `.cornerRadius(8)`
- `--radius-md` (12) → `.cornerRadius(12)`
- `--radius-lg` (16) → `.cornerRadius(16)`
- `--radius-xl` (20) → `.cornerRadius(20)`
- `--radius-pill` (999) → `Capsule()`

## Typography

- `--font-size-caption` (11) + semibold → `.system(size: 11, weight: .semibold)`
- `--font-size-footnote` (12) + medium → `.system(size: 12, weight: .medium)`
- `--font-size-body` (16) + regular → `.system(size: 16, weight: .regular)`
- `--font-size-title` (18) + bold → `.system(size: 18, weight: .bold)`

Primary family parity: SF Pro Text / `.system(...)`.

## Motion + Timing

- `--motion-fast` (180ms) → `.easeOut(duration: 0.18)`
- `--motion-base` (280ms) → `.timingCurve(0.2, 0.8, 0.2, 1, duration: 0.28)`
- `--motion-slow` (420ms) → `.timingCurve(0.2, 0.8, 0.2, 1, duration: 0.42)`
- `--curve-standard` cubic-bezier(0.2,0.8,0.2,1) → custom `Animation.timingCurve`

## State Color Intent

- Idle/Ready: neutral text + low accent glow
- Listening: green
- Translating/Speaking: accent amber
- Connecting: amber (lower intensity)
- Offline/Failed: red

## Notes for SwiftUI-native TODO

1. Implement tokens in one `FlowTheme` enum/struct (Color + spacing constants + motion presets).
2. Use one shared `FlowOrbState` mapping state → visuals.
3. Use `matchedGeometryEffect` for turn card transitions.
4. Put diagnostics in a `sheet` or `.presentationDetents([.medium, .large])` drawer.
5. Keep protocol/state machine logic in existing layer; only mirror presentation tokens.

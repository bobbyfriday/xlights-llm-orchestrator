## Why

Two user requests after watching Christmas Canon (a piano-driven holiday track):
1. **Drive props from the piano.** The trigger layer only reads the drum stem. A piano-heavy song should be able to fire effects on the piano's notes — a melodic line walking across the props — but there's no way to point a trigger at a non-drum stem. (Christmas Canon: 425 piano onsets, piano dominant for the first ~2 min.)
2. **Traditional Christmas palette.** Holiday songs should lean on red / green / white as the primary palette (with accent colors), the traditional Christmas scheme — which also happens to read with strong LED contrast (red vs green are hue-distant). The Director currently picks any palette from the named-color vocabulary.

## What Changes

- **Stem-parameterized onset triggers.** A trigger gains a `stem` field; a generic `stem_onsets` detector and a `stem_prominent` section eligibility read it, so a trigger can fire on piano / bass / guitar / vocals onsets, not just drums. `drum_onsets` / `drum_prominent` keep working (drums is the default).
- **A piano-note trigger** in the cookbook: piano onsets rotate a gentle pop across the rhythm/melodic groups in piano-prominent sections — the melody visibly walks the props.
- **Christmas-palette bias** in the Director prompt: for holiday/Christmas material, prefer red/green/white as the primary palette with 1–2 accent colors, unless the song's mood clearly calls for something else (noted as also being strong LED contrast).

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `show-orchestration`: trigger effects SHALL be able to key off any instrument stem's onsets (not only drums), with section eligibility by that stem's prominence; the creative brief SHALL prefer the traditional red/green/white primary palette for holiday songs.

## Impact

- `pipeline/triggers.py`: `stem` field on `TriggerSpec`; `stem_onsets` detector + `stem_prominent` eligibility (detectors gain access to the spec); `drum_onsets` becomes a thin alias.
- `xlights-trigger-cookbook.md`: a piano-note trigger + the `stem` field documented.
- `agents/director.py`: holiday-palette guidance.
- Back-compat: existing triggers (no `stem`) default to drums; non-holiday songs unaffected.

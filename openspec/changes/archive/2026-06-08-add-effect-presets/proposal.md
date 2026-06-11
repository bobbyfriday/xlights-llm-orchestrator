## Why

Generating valid xLights effect `settings`/`palette` strings is the project's hardest correctness problem — free-form LLM generation hallucinates keys and silently renders wrong. The fix is to never generate them free-form: mine a library of presets from the user's existing hand-crafted sequences, so later agents compose shows by *picking and tuning* presets. This is the keystone capability everything downstream depends on.

Exploration of the real corpus showed this is both feasible and worth doing properly now. A placed xLights effect is `(type, settings string, palette string, timing)` — exactly the shape of an `addEffect` call — and the source sequences contain thousands of working examples. Crucially, xLights setting keys are **self-describing by prefix** (`E_SLIDER_…`, `E_CHOICE_…`, `E_CHECKBOX_…`, `E_VALUECURVE_…`, `E_TEXTCTRL_…`; 98% classify mechanically), so we can extract **typed, tunable knobs** rather than shipping opaque strings. Parameterizing now avoids a later refactor of the keystone's public contract and gives agents a real interface ("Shockwave, end_radius=160") instead of "pick string #2847".

## What Changes

- Add an **offline extractor** (`xsq_extractor`) that mines the user's community-authored `.xsq` corpus into a committed catalog. It dereferences each placed effect through the sequence's `<EffectDB>` (settings) and `<ColorPalettes>` (palette).
- Build a **two-axis catalog** (colors are fully decoupled from motion in the data):
  - **Looks** — per effect type, grouped by structural **key-signature**; each look is `{frozen_base, knobs}`. A knob is a key whose value varies across the corpus, **typed from its key prefix** with its observed options/range and a default (the most-frequent observed value).
  - **Palettes** — distinct color sets (C_), deduped by color-set and mechanically tagged (warm/cool, count, monochrome).
  - Any look composes with any palette — both valid — for multiplicative variety.
- Add a **lookup + emit API** (`preset_library`): list effect types, get looks for a type (optionally filtered), get palettes; and **assemble a settings string** from a look + chosen knob values, validating each value against its knob's constraint.
- **Exclude asset-bound effect types** (Faces, Pictures, Video, Shader, DMX) whose settings reference external resources that won't exist in a new sequence.
- Add **offline guarantees**: per-knob value constraints derived from the corpus, plus a round-trip test proving the extractor/assembler is lossless against every source string.

**Non-goals (deferred):** LLM-written look descriptions and semantic retrieval; parameterizing palettes (color count etc.); and **live validation by replay** — confirming assembled strings (especially *novel* knob combinations) via `addEffect` + `checkSequence` needs the write path (change `add-xlights-mcp-effect-editing`), which does not exist yet.

## Capabilities

### New Capabilities
- `effect-presets`: Mine a library of parameterized xLights effect looks (typed, corpus-derived knobs) plus an independent palette catalog from a curated source corpus, excluding asset-bound effect types, and assemble valid settings strings from a look plus per-knob values constrained to what the corpus proved.

### Modified Capabilities
<!-- None. `xlights-read-access` is unaffected. -->

## Impact

- **`xlights-core` package** gains `src/xlights_core/knowledge/`: `xsq_extractor.py`, `preset_library.py` (lookup + assembly), `palettes.py`, `validators.py`, and a committed catalog under `knowledge/presets/`.
- **Corpus dependency (resolved):** the source is the **17 community-authored** `.xsq` in `/Users/rob/xlights` (`<author>` empty or "John Storms", xLights 2020.45–2023.20). The 19 `xlight-autosequencer` files and the `Backup/` folder are excluded from mining (see project memory `preset-corpus`).
- **No new runtime dependencies** beyond stdlib XML parsing (mining is offline; catalog is committed JSON).
- **Validity model shift:** guarantees move from "exact corpus string" to **per-knob constraints** (sliders within observed range; choices/checkboxes/text/value-curves categorical from observed). The residual *knob-independence* risk (novel combinations) is absorbed by **live validation in `add-xlights-mcp-effect-editing`**, which is also what makes novel combinations trustworthy.
- **Downstream:** the sequence-generation agents (later change) consume this catalog and its emit API.

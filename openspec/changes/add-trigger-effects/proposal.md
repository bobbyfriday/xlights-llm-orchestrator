## Why

The show realizes structure, rhythm, color, and motion well, but it lacks *curated semantic punctuation* — the hand-authored "when X happens in the music, do Y" moments that make a sequence feel deliberate: Lightning on a guitar solo, a whole-house Shockwave on the one biggest drum hit, per-prop shockwaves rippling on the drum onsets of a chosen section, a color word in the lyric lighting the yard that color. Today only one such rule exists (instrument *entrances*), hardcoded in `features.py`. The user wants a growing, **hand-editable** library of these — used periodically, never overdone.

## What Changes

- **A trigger cookbook (`xlights-trigger-cookbook.md`)** — a human-readable, hand-editable markdown file declaring the curated triggers (which detector, what effect, render scope, rarity, section eligibility, color/direction treatment, magnitude thresholds), parsed best-effort like the existing guides. Editing it adds or tunes effects without code.
- **A trigger layer (`pipeline/triggers.py`)** — a detector library + cookbook loader + realizer. Each trigger = a named detector (`analysis → [TriggerEvent{time, magnitude, target}]`) plus an effect spec from the cookbook. Runs as one deterministic layer (like beats/features), code-owned timing, never new LLM surface.
- **Magnitude helper** — `energy_at(stem.energy_arc, t)` so onset magnitude (small vs big hits) comes from the stem's RMS at the onset, no new extraction.
- **Word-precise lyric timing** — persist the per-word timestamps the aligner *already computes* (mlx-whisper) so color words land on the word, not the line.
- **Four launch triggers:** guitar-solo Lightning; big-moment whole-house Shockwave (Per Preview, ~once per major moment); periodic per-model drum-onset Shockwaves (rotating group + alternating contrast color + out/in radius per hit); lyric color words → that color on prominent props.
- **Two sparsity scales:** *section selection* (deterministic rotation so not every section features the same accent) and *within-section density* (per trigger — e.g. every drum onset vs the single peak event).
- The existing entrance-feature folds in as the first cookbook citizen.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `show-orchestration`: the orchestrator SHALL place curated trigger effects — deterministic rules mapping musical/lyrical events (guitar solos, drum-onset magnitude, lyric color words) to scaled effects — defined in a hand-editable cookbook, applied sparingly via section-rotation and per-trigger density, with render scope (per-model vs whole-house) and color/direction varied per event.

## Impact

- New `xlights-trigger-cookbook.md`; new `pipeline/triggers.py`; `pipeline/run.py` (trigger layer after features); `audio/lyrics_align.py` + `analyzer` (persist words); `agents/guide.py` (load the cookbook best-effort).
- `features.py` entrance logic folded into the registry (kept behavior).
- Back-compat: no cookbook / empty cookbook → no triggers; word persistence is additive.
- OUT (follow-up): simultaneous same-instant per-prop variety (needs odd/even subgroups — see the deferred follow-up); phoneme timing for singing faces (WhisperX, with its Python 3.14 install hurdle) — word-level here is enough for color.

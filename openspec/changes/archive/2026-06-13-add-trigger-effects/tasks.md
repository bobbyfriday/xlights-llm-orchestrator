## 1. Cookbook + loader + magnitude

- [x] 1.1 `xlights-trigger-cookbook.md`: human-editable trigger definitions (the 4 launch triggers + the folded-in entrance feature), one labeled block each with the D1 fields; a header explaining the field vocabulary for hand-editors
- [x] 1.2 `agents/guide.py`: register + best-effort load the cookbook (missing → "")
- [x] 1.3 `triggers.py` `energy_at(energy_arc, t)` magnitude helper (RMS at time, 0–1 normalized)

## 2. Detectors + realizer

- [x] 2.1 `triggers.py` detector library: `guitar_solo`, `drum_onsets` (magnitude-filtered), `big_moment`, `lyric_color`; each `analysis → [TriggerEvent]`
- [x] 2.2 cookbook parser → `TriggerSpec`s; realizer `TriggerSpec + events → [EffectInstruction]` honoring render scope (per_model/whole_house), rarity, section-rotation selection, per-event color/direction alternation (Shockwave out/in via radius — values live-verified)
- [x] 2.3 fold the entrance-feature in as the first cookbook citizen (keep current behavior)

## 3. Word timing + wiring

- [x] 3.1 `lyrics_align`: persist matched per-line `words:[{word,start,end}]`; `lyric_color` reads them
- [x] 3.2 `run.py`: run the trigger layer after features; tag section_index; through clamp_layer_budget + clamp_hard_caps

## 4. Tests & verification

- [x] 4.1 Hermetic: cookbook parse (valid → specs; unknown detector / malformed → skipped); each detector on synthetic analysis (guitar-solo window; drum onsets with energy magnitude buckets; big-moment = single strongest; lyric color word → event); render scope + rotation + color/in-out alternation; section sparsity (not every eligible section); word-timestamp persistence; back-compat (no cookbook → no triggers)
- [x] 4.2 Live round-trip: Shockwave per-model out (start<end) vs in (start>end) renders as expected; then a full run on DJ → guitar-solo Lightning, rotated per-model drum shockwaves on a SUBSET of sections, one whole-house big-moment, ≥1 color word lit; objective holds; user verdict
- [x] 4.3 PR (user merges)

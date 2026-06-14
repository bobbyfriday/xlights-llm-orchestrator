## Why

Aggressive segmentation now splits long passages into ≤32s analysis segments (Canon's 100s intro → 16 MusicBrief sections incl. four intro pieces). But the **director re-merges** them when planning the ShowPlan — Canon's intro came back as two sections of 63s and 37s, both over the ~35s point where one held look reads as static/boring. The director owns section boundaries (correctly — grouping is a creative call), but nothing tells it that long sections are usually undesirable.

## What Changes

- **Director prompt (LLM):** add a SECTION PACING note — the song is pre-split into musical sections; PREFER to keep that structure; a look held past ~35s reads as boring/static; keep sections ≈10–35s; merging into a longer section is allowed only when the music genuinely stays unified (a sustained build/drone) and is the justified exception, not a grouping of convenience.

This is steering, not enforcement — the director keeps judgment (there can be legitimate long sections), it's just informed of the cost.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `show-orchestration`: the creative direction SHALL be steered to keep sections short (≈10–35s) and treat a section longer than ~35s as a deliberate, justified exception rather than a default grouping.

## Impact

- `agents/director.py` prompt only. No deterministic change; behavior is steered. Back-compat: non-merging is already valid; songs already short are unaffected.

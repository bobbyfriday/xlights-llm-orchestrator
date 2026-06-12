## Why

The directional sweeps landed but don't read, and the palettes wash out (user verdict watching Carol of the Bells). Diagnosis from the run's own instruction stream: all 573 directional chase cells render "Per Model Default" — the chase traverses each prop *internally* in a ~534ms cell, a synchronized flicker rather than motion across the display — and the cell palettes are five near-identical warm golds (#FFF1D0/#FFBF00/#FFF7E5/#FFDB70/#FFD674) because `expand_palette` builds depth variants of one family and cells just rotate them. LEDs render hue contrast well and subtlety terribly: the show needs contrast as its legible signal.

## What Changes

- **Visible sweeps:** directional chase-family cells (ltr/rtl/bounce/center_out/center_in on SingleStrand/Garlands/Marquee/Wave/Bars) default to the GROUP canvas ("Default") so the motion spans the whole group (Left-Right travels across ALL the arches), with `cell_beats` floored at 2 (prompt recommends 4 — a bar-length sweep). Explicit recipe render_style still wins; non-directional cells keep the per-model dark-fix default.
- **LED contrast floor (code-owned):** `knowledge/colors.py` gains hue-spread measurement + `contrast_anchors(palette)`; when a section's resolvable colors cluster within ~60° of hue, a complement anchor is injected. Carrier and accent cells alternate between the two most hue-distant anchors beat-to-beat (the LED-legible signal); texture/bed cells keep the expanded family (depth belongs in washes). The beat-accent color becomes the hue-distant anchor, not brightened-same-hue.
- **Director prompt + catalog note:** LED color reality — palettes need hue contrast (≥1 cool vs warm anchor); subtle tints read as one color on pixels.
- PR workflow: branch `change/add-led-readability`, PR for user merge.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `show-orchestration`: directional cells SHALL render so the motion spans the full target group and persists long enough to track; automated palettes SHALL guarantee hue contrast — when a section's colors cluster in hue a contrasting anchor SHALL be injected, and rhythm-carrying cells SHALL alternate between contrasting anchors beat-to-beat.

## Impact

- `xlights-orchestrator`: `pipeline/weave.py` (directional style/beats defaults, anchor alternation for carrier/accent roles), `pipeline/beats.py` (accent contrast color), `agents/director.py` prompt note.
- `xlights-core`: `knowledge/colors.py` (hue spread, complement injection, `contrast_anchors`).
- Docs: catalog placement-rules contrast note.
- Back-compat: non-directional cells and texture/bed palettes unchanged; washes untouched.

---
name: xlo-sequencing
description: Craft rules for an xLights light show, section by section — which effect families fit intros, verses, builds, choruses, bridges and the peak; how a section's energy maps to intensity, treatment and phrasing; accent and Strobe/Shockwave budgets; the 4-layer ceiling; palette and LED-contrast rules. Load whenever you choose effect_family, effect_types, intensity, treatment, phrasing, palette or fabric for a creative brief (/xlo:design, /xlo:review), or when you weigh a qa.json finding against the craft.
---

# xlo-sequencing

Three hand-editable guides at the repo root are the single source of craft. Do not paraphrase
them from memory — open the file for the decision at hand.

## Which file for which decision

| Decision | Read | Sections |
|---|---|---|
| Effect vocabulary: what an effect looks like, which props it suits, its energy band, how long it may run | `xlights-effects-catalog.md` | §2 quick-reference table + §2.1 duration classes; §3–§10 per-effect entries; **§11 placement decision rules** (apply in order) |
| Rhythm, phrasing, dynamics philosophy; music → effect → prop mapping; song-structure playbook; color strategy; common mistakes | `xlights-sequencing-guide.md` | §1 core philosophy; §2 musical taxonomy; §3 prop roles; §4 mapping matrix; §5 notes per prop type; §6 structure playbook; §7 color; §9 mistakes |
| Render styles (group canvas vs per-model), layer order, blend modes, phrasing → soft edges, which effects sit low (beds) vs high (accents), what pairs with what | `xlights-layering-rendering-guide.md` | §2 render directions; §4 blend modes; §5 phrasing/soft edges; §6 render styles; §9 recipes; **§9b per-effect layering roles** |
| How a chosen effect should actually look, move, stack and breathe: dials, anchors to permute from, twin layers, blend semantics, value-curve shapes, exemplars | the `xlo-effects` skill, `effects/<Type>.md` | |
| Named multi-prop scenes and curated triggers | see the `xlo-scenes` skill | |

Read the catalog in full during `/xlo:design`; dip into the other two by section.

## The rules that most often shape a brief

Energy → intensity → treatment (all from the digest's per-section energy, 0–1):
- Write `intensity` to track the digest's normalized energy; the peak section is the single
  highest, and its `intensity` must be the show's max. Code treats a section within 0.12 of the
  max and ≥ 0.66 as **the peak** and gives it everything (`pipeline/beats.py:resolve_treatment`).
- Fallback treatment when you leave it blank: peak → `full`; < 0.1 → `rest`; ≥ 0.5 → `pulse`;
  ≥ 0.25 → `feature` (if the layout has `SEM_FOCAL`, else `pulse`); otherwise `gesture`.
  Set it yourself to withhold layers on purpose: a verse that is "the chorus but dimmer" reads samey.
- Phrasing: blank defaults to `legato` below 0.5 and `staccato` at/above. Say `legato` for calm or
  melancholy sections that should breathe; `staccato` for punchy ones.
- A section below 0.35 with no `pulse_groups` and no rhythm props in `target_groups` is
  **non-rhythmic**: no beat fabric, no beat accents. That is how you ask for stillness.

Vary the vocabulary:
- Never the same `effect_family` on adjacent sections (the validator warns). Field several
  families across the show; all-On/SingleStrand/Color Wash reads monotone even with new colors.
- Typical families by moment (from the catalog; pick only placeable types in `vocab.json`):
  - builds / rising energy: Spirals, Pinwheel, Bars, Fan
  - driving rhythm / chorus: Bars, SingleStrand, Marquee, Garlands, Wave
  - gentle / verse / ambient: Ripple, Color Wash, Plasma, Twinkle, Curtain
  - organic / psychedelic: Butterfly, Galaxy, Kaleidoscope, Plasma
  - warm / intense: Fire, Plasma, Meteors
  - drama / falling / winter: Meteors, Snowflakes, Snowstorm (whole-canvas groups)
  - peak / celebration: Fireworks, Spirals, Pinwheel, Fan, full-display washes
  - short impact accents: Shockwave (the community's default hit), Strobe, Lightning
- Prefer Shockwave for hit-class accents. **Strobe is peak-payoff only** — the climax, never a
  verse hit. Lightning for storm/rock stingers. Hit effects are ≤ 1 bar; Shimmer ≤ 2 bars.
- One high-attention feature per moment (Kaleidoscope, Shader, Shockwave, Fireworks); everything
  concurrent is bed or accent tier.
- Prop fit: no texture effects (Plasma, Fire, Liquid) on line props (arches, outlines, canes); no
  media effects (Text, Pictures, Video) off a matrix. Fire on the whole yard reads flat orange —
  keep it to the frame or hero. Fan and Shockwave are render-expensive: spend them on the
  hero/canvas, not `SEM_ALL`. Butterfly reads radial on round props.

Structure:
- The peak gets the broadest coverage (most groups / `SEM_ALL`) and the biggest gesture; the section
  before it builds into it. Never spend a narrow or dark look on the peak.
- Repetition with escalation: recurring labels ("chorus") reuse the motif and grow — code adds a
  group per later occurrence and a sparkle pop on the final one; plan chorus 1 at ~70%.
- Contrast is the tool: quiet sections stay quiet; blackouts before a drop; outros subtract.
- Verses: 2–3 active groups. Save the hero for the chorus. Cut 10% from every first draft.

Palette (per section, 3–5 named colors from `vocab.json` `colors`):
- Must span hues — at least one cool vs one warm anchor. LEDs render hue contrast well and
  tonal subtlety terribly: gold + amber + warm white is ONE color outdoors.
- Multi-color effects (Plasma, Spirals, Bars) need 3+ colors to render.
- Holiday songs: red + green + white primaries with 1–2 accents (gold, cool white, ice blue) unless
  the mood clearly calls for something else. White flashes are a spice, not a bed.
- Feature props pop: when a section centers on `SEM_SNOWFLAKES` / `SEM_SPINNERS` / `SEM_CHARACTERS`, make them the
  bright light-colored focal over a different-hued bed on a broad group. A featured section is
  never near-black.

Layers: ≤ 4 per row; code clamps (`clamp_layer_budget`). Don't design stacks deeper than that.

## What code decides (don't try to say it in the brief)

- Render style per effect (`pipeline/render_style.py:fallback_style`): sweeps → Per Preview,
  simple fills → Default, everything else → Per Model Default.
- Blend defaults: the beat carrier blends `Max` over the bed, texture cells `Brightness`
  (`pipeline/weave.py`). `fabric.blend` overrides only the carrier.
- Coverage by energy: how many of your `target_groups` light is `round(n × (0.3 + 0.7 × intensity))`,
  first-listed first — so order `target_groups` by priority (`pipeline/beats.py:coverage_cap`).
- Beds, peak fill, beat accents on the metric ring, curated triggers, climax flashes, phrase
  curves, the peak's composite stack on the hero, counter-rotation, the layer clamp, and the
  wash-occlusion guard are all deterministic layers over your brief. You steer them through the
  fields the `xlo-brief` skill lists; you never place individual effects.

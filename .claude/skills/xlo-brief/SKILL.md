---
name: xlo-brief
description: How to author, validate and revise creative_brief.json — the single judgment artifact of an xLights show. Every ShowPlan / SectionPlan field in plain terms with its default and what code does with it; the treatment table (full|pulse|feature|gesture|rest) and how an explicit fabric carrier re-enables the weave under pulse/feature; the fabric knobs (carrier, alternation, cell_beats, blend, direction_change, mirror); scene_id + scene_cast; label conventions; key moments (incl. lyric captions via text); song coverage and downbeat alignment; a complete worked section; the validate-fix loop over validation.json; presenting the brief in viewer language; applying review feedback by section or by time range (splitting a section). Load for /xlo:design, /xlo:realize, /xlo:review and whenever you edit a brief.
---

# xlo-brief

The brief is `creative_brief.json` in the song's cache dir
(`$XLO_CACHE_DIR/orchestrator/<song-slug>--<hash>/`; every `xlo` command prints the path). Its
contract is `ShowPlan` in `packages/xlights-orchestrator/src/xlights_orchestrator/show_plan.py`;
the per-song schema `creative_brief.schema.json` (written by `xlo groups`) enumerates the valid
names; `vocab.json` is the same vocabulary as plain lists: `groups`, `effect_types`, `cellable`,
`scene_ids`, `stems`, `colors`.

Craft lives in the companion skills: `xlo-sequencing` (effects, energy, palette), `xlo-scenes`
(scenes, triggers), `xlo-layout` (groups). This skill is the file and the loop.

## Authoring workflow

1. Read `analysis_digest.md` (headings: Overview · Energy arc · Sections (table + one block per
   section with its lyric lines) · Lyrics (repeated lines, lyric markers) · Instrument entrances ·
   Harmony · Mood) and `vocab.json`.
2. Discuss the structure with the user: where the sections fall and what each is (verse, chorus,
   build, bridge, drop, outro), the peak, the mood arc, what the song is about. The user's reading
   wins. Encode the agreed interpretation in `experience`, `concept`, the section `label`s and
   `key_moments`. There is no separate interpretation file.
3. Write `creative_brief.json`, starting with `"$schema": "creative_brief.schema.json"` (VS Code
   validates it when the user edits by hand). Base section boundaries on the digest's section
   table — those are already downbeat-snapped. Times are integer milliseconds (the digest shows
   m:ss.t).
4. Run `xlo validate-brief --song <mp3>` (`--cache <dir>` is the alternative). Read
   `validation.json`: `{ok, errors:[{path, message, allowed}], warnings:[{path, message}]}`.
   For every error, go to `path` (e.g. `sections[3].target_groups[1]`), replace the value with one
   from `allowed` (or fix the time), and re-run until `ok` is true. Treat warnings as advice:
   snap a boundary to the named downbeat, split a > 32 s section, vary a repeated family — unless
   the repetition is deliberate.
5. Present the brief to the user **in viewer language, never as JSON**: section by section, the
   time range, what a viewer sees (the `look`), the colors, the scene and fabric choice in a few
   words, then the show palette and the key moments. Invite changes before `xlo realize`.
6. `xlo realize` → `xlo qa` → read `qa.json`; then `xlo apply`.

## Show-level fields (`ShowPlan`)

| Field | Plain meaning | Default | Code uses it? |
|---|---|---|---|
| `sections` | the ordered list of sections (below) | required | yes — everything |
| `experience` | 1–2 paragraphs of what the audience sees and feels, in everyday words, no music theory | `""` | no (the user reads it) |
| `concept` | the artistic idea in a paragraph | `""` | no |
| `palette` | `{name, colors[], mapping}`: the show's named colors and how color follows the song | `null` | `colors` are validated; video-plan uses them as the film's color world |
| `group_motifs` | `{"<group>": {role, style, color}}`: each group's job across the show | `{}` | no (coherence notes for you) |
| `key_moments` | `[{at_ms, kind, treatment, text}]` — see Key moments | `[]` | yes |

## Section fields (`SectionPlan`)

| Field | Plain meaning | Default | What code does |
|---|---|---|---|
| `start_ms`, `end_ms` | the section's span, integer ms | required | every layer grids inside it |
| `label` | the musical label: `"intro"`, `"verse 1"`, `"chorus 2"`, `"bridge"`, `"drop"`, `"outro"` | `""` | recurring labels rhyme and escalate (see Labels); finalize's section timing track; video asset groups |
| `target_groups` | the groups that light here, **in priority order** (from `vocab.json` `groups`) | required | one base row per group cycling `effect_family` + `effect_types`; coverage keeps the first `round(n × (0.3 + 0.7 × intensity))` |
| `effect_family` | the main effect type (placeable) | required | the first base row's effect; "same as previous section" warns |
| `effect_types` | 1–3 further placeable types for contrast and texture | `[]` | cycled onto the remaining target groups; the first cellable one (not the carrier) becomes the fabric's texture cell |
| `intensity` | 0 = calm … 1 = peak, tracking the digest's energy | required | wash brightness, coverage, accent density, treatment/phrasing fallbacks, the peak |
| `rationale` | why, citing the section's dynamics / stems / accents | `""` | no |
| `look` | what a viewer sees, plain language | `""` | no — it is what you present |
| `palette` | 3–5 named colors (or `#RRGGBB`) spanning hues | `[]` | cell/bed/accent colors; contrast anchors for the beat |
| `motion` | the motion feel in words | `""` | no |
| `transition` | how it flows into the next section, in words | `""` | no (cell transitions are code-chosen) |
| `phrasing` | `"legato"` (soft evolving edges) or `"staccato"` (crisp on/off) | `""` → legato below 0.5, staccato at/above | soft-edge fades on cells and accents; legato lengthens short cells |
| `treatment` | which layers run — see the table | `""` → by energy | withholds layers, not just dims them |
| `scene_id` | a cookbook scene (`SC-NN` from `vocab.json` `scene_ids`) or `""` | `""` | validated; the scene's stack table **replaces** the generic base rows (see `xlo-scenes`) |
| `scene_cast` | `{"G2-HERO": "SEM_FOCAL", "G2-RHYTHM": "SEM_ARCHES", …}`: one real group per archetype row of the scene | `{}` → cast by role (`xlo-scenes` table) | the groups the scene rows are placed on; values must be `vocab.json` `groups` (error), unknown rows warn |
| `scene_adaptation` | the cast in words, plus what this layout cannot cast | `""` | no (the reader's note) |
| `pulse_groups` | 2–4 groups that walk the beat | `[]` → arches, canes, minis, snowflakes | overrides the metric ring; also opts a quiet section into rhythm |
| `follow_stem` | the stem the hero prop follows (`vocab.json` `stems`) | `""` → the melodic stem with most onsets | the hero's onset layer |
| `accent_effect` | the per-beat punctuation effect | `""` → `On` | the ring's accent cells |
| `pulse_on` | `"beat"` or `"onset"` | `""` | validated; advisory today |
| `fabric` | `{carrier, alternation, cell_beats, blend, direction_change, mirror}` — see Fabric | `null` → code chooses | the beat carrier's design; how often directional effects turn |

### Treatment → which layers appear

| `treatment` | bed | woven fabric (carrier + texture) | beat accents | composites / VU / extras | feature pop (hero / sparkle props) | phrase curves | groups |
|---|---|---|---|---|---|---|---|
| `full` | full | yes | full | yes | yes | yes | all kept by coverage |
| `pulse` | full | no — **yes (carrier + texture) when `fabric.carrier` is set** | full | no | yes | yes | all kept by coverage |
| `feature` | dim | no — **the carrier cell alone when `fabric.carrier` is set** | sparse | no | yes | no | one hero spotlight over a dim bed |
| `gesture` | none | the carrier alone | none | no | no | no | ≤ 2 |
| `rest` | dim | no (even with a carrier) | none | no | no | no | ≤ 2 |

Blank → by the section's own intensity: the peak → `full`; < 0.1 → `rest` (an explicit < 0.1 is
always `rest`); ≥ 0.5 → `pulse`; ≥ 0.25 → `feature` if the layout has `SEM_FOCAL` else `pulse`;
otherwise `gesture`. `full` is for the peak and the biggest choruses; `pulse` is the workhorse.

The fabric rule: naming a `fabric.carrier` is asking for that motion, so `pulse` and `feature`
weave it (the other fabric knobs apply too; a carrier that is not cellable is a validation error).
A `fabric` with no `carrier` (or no `fabric` at all) leaves the table as written. When the carrier
weaves, the beat accents drop their every-beat chase on the pool (the carrier is the beat).

### Fabric: the beat carrier's knobs, and how motion turns

The fabric is the section's beat-synchronous cell weave: one **carrier** cell design alternating
across the rhythm pool, plus one sparse **texture** cell from your `effect_types`. Code expands the
designs across the real beat grid (`pipeline/weave.py:weave_from_brief`). A section that is
non-rhythmic (intensity < 0.35, no `pulse_groups`, no rhythm props in `target_groups`) gets no
fabric at all, whatever `fabric` says. Treatments `pulse`, `feature`, `rest` withhold it too.

| Knob | Values | Default | What changes visibly |
|---|---|---|---|
| `carrier` | a type from `vocab.json` `cellable` (SingleStrand, Bars, Wave, Marquee, Garlands, Spirals, Pinwheel, Ripple, Butterfly, Meteors…) | `""` → SingleStrand | what the beat looks like: a chase, stripes, a wave, a spin |
| `alternation` | `chase` · `pingpong` · `all` · `sparse` | `""` → chase | which pool group each beat lights: in order and wrap; back and forth; every group at once (unison); one group every other beat with a breath between |
| `cell_beats` | 1–8 | `null` → 1 | how long each cell holds: 1 = every beat, 2 = half-time feel, 4 = one per bar |
| `blend` | an xLights layer method from `BLEND_METHODS` (`Max`, `Brightness`, `Normal`, `Average`, `Additive`, `1 is Mask`, `1 is Unmask`, `1 reveals 2`, …) | `""` → Max | how the carrier sits over the bed: Max keeps the brighter; Brightness modulates; masks/reveals let the bed show only inside the cell's shape |
| `direction_change` | `hold` · `phrase` · `bar` · `beat` | `""` → by energy: the peak `bar`; quiet (gesture/rest or intensity < 0.35) `phrase`; else `bar` | how often EVERY directional effect in the section turns (Bars, Single Strand, Spirals, Pinwheel, Meteors, Fill, Wave…, not just the carrier): one way all section; flip each 4-bar phrase; flip each bar; flip each beat. Under `bar`/`beat` the kind of motion also changes each phrase (left/right → up/down → expand/compress) |
| `mirror` | `true` · `false` | `null` → on | the right-hand groups (`SEM_SIDE_RIGHT`) move opposite the left, so the sides meet and part; `false` sends both the same way |

Direction floors (`pipeline/motion.py`): a sweep never flips faster than every 2 beats; Meteors turn
at most once a phrase; spins reverse on the cadence itself (every downbeat under `bar`), and stacked
spins (SC-02) stay opposed; Fill/Fan pick one direction per placement. Spirals also change strand
count, thickness and twist each phrase (ribbons ↔ candy cane). The hero runs one kind of motion ahead of the yard. Turns count
from the section's start, so put the section on its real downbeat.

The pool the carrier walks is `pulse_groups` when given, else the rhythm props among
`target_groups` (`SEM_ARCHES`, `SEM_CANES`, `SEM_MINITREES`, `SEM_SIDE_*`). Omit the whole block
(or leave fields `""`/`null`) and the section realizes exactly as the deterministic fallback —
and, under `pulse` / `feature`, with no fabric at all. Set `carrier` to get the weave there.

### Labels

- Lowercase words with an optional number: `"verse 1"`, `"chorus 2"`, `"chorus"`, `"bridge"`.
- Normalization strips trailing digits and `# _ -` separators (`"Chorus #3"` → `chorus`), so every
  occurrence of a part gets the same word and a different number.
- Identities with ≥ 2 occurrences **rhyme and escalate**: the same palette rotation order, +1 lit
  group per later occurrence, and a sparkle pop on an accent group for the final one. Chorus 1
  should be written at ~70% so the last chorus has room (SC-14 doctrine).
- One-off parts get their own words (`intro`, `build`, `drop`, `solo`, `outro`); don't reuse
  `verse` for a bridge just because it is quiet.
- `xlo finalize` writes these labels into the Section timing track; `xlo video-plan` films
  repeats of the same label as one returning shot.

### Key moments

`{"at_ms": 98000, "kind": "climax", "treatment": "a full-display shockwave into an all-on explosion"}`.
`kind` `climax` / `accent` / `drop` / `hit` → a short white flash on `SEM_ALL` at `at_ms` (at
most 8 are used; put the biggest hits first). `kind` `lyric` with a `text` → that lyric line as
a caption on the matrix model (`{"at_ms": 61000, "kind": "lyric", "text": "ring the bells",
"treatment": "the hook on the matrix"}`): code snaps it to the aligned lyric line that matches
the text and drops it when none matches (never a guessed time); at most 4 captions, ≥ 20 s
apart, one per section, never in the peak section, and only when the layout has a matrix. Take
the lines from `analysis_digest.md`; no comma or `=` in `text`. Any other `kind` is descriptive.
Code adds a `climax` at the peak section's downbeat when you give none inside it, and an
`entrance` per detected instrument entrance. `treatment` is free text for the reader.

### Coverage and boundaries (validator errors vs warnings)

Errors (block realize): sections not ordered by `start_ms`; first section starting more than
500 ms after 0; a gap or overlap > 500 ms between neighbours; last section ending more than
500 ms before or after the song's duration; `end_ms` ≤ `start_ms`; any name outside the
vocabulary; `intensity` outside 0–1; `fabric.carrier` not cellable; `cell_beats` outside 1–8.
Warnings (ok stays true): a boundary more than 500 ms from a downbeat (the message names the
nearest one — move to it); a section longer than 32 s (split it so the look can evolve); the same
`effect_family` as the previous section.

## A complete worked section

```json
{
  "start_ms": 60186,
  "end_ms": 88400,
  "label": "chorus 1",
  "target_groups": ["SEM_FOCAL", "SEM_ARCHES", "SEM_CANES", "SEM_ALL_LESS_FOCAL", "SEM_SNOWFLAKES"],
  "effect_family": "Bars",
  "intensity": 0.72,
  "rationale": "First chorus: drums 41% and bass 23% lead, energy jumps 0.35 → 0.72; the hook line 'ring the bells' lands at 61.0 s. Held to ~70% so chorus 3 can be the biggest.",
  "look": "Gold bars sweep across the big tree while the arches and canes trade a steady back-and-forth pulse on the beat; the rest of the yard glows deep blue underneath, and the snowflakes sparkle white on the downbeats.",
  "palette": ["deep blue", "gold", "warm white", "teal"],
  "effect_types": ["Bars", "SingleStrand", "Color Wash"],
  "motion": "Medium-fast horizontal sweeps on the hero; a ping-pong chase across the ground props every two beats.",
  "transition": "Snap on the downbeat of verse 2.",
  "phrasing": "staccato",
  "treatment": "pulse",
  "scene_id": "SC-01",
  "scene_cast": {"G2-HERO": "SEM_FOCAL", "G2-RHYTHM": "SEM_ARCHES", "G0-ALL-LESS-HERO": "SEM_ALL_LESS_FOCAL"},
  "scene_adaptation": "hero stack on the mega tree, arches drum (canes join through pulse_groups), the rest of the yard glows under it; snowflakes sparkle from the beat layer",
  "pulse_groups": ["SEM_ARCHES", "SEM_CANES"],
  "follow_stem": "drums",
  "accent_effect": "On",
  "pulse_on": "beat",
  "fabric": {
    "carrier": "SingleStrand",
    "alternation": "pingpong",
    "cell_beats": 2,
    "blend": "Max"
  }
}
```

Note: with `treatment: "pulse"` the fabric weaves here because `fabric.carrier` is set (drop the
`carrier` to keep a pulse section fabric-free). The SC-01 stack replaces the generic base rows:
`Bars` (the `effect_family`) is the hero's feature layer over its dim wash and Max-blended
Twinkle, `SEM_ALL_LESS_FOCAL` carries the 35 % wash, `SEM_ARCHES` the Single Strand chase. Copy
this section for `chorus 2` / `chorus 3`, raise `intensity`, set the last one
`"treatment": "full"`, and let the label escalation do the rest.

## Applying review feedback

Always: edit the brief → `xlo validate-brief` (loop to ok) → `xlo realize` → `xlo apply` (a full
re-emit of the whole show; `--render` also renders). Never edit `instructions.json` by hand.

- **Section feedback** ("section 4 is too busy, calm it down"): change only that section —
  typically `intensity` down a step, `treatment` to `feature` or `gesture`, fewer `effect_types`,
  `phrasing: "legato"`, a longer `cell_beats` or `alternation: "sparse"`. Leave every other
  section's entry byte-identical.
- **Time-range feedback** ("redo 1:05–1:30, bluer") when the range is inside a section: split
  that section at the requested times. Copy the parent's fields into every piece (same label,
  groups, effects, scene, fabric), set the new `start_ms`/`end_ms` so the pieces tile the parent
  exactly, and change only what was asked in the middle piece. Keep the parent's `label` on all
  pieces so escalation counts stay right. If the validator then warns that a new boundary is off
  a downbeat, move it to the named downbeat and tell the user the exact time you used.
- **Range spanning sections**: apply the edit to each section it covers, splitting only the
  first and last where the range cuts inside them.
- **qa.json findings are proposals.** Each has `section_index`, severity, metric and a
  plain-language fix (`visual:dark` = an energetic section renders dark → raise intensity, widen
  `target_groups` with a broad group, or lift the treatment; `visual:static` = coverage barely
  moves → add a rhythm pool / a cellable `effect_type` / `fabric`). Propose the brief edit and wait
  for the user; nothing in `qa.json` gates any stage.
- **applied.json skips** (`target-missing`): swap the group for one in `vocab.json` `groups`.

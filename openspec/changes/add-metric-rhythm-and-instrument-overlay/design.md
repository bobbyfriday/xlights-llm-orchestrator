## Context

`place_beat_accents` (beats.py) today: fills a `groups` list from `pulse_groups`→`RHYTHM_POOL`
(arches+canes+minitrees)→sides→targets; on the downbeat hits *all* of `groups` + `ACCENT_GROUPS`
(snowflakes/spinners); on off-beats rotates *one* group (intensity-gated stride, bounces per bar);
a hero layer rides the single prominent stem's onsets on `SEM_FOCAL`. It discards the layout's
capability/band/side classification, has no backbeat, fires sparkle every bar, and its 250ms pops
flash in calm sections.

What we can build on: `build_sem_groups` classifies every prop by capability (`res`:
LINEAR/POINT/MATRIX), band (ROOF/MID/GROUND), side, focal; the trigger layer's `energy_at` gives a
per-onset magnitude (the stem's normalized RMS at the onset); `resolve_phrasing` /
`soft_edge_settings` (mood-fades) give phrasing→soft-edge; `onsets_by_stem` is already computed per
section. xLights constraint (verified): a within-group spatial chase needs a GROUP-buffer render;
per-model render runs every prop simultaneously, and the `_LTR` groups only reorder members (they are
referenced nowhere in rendering). So the metric walk must be **discrete pulses on distinct targets**,
not a within-group chase.

## Goals / Non-Goals

**Goals:**
- A visible **meter**: each beat of the bar lights a distinct rhythm group (prop-family-per-beat),
  honoring the real `beats_per_bar`.
- An **instrument-mapped overlay**: backbeat (2&4), top-magnitude drum sparkle, melodic-lead hero,
  bass-on-ground — the groove on top of the meter.
- **Phrasing-aware** accents everywhere (legato softens/sparsens, staccato crisp).
- Group selection derived from the layout's role/capability, with the Director still able to override.
- Preserve the still-section guard, the per-section caps, and `carrier_covers` de-duplication.

**Non-Goals:**
- Within-group buffer chases / `_LTR` rendering (a separate, optional texture later).
- Kick/snare/hat separation (we have one "drums" stem — backbeat is positional, not snare-detected).
- Changing the weave, peak fill, ensemble bed, triggers, or key-moment flashes.
- A new Director field (reuse `pulse_groups`, `follow_stem`, `phrasing`).

## Decisions

**1. Meter backbone = discrete pulse on a "metric ring" of `bpb` distinct groups.**
Build an ordered ring of rhythm groups (default `[SEM_ARCHES, SEM_CANES, SEM_MINITREES, SEM_SNOWFLAKES]`
filtered to available, padded/truncated toward `bpb`; the Director's `pulse_groups` override the ring
when set). On beat index `i`, pulse `ring[i % len(ring)]` — discrete, per-model render (each beat hits
a *different* target, so per-model is correct and the walk is real). Downbeat (`i % bpb == 0`) keeps a
slightly bigger/wider hit (the bar anchor). When the ring is shorter than `bpb` it wraps; longer, it
truncates to `bpb`.
*Alternatives:* within-group buffer chase (rejected — per-model can't travel, `_LTR` is dead);
individual-prop targeting (deferred — not every prop is a sequence element).

**2. Group selection is role/capability-aware, not a flat tuple.**
A helper picks, from `available_groups`: the metric ring (rhythm-cell groups, prefer LINEAR then
POINT), the sparkle groups (`ACCENT_GROUPS`/POINT), the hero (`SEM_FOCAL`/MATRIX), the bass band
(`SEM_BAND_GROUND`), the backbeat group (a contrasting side/accent group). Each falls back gracefully
(missing category → that sublayer no-ops, never errors). The Director's `pulse_groups` still seed the
ring.

**3. Groove overlay = four instrument-routed sublayers, additive over the backbone.**
- **Backbeat:** on beats where `i % bpb` ∈ the backbeat set (4/4 → {1,3} = beats 2&4), pulse the
  backbeat group. Positional (no snare stem). Gated to drum-present sections (share/onsets) so a
  drumless ballad doesn't get a phantom snare.
- **Sparkle:** snowflake/spinner props ride the **drums** stem onsets ranked by magnitude
  (`energy_at`), keeping the top `N` per section (a tunable count / top-pct) — replaces every-bar
  firing. No drums → no sparkle.
- **Hero:** `SEM_FOCAL` rides the prominent **melodic** stem — the highest-share stem among
  {guitar, piano, vocals} (NOT drums/bass/other) — on its real onsets, magnitude-capped and
  phrasing-softened. This is where piano lives (never the metric walk).
- **Bass:** a low pulse on `SEM_BAND_GROUND` on bass onsets (sparser, longer) — low sound, low props.

**4. Instrument → layer routing is an explicit, tunable table.**
A small `route_stems(section, sa)` returns `{drums: backbone+sparkle, bass: ground, melodic_lead:
hero}` from per-section stem shares/onsets. Centralizing it makes piano's behavior a dial (e.g.
"melodic lead rides hero onsets" vs a future "sustained chord wash") we tune after the live render,
not a guess. Dials (counts, top-pct, backbeat gate, ring default) live in `tuning.py`.

**5. Phrasing modulates every gesture (reuses mood-fades).**
`resolve_phrasing(section.phrasing, intensity)` → legato lengthens accent duration toward the
beat/onset gap, applies `soft_edge_settings` fades, and sparsens (bias toward downbeats / fewer
onsets); staccato keeps today's crisp 250ms. This finally softens the accent layer in calm sections.

**6. `carrier_covers` and the still-section guard are preserved.**
When a weave carrier already rides the rhythm pool, the meter backbone defers (overlay still places),
exactly as the every-beat chase defers today. `section_is_rhythmic` still gates the whole layer.

## Risks / Trade-offs

- **Metric walk feels mechanical over a long show** → phrasing sparsens/softens it in calm sections;
  the groove overlay adds variation; density still scales with intensity. Tune on the drum-heavy song.
- **Piano-on-hero reads busy/flashy** → it's phrasing-softened (legato) and magnitude-capped; routing
  is a dial — fall back to top-onset-only or a sustained wash if the live render shows flashing. This
  is the explicit verify-and-tune item (Christmas Canon).
- **Backbeat fires on a drumless song** → gated on drum presence (share/onset threshold).
- **Ring shorter than `bpb` / few rhythm groups** → wraps; with <2 groups the backbone degrades to a
  single-group pulse (still valid). Sparse layouts never error.
- **Golden/accent tests change substantially** → expected; regenerate golden and rewrite the
  beat-accent unit tests against the new structure, asserting the new invariants (per-beat distinct
  target, backbeat positions, top-hit sparkle).

## Open Questions

- The default metric ring's 4th member (snowflakes vs a side group vs mini-trees-doubled) — seed with
  the sparkle group and tune visually.
- Sparkle/hero top-`N` counts and the backbeat drum-presence threshold — seed from the trigger layer's
  constants and tune on `dj play a christmas song`.
- Whether the downbeat anchor should additionally fire the whole ring (a fuller "1") — decide on render.

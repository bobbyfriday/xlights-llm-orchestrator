# Craft Roadmap — closing the gaps the sequencing guide calls for

Scopes every Tier-1 (missing infrastructure) and Tier-2 (have data, unused) gap from
`xlights-sequencing-guide.md` into concrete OpenSpec changes, dependency-ordered. Each is
proposed + pre-mortem'd + built individually when we get to it.

## Grounding that shapes these (verified 2026-06-09)
- **Value curves**: encoded as `C_VALUECURVE_<Param>=Active=TRUE|Id=…|Type=Ramp|Min=..|Max=..|P2=..|RV=TRUE`. We already PARSE/classify them (`settings.py` `parse_value_curve`/`classify_value_curve`), but never SYNTHESIZE them. Present in some corpus files.
- **Application seam exists**: `place_preset(knob_values=dict)` overrides settings keys, and `EffectInstruction.knob_values` already flows through. So a value curve or a brightness is just a `knob_values` entry — no new placement plumbing.
- **Brightness**: `C_SLIDER_Brightness` (static) is a common corpus knob; `C_VALUECURVE_Brightness` (ramp) also exists.
- **Submodels**: this user's `rgbeffects.xml` has **0 SubModels** → submodel work is DEFERRED (not applicable to the current layout).
- **Groups we already have** for choreography: `02_GEO_Left/Center/Right` (call-and-response), `08_HERO_*` (hero), `04_BEAT_*` (rhythm).
- **Data we already have**: per-section intensity, beats/bars/onsets, chords, `repetition_map` (in the brief), `key_moments`/`featured_lyric_moments`, lyric timing track, energy arc.

---

## Foundational layer

### 1. `value-curve-synthesis` ⭐ (Tier-1 #1) — Complexity: M
**Gap:** "value curves are your friend," builds/swells/fades/attack-release, "Spirals with a value-curve on speed is the workhorse build."
**Approach:** a `value_curve(param, shape, lo, hi)` synthesizer that emits the `Active=TRUE|Type=Ramp|Min|Max|P2|RV` string for the common shapes (Ramp Up, Ramp Down, Ramp Up-Down, flat). Apply via `EffectInstruction.knob_values["C_VALUECURVE_<param>"]`. We already parse them, so round-trip-validate against `parse_value_curve`.
**Unblocks:** brightness ramps (#2), accelerating builds (#9 build), swells on held notes, fades (intro/outro), per-bar builds. **Depends on:** nothing (uses the existing knob seam).

### 2. `effect-intensity-and-brightness` ⭐ (Tier-1 #2) — Complexity: M
**Gap:** "brightness follows the energy curve," "dim everything to ~20% during a solo," "frame at 30–60% in verses." Also the **wash-dimness** we saw on screen.
**Approach:** an energy→brightness mapping; the wash/supporting effects get a `C_SLIDER_Brightness` (static) or a `C_VALUECURVE_Brightness` swell (via #1) keyed to `section.intensity` and prop role; the hero/focal prop stays bright, the bed dims. Code-applied like palette/intensity passes.
**Unblocks:** contrast, one-focal-point, the dim-wash fix, solo dimming. **Depends on:** #1 (for ramps; static brightness works without).

### 3. `intentional-darkness` ⭐ (Tier-1 #3) — Complexity: M
**Gap:** "blackout is the most underused effect," "darkness is a tool," "the blackout before the drop is what sells it," "snap to black on the final note."
**Approach:** from the energy arc, detect genuine low-energy/silence windows and the pre-drop beat; INTENTIONALLY leave props dark there (place fewer/no effects; emit a blackout gap) instead of filling every group. A restraint pass: in low-intensity sections, light only the bed + focal, not all targetable groups.
**Unblocks:** contrast, dramatic pauses, the drop payoff. **Depends on:** none (pairs with #2).

---

## Tier-2 choreography (data exists, add the logic)

### 4. `motif-reuse-and-escalation` (Tier-2 #8) — Complexity: M
**Gap:** "reuse the chorus motif, escalate 70%→90%→100%+accents; the last chorus is the biggest."
**Approach:** use the brief's `repetition_map` to give recurring sections the SAME effect/color motif, and escalate per recurrence — more prop groups, higher brightness (#2), extra accent layer on the final chorus. Director/generator + a deterministic escalation pass.
**Unblocks:** recognizable, building shows. **Depends on:** #2 (escalate via brightness/density).

### 5. `spatial-choreography` (Tier-2 #9, #10) — Complexity: M
**Gap:** "call-and-response: lead=left, answer=right," and the DROP formula "blackout → white flash → full motion."
**Approach:** call-and-response alternates `02_GEO_Left`/`Right` on phrase boundaries; the drop (a `key_moment`) executes blackout (#3) → 1-frame white flash on all props → full-display motion. Deterministic placement around key moments + the GEO groups.
**Unblocks:** spatial interest, the single biggest visual moment. **Depends on:** #3 (blackout).

---

## Music-reactive params

### 6. `music-driven-effect-params` (Tier-1 #7)
**6a — speed → energy: ✅ DONE** (`add-effect-speed`). Section energy drives `E_SLIDER_<Effect>_Speed` (appended via extra_settings; key follows the corpus convention; verified stored intact). No new audio needed.
**6b — direction → pitch: ⏸ PARKED (low ROI, decided 2026-06-09).** Grounding: only ~4/10 of our effects support Up/Down (Bars/Spirals/Garlands/Fill); the rest use Left/Right/expand, so pitch→direction can't apply to most. AND it needs a new pitch extractor (`librosa.pyin` is monophonic — unreliable on a polyphonic/instrumental mix without a vocal/lead stem) + augment-and-resave re-analysis. Lot of new infra for a marginal, often-wrong visual. Revisit only for vocal songs (drive pitch off the vocal stem) if ever worth it. Nothing was built/scaffolded for 6b — nothing to remove.

---

## Vocal & narrative (vocal songs)

### 7. `lyric-driven-effects` (Tier-1 #4) — Complexity: L
**Gap:** singing **Faces** (phoneme timing), word "mickey-mousing" (fire/shine/snow → literal effects), **Text** on matrix.
**Approach:** Faces effect on character props driven by the lyric/phoneme timing track (built); a keyword→effect map for emphasis words at `featured_lyric_moments`; Text effect rendering lyric phrases on the matrix. Needs phoneme-level timing (we have phrase/word; phonemes may need extraction). Instrumental songs skip entirely.
**Unblocks:** the whole vocal dimension. **Depends on:** the lyric timing track (done); possibly a phoneme extractor.

### 8. `matrix-narrative-text` (Tier-1 #6, text subset) — Complexity: M
**Gap:** "the matrix is the storyteller: Text/Pictures/Video/Shaders."
**Approach:** generate **Text** effects on the matrix (section labels, lyric phrases, song title) — achievable with stock effects + no assets. Pictures/Video/Shaders need asset management → OUT for now.
**Unblocks:** narrative matrix content. **Depends on:** none. (Overlaps #7's text.)

---

## Deferred / conditional

### 9. `submodel-targeting` (Tier-1 #5) — Complexity: L — **DEFERRED**
Tree zones/rings for drum-kit mapping & vertical runs. **This layout has no submodels**, so not applicable now; revisit if the user adds submodel'd props.

---

## Recommended build sequence
1. **value-curve-synthesis** (foundation — unblocks the most)
2. **effect-intensity-and-brightness** (fixes the visible wash-dim; one-focal-point)
3. **intentional-darkness** (contrast — the guide's loudest theme)
4. **motif-reuse-and-escalation** (cheap, big craft impact; data exists)
5. **spatial-choreography + drop** (uses darkness)
6. **music-driven-effect-params** (speed/direction)
7. **lyric-driven-effects** (vocal songs; biggest single build)
8. **matrix-narrative-text**
9. ~~submodel-targeting~~ — deferred (no submodels in this layout)

Items 1–3 are the highest leverage and directly address what's visible on screen today.

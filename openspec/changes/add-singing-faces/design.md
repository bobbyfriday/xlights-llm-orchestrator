## Context

Confirmed against the live layout + saved sequences:
- `GE Hanging Bulb Singing-2/3/4` (DisplayAs=Custom) each have `faceInfo` defs — a `NodeRange` def named
  **"Bulb"** and a `Matrix` def — covering `Mouth-{AI,E,FV,L,MBP,O,U,WQ,etc,rest}` + `Eyes-{Open,Closed}`.
- The user's prior sequences use these exact Faces keys: `E_CHOICE_Faces_FaceDefinition`,
  `E_CHOICE_Faces_Phoneme`, `E_CHOICE_Faces_TimingTrack`, `E_CHOICE_Faces_Eyes`,
  `E_CHOICE_Faces_EyeBlinkFrequency`, `E_CHECKBOX_Faces_Outline`,
  `E_CHECKBOX_Faces_SuppressWhenNotSinging`, `E_CHECKBOX/E_TEXTCTRL_Faces_TransparentBlack`.
- `sa.lyrics.lines[].words` already holds `{word, start, end}` (seconds) from Whisper alignment on the
  vocals stem. The timing-track patcher (`pipeline/timing.py`) writes single-`EffectLayer` tracks today.
- `Faces` is in `ASSET_BOUND_TYPES` → excluded from the mined preset library; `place_preset` would fail
  on it (no Look). Layout semantics classify `SINGING_FACE` and exclude it from `SEM_` groups.

## Goals / Non-Goals

**Goals:**
- Fully automatic: a vocal song → faces lip-sync, zero manual xLights steps.
- Deterministic and offline (no network, no model download in the default path).
- Match xLights' native phoneme-track XML so the result is editable like a hand-made one.
- Touch only the faces; the rest of the show and non-vocal songs are unchanged.

**Non-Goals:**
- Per-voice / duet separation across the three props (v1 drives all singing props from one vocal track;
  multi-voice is a follow-up).
- Image-based ("Matrix") face rendering — v1 targets the node "Bulb" def on these custom props.
- Replacing xLights' phoneme dictionary wholesale — we mirror its viseme mapping, not its full lexicon.

## Decisions

**1. G2P = CMUdict lookup + deterministic OOV fallback.**
`word → ARPABET` via the CMU Pronouncing Dictionary (`cmudict`, a small pure-data package behind an
optional `lyrics` extra). Out-of-vocabulary words (proper nouns, "ghostbusters") fall back to a tiny
deterministic letter-group heuristic (vowel runs → a vowel viseme, consonant groups → their viseme).
The dictionary is wrapped behind an injectable lookup so tests run without the extra installed.

*Alternative considered:* a neural g2p (`g2p_en`). Rejected for v1 — heavier deps and nondeterminism for
marginal accuracy on lyrics that CMUdict already covers well.

**2. ARPABET→viseme table mirrors xLights/Papagayo (Preston-Blair 10-shape set).**
A curated constant maps each of the ~39 ARPABET phones to one of `{AI,E,FV,L,MBP,O,U,WQ,etc,rest}`
(e.g. `AA,AH,AY→AI`; `EH,IH,IY,EY,Y→E`; `F,V→FV`; `M,B,P→MBP`; `AO,OW,OY,AW→O`; `UH,UW→U`; `W→WQ`;
`L→L`; everything else consonantal → `etc`; silence/unknown → `rest`). All values owned in code; the
table is a single tunable constant.

**3. Phoneme timing distribution = even split within each word, gaps are rest.**
Within a word's `[start,end]`, its visemes tile evenly (duration-weighted is a later refinement). The
inter-word/inter-line silence becomes a `rest` mark so the mouth closes between words. Phrase marks =
lyric lines; word marks = the word timings we already have.

**4. Multi-layer `TimingTrack`.**
Add `layers: list[list[TimingMark]] | None` to `TimingTrack`. When set, the patcher writes one
`<EffectLayer>` per layer (phrases, words, phonemes — the xLights order); when `None`, it writes the
existing single `marks` layer (every current track unchanged). The Faces effect references the track by
name and reads the phoneme layer.

**5. Asset-bound Faces placement, independent of the LLM and the preset library.**
A deterministic `pipeline/faces.py` pass (not the generator): for each `SINGING_FACE` prop in the
layout, emit one `Faces` `EffectInstruction` spanning the song's vocal span, with the settings above and
`FaceDefinition` resolved to the prop's node def. `effect_emitter` gets an **asset-bound branch**: for
`effect_type == "Faces"` it assembles the settings string from `extra_settings` and calls
`client.add_effect` directly (the `xl_add_effect_raw` path), skipping `place_preset`/the library. The
effect is tagged so the layer-budget clamp and wash-occlusion guard leave it alone.

*Alternative considered:* let the generator LLM emit Faces. Rejected — it's a deterministic, data-driven
placement (one per face prop, fixed settings); no judgment needed, and asset-bound effects don't fit the
look-id/library contract the generator uses.

**6. Vocal gating is native.** `SuppressWhenNotSinging=1` + the `rest` phonemes mean the face is quiet
during instrumentals without us computing a vocal-energy gate. (The vocals-stem energy gate stays a
possible later refinement if the native suppression proves too coarse.)

## Risks / Trade-offs

- [CMUdict extra not installed] → fall back to the heuristic g2p; lip-sync is approximate but present.
  Log which path ran. Hermetic tests cover both.
- [Faces `FaceDefinition` name mismatch] → resolve it from the prop's `faceInfo` (read rgbeffects.xml via
  the existing layout-semantics parser); if no node def is found, skip that prop with a warning rather
  than placing a broken effect.
- [Asset-bound effect bypasses validation] → place defensively (catch placement errors like the rest of
  the emitter) and never let a Faces failure abort the run.
- [Even-split timing drifts on long words] → acceptable for v1; duration-weighted distribution is a
  contained follow-up.
- [Three props lip-sync in unison] → intended for v1; per-voice tracks are a follow-up.

## Open Questions

- Mouth color/palette: the node "Bulb" def carries per-mouth `-Color`, so the Faces effect may need only
  a neutral palette — confirm against a live render and default to the face def's colors.
- Whether to span one Faces effect across the whole song vs. per-vocal-section; v1 spans the full song
  and relies on `SuppressWhenNotSinging`. Revisit if rendering cost or seams warrant per-section effects.

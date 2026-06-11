# xLights Effects Catalog: Curated Reference for Effect Placement

> **Living document.** Volume 3 in the series, alongside the *Music-to-Effect Reference* and the *Layering & Rendering Guide*. This is a curated catalog of xLights built-in effects with a consistent schema per effect: what it is, what it's musically for, how it renders, and where it belongs. It is written to serve as **baseline placement instructions** — including for an automated/model-driven sequencer choosing effects — so entries favor explicit rules over prose.
>
> **Version:** 0.1 — June 2026
> **Conventions:** Prop archetypes reference Volume 1 §3 (Hero, Rhythm, Canvas, Frame, Accent, Character, Atmosphere). Render style guidance references Volume 2 §6. Energy = 1 (ambient) to 5 (drop-level).

---

## Table of Contents

1. [Entry Schema](#1-entry-schema)
2. [Quick Reference Table](#2-quick-reference-table)
3. [Foundation Effects](#3-foundation-effects)
4. [Movement & Chase Effects](#4-movement--chase-effects)
5. [Radial & Geometric Effects](#5-radial--geometric-effects)
6. [Texture & Organic Effects](#6-texture--organic-effects)
7. [Accent & Impact Effects](#7-accent--impact-effects)
8. [Media & Content Effects](#8-media--content-effects)
9. [Music-Reactive Effects](#9-music-reactive-effects)
10. [Specialty & Utility Effects](#10-specialty--utility-effects)
11. [Placement Decision Rules](#11-placement-decision-rules)
12. [Sources](#12-sources)
13. [Changelog](#13-changelog)

---

## 1. Entry Schema

Every detailed entry uses these fields:

- **What it is:** one-line render description.
- **Musical use:** what song moments it serves (mapped to Volume 1 taxonomy).
- **Render behavior:** how it draws into the buffer; group-canvas vs per-model character; directionality; cost.
- **Best on:** prop archetypes and specific props, ranked.
- **Avoid on:** where it fails and why.
- **Energy:** 1–5 typical intensity band.
- **Key parameters:** the 2–4 settings that matter most (assume value-curve drivable unless noted).
- **Pairings:** layer combos that work (Volume 2 §9 recipes referenced where applicable).

The full built-in effect roster as of current releases: Off, On, Bars, Butterfly, Candle, Circles, Color Wash, Curtain, DMX, Duplicate, Faces, Fan, Fill, Fire, Fireworks, Galaxy, Garlands, Glediator, Guitar, Kaleidoscope, Life, Lightning, Lines, Liquid, Marquee, Meteors, Morph, Moving Head, Music, Piano, Pictures, Pinwheel, Plasma, Ripple, Servo, Shader, Shape, Shimmer, Shockwave, Single Strand, Sketch, Snowflakes, Snow Storm, Spirals, Spirograph, State, Strobe, Tendrils, Text, Tree, Twinkle, Video, VU Meter, Warp, Wave.

---

## 2. Quick Reference Table

| Effect | Category | Energy | Primary props | One-line use |
|---|---|---|---|---|
| On | Foundation | 1–5 | All | Beat pulses, hits, beds |
| Color Wash | Foundation | 1–3 | Frame, whole-display | Ambient bed, palette statements |
| Off | Foundation | — | All | Guaranteed darkness, masks, resets |
| Fill | Foundation | 2–3 | Linear props | Progressive fill to a build |
| Single Strand | Movement | 2–4 | Arches, outlines, canes | The canonical chase |
| Bars | Movement | 2–4 | Matrix, tree, arches | Rhythmic stripes, VU looks |
| Curtain | Movement | 2–3 | Matrix, tree | Reveals, section opens |
| Wave | Movement | 2–3 | Matrix, outlines | Flowing melodic motion |
| Marquee | Movement | 2–3 | Outlines, frames | Classic theater chase bed |
| Meteors | Movement | 2–4 | Tree, icicles, matrix | Falling/streaking texture |
| Morph | Movement | 2–4 | Tree, arches, matrix | Directed sweeps with head/tail |
| Garlands | Movement | 2 | Tree, matrix | Gentle wrapping motion |
| Pinwheel | Radial | 2–5 | Tree, spinners, matrix | Rotation; spinner literal match |
| Fan | Radial | 2–4 | Tree, spinners, matrix | Unfolding radial sweeps |
| Galaxy | Radial | 2–4 | Tree, matrix | Elegant spiral arms |
| Shockwave | Radial | 3–5 | Tree, matrix, whole-display | Impacts, builds, drops |
| Spirals | Radial | 2–5 | Mega tree | The mega tree workhorse |
| Circles | Geometric | 2–3 | Matrix, tree | Bouncing orb playfulness |
| Spirograph | Geometric | 2–3 | Matrix, tree | Hypnotic curve patterns |
| Kaleidoscope | Geometric | 3–4 | Matrix, high-density tree | Symmetric showpieces |
| Butterfly | Texture | 2–3 | Any density prop | Colorful generative filler |
| Plasma | Texture | 1–3 | Matrix, tree, floods | Organic ambient texture |
| Fire | Texture | 2–4 | Tree base, matrix, tombstones | Flames; rock energy, Halloween |
| Liquid | Texture | 2–3 | Matrix, tree | Fluid simulation looks |
| Life | Texture | 1–2 | Matrix | Generative ambient |
| Snowflakes | Texture | 1–2 | Whole-display, matrix | Literal snow, quiet beauty |
| Snow Storm | Texture | 2–3 | Matrix, tree | Driven snow, intensity-rampable |
| Candle | Texture | 1 | Windows, lanterns, canes | Warm flicker, no palette |
| Twinkle | Accent | 1–3 | All | Sparkle layer, quiet moments |
| Shimmer | Accent | 2–4 | All | Rapid alternation, tension |
| Strobe | Accent | 4–5 | Accent props, dedicated strobes | Hits and drops only |
| Lightning | Accent | 3–5 | Matrix, floods, tree | Storm stingers, rock accents |
| Fireworks | Accent | 3–5 | Tree, matrix | Celebration bursts, finales |
| Text | Media | n/a | Matrix | Lyrics, messages |
| Pictures | Media | n/a | High-density canvas | Static/animated imagery |
| Video | Media | n/a | High-density canvas | Video clips; complex imagery |
| Shader | Media | 1–5 | Matrix, tree (group canvas) | GLSL looks beyond stock |
| Sketch | Media | 2–3 | Matrix | Hand-drawn line animation |
| Glediator | Media | varies | Matrix | Imported pattern playback |
| Faces | Character | n/a | Singing faces | Vocal lip-sync |
| VU Meter | Music-reactive | 2–5 | Tree, matrix, bars | Audio-driven meters/waveforms |
| Music | Music-reactive | 2–4 | Tree, matrix | Note-reactive motion |
| Piano | Music-reactive | 2–3 | Matrix | Keyboard visualization |
| Guitar | Music-reactive | 2–4 | Matrix, tree | String/fret visualization |
| Tendrils | Specialty | 2–3 | Matrix, tree | Organic reaching lines |
| Ripple | Specialty | 2–3 | Matrix, tree | Expanding outline shapes |
| Shape | Specialty | 1–4 | Matrix, tree | Geometric primitives, mask source |
| Lines | Specialty | 2–3 | Matrix | Bouncing vector lines |
| Tree | Specialty | 2 | Mega tree | Legacy tree-specific patterns |
| Warp | Utility | n/a | Group canvas only | Distort lower layers |
| Duplicate | Utility | n/a | Any | Mirror another layer's effect |
| State | Utility | n/a | State-defined models | Custom on/off states |
| DMX / Moving Head / Servo | Utility | n/a | DMX fixtures | Channel-level fixture control |

---

## 3. Foundation Effects

### On
- **What it is:** Sets the buffer to a color at an intensity, with start/end intensity ramps.
- **Musical use:** The most musical effect in the toolbox. Beat pulses (short cells on kicks), stingers (1–2 frames at 100%), beds (low intensity sustained), swells (start 0 → end 100 on a held note).
- **Render behavior:** Uniform fill; trivially cheap; identical at group or model level.
- **Best on:** Everything. Rhythm props for pulses, Accent props for hits, Frame for beds.
- **Avoid on:** Nothing, but a constant 100% On is the "lights stuck on" look — always shape intensity.
- **Energy:** 1–5 depending entirely on intensity/duration shaping.
- **Key parameters:** Start/End intensity, Shimmer checkbox, Transparency.
- **Pairings:** The Subtractive brightness-envelope recipe (Vol 2 §9.3); base layer under Twinkle.

### Color Wash
- **What it is:** Fills the model with color, cycling through the palette with optional horizontal/vertical fade and per-count repeats; smooth or hard color transitions.
- **Musical use:** Ambient beds under verses; palette statements at section boundaries; slow builds via count/cycle speed.
- **Render behavior:** Whole-buffer fill; fade options give it gentle directionality; cheap.
- **Best on:** Frame/outline, whole-display groups, floods, matrix as backdrop.
- **Avoid on:** Nothing inherently; on hero props during features it reads as wasted real estate.
- **Energy:** 1–3.
- **Key parameters:** Count (repeats), Horizontal/Vertical fade, Shimmer, Circular Palette (smooth wrap).
- **Pairings:** Bed of the standard Bed+Feature+Sparkle stack; mask-source white→black for envelopes.

### Off
- **What it is:** Explicit darkness — actively writes black rather than leaving the row empty.
- **Musical use:** Dramatic pauses; the pre-drop blackout; silencing a prop regardless of what lower rows are doing.
- **Render behavior:** Critical distinction: *no effect* lets earlier rows show through when Allow Blending Between Models is on; *Off* guarantees black. Also resets Persistent-layer trails.
- **Best on:** All — it's an instrument, not an absence (Vol 2 §11.5).
- **Energy:** —
- **Pairings:** 1–4 frame Off before a drop flash; Off cells to clear Persistent meteors.

### Fill
- **What it is:** Progressively fills the model from an edge, like a level gauge rising.
- **Musical use:** Builds (fill rises over 4–8 bars into the chorus); held-note swells; "charging up" moments.
- **Render behavior:** Directional fill across the buffer; position value-curvable for precise musical timing.
- **Best on:** Mega tree (bottom-up fill is a natural build), vertical props, arches, outlines.
- **Avoid on:** Props with chaotic node order where the fill direction reads as noise.
- **Energy:** 2–3, peaking when full.
- **Key parameters:** Position (curve this to the build), Direction, Band size.
- **Pairings:** Fill on tree + accelerating Spirals layered above = textbook build.

---

## 4. Movement & Chase Effects

### Single Strand
- **What it is:** A moving head/chase along the strand order of the model, with skips, multiple chases, and bounce options.
- **Musical use:** The beat-carrier. Arch-to-arch leaps on kicks; roofline chases on grooves; candy-cane runs on subdivisions.
- **Render behavior:** Follows node order, so it respects the actual geometry of linear props — the reason it beats buffer-based effects on arches and outlines. Per-model on a group = each prop chases; group Default = chase travels across the whole set.
- **Best on:** Arches (canonical), outlines, candy canes, icicle drips, mini-tree sets.
- **Avoid on:** Dense 2D canvases (reads as a single wandering pixel line).
- **Energy:** 2–4, scaling with speed and chase count.
- **Key parameters:** Chase type, Number of chases, Speed (curve to tempo), Group size.
- **Pairings:** Odd/even arch alternation via two layers or two submodel targets.

### Bars
- **What it is:** Straight-edged multi-color bars moving across the model — up/down/left/right, with highlight/3D options.
- **Musical use:** Rhythmic stripes on the beat; VU-style energy on choruses; snap (high speed) for EDM, flow (low speed) for pop.
- **Render behavior:** Buffer-based stripes; direction maps cleanly to melodic contour (rising melody = bars moving up). Behaves predictably at both group and per-model styles.
- **Best on:** Matrix, mega tree, arches (horizontal motion), outline segments.
- **Avoid on:** Tiny/low-count props where bars alias into flicker.
- **Energy:** 2–4.
- **Key parameters:** Palette rep, Direction, Speed, Highlight/3D.
- **Pairings:** Under a "1 is Mask" Text layer for striped lettering.

### Curtain
- **What it is:** Colors sweep open or closed across the model like theater curtains, from edges or center.
- **Musical use:** Section reveals — verse→chorus opens; outro closes. The visual language of "something is starting."
- **Best on:** Matrix, mega tree, garage-door/wall canvases, whole-house group for big opens.
- **Avoid on:** Sparse linear props.
- **Energy:** 2–3.
- **Key parameters:** Edge (left/center/right), Effect (open/close), Swag.
- **Pairings:** Curtain open → feature effect beneath it on a lower layer (curtain as in-transition alternative).

### Wave
- **What it is:** Sine/triangle/square waveforms traveling across the model; multiple superimposable waves.
- **Musical use:** Flowing melodic lines, ballads, water/wind imagery; tempo-locked undulation.
- **Best on:** Matrix, long outlines, fence lines, mega tree.
- **Avoid on:** 3D cube-type models in groups (known phase/tilt weirdness at group level — sequence per-model there).
- **Energy:** 2–3.
- **Key parameters:** Wave type, Height, Speed, Thickness.

### Marquee
- **What it is:** Classic theater-marquee chasing border pattern with band controls.
- **Musical use:** Nostalgic/swing/showtune beds; steady-state motion that doesn't demand attention.
- **Best on:** Outlines, window frames, signs, matrix borders.
- **Avoid on:** Hero props during features — it's a bed, not a statement.
- **Energy:** 2–3.
- **Key parameters:** Band size, Skip size, Speed, Stagger.

### Meteors
- **What it is:** Streaks of color with tails raining across the model in a chosen direction.
- **Musical use:** Falling = quiet beauty or melancholy; dense+fast = energy texture on builds; sparse 16th-note glitter.
- **Render behavior:** Direction-aware; density and speed both curve well; with Persistent layer setting, leaves accumulating trails.
- **Best on:** Mega tree (downward/implode), icicles (downward only), matrix, whole-display for meteor-shower moments.
- **Avoid on:** Arches (vertical streaks across a horizontal line read poorly).
- **Energy:** 2–4.
- **Key parameters:** Direction (incl. implode/explode), Count, Trail length, Speed.
- **Pairings:** Implode meteors accelerating = build; explode on the drop.

### Morph (effect)
- **What it is:** A moving band with head, body, and tail traveling across the model between configurable start/end positions. (Distinct from the Morph *blend mode*, Vol 2 §4.)
- **Musical use:** Directed gestures: a sweep that lands exactly on a downbeat; crossing morphs on cymbal swells; per-quadrant morphs answering vocal phrases.
- **Render behavior:** Start/end corner-to-corner control makes it the most *aimable* movement effect; multiple morphs via layers + sub-buffers interleave (Vol 2 §9.6). Community consensus: looks best on mega trees, arches, and matrices.
- **Best on:** Mega tree, matrix, arches.
- **Energy:** 2–4.
- **Key parameters:** Start/End position blocks, Head/Tail length, Repeat, Stagger.

### Garlands
- **What it is:** Rings/strands of color that wrap and settle around the model, like draping garlands.
- **Musical use:** Gentle verses, traditional carols, wrapping motion on 3/4 waltz feels.
- **Best on:** Mega tree (natural fit), matrix.
- **Energy:** 2.
- **Key parameters:** Type, Spacing, Cycles.

---

## 5. Radial & Geometric Effects

### Pinwheel
- **What it is:** Rotating arms around a configurable center point; 3D shading options.
- **Musical use:** Sustained rotation = chorus motion bed; speed ramps = builds; on spinner props it is the literal mechanical match.
- **Render behavior:** Center is positionable (corner pinwheels on a matrix read as quarter-fans). Group canvas = one big wheel across the display; Per Model = every spinner spins itself. Both are valid, different statements (Vol 2 §6).
- **Best on:** Spinners (literal), mega tree, matrix, snowflakes.
- **Avoid on:** Linear props.
- **Energy:** 2–5 with speed.
- **Key parameters:** Arms, Speed (curve it), Twist, Center X/Y, 3D style.

### Fan
- **What it is:** Radial blades unfolding/rotating outward from a center with revolution controls.
- **Musical use:** Unfolding gestures on swells; reveal motion at chorus entry; elegant on orchestral material.
- **Render behavior:** Now defaults to Scale-to-Buffer (verify on imports — older sequences may size differently).
- **Best on:** Mega tree, matrix, spinners.
- **Energy:** 2–4.
- **Key parameters:** Center, Num blades, Revolutions, Duration ramp.

### Galaxy
- **What it is:** Spiraling arm of color expanding from a center point, like a rotating galaxy.
- **Musical use:** Elegant sustained features; bridge material; "wonder" moments. The classier cousin of Pinwheel.
- **Render behavior:** Scale-to-Buffer default; expensive on large canvases.
- **Best on:** Mega tree, high-density matrix.
- **Energy:** 2–4.
- **Key parameters:** Center, Start/End radius & width, Revolutions, Duration.

### Shockwave
- **What it is:** A circular ring expanding from small to large (or contracting), from a positionable center.
- **Musical use:** The impact effect: drum hits, drops, downbeat punctuation, accelerating series on builds. Contracting = inhale-before-the-drop.
- **Render behavior:** Scale-to-Buffer default. On a whole-display group canvas, one shockwave radiating across the entire yard is a signature drop move; per-model it's a multi-point pop.
- **Best on:** Mega tree, matrix, whole-display groups; snowflakes/stars per-model for popcorn hits.
- **Energy:** 3–5.
- **Key parameters:** Center, Start/End radius, Start/End width, Acceleration.
- **Pairings:** Blackout → white Shockwave at 1–2 frame attack = the drop formula (Vol 1 §4.3).

### Spirals
- **What it is:** Helical bands wrapping the model, with rotation, thickness, and 3D/grow options.
- **Musical use:** The mega tree workhorse: steady rotation for choruses, speed-curve acceleration for builds, opposing-direction pairs for showpieces.
- **Render behavior:** Designed around tree geometry; on flat matrices reads as diagonal bands (still useful).
- **Best on:** Mega tree (definitive), pixel poles, matrix.
- **Energy:** 2–5 with speed.
- **Key parameters:** Palette rep, Count, Rotation, Thickness, Direction, 3D.
- **Pairings:** Counter-rotation recipe (Vol 2 §9.7); Spirals + Fill for builds.

### Circles / Spirograph / Kaleidoscope
- **Circles:** solid orbs moving pseudo-randomly with bounce/collide options — playful, children's songs, bouncing on staccato notes. Matrix/tree. Energy 2–3.
- **Spirograph:** mathematical curve traces — hypnotic bridges, instrumental interludes. Matrix. Energy 2–3.
- **Kaleidoscope:** mirrored symmetric patterns from a source slice — showpiece choruses on high-density canvases; mesmerizing but busy, use as the feature, never under one. Matrix/HD tree. Energy 3–4.

---

## 6. Texture & Organic Effects

### Butterfly
- **What it is:** Generative rainbow/palette swirl patterns; several algorithm styles.
- **Musical use:** Reliable colorful filler texture for verses and beds; low-speed = ambient, high-speed = energetic.
- **Best on:** Almost anything — one of the few textures that survives low-density props.
- **Energy:** 2–3.
- **Key parameters:** Style, Chunks, Skip, Speed.

### Plasma
- **What it is:** Smooth organic blob-gradient motion, lava-lamp-like.
- **Musical use:** Ambient beds, dreamy bridges, pad-heavy material.
- **Best on:** Matrix, tree, floods (as slow color movement).
- **Avoid on:** Arches/outlines — texture turns to flicker on lines (Vol 1 §5).
- **Energy:** 1–3.
- **Key parameters:** Style, Line density, Speed.

### Fire
- **What it is:** Rising flame licks with height and hue controls.
- **Musical use:** Rock energy, guitar solos, Halloween, literal "fire" lyrics.
- **Render behavior:** Per-model on groups for individual flames per prop (group canvas makes one giant fireplace — sometimes right for a wall). Historically buggy on exotic render styles; verify on submodels.
- **Best on:** Mega tree base, matrix, tombstones, pillars.
- **Avoid on:** Arches, sparse outlines.
- **Energy:** 2–4.
- **Key parameters:** Height (curve on swells), Hue shift, Grow.

### Liquid
- **What it is:** Physics-based fluid simulation (top fill, rain, etc.).
- **Musical use:** Water imagery, pouring/filling builds.
- **Render behavior:** One of the most expensive effects; budget render time, avoid stacking on huge group canvases.
- **Best on:** Matrix, tree.
- **Energy:** 2–3.

### Life
- **What it is:** Conway's Game of Life cellular automation.
- **Musical use:** Generative ambient for long instrumental stretches; nerd delight.
- **Best on:** Matrix. **Energy:** 1–2.

### Snowflakes / Snow Storm
- **Snowflakes:** discrete falling flakes with accumulate option — quiet beauty, ballads, literal snow lyrics; whole-display at low density is the classic "pretty" bed. Energy 1–2.
- **Snow Storm:** wind-driven streaking snow — intensity curve makes it a weather-as-energy metaphor; verses calm → chorus blizzard. Energy 2–3.
- **Best on:** Matrix, tree, whole-display groups. Falling direction must be down — check buffer orientation on custom models.

### Candle
- **What it is:** Warm flicker simulation; ignores the palette (always orange-red).
- **Musical use:** Intimate moments, vigil imagery, window dressing during quiet sections.
- **Best on:** Window frames, lanterns, candy canes as candles, mini trees.
- **Energy:** 1.
- **Note for automated placement:** palette-locked — do not select when the moment's color script requires non-warm colors.

---

## 7. Accent & Impact Effects

### Twinkle
- **What it is:** Random nodes fading in/out; density and speed controls.
- **Musical use:** The universal sparkle layer; quiet intros; stardust on ballads; low-density texture over any bed.
- **Best on:** Everything; the most layerable effect in the catalog.
- **Energy:** 1–3 with density.
- **Key parameters:** Count (density), Steps (speed), Re-randomize.
- **Pairings:** Top layer of the standard stack, Max blend.

### Shimmer
- **What it is:** Rapid on/off alternation of the whole effect area.
- **Musical use:** Tension, rolls, snare rushes, held-note vibrato made visible.
- **Best on:** Any prop, short cells.
- **Avoid:** Long durations — fatiguing and reads as malfunction.
- **Energy:** 2–4.

### Strobe
- **What it is:** Random-position white-flash strobing.
- **Musical use:** Drops and hits only. The exclamation point of the toolbox.
- **Best on:** Dedicated strobe groups (bottom of master view, Vol 2 §7), star toppers, whole display ≤ 1 second.
- **Avoid:** Sustained use — photosensitivity risk and instant audience fatigue (Vol 1 §9).
- **Energy:** 4–5.

### Lightning
- **What it is:** Jagged bolt flashes with fork controls.
- **Musical use:** Storm stingers, Halloween, hard rock accents, "thunder" lyrics.
- **Best on:** Matrix, tall tree, floods (as sky flash).
- **Energy:** 3–5.

### Fireworks
- **What it is:** Exploding burst particles; optional music-triggered launches.
- **Musical use:** Finales, celebration choruses, NYE shows; the manual's own guidance points it at mega trees and matrices.
- **Best on:** Mega tree, matrix.
- **Avoid on:** Low-density props (particles vanish between nodes).
- **Energy:** 3–5.
- **Key parameters:** Explosions count, Velocity, Fade, music trigger.

---

## 8. Media & Content Effects

### Text
- **What it is:** Static or scrolling text rendering with font/size/movement controls.
- **Musical use:** Lyric display on phrase timing, messages between songs, countdowns.
- **Render behavior:** Needs pixel density — minimum ~10–12 px of height for legible characters; test at distance. Group canvases spanning mismatched props mangle glyphs; keep Text on a single matrix or a carefully built group.
- **Best on:** Matrix only (practically).
- **Pairings:** Mask source for shaped reveals (Vol 2 §9.2).

### Pictures
- **What it is:** Renders image files (PNG/GIF including animated) with movement options.
- **Musical use:** Iconography (bells, trees, pumpkins) on themed moments.
- **Render behavior:** Resolution-bound: detailed images turn to mush below ~50px canvases; vendor guidance favors Video for complex imagery and bold/simple art for Pictures. File-path dependent — imports break paths; fix via Bulk Edit Path (Vol 1 §5 Matrix).
- **Best on:** High-density matrix, HD trees.
- **Avoid on:** 16-strand trees, any low-density prop.

### Video
- **What it is:** Plays video clips into the buffer with scaling/cropping and chroma-key support.
- **Musical use:** Narrative content, complex animated imagery where Pictures falls apart.
- **Render behavior:** Chroma key lets footage composite over lower layers; heavy render cost; file-path dependent.
- **Best on:** High-density matrix/panels.

### Shader
- **What it is:** Runs GLSL fragment shaders (shadertoy-style) as effects.
- **Musical use:** Looks unreachable by stock effects — entire aesthetic worlds. Use as the feature, sparingly, or it stops being special.
- **Render behavior:** GPU-rendered (cache caveats, Vol 2 §10); group-canvas oriented; parameter exposure varies per shader.
- **Best on:** Matrix, HD tree at group level.
- **Note:** flagged as a future deep-dive in Vol 2 §11.8.

### Sketch / Glediator
- **Sketch:** draws user-defined line paths over time — hand-drawn reveal aesthetics, signatures, simple character animation. Matrix.
- **Glediator:** plays recorded Glediator/Jinx pattern files — imported pattern libraries for matrix texture variety.

### Faces
- **What it is:** Phoneme-driven mouth rendering for singing face models, with eye and outline options.
- **Musical use:** All vocal lip-sync; duets via separate timing tracks per voice (Vol 1 §4.4).
- **Best on:** Singing faces/trees/pumpkins with face definitions.
- **Placement rule:** when Faces is active, surrounding props dim to ≤30% so the singer owns focus.

---

## 9. Music-Reactive Effects

These render from the audio waveform — powerful but dangerous for automated placement because they *look* synced without being *musically intentional*. Rule: use them as texture under deliberate sequencing, not as a substitute for it.

### VU Meter
- **What it is:** A family of audio-reactive renders: level bars, waveforms, spectrograms, on/off triggers, timing-track-fired variants.
- **Musical use:** EDM energy walls; honest "the lights hear the music" moments; the timing-track-triggered types are the disciplined choice (fire on *your* marks, not raw level).
- **Best on:** Matrix, mega tree.
- **Energy:** 2–5.

### Music
- **What it is:** Note-onset reactive movement bars/shapes.
- **Musical use:** Instrumental passages where hand-sequencing every note is impractical.
- **Best on:** Matrix, tree.

### Piano / Guitar
- **What it is:** Keyboard / string-and-fret visualizations driven by timing or MIDI-ish note data.
- **Musical use:** Piano ballads and guitar features where the literal instrument visual lands (Vol 1 §4.2).
- **Best on:** Matrix.

---

## 10. Specialty & Utility Effects

### Tendrils
- **What it is:** Physics-simulated reaching/waving line strands.
- **Musical use:** Organic, eerie, or graceful movement; Halloween reaching-hands; wind imagery.
- **Best on:** Matrix, tree. **Energy:** 2–3.

### Ripple
- **What it is:** Expanding/contracting outlined shapes (circle, square, triangle, star...).
- **Musical use:** Soft radial punctuation when Shockwave is too aggressive; raindrop moments.
- **Best on:** Matrix, tree. **Energy:** 2–3.

### Shape
- **What it is:** Renders geometric primitives (and emojis) with growth/movement.
- **Musical use:** Accent pops on hits; mask source for shaped reveals; falling/rising icon moments.
- **Best on:** Matrix; per-model popcorn on snowflake/star sets.

### Lines
- **What it is:** Bouncing vector lines with trails.
- **Musical use:** Retro/synthwave texture. Matrix. **Energy:** 2–3.

### Tree
- **What it is:** Legacy effect drawing a tree pattern with moving lights — mostly superseded; occasionally right for retro looks on actual tree models.

### Warp
- **What it is:** Distortion treatments (water drops, ripples, swirls) applied to *lower layers*.
- **Placement rule:** top layer, Canvas mode, group-level render style only — does not work Per Model (Vol 2 §6).

### Duplicate
- **What it is:** Mirrors another model's/layer's effect onto this row.
- **Use:** keeping paired props in lockstep without copy-paste drift.

### State
- **What it is:** Drives user-defined state definitions (like Faces but generic) — custom multi-element props, signs, fixtures with named states.

### DMX / Moving Head / Servo
- **What it is:** Direct channel-value control for DMX fixtures, moving heads, servos.
- **Placement rules:** live on their own rows/groups; **Per Model Default render style is mandatory for DMX model groups** (Vol 2 §6); position/pan/tilt sequencing follows fixture conventions, not pixel thinking (Vol 2 §11.9).

---

## 11. Placement Decision Rules

Distilled rules for automated or assisted effect placement. Apply in order:

1. **Resolve the musical moment first** (Vol 1 §2 taxonomy). The moment determines the candidate effect set; the prop determines the winner.
2. **Respect prop archetype affinities** (§2 table). Never place texture effects (Plasma, Fire, Liquid) on linear props (arches, outlines). Never place media effects (Text, Pictures, Video) on canvases under ~50px of resolution.
3. **Match energy bands.** Effect energy (±1) must match the section's energy curve rating. A 5-energy Strobe in a 2-energy verse is a defect, not a choice.
4. **One feature per moment.** At most one high-attention effect (Kaleidoscope, Shader, Shockwave, Fireworks) active at a time across the display; everything else concurrent must be bed/accent tier.
5. **Choose render style deliberately** (Vol 2 §6): unified gesture → group canvas (Default/Per Preview); rhythmic multiplicity → Per Model. DMX groups → Per Model Default, always. Warp → group canvas, always.
6. **Shape every On/Color Wash.** No flat 100%-intensity fills; use start/end intensity ramps or value curves keyed to the music.
7. **Strobe/Shimmer budget:** Strobe ≤ ~1s per instance, on hits only; Shimmer ≤ 2 bars. Hard caps.
8. **Direction follows music:** rising melody/build → upward/inward/accelerating motion; falling/outro → downward/outward/decelerating.
9. **Palette compliance:** effects inherit the section's palette script (Vol 1 §7); flag palette-locked effects (Candle) when they conflict.
10. **Layer ceiling:** ≤ 4 layers per row; each layer must name its role (bed/feature/accent/mask). Unjustified layers are pruned.
11. **Music-reactive effects (VU/Music) are texture, not sequencing.** They may support, never replace, deliberate placement on structural moments.
12. **When in doubt, choose the boring effect shaped well** (On with good curves) over the exotic effect with defaults. Curves beat novelty.

---

## 12. Sources

- xLights Manual — Built-in Effects chapters (manual.xlights.org/xlights/effects): per-effect render descriptions (Shockwave, Fireworks, Circles, Candle, Morph, Bars, Fire, Meteors, et al.)
- xLights User Manual effects reference — Color Wash parameters, Curtain behavior, Morph prop guidance (mega trees, arches, matrices)
- xLights release notes — Scale-to-Buffer defaults for Galaxy/Shockwave/Fan; Fire render-style fixes
- Volume 1 (Music-to-Effect Reference) §§2–5, 7, 9 — taxonomy, prop notes, mistakes
- Volume 2 (Layering & Rendering Guide) §§4–9 — blend modes, render styles, recipes
- Community: AusChristmasLighting threads on group render behavior; vendor import guidance (RGB Sequences) on Pictures vs Video density limits

---

## 13. Changelog

| Version | Date | Changes |
|---|---|---|
| 0.1 | 2026-06-09 | Initial catalog: schema, quick-reference, ~50 effects across 8 categories, placement decision rules |

<!--
Editing conventions:
- New observations about an effect go in its entry, not a new section.
- Display-verified findings (tested on real lights) get a ✓; preview-only observations get (preview).
- Placement rules in §11 are normative for automated sequencing; changes there bump the minor version.
-->

# xLights Sequencing: Music-to-Effect Reference & Best Practices

> **Living document.** This is a working reference for mapping musical elements to effects and props in xLights. It synthesizes community practice from sequence vendors, YouTube educators, forum wisdom (AusChristmasLighting, xlightsseq.com, Falcon Christmas, r/ChristmasLights), and analysis of professional sequences. Add to it as you mine new sequences and discover what works on your display.
>
> **Version:** 0.1 — June 2026
> **Status:** Initial draft. Sections marked `TODO` need mining/observation work.

---

## Table of Contents

1. [Core Philosophy](#1-core-philosophy)
2. [Musical Element Taxonomy](#2-musical-element-taxonomy)
3. [Prop Taxonomy & Roles](#3-prop-taxonomy--roles)
4. [The Mapping Matrix: Music → Effect → Prop](#4-the-mapping-matrix-music--effect--prop)
5. [Effect Notes by Prop Type](#5-effect-notes-by-prop-type)
6. [Song Structure Playbook](#6-song-structure-playbook)
7. [Color Strategy](#7-color-strategy)
8. [Workflow & Process](#8-workflow--process)
9. [Common Mistakes](#9-common-mistakes)
10. [Mining Existing Sequences](#10-mining-existing-sequences)
11. [Sources & Community Resources](#11-sources--community-resources)
12. [Changelog](#12-changelog)

---

## 1. Core Philosophy

Principles that show up consistently across professional sequencers:

- **The lights are the instrument, not decoration.** Every effect should map to something audible. If you mute the audio and watch the lights, a viewer should still be able to "see" the rhythm and structure of the song.
- **Tell a story / serve the song.** Pro sequencers (e.g., xTreme Sequences) describe their goal as telling a story with lights that evokes emotion, not maximizing flash. The sequence should breathe with the song: quiet moments stay quiet.
- **Contrast creates impact.** A drop only hits hard if the build before it was restrained. Whole-display moments only matter if the whole display isn't always on. Darkness is a tool.
- **One focal point at a time.** The viewer's eye should know where to look. Lead with one prop or zone, support with others. Everything fighting for attention reads as noise.
- **Layer roles, like a band.** Think of props as instruments in an arrangement: something carries rhythm (arches, mini trees), something carries melody/lead (mega tree, matrix), something holds the bed/ambience (house outline, floods), and something handles accents (star, spinners, strobes).
- **Repetition with variation.** When the chorus repeats, reuse the visual motif so viewers recognize it, but escalate: more props, brighter, faster, extra layer. The last chorus should be the biggest.
- **Match energy, not just timing.** Effect speed, brightness, and density should track the song's intensity curve, not just its beat grid.

---

## 2. Musical Element Taxonomy

Break every song down into these elements before sequencing. Most pros build timing tracks for several of these (beats, bars, lyrics/phrases via the QM Vamp plugins or manual tapping).

### Rhythmic elements
| Element | What it is | Typical timing track |
|---|---|---|
| Downbeat / kick | Primary pulse, usually kick drum | Beats (quarter notes) |
| Bar / measure | Groups of 4 beats (usually) | Bars |
| Snare / backbeat | Beats 2 and 4 in most pop/rock | Beats (offset) |
| Hi-hat / subdivision | 8th/16th note motion | Half-beats (use sparingly) |
| Drum fill | Transitional flourish, usually end of a phrase | Manual marks |
| Bass line | Low-end melodic movement | Manual or bass-isolated track |

### Melodic & harmonic elements
| Element | What it is | Sequencing relevance |
|---|---|---|
| Lead melody / vocal line | The tune people hum | The thing your "lead" prop follows |
| Sustained notes / pads | Held chords, strings, synth pads | Slow effects, washes, fades |
| Arpeggios / runs | Fast note sequences up/down | Directional movement effects |
| Key change | Harmonic lift, often final chorus | Color palette change |
| Instrument solo | Guitar/sax/piano feature | Feature one prop, mute or dim others |

### Structural elements
| Element | What it is | Sequencing relevance |
|---|---|---|
| Intro | Establishes mood | Restraint; introduce props gradually |
| Verse | Story-telling, lower energy | Fewer props, simpler motion |
| Pre-chorus / build | Rising tension | Additive layering, accelerating effects |
| Chorus | The payoff, highest recurring energy | Full display, signature motif |
| Drop | Sudden rhythmic/bass impact after a build | The single biggest visual moment |
| Bridge | Contrast section | Change palette, change texture |
| Breakdown | Stripped-back section | Strip the display back too |
| Outro | Wind-down | Subtractive layering, fade to few/none |
| Stinger / hit | Single accent (orchestra hit, cymbal crash, gunshot SFX) | Flash/strobe accents |
| Silence / pause | Dead air for drama | Blackout — the most underused effect |

### Vocal elements
| Element | Sequencing relevance |
|---|---|
| Lyric phrases | Phrase timing track; drive text on matrix, motion direction changes |
| Individual words | Word timing track for singing faces / emphasis hits |
| Vocal harmony entry | Add a layer/prop when harmonies stack |
| Spoken word / narration | Singing faces or text on matrix; calm everything else |
| Call-and-response | Bounce between two zones of the display (left answers right) |

---

## 3. Prop Taxonomy & Roles

Group props by *visual role* rather than just shape. Most displays have these archetypes:

| Archetype | Typical props | Visual role |
|---|---|---|
| **Hero / lead** | Mega tree, large matrix, mega pixel pole | Carries melody, drops, and showcase moments. Highest pixel density, most viewer attention |
| **Rhythm section** | Leaping arches, mini trees, candy canes, tombstones (Halloween) | Beat-driven, repetitive, percussive motion |
| **Canvas** | Matrix, mega tree (as canvas), pixel panels | Images, video, text, lyrics, shaders |
| **Frame / bed** | House outline (eaves, windows, ridgelines), fence, pathway | Ambient wash, structure, ties display together |
| **Accent / punctuation** | Tree-topper star, spinners, snowflakes, stars, floods, strobes | Hits, sparkle, stingers, flash moments |
| **Character** | Singing faces/trees/pumpkins, chatty ghosts | Vocals, narration, comedy |
| **Atmosphere** | Floods, wash lights, lasers, projection | Color bed, lightning, mood |

**Rule of thumb:** at any moment in the song, each archetype should have a clear job or be intentionally dark. The hero takes the melody; rhythm props take the beat; the frame holds a low-intensity bed so the display never looks "broken"; accents fire only on accents.

---

## 4. The Mapping Matrix: Music → Effect → Prop

The core reference table. Effects named are stock xLights effects.

### 4.1 Beats & rhythm

| Musical moment | Good effects | Best props | Notes |
|---|---|---|---|
| Steady kick/quarter-note pulse | On (pulse), Bars (snap), Single Strand chase, Butterfly (low speed) | Mini trees, arches, outline segments | Alternate colors or zones per beat (A/B/A/B). Don't pulse *everything*; pick one rhythm layer |
| Snare on 2 & 4 | On/Flash at lower intensity, Shockwave (small), Twinkle burst | Accent props, star, snowflakes | Counterpoint to the kick layer — different prop, different color |
| Leaping/bouncing bass groove | Single Strand (chase), Wave, Curtain | **Arches** (the canonical prop), candy canes | The classic "leaping arches" look: chase travels arch-to-arch on the beat |
| 8th/16th hi-hat motion | Twinkle, Meteors (fast/sparse), Fire (low) | Frame/outline, dense props | Keep subtle; it's texture, not a feature |
| Drum fill | Shockwave, Fan, Spirals (accelerating), VU-style Bars | Mega tree, spinners | Use the fill to "wind up" into the next section |
| Drum solo / percussion break | Per-hit flashes mapped to individual drums (kick=base, snare=mid, cymbal=top) | Split a mega tree into vertical zones, or assign one prop per drum | Tom runs = chases across mini trees or down the tree |

### 4.2 Melody & sustained sounds

| Musical moment | Good effects | Best props | Notes |
|---|---|---|---|
| Lead vocal / melody line | Morph, Galaxy, Spirals, Pinwheel (smooth), Color Wash with movement | Mega tree, matrix | Movement direction can follow pitch contour: rising melody = upward motion |
| Sustained pad / strings | Color Wash, On with ramped value curves, slow Butterfly, Plasma | Frame, whole-house group, floods | Slow attack and release; value curves are your friend |
| Arpeggio / run | Single Strand, Meteors (directional), Garlands, Piano effect | Mega tree (vertical run), arches (horizontal run), icicles | Match direction to the run: ascending arpeggio climbs the tree |
| Piano ballad | Twinkle (gentle), Fade pulses per chord, Music/Piano effect | Whole display at low intensity | Less is more; let chords breathe with slow fades |
| Guitar solo | Lightning, Fire, Tendril, Sketch, fast Pinwheel | Hero prop solo feature | Dim everything else to ~20%; the solo prop is the soloist |
| Horn stabs / orchestra hits | Flash (On at 100% short), Shockwave, Strobe burst | Star, spinners, floods | 1–2 frame full-brightness hits; brutally short |
| Key change | Palette swap on existing effects | Everything | Same motion, new colors — viewers feel the lift without a layout change |

### 4.3 Song structure moments

| Musical moment | Good effects | Best props | Notes |
|---|---|---|---|
| Intro | Slow reveals: Color Wash fade-in, Single Strand drawing the outline, Twinkle emerging | Frame first, then props one at a time | Introduce the display like characters in a story |
| Verse | 2–3 active prop groups max; simple, lower-speed effects | Rhythm props + light frame bed | Save the hero prop, or keep it minimal, so the chorus pays off |
| Pre-chorus / build | Spirals (accelerating via value curve), Shockwave series, rising Bars, Meteors increasing density, snowstorm intensifying | Add props each bar; motion converges upward/inward | Classic build: every 2 bars add a layer and raise speed/brightness |
| **The drop** | Everything at once for 1 frame (white flash) → into full-display motion: Shockwave from center, Explode/Fireworks, fast Pinwheel, Strobes layer | **All props**, hero leading | The formula: brief blackout or held strobe at the build's peak → flash → full motion. The blackout *before* the drop is what sells it |
| Chorus | Signature motif: a specific effect+color combo reused every chorus | Full display | Escalate each repetition (chorus 1: 70% of props, chorus 2: 90%, final: 100% + accents) |
| Bridge | Texture change: switch from geometric to organic effects (Bars→Plasma, Pinwheel→Fire) | Different prop emphasis than chorus | Often the place for the matrix to do something narrative |
| Breakdown | Strip to one prop + bed; Twinkle, slow wash | Hero or character prop | Mirror the arrangement: if it's just vocal + piano, it's just face + one wash |
| Outro | Subtractive: remove layers each bar, final fade or snap to black | Reverse of intro | Snap-to-black on the final note is stronger than a long fade for energetic songs |
| Silence / pause | **Blackout (no effect)** | All | Total darkness for dramatic pauses. Resist the urge to fill it |

### 4.4 Vocals & lyrics

| Musical moment | Good effects | Best props | Notes |
|---|---|---|---|
| Sung lyrics | Faces effect (with phoneme timing track) | Singing faces/trees/pumpkins | Voice 1 / Voice 2 on separate timing tracks for duets |
| Lyric emphasis words ("fire", "shine", "snow") | Literal accents: Fire effect, Twinkle/Glediator sparkle, Snowflakes/falling snow | Whichever prop suits the word | "Mickey-mousing" key words lands well with viewers; don't do every word |
| Lyrics as text | Text effect, scrolling or per-phrase | Matrix | Keep on-screen long enough to read; high contrast against background |
| Call and response | Mirror effects left/right zones | Split display into stage-left/stage-right groups | Lead vocal = left, answer = right |
| Big held vocal note | Morph expanding, Shockwave slow, brightness swell via value curve | Hero prop | Hold and grow with the note, release when it ends |

### 4.5 Genre & texture cues

| Texture | Good effects | Notes |
|---|---|---|
| EDM / synth | Bars (VU style), Strobes, Shockwave, Pinwheel high speed, Glediator patterns | Hard snaps, geometric motion, saturated colors |
| Orchestral | Color Wash, Morph, Galaxy, slow Spirals | Smooth curves, long transitions, layered swells |
| Rock | Fire, Lightning, fast chases, Strobe accents | Aggressive motion, warm palette + white hits |
| Jazz / swing | Garlands, Pinwheel (moderate), alternating chases on the swing feel | Bounce the off-beat; playful color alternation |
| Ambient / cinematic | Plasma, Shader effects, slow Meteors, Twinkle | Texture over rhythm |
| Children's / whimsical | Butterfly, Candy-cane chases (Single Strand), Bounce-style motion | High saturation, simple shapes, readable motion |

---

## 5. Effect Notes by Prop Type

What works (and doesn't) on each prop, per community consensus.

### Mega tree
- The hero. Spirals, Pinwheel, Shockwave, Morph, Galaxy, Fan, and Fireworks all read beautifully due to the conical wrap.
- Pictures/video: only on high-density trees. On a 16-strand tree, detailed images render as mush — community guidance is to prefer bold/simple imagery or use the Video effect instead of Pictures when imagery is complex.
- Spirals with a value-curve on speed is the workhorse build effect.
- Split into submodels (vertical halves, rings) for drum-kit mapping and call-response.
- Tree + topper star: the star is the cymbal/accent — fire it on hits, not constantly.

### Matrix / pixel panels
- The storyteller: Text, Pictures, Video, Shaders, Sketch, Glediator.
- Carries lyric text, character animation, and "literal" content (album art motifs, falling snow scenes).
- During non-narrative moments, treat it as a giant texture surface (Plasma, Shader, Bars) so it doesn't go dead.
- Beware solid-red blocks after importing vendor sequences — usually a broken file path to picture/video assets; fix with Bulk Edit Path.

### Leaping arches
- The display's drummer. Single Strand chases on the beat are the canonical look (the "leap" travels arch to arch).
- Bars, Wave, Curtain, and Butterfly also work; keep motion horizontal/arc-aligned.
- Odd vs even arch alternation on kick/snare is an easy, effective pattern.
- Avoid busy texture effects (Plasma, Fire) — arches are low-resolution lines; motion reads, texture doesn't.

### House outline / frame
- The bed. Color Wash, Marquee, Single Strand chases around the roofline, Twinkle.
- Keep at 30–60% brightness during verses so it frames rather than competes.
- Outline chases that "draw" the house are a great intro move.
- Window/door submodels can pulse independently as rhythm cells.

### Mini trees / candy canes / tombstones
- Rhythm cells. On/off pulses, alternating colors, chases across the line of them.
- Treat the set as one model group for sweeps; individual models for drum mapping.
- Great for call-and-response with arches.

### Spinners / snowflakes / stars
- Accent props. Pinwheel and Fan effects are literal matches for spinners.
- Fire on hits, cymbal crashes, sparkle moments; keep them dark otherwise so the accent means something.
- Snowflakes + Twinkle during quiet bridges is a reliable "pretty" moment.

### Singing faces / characters
- Faces effect driven by phoneme timing tracks; keep eyes on Auto for natural blinking.
- Dim surrounding props during dialogue/vocals so the face is clearly "speaking."
- Comedy beats land when other props "react" (flash on a punchline).

### Floods / wash
- Atmosphere. Slow color washes under everything; lightning flashes (white strobe) for storms and stingers.
- Use to unify the palette: match flood color to the dominant prop color of the moment.

### Icicles
- Meteors/falling effects (downward), Single Strand drips, Twinkle.
- Direction matters: effects should fall, not rise.

> `TODO:` Add notes for your specific props as the display grows (e.g., HD props with submodel-level vendor effects — vendors like Gilbert Engineering and Boscoyo ship effects targeted at submodel groups, so import those mappings too).

---

## 6. Song Structure Playbook

A repeatable recipe for sequencing a typical pop/rock/Christmas song:

1. **Map the song first.** Before touching effects, create timing tracks: Bars, Beats (via QM Vamp plugins — install Audacity alongside xLights to get them), Lyrics (phrase + word), and a manual "Structure" track labeling intro/verse/chorus/build/drop/bridge/outro.
2. **Write the energy curve.** On paper or in the Structure track notes, rate each section 1–10 for energy. Your brightness, prop count, and effect speed should follow this curve.
3. **Assign prop roles for this song.** Who is the hero? What carries rhythm? Any solo features?
4. **Sequence the chorus first.** It's the signature. Build the motif, then copy it to every chorus and plan escalations.
5. **Sequence the drop/biggest moment second.** Work backwards: design the build to earn it.
6. **Fill verses with restraint.** Verses are where you save energy. 2–3 active groups.
7. **Do transitions last.** Shockwaves, wipes, and blackouts that glue sections together.
8. **Watch it with the audio muted.** Can you still see the song's structure? Then watch it with eyes squinted from "across the street" distance — does the focal point read?
9. **Cut 10%.** Almost every first draft is too busy.

---

## 7. Color Strategy

- **Palette per section, not per effect.** Pick 2–3 colors per song section; change palette at structural boundaries (verse→chorus, key change).
- **White is a spice.** Full-white flashes for hits and drops; constant white kills contrast and reads as "lights stuck on."
- **Warm vs cool for emotional contrast.** Verses cool/dim, choruses warm/bright (or invert for effect).
- **Mind the medium.** Deep blues and purples are dimmer to the eye on pixels; bump brightness or pair with white sparkle. Red+green adjacency reads as muddy at distance — separate spatially.
- **Consistency across the show.** A per-song identity palette helps each song feel distinct in a multi-song show.

---

## 8. Workflow & Process

Practices that keep sequencing sane, especially for a living, multi-year display:

- **Sequence on model groups, not individual models**, wherever possible. Group-level effects treat the group as one canvas and survive layout changes far better. Note the render difference: an effect on a group is rendered across the combined canvas, which often looks better (sweeps cross the whole display) — but some effects behave differently at group level, so preview both.
- **Enable/disable "Allow Blending Between Models" deliberately** — it controls whether group effects merge with model-level effects or get overridden by render order.
- **Use Views** to keep the sequencer focused on the models that matter for the current song.
- **Save reusable looks as Effect Presets** in your own preset group (not the default group). Build a personal library of "build," "drop," "verse bed," and "transition" presets — this compounds across songs.
- **Value curves on speed/brightness** are the difference between amateur and pro-looking builds. Linear-on effects feel mechanical; ramped ones feel musical.
- **Layering:** use multiple effect layers per model (e.g., Color Wash bed + Twinkle sparkle on top). Most pro sequences are 2–4 layers deep on hero props.
- **Naming and structure discipline:** consistent model/group/submodel names make vendor-sequence imports and year-over-year reuse dramatically easier; save your XMAP mapping files when importing so future imports from the same vendor are one click.
- **Backups:** F10 backs up the XMLs in the show directory; do it before major changes.

---

## 9. Common Mistakes

- **Everything on, all the time.** No contrast → no impact. The most common beginner tell.
- **Effect soup.** Five unrelated effects running simultaneously with no focal point.
- **Ignoring the lyrics.** Sequences that track the beat but never acknowledge what the song is *about* feel mechanical.
- **No blackouts.** Darkness on a pause or before a drop is the cheapest "wow" available.
- **Same speed everywhere.** Effect speed locked at default regardless of song tempo or section energy.
- **Texture effects on line props.** Plasma/Fire on arches or outlines reads as flicker, not texture.
- **Detailed images on low-density props.** A 16-strand mega tree cannot render a photo.
- **Over-strobing.** Strobes are a hit accent, not a bed. Also a real photosensitivity concern — use sparingly and consider warning signage.
- **Sequencing to your monitor, not your yard.** Preview brightness ≠ real-world brightness; verify on actual lights, at distance, early.

---

## 10. Mining Existing Sequences

How to systematically extract knowledge from professional sequences (the best textbook available):

1. **Acquire references.** Free sequences: the xLights community Google Drive, xlightsseq.com forum shares, RGB Sequences' free offerings (their *Blinding Lights* is famously popular), vendor freebies. Paid: xTreme Sequences, Magical Light Shows, Visionary Light Shows, Pixel Pro Displays, etc. — one or two well-made purchases are worth studying frame by frame.
2. **Import into a study folder.** Use a separate show directory for imported sequences so asset paths resolve; open against the vendor's layout when provided.
3. **Reverse-engineer the structure.** For each section of the song, note: which model groups are active, what effect each carries, layer count, palette, and what changes at the boundary. The sequencer grid *is* the documentation.
4. **Toggle strands/nodes** on hero props to see how effects render at node level and which submodels the vendor targeted (HD prop vendors often ship effects at submodel-group level).
5. **Extract presets.** When you find a look you love, recreate it and save it as a named Effect Preset (e.g., `DROP-shockwave-white-flash`, `BUILD-spiral-accel`).
6. **Log findings here.** Add rows to the matrix in §4 with a source note.

### Mining log
| Date | Sequence / Source | Finding | Added to section |
|---|---|---|---|
| `TODO` | | | |

---

## 11. Sources & Community Resources

**Documentation**
- xLights Manual — manual.xlights.org (effects reference, singing faces, import workflow)
- xLights FAQ — xlights.org/faq (timing tracks, presets, Vamp plugins)

**Educators / channels to mine**
- xTreme Sequences (Ron Howard) — tutorials archive at xtremesequences.com/tutorials; deep effect-specific videos (spinners, tunnels, ripple, curves, mega tree creativity)
- Canispater Christmas — YouTube; song-sequencing process walkthroughs
- xLights Academy — structured courses and prop-specific effect tutorials (e.g., "effexLights 101 – Arches")
- Keith Westley's xLights webinar/video series (one of the lead xLights developers)

**Communities**
- AusChristmasLighting forum (and their excellent "101" manual)
- xlightsseq.com — sequence sharing forum
- Falcon Christmas forums
- r/ChristmasLights, r/xlights
- xLights Zoom Room / Facebook groups (official xLights support group)

**Sequence vendors (for mining)**
- xTreme Sequences, RGB Sequences, Magical Light Shows, Visionary Light Shows, Pixel Pro Displays, Showstopper Sequences

---

## 12. Changelog

| Version | Date | Changes |
|---|---|---|
| 0.1 | 2026-06-09 | Initial draft: taxonomy, mapping matrix, prop notes, workflow, mining process |

<!--
Editing conventions for this document:
- New mappings go in §4 as table rows; include a source note in the mining log (§10).
- Prop-specific discoveries go in §5 under the prop heading.
- Mark unverified/community-hearsay items with (unverified).
- Bump version on any substantive addition.
-->

# Highway to Hell: Video Script and Synced Timeline

A music-video script that shares its clock with the xLights show. Every shot starts on a bar line or an **Impact**. Both come from the audio analysis (`xlights-core`), so the video cuts and the lighting hits land on the same frame.

| | |
|---|---|
| Duration | 208.111 s (03:28:03 at 30 fps) |
| Tempo | 117.45 BPM, 4/4, about 2.07 s per bar, 103 bars |
| Key (detector) | D major overall estimate. Treat the key and chord labels as approximate on this distorted-guitar mix |
| Stems | drums, bass, other, vocals, guitar, piano (htdemucs_6s) |
| Shots | 33, contiguous from 0 ms to the end |

## Sync contract

1. **One master clock: the audio file.** Time 0 is the first sample of `Highway to Hell.mp3`. Render the video against this exact file. Do not trim or pad the start.
2. **Timecodes** are `MM:SS:FF` at **30 fps**. Raw milliseconds are in `cue_sheet.csv` / `video_timeline.json`. xLights works in 50 ms frames (20 fps); use the millisecond values when matching the two.
3. **In xLights**, import `Highway to Hell.xtiming` (Timing track → Import). You get the Sections, Bars, Beats, Onsets (drums/guitar/vocals), Chords and Impacts tracks. Effects placed on these marks are frame-aligned with the cuts below.
4. **In the video editor**, import `cue_sheet.csv` as markers (Resolve and Premiere both accept CSV marker lists via a small script; `frame` is the column to use), or place markers by hand from the Impacts table.
5. **Playback together** (video on a projector or TV next to the display): put the MP4 and the `.fseq` in the same FPP playlist entry, so both start from the same audio clock.

## Hard sync points (Impacts)

The 16 biggest energy surges, snapped to the bar line. A cut and a full-yard light hit should both land exactly on these.

| # | Timecode | ms | Frame | What happens |
|---|---|---|---|---|
| 1 | 00:05:21 | 5700 | 171 | Loading up (Intro - Riff (guitar alone)) |
| 2 | 00:11:24 | 11800 | 354 | Launch (Intro - Band In) |
| 3 | 00:22:09 | 22300 | 669 | Driver POV (Verse 1) |
| 4 | 00:30:20 | 30650 | 920 | Signs (Verse 1) |
| 5 | 00:38:28 | 38950 | 1168 | The gang (Verse 1) |
| 6 | 00:47:09 | 47300 | 1419 | Build (Verse 1) |
| 7 | 01:05:22 | 65750 | 1972 | Whip (Chorus 1) |
| 8 | 01:12:03 | 72100 | 2163 | Roadhouse (Verse 2) |
| 9 | 01:32:28 | 92950 | 2788 | Something behind (Verse 2) |
| 10 | 01:43:09 | 103300 | 3099 | The reveal (Chorus 2) |
| 11 | 01:55:21 | 115700 | 3471 | Real footage (Chorus 2) |
| 12 | 02:12:08 | 132250 | 3968 | Sparks (Guitar Solo) |
| 13 | 02:41:02 | 161050 | 4832 | Peak (Chorus 3 (double)) |
| 14 | 02:59:18 | 179600 | 5388 | Stopped (Breakdown (drums drop out)) |
| 15 | 03:08:00 | 188000 | 5640 | The beacon (Breakdown (drums drop out)) |
| 16 | 03:26:21 | 206700 | 6201 | Final crash (Finale) |

## Section map and palette

Each section's video color grade matches its lighting palette, so footage of the real display cuts in seamlessly.

| Section | In | Out | Bars | Video grade / light palette |
|---|---|---|---|---|
| Intro - Riff (guitar alone) | 00:00:00 | 00:09:21 | 4 | black · ember red #8B0000 · headlight white |
| Intro - Band In | 00:09:21 | 00:18:03 | 4 | red #D10000 · white · asphalt grey |
| Verse 1 | 00:18:03 | 00:49:10 | 15 | amber #FF8C00 · dusty orange · sun gold |
| Chorus 1 | 00:49:10 | 01:07:26 | 9 | hell red #FF1A00 · neon white · flame orange |
| Verse 2 | 01:07:26 | 01:43:09 | 17 | deep purple #3A0CA3 · midnight blue · red snare accents |
| Chorus 2 | 01:43:09 | 02:01:27 | 9 | hell red · white · flame orange (brighter than Chorus 1) |
| Guitar Solo | 02:01:27 | 02:28:22 | 13 | electric blue #00B4FF · lightning white · black |
| Chorus 3 (double) | 02:28:22 | 02:59:18 | 15 | red · white · gold (peak) |
| Breakdown (drums drop out) | 02:59:18 | 03:18:00 | 10 | black · single red glow |
| Finale | 03:18:00 | 03:28:03 | 7 | red · white → black |

> Section boundaries are hand-labeled. They are inferred from the stem energy (vocal entry, drum drop-out, guitar-dominant solo), because no Genius token was available for lyric alignment. They are snapped to the tracker's downbeats. Check them by ear before you lock the edit, and adjust `sections.json` and re-export if one is a bar off.

## Shot list

**Video** is the description, and it also works as the generation prompt for an AI video tool. Add a style suffix to every prompt, such as *"cinematic, anamorphic, 35mm film grain, high contrast, 1970s hard-rock album-art aesthetic"*. **Lights** is the matching xLights cue, using the orchestrator's `SEM_` groups. The same text lives in `shots.json`, keyed by start bar. A re-export recomputes the times in `video_timeline.json`; the times on this page are from the original analysis.


### Intro - Riff (guitar alone) (00:00:00 – 00:09:21)

**1. Cold open**  `00:00:00 → 00:01:12`  (1.4 s · intro · frames 0–42)

- **Video:** Pure black. Faint heat shimmer; a single red ember glows in the center of frame. Sound of the first riff chord.
- **Lights:** All dark. SEM_FOCAL at 10% deep red, slow breathe.
- **Sync:** Picture starts at 0 ms with the audio's first sample.

**2. Headlights**  `00:01:12 → 00:05:21`  (4.3 s · Bar 1–2 · frames 42–171)

- **Video:** Low angle on a black muscle car's grille at dusk on a desert highway. Each guitar chord stab snaps the headlights on, then they fade.
- **Lights:** White stab on SEM_OUTLINE + SEM_FOCAL on every 'Onsets (guitar)' mark, 300 ms decay.
- **Sync:** Cut lands on Bar 1. Flash frames = guitar onsets.

**3. Loading up**  `00:05:21 → 00:09:21`  (4.0 s · Bar 3–4 · frames 171–291)

- **Video:** Close-ups cut on the chord stabs: boots on asphalt, a guitar case slammed into the trunk, a hand turning the ignition key.
- **Lights:** SEM_ARCHES_LTR sweep left→right on each chord; red/white.
- **Sync:** Impact 1 (00:05:21) = trunk slam.


### Intro - Band In (00:09:21 – 00:18:03)

**4. Launch**  `00:09:21 → 00:13:27`  (4.2 s · Bar 5–6 · frames 291–417)

- **Video:** The drums kick in: rear wheels spin, smoke, the car launches out of frame; tail-light streaks.
- **Lights:** Drums enter → full-yard red chase. SEM_MINITREES flash on snare (beats 2 & 4).
- **Sync:** Cut exactly on the drum entry (Bar 5). Impact 2 (00:11:24) = launch.

**5. The road**  `00:13:27 → 00:18:03`  (4.2 s · Bar 7–8 · frames 417–543)

- **Video:** Drone top-down over an empty two-lane desert highway at golden hour, center dashes passing in time with the beat.
- **Lights:** SEM_PATH / SEM_ARCHES_LTR run white 'road dashes' one step per beat.
- **Sync:** One center dash per beat.


### Verse 1 (00:18:03 – 00:49:10)

**6. Driver POV**  `00:18:03 → 00:26:14`  (8.35 s · Bar 9–12 · frames 543–794)

- **Video:** Driver's-eye view over a dusty dashboard, warm amber sun low on the horizon, a dice charm swinging from the mirror.
- **Lights:** Verse bed: warm amber/orange, low intensity. Vocal onsets twinkle on the matrix/SEM_FOCAL.
- **Sync:** Verse starts on Bar 9. Impact 3 (00:22:09) = the mirror charm swings hard.

**7. Signs**  `00:26:14 → 00:34:24`  (8.35 s · Bar 13–16 · frames 794–1044)

- **Video:** Roadside signs whip past one per bar: a bent speed-limit sign, a 'NO EXIT' sign, a sun-bleached billboard. Each passes on the downbeat.
- **Lights:** Each downbeat pops a different group (SIDE_LEFT → SIDE_CENTER → SIDE_RIGHT → HOUSE), amber with a red edge.
- **Sync:** Impact 4 (00:30:20) = biggest sign whoosh.

**8. The gang**  `00:34:24 → 00:43:03`  (8.3 s · Bar 17–20 · frames 1044–1293)

- **Video:** Silhouettes of friends in the back of a pickup alongside, fists up, hair blowing, dust kicking up behind.
- **Lights:** Ping-pong SEM_SIDE_LEFT / SEM_SIDE_RIGHT on beats 2 & 4.
- **Sync:** Impact 5 (00:38:28) = pickup pulls alongside.

**9. Build**  `00:43:03 → 00:49:10`  (6.25 s · Bar 21–23 · frames 1293–1480)

- **Video:** Speedometer needle climbing, heat haze rising, the sky shifting from amber to deep red.
- **Lights:** Brightness ramp 30%→80% across 3 bars; color shifts amber → red.
- **Sync:** Impact 6 (00:47:09) = needle slam; hard cut at Bar 24.


### Chorus 1 (00:49:10 – 01:07:26)

**10. The sign**  `00:49:10 → 00:57:16`  (8.2 s · Bar 24–27 · frames 1480–1726)

- **Video:** A giant neon highway sign reading HIGHWAY TO HELL ignites letter by letter as the car blasts past camera.
- **Lights:** CHORUS LOOK: full yard red + white on every beat; megatree spiral; matrix title card 'HIGHWAY TO HELL'.
- **Sync:** Ignition = Bar 24 downbeat (chorus 1 start).

**11. Fire lane**  `00:57:16 → 01:05:22`  (8.2 s · Bar 28–31 · frames 1726–1972)

- **Video:** Lines of flame erupt along both road shoulders, chasing the car down the highway.
- **Lights:** Fire effect on SEM_ARCHES + SEM_OUTLINE; drum onsets strobe SEM_FLOODS.
- **Sync:** Flame bursts on snare hits.

**12. Whip**  `01:05:22 → 01:07:26`  (2.1 s · Bar 32–32 · frames 1972–2036)

- **Video:** Whip-pan off the car to black.
- **Lights:** White full-yard hit then drop to 20%.
- **Sync:** Impact 7 (01:05:22) = whip.


### Verse 2 (01:07:26 – 01:43:09)

**13. Roadhouse**  `01:07:26 → 01:16:08`  (8.4 s · Bar 33–36 · frames 2036–2288)

- **Video:** Night. A neon-lit roadhouse and gas station; bikes parked out front; purple and blue haze.
- **Lights:** Verse 2 bed: deep purple/blue; red only on snare hits.
- **Sync:** Impact 8 (01:12:03) = door kicks open.

**14. Inside**  `01:16:08 → 01:24:18`  (8.35 s · Bar 37–40 · frames 2288–2538)

- **Video:** Jukebox, pinball lights, dice tumbling across felt, a deck of cards fanned out. Each object lands on a downbeat.
- **Lights:** Matrix/SEM_FOCAL pinball sparkles on 'Onsets (guitar)'; bed stays cool.
- **Sync:** Object hits on downbeats.

**15. Night drive**  `01:24:18 → 01:32:28`  (8.35 s · Bar 41–44 · frames 2538–2788)

- **Video:** Back on the road under a full moon; telephone poles strobing past one per beat.
- **Lights:** Chase across the sweep order, one step per beat (poles = beats).
- **Sync:** Pole passes = beat marks.

**16. Something behind**  `01:32:28 → 01:43:09`  (10.35 s · Bar 45–49 · frames 2788–3099)

- **Video:** The rearview mirror fills with a red glow; the car accelerates; the horizon ahead starts to burn red.
- **Lights:** Red rises band by band: SEM_BAND_GROUND → MID → ROOF; final bar snare-roll ramp to white.
- **Sync:** Impact 9 (01:32:28) = mirror glance. Hard cut at Bar 50.


### Chorus 2 (01:43:09 – 02:01:27)

**17. The reveal**  `01:43:09 → 01:51:16`  (8.25 s · Bar 50–53 · frames 3099–3346)

- **Video:** The car crests a hill: below, the actual house light display blazes in the dark. This is the biggest drum surge in the song.
- **Lights:** CHORUS LOOK at 100%: full yard, megatree, matrix. Shockwave from SEM_FOCAL outward on the downbeat.
- **Sync:** Impact 10 (01:43:09) = crest cut, frame-exact.

**18. Real footage**  `01:51:16 → 01:59:24`  (8.25 s · Bar 54–57 · frames 3346–3594)

- **Video:** Intercut the real filmed light show (wide shot of the house), cut on every downbeat with flame-road shots.
- **Lights:** Same chorus look as Chorus 1, brighter.
- **Sync:** Impact 11 (01:55:21) = cut to the house.

**19. Into the pixel**  `01:59:24 → 02:01:27`  (2.1 s · Bar 58–58 · frames 3594–3657)

- **Video:** Camera pushes into a single glowing bulb until it fills the frame.
- **Lights:** Everything fades except SEM_FOCAL.
- **Sync:** Transition to the solo on Bar 59.


### Guitar Solo (02:01:27 – 02:28:22)

**20. Lightning**  `02:01:27 → 02:10:06`  (8.3 s · Bar 59–62 · frames 3657–3906)

- **Video:** Lightning storm over the desert; a guitarist silhouetted on the car roof; every bolt lands on a guitar note.
- **Lights:** Guitar-solo lightning (trigger cookbook): white strikes on 'Onsets (guitar)'; everything else dark blue.
- **Sync:** Bolt frames = guitar onsets.

**21. Sparks**  `02:10:06 → 02:18:14`  (8.25 s · Bar 63–66 · frames 3906–4154)

- **Video:** Sparks spray off a guitar neck and off wheels grinding the road; fast macro cuts.
- **Lights:** High-rate electric blue/white shimmer on SEM_ALL.
- **Sync:** Impact 12 (02:12:08) = biggest spark shower.

**22. Fretboard**  `02:18:14 → 02:26:21`  (8.25 s · Bar 67–70 · frames 4154–4401)

- **Video:** Macro shots: fingers on strings, intercut with macro shots of the real pixels; speed ramps.
- **Lights:** Fast sweeps changing direction every bar.
- **Sync:** Change direction on each downbeat.

**23. Rise**  `02:26:21 → 02:28:22`  (2.05 s · Bar 71–71 · frames 4401–4462)

- **Video:** Camera rises straight up off the road into the night sky.
- **Lights:** Vertical wipe upward on all props.
- **Sync:** Lands on Bar 72 = Chorus 3.


### Chorus 3 (double) (02:28:22 – 02:59:18)

**24. Flame tunnel**  `02:28:22 → 02:36:28`  (8.2 s · Bar 72–75 · frames 4462–4708)

- **Video:** The car drives into a tunnel of fire.
- **Lights:** Full chorus look; fire on the arches.
- **Sync:** Chorus 3 starts on Bar 72.

**25. Peak**  `02:36:28 → 02:45:04`  (8.2 s · Bar 76–79 · frames 4708–4954)

- **Video:** Neighbours and crowd outside the real house, hands up, phones out; real footage of the display at full blast. The song's energy peak.
- **Lights:** PEAK: everything at max brightness; megatree + matrix + all groups.
- **Sync:** Impact 13 (02:41:02) = crowd's big moment.

**26. Ping-pong**  `02:45:04 → 02:53:12`  (8.25 s · Bar 80–83 · frames 4954–5202)

- **Video:** Alternate drone shots of the house and the highway, one cut per downbeat.
- **Lights:** SIDE_LEFT/SIDE_RIGHT ping-pong per bar.
- **Sync:** Cut every downbeat.

**27. Cut out**  `02:53:12 → 02:59:18`  (6.2 s · Bar 84–86 · frames 5202–5388)

- **Video:** Speed blur builds to white, then hard cut to black.
- **Lights:** Crescendo into the drop.
- **Sync:** Builds toward Impact 14; the last frame is white.


### Breakdown (drums drop out) (02:59:18 – 03:18:00)

**28. Stopped**  `02:59:18 → 03:08:00`  (8.4 s · Bar 87–90 · frames 5388–5640)

- **Video:** The car sits stopped on the empty road, engine ticking, a single red glow on the horizon. Each guitar chord produces one flash of red light.
- **Lights:** Everything cuts to near-black on the first frame. Then sparse: only SEM_FOCAL + one prop per guitar chord, long decays; matrix pulses on vocal onsets.
- **Sync:** Impact 14 (02:59:18) = drums drop out. The blackout must be frame-exact.

**29. The beacon**  `03:08:00 → 03:16:09`  (8.3 s · Bar 91–95 · frames 5640–5889)

- **Video:** The house display glows on the horizon; each chord stab makes the flash bigger.
- **Lights:** Each chord adds one more group (it builds up).
- **Sync:** Impact 15 (03:08:00) = the driver looks up. This bar grid is approximate (no drums, so the tempo drifts); sync the flashes to 'Onsets (guitar)'.

**30. Fill**  `03:16:09 → 03:18:00`  (1.7 s · Bar 96–96 · frames 5889–5940)

- **Video:** The car fires up again, drum fill.
- **Lights:** Snare-roll strobe ramp.
- **Sync:** The drums come back in.


### Finale (03:18:00 – 03:28:03)

**31. Flythrough**  `03:18:00 → 03:25:09`  (7.3 s · Bar 97–101 · frames 5940–6159)

- **Video:** The camera flies down the highway, through the megatree, into the house display; the full band hits.
- **Lights:** Everything red/white at full yard; final chorus look.
- **Sync:** The finale starts on Bar 97.

**32. Held chord**  `03:25:09 → 03:26:21`  (1.4 s · Bar 102–102 · frames 6159–6201)

- **Video:** The final chord holds; the flames rise.
- **Lights:** Hold at 100%, slow color swirl.
- **Sync:** —

**33. Final crash**  `03:26:21 → 03:28:03`  (1.41 s · Bar 103–end · frames 6201–6243)

- **Video:** A hard white flash, then black. The title HIGHWAY TO HELL burns in fire on black and then fades.
- **Lights:** White flash on the final crash, matrix title, then blackout.
- **Sync:** Impact 16 (03:26:21) = final crash. Fade to black by the end of the audio.

## Files

| File | Use |
|---|---|
| `sections.json` | Hand-labeled section starts (by bar) and palettes. Edit it, then re-run the exporter |
| `shots.json` | The shot list above (video prompt, lights cue, sync note), keyed by start bar |
| `Highway to Hell.xtiming` | Generated. Import into xLights. Contains all reference timing tracks |
| `cue_sheet.csv` / `cue_sheet.json` | Generated. Every Section, Bar, Chord, Impact and Shot with ms, timecode and frame |
| `video_timeline.json` | Generated. This shot list resolved to real times, for a renderer or editor script |

The generated files need the audio (`mp3/` is not checked in). Regenerate them with:

```bash
python scripts/export_show_timeline.py --song "mp3/Highway to Hell.mp3" --out shows/highway-to-hell \
    --sections shows/highway-to-hell/sections.json --fps 30 --name "Highway to Hell" \
    --onset-stems drums,guitar,vocals
```

The exporter detects the Impacts itself (the biggest bar-to-bar jumps in whole-mix energy, at least two bars apart). If a re-analysis moves one, the shot list's Sync notes still name it by number, so check the Impacts table in `video_timeline.json` against the notes above.

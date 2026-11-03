---
name: xlo-video
description: How to write video_story.json — the short film for the show's centerpiece video matrix: the story rules (tell the song's story, never the lights; a through-line and recurring motifs; exactly one beat per brief section; no time fields; holiday-agnostic; song identity for instrumentals), the exact file shape (logline, motifs, beats[] with the Beat fields), the filmed-vs-procedural vocabulary, and the hand-off to `xlo video-plan`. Load for /xlo:video.
---

# xlo-video

You write the story; code does the timing and the media plan. The story rules below are the
whole contract (they absorbed the former Videographer prompt); the file shape is `VideoStory` in
`packages/xlights-orchestrator/src/xlights_orchestrator/video_script.py`.

## Inputs you read

- `creative_brief.json` — only `sections[].label` / `intensity` (the energy, 0–1), the show
  `palette` and `concept`. **Do not** read or echo the lighting fields (`look`, `motion`,
  `effect_types`, `target_groups`, `scene_*`…): the film must not replicate the display.
- `analysis_digest.md` — the timed lyric lines per section, repeated lines (hooks), mood, key.
- The conversation: what the user said the song is about, and the show's concept.

Number the sections exactly as the brief lists them (index 0..n-1). The climax is the section with
the highest intensity.

## Story rules

- **Tell this song's story, not the lights.** Build it from the lyrics, narrative, themes and
  featured lines. A viewer who knows the song should recognize it. Not generic holiday imagery, not
  the same cozy objects every time.
- **Never depict the light display.** No houses covered in lights, no arches, props or hardware.
- **Through-line + motifs.** One logline (1–2 sentences). A short list of recurring visual
  elements (an object, a place, a phenomenon) that carry the story beat to beat — commit to them
  up front and reuse them, or it is a slideshow.
- **Exactly one beat per brief section**, by `section_index`. Say what we see, what happens over
  the beat's length, the camera, the light and colour, which motifs appear, how it follows the
  previous beat, and which lyric / theme it draws on.
- **Follow the energy.** Quiet sections are still and intimate; builds gather; the climax is the
  film's biggest moment; the ending resolves. Fit the length: a 10 s section is a moment, a 50 s
  section can develop.
- **No time fields, no timestamps.** Refer to sections only by index; `xlo video-plan` times them.
- **No on-screen words.** No titles, captions, lyrics, signs, logos or text; lyrics show elsewhere.
- **Holiday-agnostic.** Halloween, Christmas, Thanksgiving, anything — the song decides.
- **Instrumentals: the song's identity is the story material.** A film/show/game theme carries its
  source's world, mood, settings and iconic objects; a classical piece carries its own history and
  imagery. Build the film from that world in pictures and atmosphere — never logos, titles or text.
- Use the show palette as the film's colour world, varying it with the story.

## Two media — write every beat so it survives both

Only a few sections can be **filmed** (a video model; a handful of 8 s clips a day). Everything
else is **procedural** (rendered by code, any length, free). `xlo video-plan` decides which is
which from energy, hooks and the clip budget — after you write. So:

- Write beats that work procedurally, and give **every** beat a `procedural_stand_in` (one sentence
  in the procedural vocabulary). A filmed beat without one fails the plan; an extra one on a
  procedural beat costs nothing.
- Procedural vocabulary (what code can draw): falling snow and leaves, embers and sparks, candle /
  porch / window light, the moon and stars, fog, aurora, water and reflections, fire, geometric and
  abstract motifs, flat silhouettes of *objects and landscapes* (a tree line, a rooftop, a gate, a
  record, a carved pumpkin), slow drift, parallax or push-in over a still scene, colour washes
  that breathe with the music.
- Procedural **cannot draw**: people, faces, eyes, hands, bodies, animals, crowds, vehicles, any
  object that must be recognized while it moves, text. The planner lints `imagery` + `action` of
  procedural beats and every `procedural_stand_in` for person/animal words
  (`video_script.py:PERSON_TERMS`) and refuses the story on a hit (exit 1, naming the section
  and the word).
- A character may appear only in filmed beats; carry them through procedural beats with a
  **proxy object** motif — something they own, wear, hold or leave behind, specific to this song.
  Make the proxy one of your motifs.
- Repeated sections with the same label (a returning chorus) share one filmed shot: give them the
  same imagery and action; camera and light may vary.

## The third look: a real photo under a procedural overlay (optional)

A procedural beat can be upgraded to a **photo plate**: a real photograph with a slow camera move
over it and procedural layers composited on top (fog, embers, falling leaves, candle flicker, a
breathing colour wash). On a low-res matrix it often reads better than pure procedural, and it
costs no Veo clips. Use it **sometimes, not everywhere**: where a real place or object carries the
beat (a fogged porch, an open doorway, a moonlit street). Keep pure procedural where the motion
is the point (rhythmic flicker, stillness, abstract colour).

- Add `photo` to the beat: `subject` (what the photo shows, which is also the search), `move`,
  `overlay` (procedural vocabulary), and once found, `file` (a local path), `source_url`,
  `license` and `credit`. A plate with only `subject` + `overlay` is fine at story time; the
  storyboard marks it *still to find*.
- **Licences: free to reuse only.** CC0, public domain, CC BY / CC BY-SA (with `credit`),
  Unsplash, Pexels, Pixabay, NASA, or the user's own photo (`video_script.py:PHOTO_LICENSES`).
  Never film stills, screenshots, or images of unknown licence, even when the song is a film theme.
  The planner refuses a sourced plate with no licence or with a licence not on the list.
- A plate shows **places and objects**: the planner lints `subject` + `overlay` with the same
  people/animal word list as procedural beats.
- On a procedural section the shot becomes `photo`. On a filmed section the plate is the stand-in's
  backdrop (used until the Veo clip exists); the shot stays filmed.
- When you source images, put each in the show folder (xLights and the renderer must be able to
  read it) and record the source and licence in the beat. Search Wikimedia Commons, Unsplash or
  Pexels, and check the licence on the image's own page.

```json
"photo": {
  "subject": "a wooden front porch at night, the door ajar with warm light spilling out",
  "move": "slow push-in toward the door",
  "overlay": "leaves blowing across the boards, a porch light flickering, orange wash breathing",
  "file": "",
  "source_url": "",
  "license": "",
  "credit": ""
}
```

## The file: `video_story.json`

Write it into the song's cache dir next to `creative_brief.json`.

```json
{
  "logline": "A lighthouse keeper's last winter night: the lamp he tends is the only warmth on the coast until the storm clears and the first ship answers.",
  "motifs": ["the lighthouse lamp", "the keeper's brass key", "sea fog", "a single red ship light"],
  "beats": [
    {
      "section_index": 0,
      "title": "Fog on the point",
      "imagery": "A black headland under sea fog; one dim lamp window far out on the rocks.",
      "action": "The fog drifts; the lamp window brightens by a breath as the first notes sound.",
      "camera": "Wide, static, slight push-in.",
      "lighting": "Deep blue night, a single warm amber point.",
      "motifs": ["the lighthouse lamp", "sea fog"],
      "continuity": "",
      "draws_on": "the quiet intro; 'I kept a light for you'",
      "procedural_stand_in": "Drifting fog over a black coastline silhouette, one warm amber window glowing."
    }
  ]
}
```

Beat fields (all strings unless noted): `section_index` (int), `title`, `imagery`, `action`,
`camera`, `lighting`, `motifs` (list of strings, drawn from the top-level `motifs`), `continuity`,
`draws_on`, `procedural_stand_in`, and optional `photo` (above). The first beat for an index wins; out-of-range indexes are
dropped; a section with no beat inherits the previous one and is flagged — give every section its
own beat.

## Then run the planner

`xlo video-plan --song <mp3> --matrix-size <WxH>` (`--cache <dir>` is the alternative to `--song`;
the matrix resolution is never guessed). It validates the story (one beat per section, no time
fields, the media lint), resolves beats to the brief's section cuts, splits long filmed shots on
downbeats, assigns the sung lyrics to each shot, computes the media plan (filmed vs procedural,
asset groups, clips, cost, what is renderable today) and per-shot prompts, and writes
`video_script.json` + `video_script.md` (and `media_plan.json`). Read the `.md` and present the
storyboard: per shot its time range, medium, what we see; the filmed/procedural split and clip
count from the summary. A story that fails validation writes no script — fix the named beat and
re-run.

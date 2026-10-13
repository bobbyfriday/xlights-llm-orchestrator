---
name: xlo-video
description: How to write video_story.json — the short film for the show's centerpiece video matrix: the story rules (tell the song's story, never the lights; a through-line and recurring motifs; exactly one beat per brief section; no time fields; holiday-agnostic; song identity for instrumentals), the exact file shape (logline, motifs, beats[] with the Beat fields), the filmed-vs-procedural vocabulary, and the hand-off to `xlo video-plan`. Load for /xlo:video.
---

# xlo-video

You write the story; code does the timing and the media plan. Story rules below come from the
former Videographer prompt (`packages/xlights-orchestrator/src/xlights_orchestrator/agents/prompts/videographer.md`,
kept as the reference until PR 3 deletes it); the file shape is `VideographerOut` in
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
  (`agents/videographer.py:PERSON_TERMS`) and refuses the story on a hit.
- A character may appear only in filmed beats; carry them through procedural beats with a
  **proxy object** motif — something they own, wear, hold or leave behind, specific to this song.
  Make the proxy one of your motifs.
- Repeated sections with the same label (a returning chorus) share one filmed shot: give them the
  same imagery and action; camera and light may vary.

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
`draws_on`, `procedural_stand_in`. The first beat for an index wins; out-of-range indexes are
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

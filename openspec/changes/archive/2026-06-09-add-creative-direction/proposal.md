## Why

Stage 1 gave us a real understanding of the song. Stage 2 turns that into a real *plan*. Today the Director collapses all that richness into a thin `SectionPlan` — `{target_groups, effect_family, intensity, rationale}` — with no palette, no per-group identity, no motion, and no grounding discipline (it previously invented a trap-rap story for instrumental TSO). The Generator then places effects from that thin plan, so the show has no through-line: it's "some effect on some groups," not a designed light show.

This change makes the Director produce a **deliberate creative brief** — a show concept, a color palette and how it maps to the song, a role/motif for each prop group, deep per-section direction, key-moment choreography, and transitions — all **grounded in the Stage-1 song description** (its normalized dynamics, 6-stem instrumentation, accents, harmony, journey, featured lyric moments). You review and approve it at a **hard checkpoint** before a single effect is placed, and the **Generator follows it**. That's the north star that structures the show.

## What Changes

- **Show concept — in plain, non-musical terms** — a 1–2 paragraph **audience-experience vision**: what the show *looks like* and *conveys to a viewer*, in everyday language ("opens like a single candle in the dark, grows into a warm glow, then erupts into a full-yard celebration"), NOT music theory. This leads the brief so a human can confirm the vibe at a glance.
- **Per-section "look" (plain language)** — alongside the grounded direction, each section gets a one-line, non-musical description of what a viewer sees there.
- **Color palette + palette language** — a core palette (named colors) and how color maps to sections/moods (cool for quiet, warm/hot for climaxes), with rationale tied to dynamics + harmony/key.
- **Per-group roles/motifs** — each prop group gets a role + signature style + color, kept coherent across the show ("arches = the beat; megatree = the hero/melody; matrices = imagery").
- **Deep per-section direction** — intensity · palette · featured groups · effect families/types + motion · build/transition · a rationale that **cites the analysis** (stems → which groups react to which instrument; accents → punctuation; dynamics → intensity/palette).
- **Key-moment choreography** — accents/climax + featured lyric moments → deliberate punctuation at their timestamps.
- **Transitions** — section-to-section flow, tied to harmonic-change cues.
- **Grounding discipline** — cite the song description; never invent narrative/genre not supported by it (instrumental → no fabricated story; the title is not evidence).
- **A human-readable `creative_brief.md`** + a **hard review checkpoint** (review/edit/approve before generation; `--auto` bypasses).
- **The Generator follows the brief** — its input carries the section palette, the section's group-motifs, the effect direction + motion, and the grounded rationale.

**Non-goals:** new effect types / preset-library work; the visual-critique + refine loop + revision log (already built — they *evaluate* the result); per-stem reactive channels in generation (future); auto-applying the brief.

## Capabilities

### Modified Capabilities
- `show-orchestration`: the Director produces a rich, grounded creative brief (concept, palette + palette language, per-group motifs, deep per-section direction, key-moment choreography, transitions) instead of a thin plan, gated by a hard human review checkpoint, and the Generator follows it — so the show is intentional rather than a scatter of effects.

## Impact

- **`xlights-orchestrator`**: `show_plan.py` (enriched `ShowPlan`/`SectionPlan` — additive/back-compat), `agents/director.py` (much deeper, grounded prompt), a `creative_brief.md` renderer + a design-stage hard checkpoint in `pipeline/run.py`, and `agents/generator.py::render_input` (consume the new direction). Design cache key bumped so old thin plans don't shadow.
- **Builds on** Stage 1's rich `SongDescription` (`music-interpretation`) + the 6-stem instrumentation (`audio-analysis`), and the checkpoint/markdown-render patterns. Feeds the existing generate → place → render → refine flow.

## Why

Christmas Canon's intro brief asked for falling snow, and the show targeted the dedicated snowflake props (SEM_SNOWFLAKES) — but live, the snowflakes don't read. Two causes confirmed from the rendered frames + emitted settings:

1. **Low contrast, not low brightness.** The flake props are lit by an On bed whose primary color is `#C0C0C0` (silver) over a navy (`#00008B`) house — silver-on-navy is nearly the same value/hue on LEDs, so the flakes vanish. The viewer's mental model is right: *white* snow on a *blue* house would pop. (A previous attempt that dimmed the bed was the wrong lever and was reverted/closed — on a dedicated prop group, that bed IS what lights the props.)
2. **The particle effect renders nothing here.** The "Snowflakes" effect is a falling-particle animation for a large matrix/whole-house canvas. On SEM_SNOWFLAKES it runs "Per Model Default" (each tiny flake-shaped prop gets its own buffer — nothing to fall through); on SEM_ALL it's only 5 flakes across the whole house. Frames 6s apart are identical — no visible motion.

The fix is to STEER the LLM (not hard-enforce — per the standing "don't guarantee the chosen effects land" principle): featured accent/sparkle prop groups should be the bright, high-contrast focal element in a light color over a different-hued bed, and a named particle effect needs a real canvas to read.

## What Changes

- **Director prompt (LLM):** add a "feature props pop" rule — when a section centers on a dedicated accent/sparkle prop group (SEM_SNOWFLAKES/SEM_SPINNERS), make those props the bright, high-contrast focal element in a light color over a different-hued background bed (e.g. white snow on a blue house), kept bright even in a calm section.
- **Generator prompt (LLM):** the same realization guidance, plus the caveat that named particle effects (Snowflakes/Snowstorm/Meteors) only read on a large canvas with a high Count — on small dedicated flake props, light the props directly with a bright On/Twinkle in the flake color; and set `palette_colors` EXPLICITLY on the feature instruction to pin its color.
- **Respect the LLM's explicit color (code):** `run.py` previously overwrote EVERY instruction's `palette_colors` with an index-rotated section palette — which is why the snow props rendered silver no matter what the LLM chose. It now fills `palette_colors` only when the LLM left it empty, so an explicitly-pinned color (white snow) survives.
- **Deterministic contrast floor (code):** steering alone proved unreliable — across regens the LLM produced silver On, ice-white Twinkle on a near-black plan, dropped snow for dark chases, and blue chases on the snow props. So a floor guarantees the outcome: when a dedicated sparkle/snow prop group (SEM_SNOWFLAKES/SEM_SPINNERS) is among a section's target groups, its base-lighting effects are recolored to the section's LIGHTEST palette color at a bright level — white snow that pops against the bed. Scoped to those accent prop groups only; the LLM still drives everything else.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `show-orchestration`: the creative direction SHALL steer featured accent/sparkle prop groups to read as a bright, high-contrast focal element over a different-hued bed, and steer away from particle effects that won't render on small dedicated props; an instruction's explicitly-chosen `palette_colors` SHALL be respected rather than overwritten by the section-palette rotation; and when a dedicated sparkle/snow prop group is a section feature, its base lighting SHALL deterministically take the section's lightest color at a bright level so it pops against the bed.

## Impact

- `agents/director.py` + `agents/generator.py` prompts (steering); `pipeline/beats.py` (`feature_prop_contrast` floor); `pipeline/run.py` (respect explicit `palette_colors`; apply the floor per section in generate + regen). Back-compat: instructions with no explicit `palette_colors` get the section family as before; the floor is a no-op for sections that don't feature an accent prop group.

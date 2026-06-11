## Why

⑧ gave the refine loop eyes — the visual critic *sees* problems the metrics can't (it caught our **chorus rendering completely dark**, despite effects being placed). But two things are missing. First, the critique is **not music-aware**: "dark" or "static" is not inherently wrong — a dark, quiet beat before a big drop is intentional and good; the same darkness mid-chorus is a defect. Whether a moment is good is a **judgment about the visuals *given what the music is doing there*** — and the critic can't make it without the musical context. Second, seeing isn't fixing: nothing reliably turns a *confirmed* visual defect into a scoped revision, and the Generator never learns what looked wrong. This change makes the critique **music-aware** and lets the **Judge decide** the fixes — closing a see → judge → fix → re-see loop that respects musical intent.

## What Changes

- **Music-aware visual critique.** The critic gets each section's **musical context** — energy/intensity, its role (quiet / build / drop / peak / transition), and neighboring sections — so it judges "is this darkness/staticness/energy appropriate *for this moment*?" rather than by brightness alone. A dark pre-transition lull reads as intentional; dark mid-peak reads as a defect.
- **Dynamics, variety & sync as critique dimensions.** The critic assesses whether the show is **dynamic and varied (not repetitive, not random)** and whether the **visual effects go with the music** (energy matches the section, motion lands on the structure). These are the things metrics can't see.
- **The Judge decides revisions (judgment, not rules).** The Judge — informed by the music-aware findings — converts genuine problems into scoped `RevisionBrief`s targeting the right `section_index`. We do **not** hardcode "dark → revise"; the Judge arbitrates.
- **The Generator gets the visual issue.** The originating finding's detail is threaded into the `RevisionBrief`, so a regenerated section addresses *what looked wrong* (e.g. "dark mid-chorus — brighter/fuller/more dynamic"), not a blind re-roll.
- **Narrow backstop (not a dark=bad rule).** Only when the *music-aware critic itself* confirms a section is a defect (`severity=error` **in musical context**) and the Judge fails to act does the loop ensure it is at least attempted/surfaced — bounded by `max_iterations` + the anti-oscillation ledger.
- **Re-critique after regen** (already in ⑧) closes the loop; **visual findings stay advisory to the objective gate** (taste ≠ objective regression).

**Non-goals:** deterministic "dark=revise" / "auto-light-all-groups" rules (the Judge decides, the Generator regenerates); visual findings driving the objective revert gate; video/temporal generation changes; new model types.

## Capabilities

### Modified Capabilities
- `visual-critique`: the visual critique becomes **music-aware** — it judges the rendered visuals against each section's musical context and assesses dynamics/variety/music-sync, so dark/static/energy are evaluated as appropriate-or-defective for the moment, not by brightness alone.
- `show-refinement`: the refine loop converts the (music-aware) visual critique into **Judge-decided** scoped revisions, feeds the visual issue to the Generator, and keeps a narrow backstop for critic-confirmed defects — closing the see → judge → fix → re-see loop, with visual findings advisory to the objective gate.

## Impact

- **`xlights-orchestrator`**: `agents/visual_critic.py` (music-aware `render_input` — per-section musical context + dynamics/variety/sync prompt), `agents/judge.py` (prompt elevates music-aware visual findings → revisions), the refine loop in `pipeline/run.py` + a small `refine.py` helper (thread the visual issue into the revision; narrow backstop for critic-confirmed errors).
- **Builds on** `visual-critique` (⑧) and `show-refinement` (⑦). Mostly making existing wiring *act* — plus the music-aware critique input.
- **No new deps**; live verification reuses the dark-chorus show from ⑧.

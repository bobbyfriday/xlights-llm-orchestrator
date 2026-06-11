## 1. Guide loader

- [x] 1.1 `agents/guide.py` — `sequencing_guide() -> str`: path = `XLO_SEQUENCING_GUIDE` env else default `xlights-sequencing-guide.md`; read best-effort (try/except → `""`); cache by resolved path; debug-log found/not-found
- [x] 1.2 `with_guide(prompt) -> str`: append a delimited "## SEQUENCING BEST-PRACTICES (apply unless the grounded song data says otherwise)" + guide when non-empty; else return prompt unchanged

## 2. Wire the 4 decision/critique agents

- [x] 2.1 Director (`director.py`), Generator (`generator.py`), Visual Critic (`visual_critic.py`), Judge (`judge.py`): `system_prompt=with_guide(_PROMPT)` (guide AFTER the role prompt)
- [x] 2.2 Leave the synthesizer + analyst factories unchanged (no guide)

## 3. Tests & verification

- [x] 3.1 `sequencing_guide()` reads a tmp file via `XLO_SEQUENCING_GUIDE` and returns its text; caches by path; an unset/missing path → `""` (no raise)
- [x] 3.2 `with_guide(p)`: guide set → result contains the marker + guide text and starts with `p`; guide empty → returns `p` unchanged
- [x] 3.3 With a guide configured, the Director/Generator/Visual-Critic/Judge composed system prompts contain the guide marker; the synthesizer/analyst prompts do NOT
- [x] 3.4 Existing agent/orchestrator tests still pass
- [ ] 3.5 Manual (not gated): run with the real guide present → debug log confirms it loaded; a re-gen qualitatively reflects the guidance

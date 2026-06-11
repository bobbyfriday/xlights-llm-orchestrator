## 1. Redesigner agent
- [x] 1.1 `agents/director.py`: `section_redesigner()` (output_type=SectionPlan, guides-injected) + `redesign_input(section, plan, findings)` (section JSON + violation text + "re-plan THIS section per the catalog; keep times/groups sane")
## 2. Loop escalation
- [x] 2.1 `_refine_loop(redesign=None)`: before regenerating a revision, if a rules finding for that section names an effect in `section.effect_types` OR the section was already regenerated last iteration → call redesign (default = redesigner agent; injectable), replace `st.show_plan.sections[i]`; once per section per run
## 3. Persist
- [x] 3.1 After refine, write the (possibly revised) show_plan back to creative_brief.json (+ re-render creative_brief.md)
## 4. Tests
- [x] 4.1 Fake redesign: design-implicated finding → redesign called once, section replaced, regen uses the new section; second trigger → no second redesign; clean section → never called
- [x] 4.2 Brief write-back contains the revised section; suite passes

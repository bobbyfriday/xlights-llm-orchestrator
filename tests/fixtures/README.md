# Recorded response fixtures

These JSON files mirror the xLights automation API response **envelopes**, derived from the
xLights source (`xLightsAutomations.cpp`) since a live instance was not reachable when this
slice was built.

They are accurate as to **shape** (keys, wrapping, status codes) but the **field contents**
are representative placeholders.

> ⚠️ Task 6.2 (live smoke test) must confirm these against a running xLights and replace the
> placeholder contents with a real capture. Field-set assumptions in `Model`/`Controller`
> are intentionally lenient (`extra="allow"`) so real responses won't break parsing.

Envelope rules (Accept: application/json):
- text result → `{"<key>": "<string>"}`  (e.g. `version`, `folder`)
- structured result → `{"<key>": <json>}` (e.g. `models`, `model`, `controllers`)
- error → HTTP status (`503` operational, `504` not implemented) with body `{"msg": "..."}`

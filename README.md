# xLights LLM Orchestrator

Tooling to drive [xLights](https://xlights.org) programmatically and (eventually) generate
light-show sequences with parallel LLM agents. See `PLAN.html` for the full roadmap.

This repo is a **uv workspace**. The first slice ships two packages:

| Package | What it is |
| --- | --- |
| [`packages/xlights-core`](packages/xlights-core) | Async client + typed models for the xLights automation REST API (read-only for now). |
| [`packages/xlights-mcp`](packages/xlights-mcp) | An MCP server exposing the read operations as tools (usable from Claude Code, etc.). |

## Prerequisites

- Python 3.11+
- A running **xLights** with the **automation / REST listener enabled** (it serves on
  `http://127.0.0.1:49913` by default — instance "A"; "B" uses `49914`). Without it, the
  live tools return a clean connection error.

## Setup

```bash
# with uv (recommended)
uv sync

# or with pip + venv
python -m venv .venv && . .venv/bin/activate
pip install -e packages/xlights-core -e packages/xlights-mcp
```

Configure the endpoint via `XLIGHTS_BASE_URL` (see `.env.example`); it defaults to
`http://127.0.0.1:49913`.

## Run the MCP server

```bash
xlights-mcp          # stdio MCP server
```

Add it to an MCP client (e.g. Claude Code) and call `xl_get_models`, `xl_get_model`,
`xl_get_controllers`, `xl_get_show_folder`, `xl_get_version`.

## Tests

```bash
pytest                       # unit tests (no live xLights needed; use recorded fixtures)
pytest -m live               # opt-in smoke test against a running xLights
```

## Scope (this slice)

**Read-only.** No mutation of any sequence/effect/config — safe to run against a live show.
Writing effects, audio analysis, and the agent orchestrator come in later changes (see
`openspec/changes/`).

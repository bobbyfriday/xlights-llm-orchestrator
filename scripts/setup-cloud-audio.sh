#!/usr/bin/env bash
# One-shot, idempotent install of the full audio-analysis stack into this repo's uv venv on a
# Linux box with no Docker daemon — e.g. a Claude Code cloud environment (use it as the
# environment's setup script, or run it once per session). Equivalent to the Docker image.
#
# The environment's network policy must allow: github.com (VAMP plugin sources),
# download.pytorch.org (CPU torch), dl.fbaipublicfiles.com (demucs weights, first run),
# huggingface.co + *.hf.co (whisper weights, first run). PyPI and apt are allowed by default.
set -euo pipefail
cd "$(dirname "$0")/.."

SUDO=""; [ "$(id -u)" -ne 0 ] && SUDO="sudo"
export VAMP_PREFIX="${VAMP_PREFIX:-/usr/local/lib/vamp}"

if ! command -v ffmpeg >/dev/null || ! command -v g++ >/dev/null || ! ldconfig -p | grep -q libsndfile; then
  $SUDO apt-get update -qq
  $SUDO apt-get install -y -qq --no-install-recommends build-essential git ffmpeg libsndfile1
fi

if ! ls "$VAMP_PREFIX"/{qm-vamp-plugins,nnls-chroma,segmentino}.so >/dev/null 2>&1; then
  $SUDO env VAMP_PREFIX="$VAMP_PREFIX" bash scripts/install-vamp-plugins.sh
fi

uv sync --extra preview
uv pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu
uv pip install numpy setuptools wheel Cython
uv pip install --no-build-isolation "vamp>=1.1"
uv pip install -e "packages/xlights-core[audio,lyrics,stems-torch,align-cpu]" -e packages/xlights-orchestrator

uv run --no-sync python -c \
  "from xlights_core.audio.extractors.vamp_host import check_required_plugins; check_required_plugins(); print('audio stack ready: uv run --no-sync xlo analyze <song.mp3>')"

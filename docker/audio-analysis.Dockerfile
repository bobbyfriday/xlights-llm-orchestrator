# Audio-analysis image: MP3 → analysis bundle (stems, beats/bars/tempo, onsets, key, chords,
# sections, energy, timed lyrics) for downstream LLM orchestration. Linux/x86_64 or arm64, CPU.
#
#   docker build -f docker/audio-analysis.Dockerfile -t xlights-audio .
#   docker run --rm -v "$PWD/mp3:/in:ro" -v "$PWD/out:/out" -v xlo-cache:/cache \
#       -e GENIUS_ACCESS_TOKEN xlights-audio "/in/My Song.mp3"
#
# Every model is baked in at build time, so the container runs fully offline (Genius lyric
# text is the only network call, and it's optional: pass --lyrics FILE or --no-lyrics).

# -- stage 1: compile the required VAMP plugins (not packaged by apt) ------------------
FROM debian:bookworm-slim AS vamp
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential git ca-certificates \
    && rm -rf /var/lib/apt/lists/*
COPY scripts/install-vamp-plugins.sh /tmp/install-vamp-plugins.sh
RUN VAMP_PREFIX=/opt/vamp bash /tmp/install-vamp-plugins.sh

# -- stage 2: runtime --------------------------------------------------------------------
FROM python:3.11-slim-bookworm
# ffmpeg: mp3 decode + stem export; libsndfile: soundfile; build-essential: the `vamp`
# python host compiles from sdist.
RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg libsndfile1 build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY --from=vamp /opt/vamp /usr/local/lib/vamp
ENV VAMP_PATH=/usr/local/lib/vamp \
    TORCH_HOME=/opt/models/torch \
    HF_HOME=/opt/models/hf \
    XLO_CACHE_DIR=/cache \
    XLO_STEMS_BACKEND=torch \
    XLO_WHISPER_BACKEND=faster \
    PIP_NO_CACHE_DIR=1 \
    PYTHONUNBUFFERED=1

# Heavy, slow-changing deps first (layer-cached): CPU-only torch, then the vamp host, which
# needs numpy/Cython present at build time (see packages/xlights-core/pyproject.toml).
RUN pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu \
    && pip install numpy setuptools wheel Cython \
    && pip install --no-build-isolation "vamp>=1.1"

WORKDIR /app
COPY packages/ packages/
RUN pip install "./packages/xlights-core[audio,lyrics,stems-torch,align-cpu]" ./packages/xlights-orchestrator

# Bake the models in: demucs 6-stem weights + faster-whisper small (int8).
ARG STEMS_MODEL=htdemucs_6s
ARG WHISPER_MODEL=small
ENV XLO_STEMS_MODEL=${STEMS_MODEL} XLO_WHISPER_MODEL=${WHISPER_MODEL}
RUN python -c "from demucs.pretrained import get_model; get_model('${STEMS_MODEL}')" \
    && python -c "from faster_whisper import WhisperModel; WhisperModel('${WHISPER_MODEL}', device='cpu', compute_type='int8')" \
    && python -c "from xlights_core.audio.extractors.vamp_host import check_required_plugins; check_required_plugins(); print('vamp plugins OK')"
# Models are baked in: never reach for the Hugging Face hub at run time.
ENV HF_HUB_OFFLINE=1

VOLUME ["/cache", "/out"]
WORKDIR /work
ENTRYPOINT ["xlo", "analyze", "--out", "/out"]

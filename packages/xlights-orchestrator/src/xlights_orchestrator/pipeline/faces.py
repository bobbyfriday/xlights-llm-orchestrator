"""Auto-place an xLights Faces effect on singing-face props so they lip-sync to the vocals.

Deterministic (not LLM-driven): for each face prop in the layout, one `Faces` effect spanning the
vocal region, reading the phoneme timing track the pipeline writes (see `timing._phoneme_track`). The
face rests during instrumental passages natively (`SuppressWhenNotSinging`). `Faces` is asset-bound,
so the emitter places it from these explicit settings, not the preset library.
"""

from __future__ import annotations

import json
import logging
import xml.etree.ElementTree as ET
from collections.abc import Sequence
from pathlib import Path

from ..show_plan import EffectInstruction
from xlights_core.audio.phonemes import word_to_visemes

from .timing import (FACES_XTIMING_NAME, TimingMark, TimingTrack, _phoneme_track, _timed_words,
                     load_xtiming, xtiming_lines)

log = logging.getLogger(__name__)

FACES_TIMING_TRACK = "Faces"          # MUST match timing._phoneme_track's track name
_IMAGE_FACE_TYPES = {"Matrix", "Rendered"}   # image-based defs; we drive the node defs
MATRIX_FACE_NAME = "matrix_face.json"  # per-song opt-in: an image face (e.g. Slimer) on a matrix
LEAD_FRAMES = 30                      # stay lit ~1.5 s (at 50 ms) around each sound, fading in/out


def singing_face_props(rgb_path: str | Path) -> list[tuple[str, str]]:
    """`(model_name, face_definition_name)` for every prop with a node-based face definition.

    A model that carries a `faceInfo` is a singing face; we pick its first node-based definition
    (skip image `Matrix`/`Rendered` defs) so the Faces effect drives the actual pixels.
    """
    out: list[tuple[str, str]] = []
    try:
        root = ET.parse(rgb_path).getroot()
    except Exception as exc:  # noqa: BLE001 — no/short layout → no faces, never fatal
        log.info("singing_face_props: could not read %s: %s", rgb_path, exc)
        return out
    for m in root.iter("model"):
        name = m.get("name") or ""
        defs = [f for f in m.findall("faceInfo") if (f.get("Type") or "") not in _IMAGE_FACE_TYPES]
        if name and defs:
            out.append((name, defs[0].get("Name") or "Default"))
    return out


def _face_def(model: ET.Element, face: str) -> str | None:
    """The model's face definition named `face` (case-insensitive, any type), as spelled there."""
    for f in model.findall("faceInfo"):
        if (f.get("Name") or "").casefold() == face.casefold():
            return f.get("Name")
    return None


def matrix_face(song_dir: str | Path | None, rgb_path: str | Path) -> tuple[str, str, str | None] | None:
    """`(model, face_definition, hook_face_definition | None)` from `<song dir>/matrix_face.json`.

    `{"target": "Panel Matrix", "face": "Slimer", "hook_face": "Ghostbusters"}` sings the song with
    the model's IMAGE face definitions, which `singing_face_props` skips by default (they would cover
    a whole matrix on every song). The optional `hook_face` sings the repeated lyric lines (the
    hooks) and `face` the rest. Each must be a `faceInfo` Name on the target (any type,
    case-insensitive); an unknown hook face just leaves every line to `face`.
    """
    if song_dir is None:
        return None
    p = Path(song_dir) / MATRIX_FACE_NAME
    if not p.exists():
        return None
    try:
        spec = json.loads(p.read_text())
        root = ET.parse(rgb_path).getroot()
    except Exception as exc:  # noqa: BLE001 — a bad opt-in file must not break realize
        log.warning("%s: %s; no matrix face placed", MATRIX_FACE_NAME, exc)
        return None
    target, face, hook = spec.get("target", ""), spec.get("face", ""), spec.get("hook_face", "")
    model = next((m for m in root.iter("model") if m.get("name") == target), None)
    if model is None:
        log.warning("%s: no model %r in the layout; no matrix face placed", MATRIX_FACE_NAME, target)
        return None
    main = _face_def(model, face)
    if main is None:
        log.warning("%s: %r has no face definition %r; no matrix face placed",
                    MATRIX_FACE_NAME, target, face)
        return None
    hook_def = _face_def(model, hook) if hook else None
    if hook and hook_def is None:
        log.warning("%s: %r has no face definition %r; %s sings every line",
                    MATRIX_FACE_NAME, target, hook, main)
    return target, main, hook_def


def _get(o, key, default=None):
    return o.get(key, default) if isinstance(o, dict) else getattr(o, key, default)


def _spec(song_dir) -> dict:
    p = Path(song_dir) / MATRIX_FACE_NAME if song_dir is not None else None
    try:
        return json.loads(p.read_text()) if p is not None and p.exists() else {}
    except Exception as exc:  # noqa: BLE001 — matrix_face() warns about the bad file
        log.debug("%s unreadable: %s", MATRIX_FACE_NAME, exc)
        return {}


ENV_HOP_MS = 50                        # vocal envelope resolution for shout timing


def vocal_envelope(sa) -> list[float] | None:
    """The vocal stem's loudness every ENV_HOP_MS (RMS), decoded from the analyzer's stem cache.

    None when the stem audio isn't on disk (no separation, moved cache) — callers fall back to the
    analysis' coarse energy arc.
    """
    import shutil
    import subprocess

    import numpy as np
    from xlights_core.audio.analyzer import AudioAnalyzer

    try:
        an = AudioAnalyzer()
        stem_dir = an.cache_dir / an._entry(str(_get(sa, "path") or "")) / "stems"
        stem = next((stem_dir / f"vocals.{x}" for x in ("wav", "mp3") if (stem_dir / f"vocals.{x}").exists()), None)
        if stem is None or shutil.which("ffmpeg") is None:
            return None
        raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", str(stem), "-ac", "1", "-ar", "8000",
                              "-f", "s16le", "-"], capture_output=True, check=True).stdout
    except Exception as exc:  # noqa: BLE001 — shouts fall back to the coarse arc
        log.debug("vocal envelope unavailable: %s", exc)
        return None
    x = np.frombuffer(raw, np.int16).astype(float) / 32768
    hop = 8000 * ENV_HOP_MS // 1000
    n = len(x) // hop
    return np.sqrt((x[: n * hop].reshape(n, hop) ** 2).mean(axis=1)).tolist() if n else None


def _bursts(env: list[float], lo_ms: int, hi_ms: int, *, gap_ms: int = 300) -> list[tuple[int, int, float]]:
    """Loud stretches (start, end, energy) in [lo, hi): frames ≥ 40% of the window peak, joined
    across gaps ≤ gap_ms (the syllables of one shouted word)."""
    i0, i1 = max(0, lo_ms // ENV_HOP_MS), min(len(env), hi_ms // ENV_HOP_MS)
    if i1 <= i0:
        return []
    thr = 0.4 * max(env[i0:i1])
    out: list[list] = []
    for i in range(i0, i1):
        if env[i] < thr or thr <= 0:
            continue
        t = i * ENV_HOP_MS
        if out and t - out[-1][1] <= gap_ms:
            out[-1][1], out[-1][2] = t + ENV_HOP_MS, out[-1][2] + env[i]
        else:
            out.append([t, t + ENV_HOP_MS, env[i]])
    return [tuple(b) for b in out]


def shout_spans(sa, words: list[TimingMark], after: str, *, window_ms: int = 3000,
                half_ms: int = 600, envelope: list[float] | None = None) -> list[tuple[int, int]]:
    """The un-transcribed answer shouted after each `after` word ("call" → "Ghostbusters!").

    For every `after` word followed by a pause, the strongest burst on the vocal stem in the next
    `window_ms` (before the next sung word). With the stem's fine `envelope` that burst's own edges
    are the span; without it, ~1.2 s around the peak of the analysis' coarse energy arc. Bursts
    under a quarter of the song's loudest vocal are ignored (no answer there).
    """
    vocals = next((st for st in _get(sa, "stems") or [] if _get(st, "stem") == "vocals"), None)
    arc = [(float(_get(e, "time")) * 1000, float(_get(e, "rms")))
           for e in (_get(vocals, "energy_arc") or [])] if vocals is not None else []
    if not arc and not envelope:
        return []
    loud = max(envelope) if envelope else max(r for _, r in arc)
    want = _norm_line(after)
    out: list[tuple[int, int]] = []
    for i, w in enumerate(words):
        if _norm_line(w.label) != want:
            continue
        nxt = words[i + 1].start_ms if i + 1 < len(words) else w.end_ms + window_ms
        hi = min(nxt, w.end_ms + window_ms)
        if envelope:
            bursts = [b for b in _bursts(envelope, w.end_ms + 100, hi - 50)
                      if max(envelope[b[0] // ENV_HOP_MS:b[1] // ENV_HOP_MS]) >= 0.25 * loud]
            if bursts:
                s, e, _ = max(bursts, key=lambda b: b[2])
                if e - s >= 300:
                    out.append((s, e))
            continue
        cand = [(t, r) for t, r in arc if w.end_ms < t < hi]
        if not cand:
            continue
        t, r = max(cand, key=lambda x: x[1])
        if r < 0.25 * loud:
            continue
        s, e = max(w.end_ms + 50, int(t - half_ms)), min(hi - 50, int(t + half_ms))
        if e - s >= 300:
            out.append((s, e))
    return out


def _add_word(track: TimingTrack, word: str, s: int, e: int) -> None:
    """Insert a word (and its mouth shapes, spread evenly) into a phrases/words/phonemes track."""
    layers = track.layer_list()
    vis = [v for part in word.split() for v in (word_to_visemes(part) or ["rest"])]
    layers[1].append(TimingMark(word.upper(), s, e))
    step = max(1, (e - s) // len(vis))
    for i, v in enumerate(vis):
        layers[2].append(TimingMark(v, s + i * step, e if i == len(vis) - 1 else s + (i + 1) * step))
    for layer in layers[1:]:
        layer.sort(key=lambda m: m.start_ms)


def song_faces_track(song_dir, sa) -> tuple[TimingTrack | None, list[tuple[int, int]]]:
    """The song's `Faces` timing track and the shout spans added to it.

    The hand-made `faces.xtiming` when present, else the generated lyric track; plus, when
    `matrix_face.json` has `"shout": {"word": "Ghostbusters", "after": "call"}`, that word at each
    detected answer. `(None, [])` when the song has neither (the caller generates as usual).
    """
    xt = Path(song_dir) / FACES_XTIMING_NAME if song_dir is not None else None
    track = load_xtiming(xt) if xt is not None and xt.exists() else None
    shout = _spec(song_dir).get("shout") or {}
    if not (shout.get("word") and shout.get("after")):
        return track, []
    if track is None:
        track = _phoneme_track(sa, int(float(_get(sa, "duration_s", 0) or 0) * 1000))
    if track is None or len(track.layer_list()) < 3:
        return track, []
    words = [m for m in track.layer_list()[1] if not m.label.endswith("*")]
    spans = shout_spans(sa, words, shout["after"], envelope=vocal_envelope(sa))
    for s, e in spans:
        _add_word(track, shout["word"], s, e)
    return track, spans


def _norm_line(text: str) -> str:
    return " ".join("".join(c for c in text.casefold() if c.isalnum() or c.isspace()).split())


def _sung_lines(lyrics) -> list[tuple[str, int, int]]:
    """(normalized text, first word start, last word end) per lyric line that has timed words."""
    out = []
    for ln in (lyrics.get("lines") if isinstance(lyrics, dict) else None) or []:
        words = _timed_words({"lines": [ln]})
        if words and _norm_line(ln.get("text") or ""):
            out.append((_norm_line(ln["text"]), words[0][1], max(e for _, _, e in words)))
    return sorted(out, key=lambda x: x[1])


def _duet_spans(lines: list[tuple[str, int, int]], face: str, hook: str,
                shouts: Sequence[tuple[int, int]] = (), lead_ms: int = 0) -> list[tuple[str, int, int]]:
    """Hand each sung line to `face` or `hook`; merge runs into tiled spans.

    A shout (an answer the lyric doesn't transcribe) goes to `hook`, and the line it answers to
    `face` — the call and response. Otherwise a line that repeats or contains a repeated 3+ word
    line (a hook) goes to `hook`, the rest to `face`. Each span runs to the next span's start; the
    first starts `lead_ms` early and the last ends `lead_ms` late so the fade has room.
    """
    counts: dict[str, int] = {}
    for t, _, _ in lines:
        counts[t] = counts.get(t, 0) + 1
    hooks = [t for t, n in counts.items() if n >= 2 and len(t.split()) >= 3]
    timeline = sorted([(s, e, t, False) for t, s, e in lines] + [(s, e, "", True) for s, e in shouts])
    runs: list[list] = []
    for i, (s, e, t, is_shout) in enumerate(timeline):
        if is_shout:
            who = hook
        elif i + 1 < len(timeline) and timeline[i + 1][3]:
            who = face                        # the call; the hook face answers
        else:                                 # "oh who you gon call" still carries the hook
            who = hook if counts[t] >= 2 or any(f" {h} " in f" {t} " for h in hooks) else face
        if runs and runs[-1][0] == who:
            runs[-1][2] = max(runs[-1][2], e)
        else:
            runs.append([who, s, e])
    if not runs:
        return []
    runs[0][1] = max(0, runs[0][1] - lead_ms)
    return [(who, s, runs[i + 1][1] if i + 1 < len(runs) else e + lead_ms)
            for i, (who, s, e) in enumerate(runs)]


def _faces_settings(face_def: str, track: str, lead_frames: int = LEAD_FRAMES) -> dict[str, str]:
    # No E_CHOICE_Faces_Phoneme: xLights reads phonemes from the track only when that setting is
    # absent/empty; "(Auto)" is taken literally as a mouth name (no image → a red box on matrices).
    return {
        "E_CHOICE_Faces_TimingTrack": track,
        "E_CHOICE_Faces_FaceDefinition": face_def,
        "E_CHOICE_Faces_Eyes": "Auto",                       # natural blinking
        "E_CHECKBOX_Faces_SuppressWhenNotSinging": "1",      # rest during instrumental passages
        "E_CHECKBOX_Faces_Outline": "0",
        "E_SPINCTRL_Faces_LeadFrames": str(lead_frames),     # bridge short pauses …
        "E_CHECKBOX_Faces_Fade": "1",                        # … and fade, never blink
    }


def place_faces(sa, rgb_path: str | Path, *, track: str = FACES_TIMING_TRACK,
                song_dir: str | Path | None = None) -> list[EffectInstruction]:
    """One Faces `EffectInstruction` per singing-face prop, spanning the vocal region.

    Plus the song's opt-in matrix face (`matrix_face.json`), if any. Empty when the song has no
    timed lyric words or the layout has no usable face prop.
    """
    lyrics = getattr(sa, "lyrics", None)
    xt = Path(song_dir) / FACES_XTIMING_NAME if song_dir is not None else None
    hand = load_xtiming(xt) if xt is not None and xt.exists() else None
    if hand is not None:                      # a hand-made lyric track wins over the alignment
        lines = [(_norm_line(t), s, e) for t, s, e in xtiming_lines(hand)]
    else:
        lines = _sung_lines(lyrics) if lyrics else []
    _, shouts = song_faces_track(song_dir, sa) if lines else (None, [])
    faces = singing_face_props(rgb_path) if lines else []
    extra = matrix_face(song_dir, rgb_path) if lines else None
    if not lines or not (faces or extra):
        return []
    lead_ms = LEAD_FRAMES * 50                # room for the fade in before / out after the vocals
    start_ms, end_ms = max(0, lines[0][1] - lead_ms), max(e for _, _, e in lines) + lead_ms
    out: list[EffectInstruction] = []
    for model, face_def in faces:
        if extra and model == extra[0]:
            continue                                      # the opt-in owns that model
        out.append(EffectInstruction(
            target=model, effect_type="Faces", look_id="",
            start_ms=start_ms, end_ms=end_ms,
            extra_settings=_faces_settings(face_def, track), on_top=True))
    if extra:
        model, face_def, hook_def = extra
        spans = (_duet_spans(lines, face_def, hook_def, shouts, lead_ms) if hook_def
                 else [(face_def, start_ms, end_ms)])
        for who, s, e in spans:
            out.append(EffectInstruction(
                target=model, effect_type="Faces", look_id="", start_ms=s, end_ms=e,
                extra_settings=_faces_settings(who, track), on_top=True))
        faces = [*faces, (model, face_def)]
    log.info("singing faces: placed %d Faces effect(s) [%d-%dms] on %s",
             len(out), start_ms, end_ms, ", ".join(m for m, _ in faces))
    return out

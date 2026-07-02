"""FSEQ v2 binary reader (PSEQ): fixed header + compression-block index + zstd blocks.

Ported near-verbatim from the proven xlight-autosequencer/src/video/fseq.py.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import zstandard as zstd


@dataclass
class FseqHeader:
    channels: int
    frames: int
    step_ms: int
    data_offset: int


def load_fseq(path: str | Path) -> tuple[FseqHeader, np.ndarray]:
    """Return (header, frames) where frames is a uint8 [num_frames, channels] array."""
    path = Path(path)
    raw = path.read_bytes()
    if raw[:4] != b"PSEQ":
        raise ValueError(f"{path} is not an FSEQ v2 file (magic={raw[:4]!r})")

    data_offset = struct.unpack_from("<H", raw, 4)[0]
    channels = struct.unpack_from("<I", raw, 10)[0]
    num_frames = struct.unpack_from("<I", raw, 14)[0]
    step_ms = raw[18]
    # Byte 20: compression type in the low nibble, high bits of the block count in the
    # high nibble; byte 21: low bits of the block count.
    comp_type = raw[20] & 0x0F
    block_count = ((raw[20] & 0xF0) << 4) | raw[21]

    out = np.zeros((num_frames, channels), dtype=np.uint8)

    if comp_type == 0:  # uncompressed: channel data laid out directly at data_offset
        n = min(num_frames, (len(raw) - data_offset) // channels)
        arr = np.frombuffer(raw, dtype=np.uint8, count=n * channels, offset=data_offset)
        out[:n] = arr.reshape(n, channels)
        return FseqHeader(channels=channels, frames=num_frames, step_ms=step_ms,
                          data_offset=data_offset), out
    if comp_type != 1:
        raise ValueError(f"{path}: unsupported FSEQ compression type {comp_type} (only zstd)")

    # Compression-block index: block_count entries of 4-byte first-frame + 4-byte length.
    blocks = []
    for i in range(block_count):
        off = 32 + i * 8
        if off + 8 > data_offset:
            break
        frame_idx = struct.unpack_from("<I", raw, off)[0]
        blen = struct.unpack_from("<I", raw, off + 4)[0]
        if blen == 0:
            continue  # placeholder/padding entry, occupies no data
        blocks.append((frame_idx, blen))

    dctx = zstd.ZstdDecompressor()
    cursor = data_offset
    for frame_idx, blen in blocks:
        block = raw[cursor:cursor + blen]
        cursor += blen  # data blocks are sequential; advance even if we skip writing
        if frame_idx >= num_frames:
            continue
        decompressed = dctx.decompress(block, max_output_size=channels * 200)
        n = min(len(decompressed) // channels, num_frames - frame_idx)
        arr = np.frombuffer(decompressed, dtype=np.uint8, count=n * channels)
        out[frame_idx:frame_idx + n] = arr.reshape(n, channels)

    return FseqHeader(channels=channels, frames=num_frames, step_ms=step_ms,
                      data_offset=data_offset), out

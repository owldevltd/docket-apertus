"""Page images in and out.

Pages come from poppler as raw PPM (colour) or PGM (grey), which need no decoder; control images and page
images for the browser go out as PNG written here. Scaling is a box filter with fractional coverage: a work
pixel covers width / w source pixels, fractions included, so the blocks drift slightly across the page the way
image libraries scale. The geometry was measured against masks scaled that way (6 October 2026).
"""

from __future__ import annotations

import struct
import zlib
from pathlib import Path

import numpy as np

# Rec. 709 luma with the coefficients of the image library behind the measurements, computed on 16-bit values
# and cut to 8 bit without rounding, which is what that library does (checked pixel for pixel, 8 October 2026)
LUMA = (0.212656, 0.715158, 0.072186)
QUANTUM = 257


def read_pnm(path: str | Path) -> np.ndarray:
    """A P5 (grey, H x W) or P6 (colour, H x W x 3) file as an 8-bit array."""
    data = Path(path).read_bytes()
    magic, width, height, maxval, offset = _header(data)
    if maxval != 255:
        raise ValueError(f"{path}: only 8-bit PNM is supported")
    channels = 3 if magic == b"P6" else 1
    pixels = np.frombuffer(data, dtype=np.uint8, count=width * height * channels, offset=offset)
    if channels == 1:
        return pixels.reshape(height, width)
    return pixels.reshape(height, width, 3)


def _header(data: bytes) -> tuple[bytes, int, int, int, int]:
    """Magic number, width, height, maximum value and where the pixels start; comments allowed."""
    pos = 0
    fields: list[bytes] = []
    while len(fields) < 4:
        while data[pos : pos + 1].isspace():
            pos += 1
        if data[pos : pos + 1] == b"#":
            while data[pos : pos + 1] not in (b"\n", b""):
                pos += 1
            continue
        start = pos
        while pos < len(data) and not data[pos : pos + 1].isspace():
            pos += 1
        fields.append(data[start:pos])
    magic = fields[0]
    if magic not in (b"P5", b"P6"):
        raise ValueError("not a binary PGM or PPM file")
    # exactly one whitespace byte separates the header from the pixels
    return magic, int(fields[1]), int(fields[2]), int(fields[3]), pos + 1


def luma_quantum(image: np.ndarray) -> np.ndarray:
    """Grey per pixel on the 16-bit scale (0 to 65535); a grey image is spread onto that scale."""
    if image.ndim == 2:
        return image.astype(np.int32) * QUANTUM
    values = image.astype(np.float64) * QUANTUM
    luma = values[:, :, 0] * LUMA[0] + values[:, :, 1] * LUMA[1] + values[:, :, 2] * LUMA[2]
    return np.rint(luma).astype(np.int32)


def to_gray(image: np.ndarray) -> np.ndarray:
    """One grey byte per pixel, the 16-bit grey cut to 8 bit."""
    if image.ndim == 2:
        return image
    return (luma_quantum(image) // QUANTUM).astype(np.uint8)


def to_rgb(image: np.ndarray) -> np.ndarray:
    """Three bytes per pixel; a grey image is spread over the channels."""
    if image.ndim == 3:
        return image
    return np.repeat(image[:, :, np.newaxis], 3, axis=2)


def coverage(source: int, target: int) -> list[tuple[np.ndarray, np.ndarray]]:
    """For every offset k the source index and its weight per target pixel, so that a sum over k is the box
    filter with fractional coverage. A target pixel covers at most ceil(ratio) + 1 source pixels."""
    ratio = source / target
    t = np.arange(target, dtype=np.float64)
    s0 = t * ratio
    s1 = s0 + ratio
    first = np.floor(s0).astype(np.int64)
    out = []
    for k in range(int(np.ceil(ratio)) + 1):
        index = first + k
        weight = np.minimum(index + 1, s1) - np.maximum(index, s0)
        weight = np.where((index < source) & (weight > 1e-9), weight, 0.0)
        out.append((np.minimum(index, source - 1), weight))
    return out


def scale_box(values: np.ndarray, width: int, height: int) -> np.ndarray:
    """A 2-D array scaled to width x height by averaging over the covered pixels, rows first, then columns."""
    cols = coverage(values.shape[1], width)
    rows = coverage(values.shape[0], height)
    across = np.zeros((values.shape[0], width), dtype=np.float64)
    total = np.zeros(width, dtype=np.float64)
    for index, weight in cols:
        across += values[:, index] * weight
        total += weight
    across /= total
    down = np.zeros((height, width), dtype=np.float64)
    total = np.zeros(height, dtype=np.float64)
    for index, weight in rows:
        down += across[index, :] * weight[:, np.newaxis]
        total += weight
    return down / total[:, np.newaxis]


def scale_rgb(image: np.ndarray, width: int) -> np.ndarray:
    """A colour image scaled to a width, the height by the same ratio."""
    height = max(1, int(round(image.shape[0] * width / image.shape[1])))
    out = np.zeros((height, width, 3), dtype=np.uint8)
    for c in range(3):
        out[:, :, c] = np.clip(np.rint(scale_box(image[:, :, c].astype(np.float64), width, height)), 0, 255)
    return out


def write_png(path: str | Path, image: np.ndarray) -> None:
    """An 8-bit colour image as PNG, no filtering, deflate from the standard library."""
    rgb = to_rgb(np.ascontiguousarray(image))
    height, width = rgb.shape[:2]
    raw = np.zeros((height, 1 + width * 3), dtype=np.uint8)
    raw[:, 1:] = rgb.reshape(height, width * 3)
    header = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    Path(path).write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + _chunk(b"IHDR", header)
        + _chunk(b"IDAT", zlib.compress(raw.tobytes(), 6))
        + _chunk(b"IEND", b"")
    )


def _chunk(name: bytes, body: bytes) -> bytes:
    return struct.pack(">I", len(body)) + name + body + struct.pack(">I", zlib.crc32(name + body) & 0xFFFFFFFF)

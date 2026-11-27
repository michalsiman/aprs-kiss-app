"""Smaller files for packet radio: a picture made smaller (fewer pixels, JPEG), any other file zipped.

At 1200 Bd a file goes at about 60–100 bytes a second, so a 4 MB photo takes hours while the same picture at
480 px is some 25 kB and a few minutes. The variants are worked out at once and offered with their size; the
person sending picks one. Pictures lose their EXIF (the camera's GPS position too) and are turned upright first.
"""

from __future__ import annotations

import io
import zipfile
from dataclasses import dataclass
from pathlib import PurePath

# (the longest side in pixels, JPEG quality, grey) from big to tiny
PRESETS = ((1280, 70, False), (800, 62, False), (480, 55, False), (320, 50, False), (160, 45, True))
ZIP_GAIN = 0.9  # a zip is offered only when it is at most this much of the original


@dataclass(frozen=True)
class Variant:
    key: str  # "original", "1280", …, "zip"
    name: str  # the file name it goes under
    data: bytes
    width: int = 0
    height: int = 0
    grey: bool = False


def _open(data: bytes):
    try:
        from PIL import Image, ImageOps  # noqa: PLC0415 - only for pictures
    except ImportError:
        return None
    try:
        img = Image.open(io.BytesIO(data))
        img.load()
    except Exception:  # noqa: BLE001 - not a picture Pillow reads
        return None
    return ImageOps.exif_transpose(img)


def is_picture(data: bytes) -> bool:
    return _open(data) is not None


def picture_variants(name: str, data: bytes) -> list[Variant]:
    """The original and the smaller versions that really are smaller (and smaller than the one before);
    [] when it is not a picture."""
    img = _open(data)
    if img is None:
        return []
    out = [Variant("original", name, data, *img.size)]
    stem = PurePath(name).stem or "picture"
    longest = max(img.size)
    for side, quality, grey in PRESETS:
        if side >= longest and not grey:
            continue  # no bigger than it is
        small = img.copy()
        small.thumbnail((side, side))
        small = small.convert("L") if grey else small.convert("RGB")
        buf = io.BytesIO()
        small.save(buf, "JPEG", quality=quality, optimize=True, progressive=False)
        blob = buf.getvalue()
        if blob and len(blob) < len(out[-1].data):
            out.append(Variant(str(side), f"{stem}_{side}.jpg", blob, *small.size, grey=grey))
    return out


def zipped(name: str, data: bytes) -> Variant | None:
    """The file in a ZIP (deflate, the best level), when that saves at least a tenth; any computer opens it."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        z.writestr(PurePath(name).name or "file", data)
    blob = buf.getvalue()
    if len(blob) > len(data) * ZIP_GAIN:
        return None
    return Variant("zip", f"{PurePath(name).name or 'file'}.zip", blob)

#!/usr/bin/env python3
"""Build a true call-me animation while keeping the face and body pixel-still.

Only the telephone-gesture hand is rotated; no full-body fades and no external
image services are needed. Input: author's sharp original-style repository JPG.
"""
from __future__ import annotations

import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageChops

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "assets/author-fullbody-call-me.jpg"
WEBP = ROOT / "assets/author-call-me.gif.webp"
GIF = ROOT / "assets/author-call-me.gif"

# Polygon around the raised hand in the 804x1600 sharp source. The face, shirt,
# forearm, legs, and shoes are not part of this mask and cannot flicker.
HAND_REF = [
    (277, 275), (269, 261), (275, 243), (286, 224), (297, 204),
    (311, 180), (321, 155), (320, 111), (323, 105), (330, 105),
    (338, 114), (345, 133), (346, 158), (355, 157), (371, 159),
    (384, 163), (400, 172), (403, 185), (398, 197), (405, 213),
    (433, 216), (443, 219), (446, 225), (445, 236), (433, 241),
    (415, 242), (396, 237), (375, 233), (355, 243),
    (335, 255), (315, 269), (294, 284), (286, 284),
]
PIVOT_REF = (291, 280)
# A small wrist twist and a pause: keeps the recognizable phone sign at all times.
ANGLES = (0, 0, 1, 2, 4, 6, 8, 10, 9, 7, 5, 3, 1, 0, 0,
          -1, -2, -3, -4, -3, -2, -1, 0, 0, 0, 0, 0, 0)


def generate() -> tuple[int, int, int]:
    if not SOURCE.is_file():
        raise SystemExit("Missing original character image: " + str(SOURCE))
    with Image.open(SOURCE) as f:
        original = f.convert("RGB")
    sw, sh = original.size
    if sw < 400 or sh < 800 or abs(sw / sh - 804 / 1600) > 0.12:
        raise SystemExit(f"Unexpected character image dimensions: {sw}x{sh}")

    # Keep GIF bandwidth modest while retaining sharp original art on the site.
    w = 500
    h = round(sh * (w / sw))
    original = original.resize((w, h), Image.Resampling.LANCZOS)
    sx, sy = w / 804, h / 1600
    mask = Image.new("L", (w, h), 0)
    draw = ImageDraw.Draw(mask)
    draw.polygon([(round(x*sx), round(y*sy)) for x, y in HAND_REF], fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(radius=0.75))

    # Source hand is backed by clean white: remove ONLY that hand from the
    # stationary frame before rendering the moving hand overlay.
    fixed = original.copy()
    fixed.paste(Image.new("RGB", (w,h),"white"), (0, 0), mask)
    cutout = original.convert("RGBA")
    cutout.putalpha(mask)
    pivot = (round(PIVOT_REF[0] * sx), round(PIVOT_REF[1] * sy))

    frames = []
    for a in ANGLES:
        composed = fixed.convert("RGBA")
        composed.alpha_composite(
            cutout.rotate(-a, Image.Resampling.BICUBIC, center=pivot, expand=False)
        )
        frames.append(composed.convert("RGB"))

    # The torso and entire lower half MUST be identical in every frame.
    control = frames[0].crop((0, round(h*0.35), w, h))
    for index, frame in enumerate(frames[1:], start=1):
        delta = ImageChops.difference(
            control, frame.crop((0, round(h*0.35), w, h))
        )
        if delta.getbbox():
            raise SystemExit(f"Body moved at animation frame {index}")

    # One fixed palette avoids color flashing throughout the animation.
    pal = frames[0].quantize(colors=192, method=Image.Quantize.MEDIANCUT,
                             dither=Image.Dither.NONE)
    indexed = [f.quantize(palette=pal, dither=Image.Dither.NONE)
               for f in frames]
    indexed[0].save(
        GIF, save_all=True, append_images=indexed[1:], loop=0,
        duration=90, optimize=True, disposal=2
    )
    frames[0].save(
        WEBP, save_all=True, append_images=frames[1:], loop=0,
        duration=90, quality=89, method=5
    )

    for path in (GIF, WEBP):
        with Image.open(path) as f:
            if getattr(f, "n_frames", 1) < 20 or f.size != (w,h):
                raise SystemExit(f"Animation validation failed: {path}")
    if max(ImageChops.difference(frames[0],f).getbbox() is not None
           for f in frames[1:]) == 0:
        raise SystemExit("Gesture did not move")
    print(f"Animation built: {w}x{h}, {len(frames)} frames; GIF={GIF.stat().st_size:,} B / WebP={WEBP.stat().st_size:,} B")
    return w, h, len(frames)


if __name__ == "__main__":
    generate()

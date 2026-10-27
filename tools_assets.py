"""Rebuild original Apache-2.0 studio backgrounds; no external imagery or fonts."""

from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw

root = Path(__file__).parent / "studio" / "assets"
root.mkdir(exist_ok=True)
w, h = 2400, 1800
for name, top, floor in [
    ("light", (232, 235, 239), (202, 207, 213)),
    ("dark", (47, 56, 69), (62, 70, 81)),
    ("branded", (208, 221, 224), (180, 196, 199)),
]:
    yy, xx = np.mgrid[0:h, 0:w]
    mix = np.clip((yy / h - 0.42) / 0.48, 0, 1)[..., None]
    glow = (1 - ((xx / w - 0.5) ** 2 + (yy / h - 0.25) ** 2)) * 9
    values = np.array(top) * (1 - mix) + np.array(floor) * mix + glow[..., None]
    image = Image.fromarray(np.uint8(np.clip(values, 0, 255)))
    if name == "branded":
        draw = ImageDraw.Draw(image)
        draw.rectangle((140, 120, 166, 700), fill="#609b99")
        draw.rectangle((190, 120, 196, 700), fill="#9bbab9")
    image.save(root / f"{name}.png")

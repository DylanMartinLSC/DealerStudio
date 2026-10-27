"""Build explicitly coarse manual reference masks, independently of model inference."""

import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).parent


def reference_mask(annotation, size):
    mask = Image.new("L", size)
    ImageDraw.Draw(mask).polygon(annotation["polygon"], fill=255)
    return mask


def main():
    annotations = json.loads((ROOT / "annotations.json").read_text())
    manifest = json.loads((ROOT / "manifest.json").read_text())
    output = ROOT / "references"
    output.mkdir(exist_ok=True)
    sheet = Image.new("RGB", (1500, 1500), "#17202c")
    for index, item in enumerate(x for x in manifest["samples"] if x["photo_type"] == "exterior"):
        image = Image.open(ROOT / item["image"]).convert("RGB")
        image = image.resize((1000, round(image.height * 1000 / image.width)))
        ann = annotations["samples"][item["id"]]
        mask = reference_mask(ann, image.size)
        mask.save(output / (item["id"] + ".png"))
        draw = ImageDraw.Draw(image)
        draw.line(ann["polygon"] + [ann["polygon"][0]], fill="#00ffff", width=2)
        for kind, color in (("foreground", "#00ff00"), ("background", "#ff3030")):
            for x, y, _ in ann[kind]:
                draw.ellipse((x - 4, y - 4, x + 4, y + 4), outline=color, width=2)
        image.thumbnail((740, 450))
        x, y = (index % 2) * 750, (index // 2) * 500
        sheet.paste(image, (x, y + 30))
        ImageDraw.Draw(sheet).text((x + 10, y + 8), item["id"], fill="white")
    sheet.save(ROOT / "reference-review.jpg", quality=95)
    print("Annotation SHA-256:", hashlib.sha256((ROOT / "annotations.json").read_bytes()).hexdigest())


if __name__ == "__main__":
    main()

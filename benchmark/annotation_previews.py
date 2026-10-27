"""Original-only coordinate guides; no predictions are used when authoring labels."""

from pathlib import Path
from PIL import Image, ImageDraw

root = Path(__file__).parent
(root / "annotation-previews").mkdir(exist_ok=True)
for path in (root / "images").glob("*.jpg"):
    im = Image.open(path).convert("RGB")
    im = im.resize((1000, round(im.height * 1000 / im.width)))
    draw = ImageDraw.Draw(im)
    for x in range(0, 1000, 100):
        draw.line((x, 0, x, im.height), fill=(80, 180, 180), width=1)
        draw.text((x + 3, 5), str(x), fill="red")
    for y in range(100, im.height, 100):
        draw.line((0, y, 1000, y), fill=(80, 180, 180), width=1)
        draw.text((4, y + 2), str(y), fill="red")
    im.save(root / "annotation-previews" / path.name)

import copy
import json
from pathlib import Path
import shutil
import uuid

from PIL import Image, ImageOps

DEFAULTS = dict(
    background="light",
    scale=0.86,
    x=0.5,
    floor=0.85,
    shadow=0.22,
    feather=0.6,
    decontaminate=0,
    exposure=1.0,
    width=2000,
    height=1500,
    quality=92,
    format="JPEG",
    logo="",
    logo_size=0.15,
    padding=0.035,
    corner="bottom-right",
    custom_background="",
    plate_mode="blur",
    plate_graphic="",
)
EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}


def load_image(path):
    with Image.open(path) as image:
        if image.width * image.height > 80_000_000:
            raise ValueError("Image exceeds the 80 megapixel safety limit. Resize it before import.")
        return ImageOps.exif_transpose(image).convert("RGB")


class Project:
    def __init__(self, root, name="New vehicle"):
        self.root = Path(root)
        self.name = name
        self.photos = []
        self.settings = copy.deepcopy(DEFAULTS)
        for folder in ("originals", "masks", "assets"):
            (self.root / folder).mkdir(parents=True, exist_ok=True)

    @classmethod
    def open(cls, root):
        data = json.loads((Path(root) / "project.json").read_text(encoding="utf-8"))
        if data.get("version") != 1:
            raise ValueError("Unsupported project version")
        obj = cls(root, data["name"])
        obj.photos = data["photos"]
        obj.settings.update(data["settings"])
        for photo in obj.photos:
            for key in ("source", "mask"):
                if not (obj.root / photo[key]).resolve().is_relative_to(obj.root.resolve()):
                    raise ValueError("Project paths must stay inside the project")
            if photo["status"] in ("queued", "processing"):
                photo["status"] = "pending"
        for key in ("logo", "custom_background", "plate_graphic"):
            value = obj.settings.get(key)
            if value and not (obj.root / value).resolve().is_relative_to(obj.root.resolve()):
                raise ValueError("Asset paths must stay inside project")
        return obj

    def save(self):
        tmp = self.root / "project.tmp"
        tmp.write_text(
            json.dumps(dict(version=1, name=self.name, photos=self.photos, settings=self.settings), indent=2),
            encoding="utf-8",
        )
        tmp.replace(self.root / "project.json")

    def add(self, paths):
        errors = []
        for path in paths:
            path = Path(path)
            if path.suffix.lower() not in EXTENSIONS:
                continue
            try:
                image = load_image(path)
                ident = uuid.uuid4().hex
                source = f"originals/{ident}{path.suffix.lower()}"
                shutil.copy2(path, self.root / source)
                self.photos.append(
                    dict(
                        id=ident,
                        source=source,
                        mask=f"masks/{ident}.png",
                        name=path.name,
                        kind="exterior",
                        status="pending",
                        error="",
                        plates=[],
                        adjustments={},
                        size=list(image.size),
                    )
                )
            except Exception as exc:
                errors.append(f"{path.name}: {exc}")
        self.save()
        return errors

    def asset(self, path, key):
        load_image(path)
        dest = self.root / "assets" / (uuid.uuid4().hex + Path(path).suffix.lower())
        shutil.copy2(path, dest)
        self.settings[key] = str(dest.relative_to(self.root))
        self.save()

    def options(self, photo):
        return self.settings | photo.get("adjustments", {})

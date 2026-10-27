from datetime import datetime
from pathlib import Path
import re
import shutil

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageOps

from .project import load_image

ASSETS = Path(__file__).parent / "assets"


def brush(mask, start, end, radius, foreground):
    draw = ImageDraw.Draw(mask)
    color = 255 if foreground else 0
    draw.line([start, end], fill=color, width=max(1, radius * 2))
    for x, y in (start, end):
        draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=color)


def plate_treatment(image, rectangles, mode, graphic=None):
    image = image.copy()
    for rect in rectangles:
        x0, y0, x1, y1 = rect
        box = (
            max(0, int(x0 * image.width)),
            max(0, int(y0 * image.height)),
            min(image.width, int(x1 * image.width)),
            min(image.height, int(y1 * image.height)),
        )
        if box[2] <= box[0] or box[3] <= box[1]:
            continue
        region = image.crop(box)
        if mode == "graphic" and graphic:
            region = Image.open(graphic).convert("RGB").resize(region.size)
        elif mode == "solid" or mode == "graphic":
            region = Image.new("RGB", region.size, "#252a33")
        else:
            region = region.filter(ImageFilter.GaussianBlur(max(12, region.width / 8)))
        image.paste(region, box)
    return image


def composite(project, photo, preview=False):
    s = project.options(photo)
    width, height = int(s["width"]), int(s["height"])
    if not (64 <= width <= 10000 and 64 <= height <= 10000 and width * height <= 40_000_000):
        raise ValueError("Export dimensions must be 64–10000 pixels, at most 40 megapixels.")
    if preview:
        ratio = min(1, 1200 / max(width, height))
        width, height = round(width * ratio), round(height * ratio)
    source = load_image(project.root / photo["source"])
    source = plate_treatment(
        source,
        photo["plates"],
        s["plate_mode"],
        project.root / s["plate_graphic"] if s["plate_graphic"] else None,
    )
    source = ImageEnhance.Brightness(source).enhance(float(s["exposure"]))
    if photo["kind"] != "exterior":
        result = ImageOps.pad(source, (width, height), color="#e5e7eb", method=Image.Resampling.LANCZOS)
    else:
        mask_path = project.root / photo["mask"]
        if not mask_path.exists():
            raise RuntimeError("No mask yet. Process this photo or create a manual mask.")
        mask = Image.open(mask_path).convert("L")
        if mask.size != source.size:
            raise ValueError("Mask dimensions differ from the source")
        if preview:
            source.thumbnail((1600, 1600), Image.Resampling.LANCZOS)
            mask = mask.resize(source.size, Image.Resampling.LANCZOS)
        # Optional erosion removes contaminated edge pixels without altering the paint RGB.
        if s["decontaminate"]:
            mask = mask.filter(ImageFilter.MinFilter(1 + 2 * int(s["decontaminate"])))
        if s["feather"]:
            mask = mask.filter(ImageFilter.GaussianBlur(float(s["feather"])))
        bbox = mask.point(lambda v: 255 if v > 24 else 0).getbbox()
        if not bbox:
            raise ValueError("Mask is empty. Paint foreground in Mask view.")
        foreground = source.convert("RGBA")
        foreground.putalpha(mask)
        foreground = foreground.crop(bbox)
        factor = min(width * float(s["scale"]) / foreground.width, height * 0.76 / foreground.height)
        foreground = foreground.resize(
            (max(1, round(foreground.width * factor)), max(1, round(foreground.height * factor))),
            Image.Resampling.LANCZOS,
        )
        bg = (
            project.root / s["custom_background"]
            if s["background"] == "custom" and s["custom_background"]
            else ASSETS / (s["background"] + ".png")
        )
        result = ImageOps.fit(Image.open(bg).convert("RGBA"), (width, height))
        x = round(width * float(s["x"]) - foreground.width / 2)
        y = round(height * float(s["floor"]) - foreground.height)
        # Project only alpha near the lowest contact band down onto the floor.
        # This follows visible tire contacts, rather than a detached ellipse.
        alpha = np.asarray(foreground.getchannel("A"))
        band = alpha[max(0, alpha.shape[0] - max(2, int(alpha.shape[0] * 0.045))) :]
        profile = band.max(axis=0)
        depth = max(3, int(height * 0.018))
        falloff = np.exp(-(np.linspace(-2.5, 2.5, depth) ** 2))
        shadow = Image.fromarray((falloff[:, None] * profile[None, :]).astype("uint8"))
        blur = max(1, round(width * 0.004))
        shadow = ImageOps.expand(shadow, border=blur * 3, fill=0)
        shadow = shadow.filter(ImageFilter.GaussianBlur(blur))
        shadow = shadow.point(lambda v: int(v * float(s["shadow"])))
        layer = Image.new("RGBA", result.size)
        layer.paste((0, 0, 0, 0), (0, 0, width, height))
        layer.paste(
            Image.new("RGBA", shadow.size, (0, 0, 0, 255)),
            (x - blur * 3, y + foreground.height - depth // 2 - blur * 3),
            shadow,
        )
        # Explicit tire-contact points support perspective where the far tire sits higher.
        for cx, cy in photo.get("contacts", []):
            px = x + (cx * source.width - bbox[0]) * factor
            py = y + (cy * source.height - bbox[1]) * factor
            contact = Image.new("L", result.size)
            draw = ImageDraw.Draw(contact)
            rx, ry = width * 0.033, height * 0.005
            draw.ellipse((px - rx, py - ry, px + rx, py + ry), fill=int(255 * float(s["shadow"])))
            contact = contact.filter(ImageFilter.GaussianBlur(width * 0.004))
            ink = Image.new("RGBA", result.size, (0, 0, 0, 0))
            ink.putalpha(contact)
            layer = Image.alpha_composite(layer, ink)
        result = Image.alpha_composite(result, layer)
        result.alpha_composite(foreground, (x, y))
        result = result.convert("RGB")
    if s["logo"]:
        with Image.open(project.root / s["logo"]) as raw:
            logo = raw.convert("RGBA")
        logo.thumbnail(
            (max(1, int(width * s["logo_size"])), max(1, int(height * 0.22))), Image.Resampling.LANCZOS
        )
        pad = int(min(width, height) * s["padding"])
        x = width - logo.width - pad if "right" in s["corner"] else pad
        y = height - logo.height - pad if "bottom" in s["corner"] else pad
        result.paste(logo, (x, y), logo)
    return result


def export_set(project, destination, cancel, progress, originals=False):
    # Exclusive new directory prevents overwrites, including exports into source folders.
    stem = re.sub(r"[^\w-]+", "-", project.name, flags=re.UNICODE).strip("-.")[:70] or "vehicle"
    root = Path(destination) / f"{stem}-{datetime.now():%Y%m%d-%H%M%S-%f}"
    root.mkdir(parents=True, exist_ok=False)
    errors = []
    for index, photo in enumerate(project.photos):
        if cancel.is_set():
            break
        try:
            result = composite(project, photo)
            s = project.options(photo)
            ext = "jpg" if s["format"] == "JPEG" else "png"
            result.save(
                root / f"{stem}-{index + 1:03d}-{photo['kind']}.{ext}",
                format=s["format"],
                quality=int(s["quality"]),
                subsampling=0,
            )
            if originals:
                (root / "originals").mkdir(exist_ok=True)
                shutil.copy2(
                    project.root / photo["source"],
                    root / "originals" / f"{index + 1:03d}-{Path(photo['source']).name}",
                )
        except Exception as exc:
            errors.append(f"{photo['name']}: {exc}")
        progress(index + 1, len(project.photos))
    (root / "export-report.txt").write_text(
        "Cancelled: " + str(cancel.is_set()) + "\n" + "\n".join(errors), encoding="utf-8"
    )
    return root, errors

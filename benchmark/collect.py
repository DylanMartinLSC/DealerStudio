"""Explicit, bounded Commons collection. Never imported by the desktop application."""

from datetime import datetime, timezone
import hashlib
import html
import json
from pathlib import Path
import re
import time
import urllib.parse
import urllib.request
import urllib.error

from PIL import Image, ImageDraw, ImageOps

ROOT = Path(__file__).parent
SELECTION = [
    (
        "sedan-front",
        "2018 Toyota Camry LE front 6.13.18.jpg",
        "exterior",
        "known-development",
        "sedan, silver, front three-quarter, reflections",
    ),
    (
        "sedan-rear",
        "2018 Toyota Camry LE rear 6.13.18.jpg",
        "exterior",
        "evaluation",
        "sedan, silver, rear three-quarter, street",
    ),
    (
        "pickup",
        "'18 Ford F-150.jpg",
        "exterior",
        "evaluation",
        "pickup, dark paint, tall profile, smaller subject",
    ),
    (
        "suv-rack",
        "2019 Subaru Forester 2.5i Premium, front 10.6.19.jpg",
        "exterior",
        "evaluation",
        "SUV, roof rails, windows, adjacent vehicles",
    ),
    (
        "hatch-side",
        "2020 Volkswagen Golf Style 1.5 Side.jpg",
        "exterior",
        "evaluation",
        "hatchback, side view, wheel gaps",
    ),
    (
        "convertible",
        "1990 Mazda MX-5 Miata, front left, 06-08-2024.jpg",
        "exterior",
        "evaluation",
        "convertible, open cabin, thin windshield, busy scene",
    ),
    (
        "interior",
        "2018 Toyota Camry Interior.jpg",
        "interior",
        "routing-control",
        "interior, basic correction and padding; never segment",
    ),
]
ALLOWED = {"CC BY-SA 4.0", "CC BY-SA 3.0", "CC BY 4.0", "CC BY 3.0", "CC BY 2.0", "CC0", "Public domain"}


def request(url):
    req = urllib.request.Request(
        url, headers={"User-Agent": "DealerStudioBenchmark/0.1 (bounded licensed-image evaluation)"}
    )
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=60) as response:
                return response.read()
        except urllib.error.HTTPError as exc:
            if exc.code not in (429, 503) or attempt == 2:
                raise
            delay = max(60, int(exc.headers.get("Retry-After", "60")))
            print(f"HTTP {exc.code}; respecting {delay}s retry delay", flush=True)
            time.sleep(delay)


def plain(value):
    return html.unescape(re.sub("<[^>]+>", "", value))


def collect():
    images = ROOT / "images"
    sources = ROOT / "sources"
    images.mkdir(exist_ok=True)
    sources.mkdir(exist_ok=True)
    records = []
    for ident, title, kind, split, tags in SELECTION:
        query = urllib.parse.urlencode(
            dict(
                action="query",
                format="json",
                prop="imageinfo",
                iiprop="url|extmetadata|size|sha1",
                titles="File:" + title,
            )
        )
        cached = sources / (ident + ".json")
        raw = (
            cached.read_bytes()
            if cached.exists()
            else request("https://commons.wikimedia.org/w/api.php?" + query)
        )
        data = json.loads(raw)
        page = next(iter(data["query"]["pages"].values()))
        info = page["imageinfo"][0]
        meta = info["extmetadata"]
        license_name = meta["LicenseShortName"]["value"]
        if license_name not in ALLOWED:
            raise ValueError(f"Unapproved/unclear license: {title}: {license_name}")
        url = info["url"].split("?")[0]
        target = images / (ident + ".jpg")
        if not target.exists():
            target.write_bytes(request(url))
        digest = hashlib.sha1(target.read_bytes()).hexdigest()
        if digest != info["sha1"]:
            raise ValueError(f"Commons original checksum mismatch: {ident}")
        (sources / (ident + ".json")).write_bytes(raw)
        records.append(
            dict(
                id=ident,
                image=str(target.relative_to(ROOT)).replace("\\", "/"),
                title=title,
                photo_type=kind,
                split=split,
                tags=tags,
                url=url,
                page=info["descriptionurl"],
                author=plain(meta["Artist"]["value"]),
                license=license_name,
                license_url=meta.get("LicenseUrl", {}).get(
                    "value", "https://creativecommons.org/publicdomain/mark/1.0/"
                ),
                sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
                size=[info["width"], info["height"]],
                retrieved=datetime.now(timezone.utc).isoformat(),
                transformation="Unmodified original",
            )
        )
        print(ident, license_name, info["width"], info["height"], flush=True)
        time.sleep(1)
    # A derived detail control, linked to its source group to prevent leakage claims.
    source = records[0]
    with Image.open(ROOT / source["image"]) as image:
        box = [
            round(image.width * 0.39),
            round(image.height * 0.49),
            round(image.width * 0.59),
            round(image.height * 0.92),
        ]
        image.crop(box).save(images / "wheel-detail.jpg", quality=97)
    records.append(
        source
        | dict(
            id="wheel-detail",
            image="images/wheel-detail.jpg",
            photo_type="detail",
            split="routing-control",
            tags="derived wheel detail; basic correction only",
            source_group="sedan-front",
            sha256=hashlib.sha256((images / "wheel-detail.jpg").read_bytes()).hexdigest(),
            size=list(Image.open(images / "wheel-detail.jpg").size),
            transformation=f"Cropped from sedan-front at pixel box {box}; JPEG quality 97",
        )
    )
    (ROOT / "manifest.json").write_text(
        json.dumps(dict(version=1, samples=records), indent=2), encoding="utf-8"
    )
    credits = [
        "# Benchmark image attribution\n",
        "Image licenses are separate from Apache-2.0 application code. Modified derivatives retain the source license, including CC BY-SA share-alike where applicable.\n",
    ]
    for item in records:
        credits.append(
            f"## {item['id']}\n\n{item['title']} — {item['author']}. [{item['license']}]({item['license_url']}). [Source]({item['page']}).\n\n{item['transformation']}. SHA-256: `{item['sha256']}`.\n"
        )
    (ROOT / "ATTRIBUTION.md").write_text("\n".join(credits), encoding="utf-8")
    sheet = Image.new("RGB", (1600, 1200), "#17202c")
    draw = ImageDraw.Draw(sheet)
    for i, item in enumerate(records):
        x, y = (i % 2) * 800, (i // 2) * 300
        image = ImageOps.contain(Image.open(ROOT / item["image"]).convert("RGB"), (780, 260))
        sheet.paste(image, (x + (800 - image.width) // 2, y + 30 + (260 - image.height) // 2))
        draw.text((x + 12, y + 8), f"{item['id']} | {item['photo_type']} | {item['size']}", fill="white")
    sheet.save(ROOT / "originals-contact-sheet.jpg", quality=95)


if __name__ == "__main__":
    collect()

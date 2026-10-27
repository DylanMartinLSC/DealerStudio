"""Actual model benchmark, independent coarse labels, and real project/export smoke checks."""

import argparse
from contextlib import ExitStack
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import socket
import threading
import time
from unittest.mock import patch

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageOps

from studio.model import Segmenter, SHA256
from studio.pipeline import composite, export_set
from studio.project import Project, load_image
from .reference import reference_mask

ROOT = Path(__file__).parent


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def evaluate(mask, ann, size, boundary=12):
    reference = reference_mask(ann, size)
    alpha = np.asarray(mask.resize(size, Image.Resampling.LANCZOS))
    predicted = alpha >= 128
    truth = np.asarray(reference) >= 128
    outer = np.asarray(reference.filter(ImageFilter.MaxFilter(2 * boundary + 1))) >= 128
    inner = np.asarray(reference.filter(ImageFilter.MinFilter(2 * boundary + 1))) >= 128
    valid = ~(outer ^ inner)

    def iou(region):
        intersection = np.count_nonzero(predicted & truth & region)
        union = np.count_nonzero((predicted | truth) & region)
        return intersection / max(1, union)

    probes = []
    for group in ("foreground", "background"):
        for x, y, name in ann[group]:
            value = float(np.median(alpha[max(0, y - 1) : y + 2, max(0, x - 1) : x + 2]))
            probes.append(
                dict(
                    group=group,
                    x=x,
                    y=y,
                    name=name,
                    alpha=round(value / 255, 4),
                    correct=bool(value >= 128) if group == "foreground" else bool(value < 128),
                )
            )
    fg = [p for p in probes if p["group"] == "foreground"]
    bg = [p for p in probes if p["group"] == "background"]
    return dict(
        coarse_silhouette_iou=iou(np.ones_like(truth)),
        core_region_iou=iou(valid),
        excluded_boundary_fraction=float((~valid).mean()),
        foreground_probe_recall=sum(p["correct"] for p in fg) / len(fg),
        background_probe_rejection=sum(p["correct"] for p in bg) / len(bg),
        opaque_foreground_fraction=sum(p["alpha"] >= 0.98 for p in fg) / len(fg),
        probes=probes,
    )


def verify_inputs():
    manifest = json.loads((ROOT / "manifest.json").read_text())
    freeze = json.loads((ROOT / "freeze.json").read_text())
    if digest(ROOT / "annotations.json") != freeze["annotations_sha256"]:
        raise ValueError("Frozen annotations changed. Do not silently relabel after seeing predictions.")
    if digest(ROOT / "manifest.json") != freeze["manifest_sha256"]:
        raise ValueError("Frozen dataset manifest changed")
    for sample in manifest["samples"]:
        if digest(ROOT / sample["image"]) != sample["sha256"]:
            raise ValueError(f"Source checksum mismatch: {sample['id']}")
    return manifest, freeze


def run(output, block_network=True):
    manifest, freeze = verify_inputs()
    annotations = json.loads((ROOT / "annotations.json").read_text())
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    if (output / "report.json").exists() or (output / "project" / "project.json").exists():
        raise ValueError("Use a new output folder for every benchmark run")
    project = Project(output / "project", "Vehicle-benchmark")
    errors = project.add([ROOT / item["image"] for item in manifest["samples"]])
    if errors or len(project.photos) != len(manifest["samples"]):
        raise ValueError(f"Import failed: {errors}")
    (output / "composites").mkdir(exist_ok=True)
    sheet = Image.new("RGB", (1800, 350 * len(project.photos)), "#17202c")
    draw = ImageDraw.Draw(sheet)
    results = []
    started = time.perf_counter()
    with ExitStack() as stack:
        if block_network:
            stack.enter_context(
                patch.object(socket.socket, "connect", side_effect=RuntimeError("Benchmark network blocked"))
            )
            stack.enter_context(
                patch.object(
                    socket, "create_connection", side_effect=RuntimeError("Benchmark network blocked")
                )
            )
        segmenter = Segmenter(cpu=True)
        for index, (photo, item) in enumerate(zip(project.photos, manifest["samples"], strict=True)):
            begin = time.perf_counter()
            photo["kind"] = item["photo_type"]
            image = load_image(project.root / photo["source"])
            row = dict(
                id=item["id"], split=item["split"], photo_type=photo["kind"], source_size=list(image.size)
            )
            if photo["kind"] == "exterior":
                mask = segmenter.predict(image)
                mask.save(project.root / photo["mask"])
                size = (1000, round(image.height * 1000 / image.width))
                row.update(evaluate(mask, annotations["samples"][item["id"]], size))
                row["needs_manual_review"] = (
                    row["core_region_iou"] < 0.95
                    or row["foreground_probe_recall"] < 0.95
                    or row["background_probe_rejection"] < 0.95
                )
                mask_view = mask.convert("RGB")
            else:
                assert not (project.root / photo["mask"]).exists(), "Interior/detail must bypass segmentation"
                mask_view = Image.new("RGB", (600, 300), "#263343")
                ImageDraw.Draw(mask_view).text((60, 130), "NO SEGMENTATION: routing control", fill="white")
                row["routing_bypass_verified"] = True
            result = composite(project, photo)
            result.save(output / "composites" / (item["id"] + ".png"))
            row["export_size"] = list(result.size)
            assert result.size == (2000, 1500)
            assert digest(project.root / photo["source"]) == item["sha256"], "Copied original was altered"
            row["original_preserved"] = True
            row["seconds"] = round(time.perf_counter() - begin, 3)
            photo["status"] = "review"
            project.save()
            for column, panel in enumerate((image, mask_view, result)):
                panel = ImageOps.contain(panel, (590, 310))
                x, y = column * 600, index * 350
                sheet.paste(panel, (x + (600 - panel.width) // 2, y + 30 + (310 - panel.height) // 2))
                draw.text(
                    (x + 10, y + 8),
                    f"{item['id']} | {['ORIGINAL', 'RAW MASK', 'AUTO COMPOSITE'][column]}",
                    fill="white",
                )
            results.append(row)
            print(
                item["id"], f"{row['seconds']}s", f"core IoU {row.get('core_region_iou', 'n/a')}", flush=True
            )
        exported, errors = export_set(project, output, threading.Event(), lambda *_: None, originals=True)
        if errors:
            raise RuntimeError(f"Batch export failed: {errors}")
        for file in exported.glob("*.jpg"):
            assert Image.open(file).size == (2000, 1500)
        assert len(list(exported.glob("*.jpg"))) == len(project.photos)
        reopened = Project.open(project.root)
        assert [p["name"] for p in reopened.photos] == [p["name"] for p in project.photos]
    evaluation = [r for r in results if r["split"] == "evaluation"]
    metrics = [
        "coarse_silhouette_iou",
        "core_region_iou",
        "foreground_probe_recall",
        "background_probe_rejection",
        "opaque_foreground_fraction",
    ]
    report = dict(
        version=1,
        utc=datetime.now(timezone.utc).isoformat(),
        platform=platform.platform(),
        python=platform.python_version(),
        model_sha256=SHA256,
        annotation_freeze=freeze,
        providers=segmenter.session.get_providers(),
        seconds=round(time.perf_counter() - started, 3),
        network="Python socket connects blocked" if block_network else "not blocked by runner",
        network_interfaces=socket.if_nameindex() if hasattr(socket, "if_nameindex") else [],
        aggregate_evaluation={key: sum(r[key] for r in evaluation) / len(evaluation) for key in metrics},
        evaluation_images=len(evaluation),
        evaluation_review_flags=sum(r["needs_manual_review"] for r in evaluation),
        exported_count=len(project.photos),
        export_path=str(exported),
        results=results,
    )
    (output / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    sheet.save(output / "contact-sheet.jpg", quality=95)
    lines = [
        "# Vehicle benchmark results\n",
        "Small single-annotator challenge set. Coarse masks exclude a 12px boundary band for core metrics; these are not pixel-accurate matting scores. Known-development sample is excluded from evaluation averages.\n",
        "| Sample | Core IoU | FG probes | BG probes | Manual review trigger |\n|---|---:|---:|---:|---|",
    ]
    for row in results:
        if row["photo_type"] == "exterior":
            lines.append(
                f"| {row['id']} ({row['split']}) | {row['core_region_iou']:.3f} | {row['foreground_probe_recall']:.1%} | {row['background_probe_rejection']:.1%} | {row['needs_manual_review']} |"
            )
        else:
            lines.append(f"| {row['id']} | segmentation bypass | — | — | visual review |")
    lines.append(
        "\nAutomatic review trigger: core IoU, FG probe recall or BG probe rejection < 0.95. These are project-selected diagnostic thresholds, not a certification or guarantee. All outputs require human review regardless of score.\n"
    )
    (output / "RESULTS.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps(report["aggregate_evaluation"], indent=2))
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output", type=Path, default=ROOT / "results" / datetime.now().strftime("run-%Y%m%d-%H%M%S")
    )
    parser.add_argument(
        "--enforce", action="store_true", help="Exit 2 when any evaluation sample crosses a review threshold"
    )
    args = parser.parse_args()
    report = run(args.output)
    if args.enforce and report["evaluation_review_flags"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()

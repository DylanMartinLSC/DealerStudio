import numpy as np
from PIL import Image

from benchmark.run import evaluate, verify_inputs
from benchmark.reference import reference_mask


def test_metrics_distinguish_vehicle_loss_from_background_retention():
    ann = dict(
        polygon=[[4, 4], [15, 4], [15, 15], [4, 15]],
        foreground=[[8, 8, "vehicle"]],
        background=[[1, 1, "scene"]],
    )
    truth = reference_mask(ann, (20, 20))
    perfect = evaluate(truth, ann, (20, 20), boundary=1)
    assert perfect["core_region_iou"] == 1
    assert perfect["foreground_probe_recall"] == 1
    assert perfect["background_probe_rejection"] == 1
    missing = evaluate(Image.new("L", (20, 20)), ann, (20, 20), boundary=1)
    assert missing["core_region_iou"] == 0
    assert missing["foreground_probe_recall"] == 0
    assert missing["background_probe_rejection"] == 1
    retained = evaluate(Image.new("L", (20, 20), 255), ann, (20, 20), boundary=1)
    assert retained["foreground_probe_recall"] == 1
    assert retained["background_probe_rejection"] == 0
    assert retained["core_region_iou"] < 1


def test_frozen_dataset_integrity_and_annotation_coordinates():
    from benchmark.run import ROOT
    import json

    manifest, freeze = verify_inputs()
    annotations = json.loads((ROOT / "annotations.json").read_text())
    assert len(manifest["samples"]) == 8
    assert len([s for s in manifest["samples"] if s["split"] == "evaluation"]) == 5
    assert len(freeze["annotations_sha256"]) == 64
    for sample in manifest["samples"]:
        if sample["photo_type"] != "exterior":
            continue
        ann = annotations["samples"][sample["id"]]
        width, height = 1000, round(sample["size"][1] * 1000 / sample["size"][0])
        for points in (ann["foreground"], ann["background"]):
            assert len(points) >= 10
            assert all(0 <= x < width and 0 <= y < height for x, y, _ in points)
        assert np.asarray(reference_mask(ann, (width, height))).max() == 255

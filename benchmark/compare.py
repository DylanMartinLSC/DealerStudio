"""Compare two complete actual runs without comparing timestamped filenames."""

import argparse
import json
from pathlib import Path
import numpy as np
from PIL import Image


def compare(first, second):
    rows = []
    projects = [json.loads((root / "project" / "project.json").read_text()) for root in (first, second)]
    for left, right in zip(projects[0]["photos"], projects[1]["photos"], strict=True):
        assert left["name"] == right["name"] and left["kind"] == right["kind"]
        if left["kind"] != "exterior":
            continue
        a, b = [
            np.asarray(Image.open(root / "project" / photo["mask"]), dtype=np.int16)
            for root, photo in ((first, left), (second, right))
        ]
        delta = np.abs(a - b)
        rows.append(
            dict(
                id=Path(left["name"]).stem,
                max_alpha_delta=int(delta.max()),
                mean_alpha_delta=float(delta.mean()),
                threshold_disagreement_fraction=float(((a >= 128) != (b >= 128)).mean()),
            )
        )
    return dict(
        first=str(first),
        second=str(second),
        mask_comparisons=rows,
        aggregate_metrics_equal=json.loads((first / "report.json").read_text())["aggregate_evaluation"]
        == json.loads((second / "report.json").read_text())["aggregate_evaluation"],
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("first", type=Path)
    parser.add_argument("second", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    report = compare(args.first, args.second)
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))

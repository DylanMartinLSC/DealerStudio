r"""Real CPU inference + export with Python networking blocked after setup.

Run from root: .venv\Scripts\python.exe -m verification.run_real
"""

import json
from pathlib import Path
import socket
import threading
import time
from unittest.mock import patch

from PIL import Image

from studio.model import Segmenter
from studio.pipeline import brush, composite, export_set
from studio.project import Project, load_image


def main():
    base = Path(__file__).parent
    project_root = base / "output" / "camry"
    project = (
        Project.open(project_root)
        if (project_root / "project.json").exists()
        else Project(project_root, "Camry-CPU-offline")
    )
    if not project.photos:
        project.add([base / "camry.jpg"])
    photo = project.photos[0]
    photo["plates"], photo["contacts"] = [], []
    start = time.perf_counter()
    with (
        patch.object(socket.socket, "connect", side_effect=RuntimeError("Network blocked")),
        patch.object(socket, "create_connection", side_effect=RuntimeError("Network blocked")),
    ):
        model = Segmenter(cpu=True)
        mask = model.predict(load_image(project.root / photo["source"]))
        mask.save(project.root / photo["mask"])
        photo["status"] = "review"
        # An actual manual correction, deliberately restricted to the known background corner.
        brush(mask, (5, 5), (30, 5), 4, False)
        mask.save(project.root / photo["mask"])
        project.save()
        root, errors = export_set(project, base / "output", threading.Event(), lambda *_: None)
        composite(project, photo).save(base / "output" / "result.png")
        photo["plates"] = [[0.074, 0.635, 0.134, 0.753]]
        photo["contacts"] = [[0.492, 0.90], [0.915, 0.668]]
        photo["adjustments"]["plate_mode"] = "solid"
        project.save()
        composite(project, photo).save(base / "output" / "reviewed.png")
    report = dict(
        seconds=round(time.perf_counter() - start, 2),
        providers=model.session.get_providers(),
        source_size=load_image(base / "camry.jpg").size,
        mask_size=mask.size,
        export_size=Image.open(next(root.glob("*.jpg"))).size,
        errors=errors,
        network="Python socket connect/create_connection blocked throughout session load, inference and export",
    )
    (base / "real-report.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()

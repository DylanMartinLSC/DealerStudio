"""Explicit packaged smoke check; uses real inference, never a mock result."""

import json
from pathlib import Path
import threading
import time

from PIL import Image
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from .app import Window, configure_app
from .model import Segmenter
from .pipeline import export_set
from .project import Project, load_image


def verify(source, destination):
    root = Path(destination)
    root.mkdir(parents=True, exist_ok=True)
    try:
        started = time.perf_counter()
        project = Project(root / "project", "Package-check")
        errors = project.add([source])
        if errors or not project.photos:
            raise ValueError(str(errors or "No supported source image"))
        photo = project.photos[0]
        segmenter = Segmenter(cpu=True)
        segmenter.predict(load_image(project.root / photo["source"])).save(project.root / photo["mask"])
        photo["status"] = "review"
        project.save()
        exported, errors = export_set(project, root, threading.Event(), lambda *_: None)
        if errors:
            raise RuntimeError(str(errors))
        app = QApplication.instance() or QApplication([])
        configure_app(app)
        window = Window()
        window.project = project
        window.refresh()
        window.show()

        def capture():
            window.grab().save(str(root / "packaged-ui.png"))
            window.close()
            app.quit()

        QTimer.singleShot(350, capture)
        app.exec()
        report = dict(
            ok=True,
            seconds=round(time.perf_counter() - started, 2),
            providers=segmenter.session.get_providers(),
            dimensions=Image.open(next(exported.glob("*.jpg"))).size,
            export=str(exported),
        )
    except Exception as exc:
        report = dict(ok=False, error=str(exc))
    (root / "package-report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return 0 if report["ok"] else 1

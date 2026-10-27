import os

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PIL import Image
from PySide6.QtWidgets import QApplication
from studio.app import Window, Worker
from studio.project import Project


def test_ui_settings_mask_and_reorder(tmp_path):
    app = QApplication.instance() or QApplication([])
    window = Window()
    window.project = Project(tmp_path / "project")
    for name in ("one", "two"):
        path = tmp_path / f"{name}.png"
        Image.new("RGB", (100, 80), "red").save(path)
        window.project.add([path])
    window.refresh()
    window.manual_mask()
    assert window.canvas.mask is not None
    window.controls["width"].setValue(1600)
    assert window.current()["adjustments"]["width"] == 1600
    window.reorder(1)
    assert window.project.photos[1]["name"] == "one.png"
    window.grab().save(str(tmp_path / "ui.png"))
    app.processEvents()
    window.close()


def test_worker_cancel_before_model_load(tmp_path):
    app = QApplication.instance() or QApplication([])
    project = Project(tmp_path / "project")
    path = tmp_path / "one.png"
    Image.new("RGB", (100, 80), "red").save(path)
    project.add([path])
    worker = Worker("process", project)
    worker.cancel.set()
    results = []
    worker.complete.connect(results.append)
    worker.run()
    assert "cancelled" in results[0]
    assert project.photos[0]["status"] == "pending"
    app.processEvents()


def test_worker_cancel_between_photos_keeps_first_mask(tmp_path, monkeypatch):
    from studio import model

    project = Project(tmp_path / "project")
    path = tmp_path / "one.png"
    Image.new("RGB", (100, 80), "red").save(path)
    project.add([path, path])

    class FixtureSegmenter:
        def predict(self, image):
            return Image.new("L", image.size, 255)

    monkeypatch.setattr(model, "Segmenter", FixtureSegmenter)
    worker = Worker("process", project)
    worker.progress.connect(lambda *_: worker.cancel.set())
    worker.run()
    assert (project.root / project.photos[0]["mask"]).exists()
    assert not (project.root / project.photos[1]["mask"]).exists()
    assert Project.open(project.root).photos[0]["status"] == "review"


def test_worker_isolates_per_photo_failure(tmp_path, monkeypatch):
    from studio import model

    project = Project(tmp_path / "project")
    path = tmp_path / "one.png"
    Image.new("RGB", (100, 80), "red").save(path)
    project.add([path, path])

    class FixtureSegmenter:
        count = 0

        def predict(self, image):
            self.count += 1
            if self.count == 1:
                raise RuntimeError("Fixture error")
            return Image.new("L", image.size, 255)

    monkeypatch.setattr(model, "Segmenter", FixtureSegmenter)
    Worker("process", project).run()
    assert [p["status"] for p in project.photos] == ["error", "review"]
    assert project.photos[0]["error"] == "Fixture error"

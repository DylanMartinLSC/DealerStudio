import hashlib
import json
import threading

import pytest
from PIL import Image

from studio.pipeline import brush, composite, export_set, plate_treatment
from studio.project import Project


@pytest.fixture
def job(tmp_path):
    source = tmp_path / "input.png"
    Image.new("RGB", (320, 240), (120, 140, 160)).save(source)
    project = Project(tmp_path / "project", "Stock / 42")
    assert not project.add([source])
    photo = project.photos[0]
    mask = Image.new("L", (320, 240))
    brush(mask, (60, 150), (260, 150), 35, True)
    mask.save(project.root / photo["mask"])
    project.settings.update(width=640, height=480)
    project.save()
    return project, photo, source


def test_project_roundtrip_and_original_copy(job):
    project, photo, source = job
    photo["plates"] = [[0.1, 0.2, 0.3, 0.4]]
    photo["adjustments"]["floor"] = 0.75
    project.save()
    source.unlink()
    restored = Project.open(project.root)
    assert restored.photos == project.photos
    assert restored.settings == project.settings
    assert (restored.root / photo["source"]).exists()


def test_brush_add_remove_persist(job):
    project, photo, _ = job
    mask = Image.open(project.root / photo["mask"]).convert("L")
    brush(mask, (160, 150), (180, 150), 10, False)
    assert mask.getpixel((170, 150)) == 0
    brush(mask, (170, 150), (170, 150), 3, True)
    mask.save(project.root / photo["mask"])
    assert Image.open(project.root / photo["mask"]).getpixel((170, 150)) == 255


@pytest.mark.parametrize("format,extension", [("JPEG", "jpg"), ("PNG", "png")])
def test_export_dimensions_names_and_no_overwrite(job, tmp_path, format, extension):
    project, photo, source = job
    project.settings["format"] = format
    original_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    first, errors = export_set(project, tmp_path, threading.Event(), lambda *_: None, True)
    second, _ = export_set(project, tmp_path, threading.Event(), lambda *_: None)
    assert not errors and first != second
    output = first / f"Stock-42-001-exterior.{extension}"
    assert Image.open(output).size == (640, 480)
    assert hashlib.sha256(source.read_bytes()).hexdigest() == original_hash
    assert len(list((first / "originals").iterdir())) == 1


def test_cancel_exports_and_partial_failure(job, tmp_path):
    project, photo, _ = job
    event = threading.Event()
    event.set()
    root, _ = export_set(project, tmp_path, event, lambda *_: None)
    assert not list(root.glob("*.jpg"))
    event.clear()
    (project.root / photo["mask"]).unlink()
    root, errors = export_set(project, tmp_path, event, lambda *_: None)
    assert "No mask" in errors[0]
    assert (root / "export-report.txt").exists()


def test_interior_bypasses_model_and_mask(job):
    project, photo, _ = job
    (project.root / photo["mask"]).unlink()
    photo["kind"] = "interior"
    assert composite(project, photo).size == (640, 480)


def test_no_condition_or_color_edit_at_default(job):
    project, photo, _ = job
    result = composite(project, photo)
    assert result.getpixel((320, 350)) == (120, 140, 160)


def test_plate_rect_and_graphic(job, tmp_path):
    image = Image.new("RGB", (100, 100), "white")
    out = plate_treatment(image, [[0.2, 0.2, 0.5, 0.4]], "solid")
    assert out.getpixel((30, 30)) == (37, 42, 51)
    assert out.getpixel((0, 0)) == (255, 255, 255)
    assert image.getpixel((30, 30)) == (255, 255, 255)


def test_path_traversal_rejected(job):
    project, _, _ = job
    path = project.root / "project.json"
    data = json.loads(path.read_text())
    data["photos"][0]["source"] = "../outside.jpg"
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="inside"):
        Project.open(project.root)


def test_invalid_dimensions_and_empty_mask(job):
    project, photo, _ = job
    project.settings["width"] = 0
    with pytest.raises(ValueError, match="dimensions"):
        composite(project, photo)
    project.settings["width"] = 640
    Image.new("L", (320, 240)).save(project.root / photo["mask"])
    with pytest.raises(ValueError, match="empty"):
        composite(project, photo)


def test_branding_assets_and_shared_adjustments_persist(job, tmp_path):
    project, photo, _ = job
    logo = tmp_path / "logo.png"
    Image.new("RGBA", (80, 40), (250, 20, 30, 255)).save(logo)
    project.asset(logo, "logo")
    logo.unlink()
    photo["adjustments"].update(corner="top-left", padding=0, logo_size=0.15)
    project.save()
    reopened = Project.open(project.root)
    result = composite(reopened, reopened.photos[0])
    assert result.getpixel((5, 5)) == (250, 20, 30)
    photo["contacts"] = [[0.7, 0.7]]
    assert composite(project, photo).size == (640, 480)

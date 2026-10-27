import copy
import sys
import threading
from pathlib import Path

from PIL import Image
from PySide6.QtCore import Qt, QThread, Signal, QRectF, QTimer, QSize
from PySide6.QtGui import QColor, QIcon, QPainter, QPen, QPixmap, QImage
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from . import model
from .pipeline import brush, composite, export_set
from .project import Project, load_image


class Worker(QThread):
    status = Signal(str)
    progress = Signal(int, int)
    complete = Signal(object)

    def __init__(self, action, project=None, destination=None, originals=False):
        super().__init__()
        self.action, self.project = action, project
        self.destination, self.originals = destination, originals
        self.cancel = threading.Event()

    def run(self):
        try:
            if self.action == "model":
                model.install(lambda n: self.progress.emit(n, 100))
                result = "Model installed and SHA-256 verified. Processing is now offline."
            elif self.action == "export":
                root, errors = export_set(
                    self.project, self.destination, self.cancel, self.progress.emit, self.originals
                )
                result = f"Export: {root}\n" + "\n".join(errors)
            else:
                segmenter = None
                for index, photo in enumerate(self.project.photos):
                    if self.cancel.is_set():
                        break
                    self.status.emit(f"{index + 1}/{len(self.project.photos)} · {photo['name']}")
                    try:
                        if photo["kind"] == "exterior" and not (self.project.root / photo["mask"]).exists():
                            if segmenter is None:
                                segmenter = model.Segmenter()
                            mask = segmenter.predict(load_image(self.project.root / photo["source"]))
                            if self.cancel.is_set():
                                break
                            mask.save(self.project.root / photo["mask"])
                        photo["status"], photo["error"] = "review", ""
                    except Exception as exc:
                        photo["status"], photo["error"] = "error", str(exc)
                    self.project.save()
                    self.progress.emit(index + 1, len(self.project.photos))
                self.project.save()
                result = (
                    "Queue cancelled. Completed masks kept."
                    if self.cancel.is_set()
                    else "Processing finished. Inspect masks, glass, wheel gaps and floor contact before export."
                )
            self.complete.emit(result)
        except Exception as exc:
            self.complete.emit(f"Failed: {exc}")


class Canvas(QWidget):
    edited = Signal()
    plate = Signal(object)
    contact = Signal(object)

    def __init__(self):
        super().__init__()
        self.setMinimumSize(300, 260)
        self.image = None
        self.mask = None
        self.mode = "Result"
        self.tool = "Foreground"
        self.radius = 18
        self.last = None
        self.begin = None
        self.undo = []
        self.rect = QRectF()

    def set_image(self, image, mask=None):
        self.image, self.mask = image, mask
        self.undo.clear()
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        p.fillRect(self.rect if self.rect.isValid() else self.rect, QColor("#111720"))
        if self.image is None:
            p.setPen(QColor("#94a3b8"))
            p.drawText(
                self.rect.adjusted(0, 0, self.width(), self.height()),
                Qt.AlignmentFlag.AlignCenter,
                "Import vehicle photos to begin",
            )
            return
        image = self.image
        if self.mode == "Mask" and self.mask:
            image = self.image.convert("RGBA")
            tint = Image.new("RGBA", image.size, (235, 68, 87, 0))
            tint.putalpha(self.mask.point(lambda v: int((255 - v) * 0.52)))
            image = Image.alpha_composite(image, tint)
        rgba = image.convert("RGBA")
        qimage = QImage(
            rgba.tobytes(), rgba.width, rgba.height, rgba.width * 4, QImage.Format.Format_RGBA8888
        ).copy()
        pixmap = QPixmap.fromImage(qimage)
        scale = min(self.width() / image.width, self.height() / image.height)
        self.rect = QRectF(
            (self.width() - image.width * scale) / 2,
            (self.height() - image.height * scale) / 2,
            image.width * scale,
            image.height * scale,
        )
        p.drawPixmap(self.rect, pixmap, QRectF(pixmap.rect()))
        if self.begin and self.last and self.tool == "Plate rectangle":
            p.setPen(QPen(QColor("#65d8c5"), 2))
            x0, y0 = self.begin
            x1, y1 = self.last
            p.drawRect(
                QRectF(
                    self.rect.x() + x0 * scale,
                    self.rect.y() + y0 * scale,
                    (x1 - x0) * scale,
                    (y1 - y0) * scale,
                ).normalized()
            )

    def point(self, event):
        if self.image is None or not self.rect.contains(event.position()):
            return None
        return (
            int((event.position().x() - self.rect.x()) * self.image.width / self.rect.width()),
            int((event.position().y() - self.rect.y()) * self.image.height / self.rect.height()),
        )

    def mousePressEvent(self, event):
        if self.mode != "Mask":
            return
        point = self.point(event)
        if point and self.mask:
            if self.tool == "Tire contact":
                self.contact.emit([point[0] / self.image.width, point[1] / self.image.height])
                return
            self.undo.append(self.mask.copy())
            self.undo = self.undo[-4:]
            self.last = self.begin = point
            if self.tool != "Plate rectangle":
                brush(self.mask, point, point, self.radius, self.tool == "Foreground")
            self.update()

    def mouseMoveEvent(self, event):
        point = self.point(event)
        if point and self.last:
            if self.tool != "Plate rectangle":
                brush(self.mask, self.last, point, self.radius, self.tool == "Foreground")
            self.last = point
            self.update()

    def mouseReleaseEvent(self, event):
        if self.last:
            if self.tool == "Plate rectangle":
                x0, y0 = self.begin
                x1, y1 = self.last
                self.plate.emit(
                    [
                        min(x0, x1) / self.image.width,
                        min(y0, y1) / self.image.height,
                        max(x0, x1) / self.image.width,
                        max(y0, y1) / self.image.height,
                    ]
                )
            else:
                self.edited.emit()
        self.last = self.begin = None
        self.update()


class Window(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("DealerStudio · Local vehicle photography")
        self.resize(1480, 920)
        self.project = None
        self.worker = None
        self.loading = False
        self.setAcceptDrops(True)
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.render)
        container = QWidget()
        self.setCentralWidget(container)
        layout = QVBoxLayout(container)
        header = QHBoxLayout()
        title = QLabel("DEALERSTUDIO")
        title.setStyleSheet("font-size:22px; font-weight:700; color:#72dbc8")
        header.addWidget(title)
        header.addWidget(QLabel("  LOCAL PHOTO WORKSPACE"))
        header.addStretch()
        self.model_button = self.button("Model setup · 176 MB", self.setup_model, header)
        layout.addLayout(header)
        self.split = QSplitter()
        layout.addWidget(self.split, 1)
        left = QWidget()
        left.setMinimumWidth(330)
        sidebar = QVBoxLayout(left)
        sidebar.addWidget(QLabel("VEHICLE PROJECT"))
        self.name = QLineEdit("New vehicle")
        self.name.editingFinished.connect(self.save_name)
        sidebar.addWidget(self.name)
        row = QHBoxLayout()
        self.button("New", self.new_project, row)
        self.button("Open", self.open_project, row)
        sidebar.addLayout(row)
        self.button("Import photos…", self.import_files, sidebar)
        self.button("Import folder…", self.import_folder, sidebar)
        self.photos = QListWidget()
        self.photos.setViewMode(QListWidget.ViewMode.IconMode)
        self.photos.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.photos.setMovement(QListWidget.Movement.Static)
        self.photos.setGridSize(QSize(148, 145))
        self.photos.setWordWrap(True)
        self.photos.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        self.photos.setIconSize(QSize(128, 88))
        self.photos.currentRowChanged.connect(self.select)
        sidebar.addWidget(self.photos, 1)
        row = QHBoxLayout()
        self.button("↑", lambda: self.reorder(-1), row)
        self.button("↓", lambda: self.reorder(1), row)
        sidebar.addLayout(row)
        self.split.addWidget(left)
        center = QWidget()
        middle = QVBoxLayout(center)
        bar = QHBoxLayout()
        self.view = QComboBox()
        self.view.addItems(["Result", "Original", "Comparison", "Mask"])
        self.view.currentTextChanged.connect(self.render)
        bar.addWidget(self.view)
        self.kind = QComboBox()
        self.kind.addItems(["exterior", "interior", "detail"])
        self.kind.currentTextChanged.connect(self.change_kind)
        bar.addWidget(self.kind)
        bar.addStretch()
        middle.addLayout(bar)
        self.canvas = Canvas()
        self.canvas.edited.connect(self.mask_edited)
        self.canvas.plate.connect(self.add_plate)
        self.canvas.contact.connect(self.add_contact)
        self.canvas_scroll = QScrollArea()
        self.canvas_scroll.setWidgetResizable(True)
        self.canvas_scroll.setWidget(self.canvas)
        middle.addWidget(self.canvas_scroll, 1)
        zoom = QHBoxLayout()
        self.button("Fit preview", lambda: self.canvas.setMinimumSize(300, 260), zoom)
        self.button("100% inspection", self.native_zoom, zoom)
        middle.addLayout(zoom)
        tools = QHBoxLayout()
        self.tool = QComboBox()
        self.tool.addItems(["Foreground", "Background", "Plate rectangle", "Tire contact"])
        self.tool.currentTextChanged.connect(lambda text: setattr(self.canvas, "tool", text))
        tools.addWidget(self.tool)
        self.brush = QSpinBox()
        self.brush.setRange(1, 250)
        self.brush.setValue(18)
        self.brush.setSuffix(" px brush")
        self.brush.valueChanged.connect(lambda n: setattr(self.canvas, "radius", n))
        tools.addWidget(self.brush)
        self.button("Undo brush", self.undo_brush, tools)
        middle.addLayout(tools)
        mask_actions = QHBoxLayout()
        self.button("Manual mask", self.manual_mask, mask_actions)
        self.button("Clear plates", self.clear_plates, mask_actions)
        self.button("Clear contacts", self.clear_contacts, mask_actions)
        middle.addLayout(mask_actions)
        caution = QLabel(
            "Review every exterior mask. Glass and hidden details are not reconstructed.\n"
            "Set floor contact manually; no vehicle parts, paint or condition details are generated."
        )
        caution.setWordWrap(True)
        caution.setStyleSheet("color:#a5b1c3; padding:8px")
        middle.addWidget(caution)
        self.split.addWidget(center)
        scroll = QScrollArea()
        scroll.setMinimumWidth(340)
        scroll.setWidgetResizable(True)
        settings = QWidget()
        form = QFormLayout(settings)
        self.controls = {}
        self.combo(form, "background", "Studio", ["light", "dark", "branded", "custom"])
        self.button("Import background…", lambda: self.asset("custom_background"), form)
        for key, label, lo, hi, step in [
            ("scale", "Vehicle width", 0.2, 0.98, 0.01),
            ("x", "Horizontal center", 0, 1, 0.01),
            ("floor", "Floor contact", 0.2, 0.99, 0.01),
            ("shadow", "Contact shadow", 0, 0.6, 0.02),
            ("feather", "Edge feather (px)", 0, 5, 0.1),
            ("decontaminate", "Edge trim (px)", 0, 3, 1),
            ("exposure", "Exposure multiplier", 0.8, 1.2, 0.01),
        ]:
            self.number(form, key, label, lo, hi, step)
        self.combo(form, "plate_mode", "Plate treatment", ["blur", "solid", "graphic"])
        self.button("Import plate graphic…", lambda: self.asset("plate_graphic"), form)
        self.button("Import logo…", lambda: self.asset("logo"), form)
        self.button("Remove logo", self.remove_logo, form)
        self.number(form, "logo_size", "Logo width", 0.03, 0.4, 0.01)
        self.number(form, "padding", "Logo padding", 0, 0.15, 0.005)
        self.combo(form, "corner", "Logo placement", ["bottom-right", "bottom-left", "top-right", "top-left"])
        self.number(form, "width", "Export width (px)", 64, 10000, 1)
        self.number(form, "height", "Export height (px)", 64, 10000, 1)
        self.combo(form, "format", "File format", ["JPEG", "PNG"])
        self.number(form, "quality", "JPEG quality", 40, 100, 1)
        self.originals = QCheckBox("Include separate originals")
        form.addRow(self.originals)
        self.button("Copy framing to selected", self.copy_adjustments, form)
        self.button("Use set defaults for photo", self.reset_adjustments, form)
        self.button("Save settings preset…", self.save_preset, form)
        self.button("Load settings preset…", self.load_preset, form)
        hint = QLabel(
            "Settings are saved per photo. Copy to selected photos for a consistent set.\nPlate rectangles are drawn in Mask view, on original coordinates."
        )
        hint.setWordWrap(True)
        form.addRow(hint)
        scroll.setWidget(settings)
        self.split.addWidget(scroll)
        self.split.setSizes([330, 780, 340])
        bottom = QHBoxLayout()
        self.run_button = self.button("Process vehicle set", self.process, bottom)
        self.export_button = self.button("Export set…", self.export, bottom)
        self.cancel_button = self.button("Cancel queue", self.cancel, bottom)
        self.progress = QProgressBar()
        bottom.addWidget(self.progress, 1)
        layout.addLayout(bottom)
        self.message = QLabel("Create or open a project. Sources are copied and never overwritten.")
        self.message.setWordWrap(True)
        layout.addWidget(self.message)

    def button(self, text, callback, layout):
        button = QPushButton(text)
        button.clicked.connect(callback)
        if isinstance(layout, QFormLayout):
            layout.addRow(button)
        else:
            layout.addWidget(button)
        return button

    def combo(self, form, key, label, values):
        control = QComboBox()
        control.addItems(values)
        control.currentTextChanged.connect(self.settings_changed)
        self.controls[key] = control
        form.addRow(label, control)

    def number(self, form, key, label, lo, hi, step):
        control = QSpinBox() if step == 1 else QDoubleSpinBox()
        control.setRange(lo, hi)
        control.setSingleStep(step)
        control.valueChanged.connect(self.settings_changed)
        self.controls[key] = control
        form.addRow(label, control)

    def current(self):
        row = self.photos.currentRow()
        return self.project.photos[row] if self.project and 0 <= row < len(self.project.photos) else None

    def busy(self):
        return self.worker is not None and self.worker.isRunning()

    def new_project(self):
        if self.busy():
            return
        parent = QFileDialog.getExistingDirectory(self, "Choose parent for new project")
        if parent:
            import uuid

            self.project = Project(Path(parent) / ("vehicle-" + uuid.uuid4().hex[:8]))
            self.project.save()
            self.refresh()

    def open_project(self):
        if self.busy():
            return
        path = QFileDialog.getExistingDirectory(self, "Open project folder containing project.json")
        if path:
            try:
                self.project = Project.open(path)
                self.refresh()
            except Exception as exc:
                self.message.setText(str(exc))

    def save_name(self):
        if self.project and not self.busy():
            self.project.name = self.name.text()
            self.project.save()

    def import_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "Import vehicle photos", filter="Images (*.jpg *.jpeg *.png *.webp *.bmp *.tif *.tiff)"
        )
        self.add(files)

    def import_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Import photo folder")
        if folder:
            self.add(sorted(Path(folder).iterdir()))

    def add(self, paths):
        if not self.project:
            self.message.setText("Create a project first, then import photos.")
            return
        if self.busy():
            return
        errors = self.project.add(paths)
        self.refresh()
        self.message.setText(
            "\n".join(errors) or f"{len(self.project.photos)} photos · correct their types before processing"
        )

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        paths = []
        for url in event.mimeData().urls():
            path = Path(url.toLocalFile())
            paths.extend(sorted(path.iterdir()) if path.is_dir() else [path])
        self.add(paths)

    def refresh(self):
        old = self.photos.currentRow()
        self.photos.blockSignals(True)
        self.photos.clear()
        if self.project:
            self.name.setText(self.project.name)
            for index, photo in enumerate(self.project.photos):
                item = QListWidgetItem(
                    f"{index + 1:02d}  {photo['name']}\n{photo['kind']} · {photo['status']}"
                )
                icon = QPixmap(str(self.project.root / photo["source"]))
                item.setIcon(
                    QIcon(
                        icon.scaled(
                            128,
                            88,
                            Qt.AspectRatioMode.KeepAspectRatio,
                            Qt.TransformationMode.SmoothTransformation,
                        )
                    )
                )
                item.setToolTip(photo["error"] or "Ready for review")
                self.photos.addItem(item)
        self.photos.blockSignals(False)
        self.photos.setCurrentRow(max(0, min(old, self.photos.count() - 1)))
        self.select()

    def select(self, *_):
        photo = self.current()
        if not photo:
            return
        self.loading = True
        self.kind.setCurrentText(photo["kind"])
        for key, control in self.controls.items():
            value = self.project.options(photo)[key]
            if isinstance(control, QComboBox):
                control.setCurrentText(value)
            else:
                control.setValue(int(value) if isinstance(control, QSpinBox) else value)
        self.loading = False
        self.render()

    def settings_changed(self, *_):
        if self.loading or self.busy() or not self.current():
            return
        s = self.current()["adjustments"]
        for key, control in self.controls.items():
            s[key] = control.currentText() if isinstance(control, QComboBox) else control.value()
        self.project.save()
        self.timer.start(180)

    def render(self, *_):
        photo = self.current()
        if not photo:
            return
        try:
            mode = self.view.currentText()
            self.canvas.mode = mode
            if mode in ("Result", "Comparison"):
                image, mask = composite(self.project, photo, preview=True), None
                if mode == "Comparison":
                    from PIL import ImageOps

                    original = ImageOps.pad(
                        load_image(self.project.root / photo["source"]), image.size, color="#121b26"
                    )
                    pair = Image.new("RGB", (image.width * 2, image.height))
                    pair.paste(original, (0, 0))
                    pair.paste(image, (image.width, 0))
                    image = pair
            else:
                image = load_image(self.project.root / photo["source"])
                path = self.project.root / photo["mask"]
                mask = Image.open(path).convert("L") if path.exists() else Image.new("L", image.size, 255)
            self.canvas.set_image(image, mask)
            self.message.setText(photo["error"] or f"{photo['name']} · {photo['kind']} · {photo['status']}")
        except Exception as exc:
            self.canvas.mode = "Original"
            try:
                self.canvas.set_image(load_image(self.project.root / photo["source"]))
            except Exception:
                self.canvas.set_image(None)
            self.message.setText(str(exc))

    def change_kind(self, text):
        if self.current() and not self.loading and not self.busy():
            self.current()["kind"] = text
            self.project.save()
            self.refresh()

    def reorder(self, direction):
        if self.busy() or not self.current():
            return
        a = self.photos.currentRow()
        b = a + direction
        if 0 <= b < len(self.project.photos):
            self.project.photos[a], self.project.photos[b] = self.project.photos[b], self.project.photos[a]
            self.project.save()
            self.refresh()
            self.photos.setCurrentRow(b)

    def mask_edited(self):
        if self.current() and self.canvas.mask and not self.busy():
            self.canvas.mask.save(self.project.root / self.current()["mask"])
            self.current()["status"] = "review"
            self.project.save()

    def undo_brush(self):
        if self.canvas.undo and not self.busy():
            self.canvas.mask = self.canvas.undo.pop()
            self.mask_edited()
            self.canvas.update()

    def manual_mask(self):
        if self.current() and not self.busy():
            photo = self.current()
            image = load_image(self.project.root / photo["source"])
            if not (self.project.root / photo["mask"]).exists():
                Image.new("L", image.size, 0).save(self.project.root / photo["mask"])
            self.view.setCurrentText("Mask")
            self.render()

    def add_plate(self, rect):
        if self.current() and not self.busy():
            self.current()["plates"].append(rect)
            self.project.save()

    def clear_plates(self):
        if self.current() and not self.busy():
            self.current()["plates"] = []
            self.project.save()
            self.render()

    def add_contact(self, point):
        if self.current() and not self.busy():
            self.current().setdefault("contacts", []).append(point)
            self.project.save()

    def clear_contacts(self):
        if self.current() and not self.busy():
            self.current()["contacts"] = []
            self.project.save()
            self.render()

    def native_zoom(self):
        if self.current() and self.view.currentText() == "Result":
            try:
                self.canvas.set_image(composite(self.project, self.current()))
            except Exception as exc:
                self.message.setText(str(exc))
        if self.canvas.image:
            self.canvas.setMinimumSize(*self.canvas.image.size)

    def save_preset(self):
        if not self.current() or self.busy():
            return
        import json

        path, _ = QFileDialog.getSaveFileName(self, "Save reusable settings", filter="Preset (*.json)")
        if path:
            settings = {key: self.project.options(self.current())[key] for key in self.controls}
            Path(path).write_text(json.dumps(settings, indent=2), encoding="utf-8")

    def load_preset(self):
        if not self.current() or self.busy():
            return
        import json

        path, _ = QFileDialog.getOpenFileName(self, "Load reusable settings", filter="Preset (*.json)")
        if path:
            try:
                values = json.loads(Path(path).read_text(encoding="utf-8"))
                for key, control in self.controls.items():
                    value = values.get(key)
                    if isinstance(control, QComboBox) and value in [
                        control.itemText(i) for i in range(control.count())
                    ]:
                        control.setCurrentText(value)
                    elif isinstance(value, (float, int)) and not isinstance(control, QComboBox):
                        control.setValue(int(value) if isinstance(control, QSpinBox) else value)
                self.settings_changed()
            except Exception as exc:
                self.message.setText(f"Invalid preset: {exc}")

    def asset(self, key):
        if not self.project or self.busy():
            return
        path, _ = QFileDialog.getOpenFileName(
            self, "Import image asset", filter="Images (*.png *.jpg *.jpeg *.webp)"
        )
        if path:
            try:
                self.project.asset(path, key)
                # Assets are shared across the set.
                for photo in self.project.photos:
                    photo["adjustments"].pop(key, None)
                self.project.save()
                self.render()
            except Exception as exc:
                self.message.setText(str(exc))

    def remove_logo(self):
        if self.project and not self.busy():
            self.project.settings["logo"] = ""
            self.project.save()
            self.render()

    def copy_adjustments(self):
        if self.current() and not self.busy():
            values = copy.deepcopy(self.current()["adjustments"])
            for item in self.photos.selectedItems():
                self.project.photos[self.photos.row(item)]["adjustments"] = copy.deepcopy(values)
            self.project.save()

    def reset_adjustments(self):
        if self.current() and not self.busy():
            self.current()["adjustments"] = {}
            self.project.save()
            self.select()

    def setup_model(self):
        if self.busy():
            return
        self.message.setText(
            f"U²-Net · Apache-2.0 · 175,997,641 bytes\nCache: {model.model_path()} · Explicit setup is the only network operation."
        )
        if model.verified(model.model_path()):
            self.message.setText(f"Model ready and verified: {model.model_path()}")
            return
        self.start(Worker("model"))

    def process(self):
        if self.project and self.project.photos and not self.busy():
            self.start(Worker("process", self.project))

    def export(self):
        if self.project and self.project.photos and not self.busy():
            path = QFileDialog.getExistingDirectory(
                self, "Choose export parent (a new folder will be created)"
            )
            if path:
                self.start(Worker("export", self.project, path, self.originals.isChecked()))

    def start(self, worker):
        self.timer.stop()
        self.worker = worker
        self.split.setEnabled(False)
        self.run_button.setEnabled(False)
        self.export_button.setEnabled(False)
        self.model_button.setEnabled(False)
        worker.status.connect(self.message.setText)
        worker.progress.connect(lambda n, total: (self.progress.setMaximum(total), self.progress.setValue(n)))
        worker.complete.connect(self.done)
        worker.finished.connect(self.worker_finished)
        worker.start()

    def done(self, result):
        self.refresh()
        self.message.setText(str(result))

    def worker_finished(self):
        self.split.setEnabled(True)
        self.run_button.setEnabled(True)
        self.export_button.setEnabled(True)
        self.model_button.setEnabled(True)

    def cancel(self):
        if self.busy():
            self.worker.cancel.set()
            self.message.setText(
                "Cancellation requested. Waiting for the current inference/export to return."
            )

    def closeEvent(self, event):
        if self.busy():
            self.cancel()
            event.ignore()
            self.message.setText(
                "Wait for the worker to stop, then close again. Model setup must finish first."
            )
        else:
            if self.project:
                self.project.save()
            event.accept()


def configure_app(app):
    app.setStyle("Fusion")
    app.setStyleSheet("""
        QWidget { background:#17202c; color:#e6edf5; font-family:'Segoe UI'; font-size:12px; }
        QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox { background:#232f3f; padding:6px; border:1px solid #344458; border-radius:4px; }
        QPushButton { background:#29394c; border:1px solid #3b5068; border-radius:5px; padding:8px; }
        QPushButton:hover { background:#35536a; } QPushButton:disabled { color:#718096; }
        QListWidget { background:#121b26; border:0; } QListWidget::item { padding:8px; border-bottom:1px solid #283447; }
        QListWidget::item:selected { background:#254b52; } QProgressBar { border:0; background:#263244; text-align:center; height:20px; }
        QProgressBar::chunk { background:#367e76; } QScrollArea { border:0; }
    """)


def main():
    app = QApplication(sys.argv)
    configure_app(app)
    window = Window()
    window.show()
    sys.exit(app.exec())

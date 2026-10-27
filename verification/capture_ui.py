"""Render the actual Qt window offscreen with the real processed project."""

import os

os.environ["QT_QPA_PLATFORM"] = "offscreen"
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFontDatabase
from studio.app import Window, configure_app
from studio.project import Project

app = QApplication([])
QFontDatabase.addApplicationFont("C:/Windows/Fonts/segoeui.ttf")
configure_app(app)
window = Window()
window.project = Project.open(Path(__file__).parent / "output" / "camry")
window.refresh()
window.show()
app.processEvents()
window.grab().save(str(Path(__file__).parent / "ui.png"))
window.close()

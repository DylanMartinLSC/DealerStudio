"""Collect required Qt dependencies while omitting unused PDF and virtual keyboard plugins.

In particular, virtual keyboard has GPL/commercial terms and is not part of this app.
Filtering here happens before PyInstaller recursively collects plugin DLL dependencies.
"""

from pathlib import Path
from PyInstaller.utils.hooks.qt import add_qt6_dependencies

hiddenimports, binaries, datas = add_qt6_dependencies(__file__)
binaries = [
    entry
    for entry in binaries
    if Path(entry[0]).name.lower() not in {"qpdf.dll", "qtvirtualkeyboardplugin.dll"}
]

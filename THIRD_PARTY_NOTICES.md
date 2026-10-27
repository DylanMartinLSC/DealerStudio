# Third-party notices

DealerStudio original code and bundled original studio backgrounds: Copyright 2026 DealerStudio contributors, Apache License 2.0.

U²-Net (Qin et al., 2020): Apache License 2.0. The general pretrained weights are used through the ONNX conversion distributed by Daniel Gatis/rembg. See `licenses/U2Net-Apache-2.0.txt` and `licenses/rembg-MIT.txt`. Model weights are installed separately and remain subject to their own license.

PySide6, Shiboken6 and Qt: Copyright The Qt Company Ltd. and contributors. Used under LGPL version 3. This software dynamically links Qt. The separate libraries may be replaced with compatible modified versions. Relevant Qt/PySide wheel license notices are under `licenses/dependencies/`; LGPL/GPL texts are included under `licenses/`. Corresponding upstream source: https://code.qt.io/qt/pyside-setup.git and https://download.qt.io/archive/qt/6.10/6.10.0/ . No restriction is placed on reverse engineering for debugging modifications to these libraries.

Pillow, NumPy, ONNX Runtime and all transitive packages retain their original copyright notices and bundled dependency notices in `licenses/dependencies/`. The Python runtime has its PSF and bundled notices in `licenses/Python.txt`. Build tool licenses and the PyInstaller bootloader exception are retained where available. See `LICENSE_INVENTORY.md` and the machine-readable dependency inventory.

Qt bundled-component notices and source attribution manifests from the exact v6.10.0 tags are in `licenses/qt-6.10.0/`. This includes permissive third-party libraries such as FreeType, HarfBuzz, PCRE2, double-conversion, zlib and image codecs where enabled by Qt's upstream Windows build. The manifest identifies upstream source URLs. Qt PDF and Virtual Keyboard plugins are omitted from the application package.

The optional verification photograph, by Kevauto, and derived verification images are CC BY-SA 4.0, separately licensed from the application. Attribution, source and transformation details: `verification/PROVENANCE.md`. The photograph is not included in the application package.

The separate benchmark dataset has seven Commons originals plus a derived detail crop. Individual photographs retain CC BY-SA 4.0 or public-domain status; derived annotation data/contact sheets/composites are CC BY-SA 4.0. Credits and source metadata: `benchmark/ATTRIBUTION.md` and `benchmark/sources/`. These data are excluded from the Windows application package; benchmark Python code remains Apache-2.0.

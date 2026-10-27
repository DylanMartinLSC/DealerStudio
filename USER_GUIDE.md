# DealerStudio user guide

A free, local Windows desktop workspace for vehicle listing photos. Original application code and the three original studio backgrounds are Apache-2.0. No accounts, telemetry, server, cloud inference, subscription or per-image fees. This is a usable **0.1 release**, with required human mask and grounding review.

## Launch from source

Open PowerShell:

```powershell
cd path\to\DealerStudio
.\launch.ps1
```

Run setup first on a new installation. Alternatively run `dist\DealerStudio\DealerStudio.exe` after packaging. The portable folder must stay together; do not copy only the EXE.

## Reproduce installation

Install Python 3.13 and [uv](https://docs.astral.sh/uv/), then run `./setup.ps1` (uses the committed `uv.lock`). Launch and click **Model setup · 176 MB** once. This is an explicit download; processing never downloads models automatically. Cache: `%USERPROFILE%\.dealerstudio\models\u2net.onnx`. Override with `DEALERSTUDIO_MODELS` pointing to a directory. Setup displays progress, checks the exact SHA-256, installs atomically, and reports failures. An interrupted download can be retried.

To set up a disconnected machine, copy the environment/package and the verified model cache from an online setup. No API keys are used. Model verification occurs before session creation, and a missing/corrupt model gives a setup error.

## Short user guide

1. **New** chooses a parent folder and creates a unique editable project. Enter the vehicle name or stock number. **Open** selects an existing project folder.
2. Import files, choose a folder, or drop files/folders into the window. Imported sources are copied byte-for-byte. Folder imports use filename order; multi-file picker/drop order is retained. Use ↑ / ↓ to reorder.
3. Select each photo and correct its **exterior / interior / detail** type. Interior and detail images retain their background and are padded to fit without cropping.
4. **Process vehicle set** runs one photo at a time. Existing edited masks are reused. Cancellation takes effect after the current model call returns; finished masks are retained. Errors are isolated to a photo and shown in its tooltip and preview message.
5. Review **Comparison** (original left, result right). In **Mask**, red indicates removed pixels. Foreground/background brushes edit the original-resolution grayscale mask. Brush size is in source pixels; use **100% inspection** and scroll for fine work. Four brush undos are kept in memory. A manual mask starts empty if a mask does not exist. Every completed stroke saves immediately.
6. Choose light, dark or branded studio; import a custom background if desired. Set vehicle width, horizontal center, floor contact, feather and restrained contact shadow. Edge trim removes 1–3 pixels of contaminated fringe; it does not repaint edge colors. **Tire contact** in Mask view adds soft local contact shadows at clicked points; use it for a far tire at a different perspective height. Clear contacts to start over. No automatic camera/perspective recovery is claimed.
7. Draw **Plate rectangle** in Mask view, then choose blur, solid or imported dealer graphic. Solid/graphic is preferable for privacy: blur may leave some information discernible. Rectangles use source coordinates and apply before compositing. Clear plates removes all rectangles for that photo. No automatic plate detection is included.
8. Import a transparent PNG logo, set width, padding and corner. Imported logo/background/plate assets are copied inside the project and shared across the set. The branded studio is an original geometric wall, without third-party logos or text.
9. Adjust export dimensions, JPEG quality or PNG. Settings are per photo; Ctrl/Shift-select targets and use **Copy framing to selected** to copy all current numeric, studio and export settings. Masks, plate rectangles and contact points remain photo-specific. Save/load reusable JSON settings presets (asset images stay in their project).
10. **Export set** creates a uniquely named subfolder. Names include vehicle, sequence and photo type. An export report lists errors or cancellation. Optional originals go into a separate subfolder. Source files and previous exports are never overwritten. Inspect exports at full resolution before posting.

Jobs save automatically to `project.json`, `originals/`, `masks/` and `assets/`. Copy the whole folder to resume elsewhere. There is no destructive source editing. Keep backups of important projects. Only one project is open at once; the sidebar is the current vehicle set.

## Hardware and model

The default is **U²-Net general saliency**, 320×320 inference, using a verified 175,997,641-byte ONNX conversion. Source photographs remain full resolution for export. The model may miss thin antennas, wheel openings, mirrors, racks and spoilers; manual correction is essential. See [model and license decisions](LICENSE_INVENTORY.md).

CPU works without a GPU; 8 GB RAM or more is recommended, with more for large masks and undo. Input limit: 80 megapixels; export limit: 40 megapixels. One inference/export worker limits peak memory. Previews use a smaller composite; full-resolution output is computed separately. Full-size decoding, previews, thumbnails and brush work can still pause the UI on very large files.

For an NVIDIA GPU, in a separate environment replace `onnxruntime` with the matching `onnxruntime-gpu` release and install its documented CUDA/cuDNN prerequisites. The app uses CUDA when the provider is available and falls back to CPU if session creation fails. CPU is the tested and reproducibly locked distribution; GPU acceleration has **not** been verified here. Do not install both ONNX runtime variants together. CPU execution can always be selected programmatically with `Segmenter(cpu=True)`.

## Development and packaging

```powershell
uv sync --frozen
uv run pytest -q
uv run ruff check .
uv run ruff format --check .
.\package.ps1
```

`package.ps1` builds a PyInstaller **onedir** Windows distribution, including backgrounds and license notices. Dynamic Qt DLLs remain separate for replacement under LGPL terms. Model weights are deliberately separate and cached on first explicit setup. Packaging is unsigned; no installer, automatic updates or code-signing certificate is included.

The build isolates PATH to avoid collecting unrelated DLLs. An explicit packaged diagnostic runs real CPU inference and captures the UI: `DealerStudio.exe --verify-package SOURCE_IMAGE OUTPUT_FOLDER`. Startup import failures are recorded in `%USERPROFILE%\.dealerstudio\startup-error.log`.

Modules: `studio/app.py` native UI and serial queue; `project.py` storage/import; `model.py` explicit setup and local inference; `pipeline.py` masks/compositing/export. Tests use synthetic fixtures only inside `tests/`, with no mock AI mode exposed in the app. `verification/run_real.py` runs actual CPU inference on the separately attributed vehicle fixture with Python socket networking blocked. See [verification report](VERIFICATION.md).

The separately licensed [8-sample vehicle benchmark](benchmark/README.md) adds frozen manual coarse silhouettes and sparse probes. Its [report](benchmark/BENCHMARK_REPORT.md) found missing mirrors/roof details and retained backgrounds in **3 of 5 new exterior views**. Do not use automatic export without review. Windows and a fresh Ubuntu WSL2 install produced identical CPU masks; the Linux benchmark also passed with external networking removed. See the [clean-install report](verification/wsl/REPORT.md). WSL validates the Linux source path, not a clean Windows EXE installation.

For a Linux/WSL source install, the tested Ubuntu **headless Qt prerequisites** are `ca-certificates curl tar gzip libegl1 libopengl0 libgl1 libglib2.0-0 libdbus-1-3 libxkbcommon0 libfontconfig1 libfreetype6 fonts-dejavu-core libx11-6 libxrender1 libxext6 libxcb1`. Run `uv sync --frozen` and install the model explicitly. Headless verification uses `QT_QPA_PLATFORM=offscreen`; interactive `uv run python launch.py` additionally needs a graphical environment and may require further XCB/Wayland packages. A Linux desktop package and interactive WSLg session have not been validated.

## Known quality limits

- General saliency is not vehicle-specific. It can retain adjacent objects or remove genuine parts. No unattended quality guarantee is possible.
- Glass retains original pixels and original scenery/reflections. Transparent panes are not reconstructed. Paint reflections and lighting remain from the original photograph.
- Conservative exposure multiplication is the only color correction. There is no automatic white balance or relighting. ICC profiles are not color-managed; use sRGB photos for predictable paint appearance.
- Contact shadows are an approximation. Manual tire-contact points and framing are provided, but there is no calibrated perspective, floor reflection or physically accurate light transport.
- Mask feather/edge trim can soften or remove tiny detail. Use minimal values and inspect badges, antennas and wheel gaps.
- No unseen parts, repaired damage, generated reflections or invented condition detail. Export resampling affects pixels as ordinary resizing does.
- Current photo sidebar is a thumbnail grid for one project, not a multi-project library. There is no project search, individual photo removal, automatic classification, automatic plate detection or HEIC/RAW support.
- Full-resolution mask undo is memory intensive. No brush-pressure support, redo, lasso or automatic matting refinement is included.
- Local JSON projects are trusted editable documents, with path confinement checks; they are not an encrypted archive. Writes are atomic but not a database transaction spanning every mask and source.

Original code copyright © 2026 DealerStudio contributors. See `LICENSE`, `THIRD_PARTY_NOTICES.md`, and `licenses/` before redistributing.

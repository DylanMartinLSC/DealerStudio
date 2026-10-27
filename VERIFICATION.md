# Release 0.1 verification report

**Follow-up:** the later [benchmark report](benchmark/BENCHMARK_REPORT.md) and [WSL clean-install report](verification/wsl/REPORT.md) extend this initial record. Current test count is **21 passing on Windows and Linux**. An 8-sample licensed dataset identified review failures in 3/5 new exterior views. A fresh Linux dependency/model install and OS-level network-isolated benchmark passed; six Windows/Linux masks matched pixel-for-pixel. The temporary distro and its archive/install directory were removed. Clean Windows installation and GPU execution remain unverified.

Executed 2026-10-27 on Windows 11 (10.0.26200), Python 3.13.7. Application folder: `C:\Users\dylan\DealerStudio`.

## Delivered and exercised

- Real local vertical slice: import a vehicle photograph, infer a full-size mask with U²-Net/ONNX Runtime, save a foreground/background brush correction, composite onto an original bundled studio and export JPEG/PNG.
- Native Qt interface: vehicle project name, ordered thumbnail grid, manual classification, original/result/comparison views, original-coordinate brush/plate/contact tools, fit/100% inspection, settings, serial queue, cancellation and per-photo errors.
- Saved editable project folders, shared copied branding assets, custom backgrounds, per-photo adjustments, copy-to-selected and reusable JSON settings presets.
- Manual license-plate rectangles, blur/solid/dealer graphic, logo placement, framing, exposure multiplier, feather/edge trim, contact shadows and manual tire contact points.
- Unique output folders and ordered names, export resolution/quality, optional untouched originals and partial-job error report. No source overwrites.
- Locked dependency environment, Apache-2.0 original code and backgrounds, third-party notices, exact weight digest, model provenance, dependency inventory and a Windows onedir packaging script.

## Automated results

`uv run pytest -q`: **19 passed**. Coverage includes project/source persistence after deletion of the import source, stored adjustments/branding, brush edits, JPEG and PNG output dimensions/names, repeat exports without overwrites, separate originals, cancellation before and between photos, preserving a completed mask, per-photo failure isolation, interior bypass, unchanged opaque source RGB at neutral settings, plate rectangles, empty-mask/export-bound errors, project path traversal, actionable missing-model state, bad-download rejection/partial cleanup, finite black-image preprocessing and explicit CUDA-session failure → CPU fallback.

Queue/model boundary unit tests use clearly named fixture segmenters inside tests only. They do not establish model quality. The separate real run below exercises actual weights.

`uv run ruff check .` and `uv run ruff format --check .`: pass.

`./package.ps1`: pass. Packaging excludes unused PDF/virtual-keyboard plugins before dependency collection. Final Qt DLLs are Core, Gui, Network, Svg and Widgets. The build script isolates PATH to prevent unrelated developer-toolchain DLLs being copied into the package. The final portable folder is approximately 176 MB, excluding the separately cached 176 MB model.

## Real CPU/offline run

`./.venv/Scripts/python.exe -m verification.run_real`: actual U²-Net inference on Kevauto's CC BY-SA 4.0 Toyota Camry photograph; exact attribution is in `verification/PROVENANCE.md`.

- Input and saved mask: **4,841 × 2,534**.
- Provider: **CPUExecutionProvider**.
- Export: **2,000 × 1,500**.
- Latest source run: **1.79 seconds** for session creation, inference, correction and multiple composites/exports on this machine; this is a single observation, not a performance guarantee.
- Errors: **none**. Machine-readable evidence: `verification/real-report.json`.
- Networking: Python socket `connect` and `create_connection` were patched to raise for the entire model-session construction, inference and export path after setup. No cloud fallback exists. This was an application-level networking block, **not an OS firewall/network-adapter isolation test**.
- Setup reused the machine's existing model after matching its MD5 to the rembg publisher checksum and computing/pinning SHA-256. The fresh 176 MB installer download was not repeated. Installer corruption/missing-model behavior is unit-tested.

`verification/output/result.png` is the automatic mask result with a small explicit brush correction in a known background corner. `reviewed.png` additionally exercises a manually chosen solid plate rectangle and tire-contact points. Source pixels and condition markings remain visible. Neither is claimed to be fully retouched or automatically approved for publication.

## Packaged executable check

Executed the actual `dist/DealerStudio/DealerStudio.exe` with:

```powershell
$check = Start-Process .\dist\DealerStudio\DealerStudio.exe -ArgumentList @('--verify-package','C:\Users\dylan\DealerStudio\verification\camry.jpg','C:\Users\dylan\DealerStudio\verification\packaged') -Wait -PassThru -WindowStyle Hidden
$check.ExitCode
```

**Exit 0**, `ok: true`, CPU provider, **2,000 × 1,500** exported JPEG, native Qt window rendered and captured, approximately **2.17 seconds**. Evidence: `verification/packaged/package-report.json`, `verification/packaged/packaged-ui.png`. The diagnostic does actual inference using the existing model cache; it is not a mock. The source capture is `verification/ui.png`. The package was tested on this host, not a clean second Windows installation.

## Visual review and limits

Inspected the exported 2000×1500 image and native-scale crops showing badge/plate, front wheel, mirror/door and roof/rear wheel. The actual vehicle silhouette, trim, badge and visible leaf/condition markings remain from the input. The original window scenery and paint reflections remain. Fine roof and rear edges are softened and can retain a halo. No claim is made that this single photograph establishes dependable masks for every vehicle or view. Antennas, racks, fine gaps and difficult backgrounds still require representative multi-vehicle testing and manual masks.

Visual review caught a rectangular shadow boundary and it was fixed by padding and tapering the contact profile before blur. Automatic contact still emphasizes the nearest low tire; manual points support a higher far tire. This remains approximate grounding, without calibrated floor perspective or reflections. Edge cleanup is feathering and erosion/trim, rather than paint-color reconstruction or advanced matting decontamination.

The packaged screenshot was visually inspected for layout, readable controls, displayed real image and visible queue/export controls. Programmatic UI tests exercise settings, manual mask creation and reordering. There was no manual end-user usability session or drag-and-drop hardware interaction test.

## Remaining work

GPU acceleration is implemented as an optional provider selection/fallback but has not been run on hardware. No automatic plate detector, auto photo classifier, HEIC/RAW support, multi-project searchable library, calibrated automatic grounding, generative relighting, reflections or viewpoint estimation is included. Full-resolution previews/brush undo can still pause or use substantial memory on very large images. Distribution is unsigned, with no installer or automatic updater. Broad vehicle-quality benchmarking and clean-machine packaging validation remain necessary before calling this a dealership-wide production release.

## Launch

Double-click `dist\DealerStudio\DealerStudio.exe` with its sibling `_internal` folder intact, or run `./launch.ps1` from the source directory. Script-free alternative: `./.venv/Scripts/python.exe launch.py`. Setup and the short user guide are in `README.md`. Rare startup errors are written to `%USERPROFILE%\.dealerstudio\startup-error.log`.

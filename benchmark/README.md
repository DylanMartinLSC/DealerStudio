# Small vehicle-photo regression benchmark

**8 samples from 7 licensed originals**: six exterior views (sedan front/rear, pickup, SUV with rails, side-on hatchback, open convertible), one interior, and one wheel-detail crop derived from the known sedan-front image. Five new exterior photographs form the evaluation subset. The existing sedan-front development image is reported separately; the rear view is the same sedan and is not an independent vehicle group. Interior/detail are routing controls, not segmentation-accuracy cases.

Collected with a bounded Wikimedia Commons API downloader, not arbitrary dealership scraping. Original bytes are checked against Commons SHA-1 and pinned by SHA-256. `manifest.json`, `sources/*.json` and [ATTRIBUTION.md](ATTRIBUTION.md) retain URLs, author, exact license, dimensions, retrieval time and transformations. The collector respects HTTP 429/503 retry delays and caches successful downloads. Files are kept locally; this collector is never invoked by the desktop app.

## What is measured

`annotations.json` has **six manually drawn coarse silhouettes and 192 named probes** (20 vehicle + 12 background points per exterior). For the five evaluation images, there are 100 foreground and 60 background probes. Labels were authored by the agent from the original photographs, before viewing predictions for those five images, and frozen by SHA-256 in `freeze.json`. `reference-review.jpg` shows the contours and probes. These are **single-annotator approximate references**, not expert pixel-accurate masks or an independent certification.

- Coarse silhouette IoU: binary alpha ≥128 against the approximate polygon.
- Core-region IoU: excludes a 12-pixel band around the reference contour at 1000px image width. This deliberately avoids pretending the coarse contours are accurate matting boundaries; it can hide small-part errors.
- Foreground probe recall: fraction of named vehicle points retained at alpha ≥128.
- Background probe rejection: fraction of named scenery/gap points below alpha 128.
- Opaque foreground fraction: foreground probes with alpha ≥0.98.

Glass is conservatively treated as foreground, including original scenery visible through panes. Actual open gaps and neighboring vehicles should be removed. Existing cast shadows are background. Roof-rail gaps and thin parts are principally tested by probes, not the coarse filled silhouette. Each probe uses the median of a 3×3 patch at reference scale. A review flag fires when core IoU, foreground recall, or background rejection is below 0.95. These are project-selected diagnostic thresholds, not marketplace standards.

**Do not describe the scores as overall vehicle-photo accuracy.** The set is small, mostly daylight and light-colored vehicles, with no dense matting labels, multiple annotators, systematic night/weather/damage coverage, or confidence intervals. Training-set overlap with U²-Net's historical datasets is unknown. The benchmark does not establish that reflections, condition details or floor geometry are correct. A high score still requires visual inspection.

## Reproduce

The source images and frozen labels are included. With the app environment and verified model installed:

```powershell
uv run python -m benchmark.run --output benchmark/results/my-new-run
uv run python -m benchmark.run --output benchmark/results/ci-run --enforce
```

Each run requires a new output folder. `--enforce` exits **2** if any evaluation image crosses a review threshold. Output contains JSON/Markdown metrics, raw original-resolution masks in the editable project, automatic PNG composites, a contact sheet and the complete ordered 2000×1500 JPEG set with separate original copies. Source hashes, frozen-label hashes, source preservation, export dimensions/count and project round-trip order are checked. Python socket connections are blocked throughout actual model loading, inference and export.

Explicitly rebuilding the online collection: `uv run python -m benchmark.collect`. This refreshes retrieval timestamps/metadata and therefore intentionally invalidates the freeze. Archive the old manifest/results and independently review/refreeze labels before treating a refreshed collection as a new benchmark version. Do not silently adjust annotations to make a model score better. `benchmark.reference` builds masks/annotation review images without inference; `benchmark.annotation_previews` produces original-only coordinate guides.

Compare two runs: `uv run python -m benchmark.compare FIRST_RUN SECOND_RUN benchmark/cross-platform.json`.

## Results and retained artifacts

See [BENCHMARK_REPORT.md](BENCHMARK_REPORT.md). Local full outputs are in `results/windows-baseline/` and `results/wsl-offline/` (excluded from Git because of their size). Summary JSON reports, frozen references, dataset originals and attribution remain in the source tree. The associated frozen metadata's pickup tags were provisional; visual review confirms a **white, close frontal pickup** among other vehicles, not a dark/small subject. That descriptive correction is recorded here without modifying the frozen manifest or labels.

To review or correct the actual examples in DealerStudio, use **Open** and choose `benchmark/results/windows-baseline/project`. It contains all eight ordered originals, classifications and uncorrected model masks. Benchmark report scores stay tied to the frozen automatic run; editing the project does not retroactively change them.

## Data licensing

Photographs keep their individual licenses: six downloaded originals are CC BY-SA 4.0; the pickup original is public domain. The detail crop retains the sedan source's CC BY-SA 4.0. Derived benchmark contact sheets, masks, annotation JSON and composites are distributed under [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/), with underlying photo credits in ATTRIBUTION.md. Public-domain source pixels remain public domain. None of these photographic data files are covered by the app's Apache-2.0 license. Benchmark Python code is Apache-2.0. The dataset is not included in the Windows application package.

# Benchmark findings — 2026-10-27

**The automatic masks are not dependable enough for unattended dealership exports. Three of five new exterior photos triggered review.** The benchmark detected meaningful missing parts and retained background even though coarse silhouette metrics were high.

| New evaluation photo | Coarse IoU | Core IoU (boundary ignored) | FG probes retained | BG probes rejected | Trigger |
|---|---:|---:|---:|---:|---|
| Rear sedan | 0.956 | 0.988 | 100% | 91.7% | Neighboring pickup retained |
| Pickup | 0.935 | 0.975 | 85% | 100% | Roof fin and extended mirror lost |
| SUV with rails | 0.964 | 0.996 | 100% | 91.7% | Roof-rail opening filled |
| Side hatchback | 0.960 | 0.999 | 100% | 100% | No probe/core trigger; edges still need review |
| Open convertible | 0.947 | 0.992 | 100% | 100% | No probe/core trigger; thin details still need review |

Across the five evaluation photos: **0.9525 coarse silhouette IoU**, **0.9902 core-region IoU**, **97/100 foreground probes retained**, **58/60 background probes rejected**. The core score ignores the reference boundary band and must not be presented as 99% vehicle accuracy. The three missing foreground probes correspond to a roof fin and two points on the same extended mirror. The known development sedan-front sample scored well but is excluded from these averages.

All eight samples imported, saved and exported successfully. Interior and detail bypassed segmentation. All JPEG outputs were 2000×1500, sequence order persisted, copies of original bytes remained unchanged, and a complete editable project was saved. No masks were corrected before scoring. Source/label SHA-256 checks passed.

## Visual findings

Reviewed the full original/mask/result contact sheet and the original-resolution masks/composites for the rear-sedan, pickup and SUV failure cases. The sedan retains a conspicuous piece of the background pickup near the forward windshield edge. The white pickup's large extended side mirror is removed, along with a small roof fin; some underbody/edge contamination also remains. The SUV's roof opening is filled. Window scenery and paint reflections remain from the input, as expected. Automatic shadows/framing can make far tires look ungrounded and need manual contact points. The side hatchback and convertible pass the sparse tests, but that says little about every thin edge, badge, or open gap.

These are model limitations, not repaired by changing the labels or hiding failed examples. The app's foreground/background brushes can restore source pixels or remove retained scenery. Fine-part handling, a more capable commercially usable model, and broader dense annotations remain priorities before unattended use. No unseen parts were generated.

## Cross-platform and offline verification

Ran the actual frozen set on Windows and in a freshly installed Ubuntu 24.04.5 WSL2 distro. Linux performed a fresh dependency setup and real verified model download. The full Linux benchmark then ran under **`unshare --net`** with only a loopback interface and no external routes; `uv` was offline and Python socket connects were also blocked.

All **six full-resolution predicted masks were pixel-identical between Windows and Linux** (maximum/mean alpha difference 0), and every reported aggregate metric matched. This is evidence for these exact CPU/model/dependency versions, not a promise of identical GPU inference. See `cross-platform.json`, `windows-report.json` and `wsl-report.json`; the detailed output projects and review sheets are in `results/`.

**21 tests pass** on both Windows and clean Linux, including analytical metric checks and frozen dataset integrity. The fresh Linux setup uncovered missing fontconfig/FreeType/X11 prerequisites, which were added to the reproducible setup script. Qt's offscreen window rendered and was visually inspected. This validates the Linux source path, not the Windows EXE on a clean Windows machine.

The temporary `DealerStudioVerify` WSL distro was unregistered and its root filesystem/archive directory removed. The pre-existing stopped `docker-desktop` distro was retained. Setup/offline logs and the cleanup evidence remain under `verification/wsl/`.

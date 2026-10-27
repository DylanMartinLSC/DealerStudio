# Isolated WSL2 clean-install check

Completed 2026-10-27 using a temporary distro named `DealerStudioVerify`, imported separately from the existing Docker distro. Base: official Ubuntu Base 24.04.5 amd64 archive, SHA-256 `e77b6f10c2590cef872b33ee9f635a0e3fd1f57fb074c0e52b5c7f56147a0c86`, matching the publisher's HTTPS SHA256SUMS retained here. This was a checksum check, not a detached-signature verification.

No Windows virtual environment, pip/uv cache, model cache or site packages were reused. Source/data files were copied to `/opt/dealerstudio`, uv 0.9.5 installed Python **3.13.9**, and `uv sync --frozen` installed the Linux wheels from the existing lockfile. The app's model installer downloaded and SHA-256-verified the real 176MB U²-Net ONNX file into the fresh Linux home directory. The first attempt found missing `libfontconfig.so.1`; its log is preserved. The final `install.sh` includes the working native Qt prerequisites and fonts, and the rerun passed tests, lint, real CPU processing and offscreen UI rendering.

Evidence:

- `install.sh`, `install.log`, `first-attempt.log`: setup commands and actual outcomes.
- `os-release.txt`, `kernel.txt`: OS/kernel identity.
- `real-report.json`: real 4841×2534 source/mask → 2000×1500 export, CPU provider, no processing errors.
- `ui.png`: actual Qt offscreen window, visually inspected with readable controls and the real composite.
- `offline.sh`, `offline.log`: **21 passing tests and all 8 benchmark samples** under a separate network namespace (`unshare --net`), with only `lo` and no external routes. No host network configuration was changed.
- `../../benchmark/cross-platform.json`: all six exterior masks pixel-identical to Windows.
- `cleanup.json`: temporary distro unregistered, dedicated host archive/install directory absent, only the original stopped Docker distro remains.

No GPU hardware run, visible WSLg interactive usability session, Linux packaging build or clean Windows machine test was performed. WSL logged a NAT-to-VirtioProxy fallback during online setup; it did not prevent dependency/model downloads. ONNX Runtime's GPU discovery warning is expected for this CPU test. The isolated offline inference run had no external network interfaces.

`install.sh` and `offline.sh` record the test's machine-specific `/mnt/c/Users/dylan/DealerStudio` paths. To repeat elsewhere, adapt those paths, import a new disposable Ubuntu Base distro and run setup; then run `unshare --net bash offline.sh`. Never unregister a pre-existing distro or delete an unrelated installation directory.

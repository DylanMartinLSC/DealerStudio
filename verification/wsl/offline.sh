#!/usr/bin/env bash
set -euo pipefail
cd /opt/dealerstudio
export QT_QPA_PLATFORM=offscreen
export UV_OFFLINE=1
cat /proc/net/dev
cat /proc/net/route
/root/.local/bin/uv run --frozen --offline pytest -q
/root/.local/bin/uv run --frozen --offline python -m benchmark.run --output /opt/benchmark-offline
cp -r /opt/benchmark-offline /mnt/c/Users/dylan/DealerStudio/benchmark/results/wsl-offline
printf 'WSL_OFFLINE_BENCHMARK_PASS\n'

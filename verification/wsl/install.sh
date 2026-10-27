#!/usr/bin/env bash
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y ca-certificates curl tar gzip libegl1 libopengl0 libgl1 libglib2.0-0 libdbus-1-3 libxkbcommon0 libfontconfig1 libfreetype6 fonts-dejavu-core libx11-6 libxrender1 libxext6 libxcb1
curl --fail --location https://astral.sh/uv/0.9.5/install.sh -o /tmp/uv-install.sh
sh /tmp/uv-install.sh
mkdir -p /opt/dealerstudio
tar -C /mnt/c/Users/dylan/DealerStudio --exclude=.venv --exclude=.git --exclude=build --exclude=dist --exclude=.pytest_cache --exclude=.ruff_cache --exclude=verification/output --exclude=verification/packaged --exclude=benchmark/results --exclude='__pycache__' -cf - . | tar -C /opt/dealerstudio -xf -
cd /opt/dealerstudio
/root/.local/bin/uv sync --frozen
export QT_QPA_PLATFORM=offscreen
/root/.local/bin/uv run pytest -q
/root/.local/bin/uv run ruff check .
/root/.local/bin/uv run python -c 'from studio.model import install,model_path; print("Fresh download:",model_path()); install(lambda n: print("model",n,flush=True) if n%10==0 else None)'
/root/.local/bin/uv run python -m verification.run_real
/root/.local/bin/uv run python -m verification.capture_ui
cp verification/real-report.json /mnt/c/Users/dylan/DealerStudio/verification/wsl/real-report.json
cp verification/ui.png /mnt/c/Users/dylan/DealerStudio/verification/wsl/ui.png
uname -a > /mnt/c/Users/dylan/DealerStudio/verification/wsl/kernel.txt
cat /etc/os-release > /mnt/c/Users/dylan/DealerStudio/verification/wsl/os-release.txt
printf 'WSL_CLEAN_INSTALL_PASS\n'

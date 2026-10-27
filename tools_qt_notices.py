"""Retain upstream Qt bundled-component notices from the exact 6.10.0 source tag.

Explicit maintainer/setup command; never imported or run by the application.
"""

from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import urllib.request

root = Path(__file__).parent / "licenses" / "qt-6.10.0"
root.mkdir(parents=True, exist_ok=True)
manifest = []


def get(url):
    request = urllib.request.Request(url, headers={"User-Agent": "DealerStudio-license-audit"})
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read()


for repo in ("qtbase", "qtimageformats", "qtsvg"):
    tree = json.loads(get(f"https://api.github.com/repos/qt/{repo}/git/trees/v6.10.0?recursive=1"))
    for item in tree["tree"]:
        path = item["path"]
        name = Path(path).name.lower()
        if item["type"] == "blob" and (
            path.startswith("LICENSES/")
            or (
                "3rdparty/" in path
                and (name.startswith(("license", "copying", "copyright")) or name == "qt_attribution.json")
            )
        ):
            url = f"https://raw.githubusercontent.com/qt/{repo}/v6.10.0/{path}"
            manifest.append(dict(repo=repo, path=path, url=url))


def retain(item):
    dest = root / item["repo"] / item["path"]
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(get(item["url"]))


with ThreadPoolExecutor(max_workers=8) as pool:
    list(pool.map(retain, manifest))
(root / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
print(f"Retained {len(manifest)} Qt source notices and attribution manifests")

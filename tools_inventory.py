"""Retain installed distribution license texts and enumerate the exact locked environment."""

from importlib import metadata
import json
from pathlib import Path
import shutil

root = Path(__file__).parent / "licenses"
inventory = []
for dist in sorted(metadata.distributions(), key=lambda d: d.metadata["Name"].lower()):
    name = dist.metadata["Name"]
    row = dict(
        name=name,
        version=dist.version,
        license=dist.metadata.get("License-Expression")
        or dist.metadata.get("License", "See retained upstream notices"),
        notices=[],
    )
    for file in dist.files or []:
        parts = str(file).replace("\\", "/").split("/")
        if any(
            "license" in p.lower() or p.lower().startswith(("copying", "notice", "copyright")) for p in parts
        ) and str(file).lower().endswith((".txt", ".md", ".rst", "/license", "/copying", "/notice")):
            source = Path(dist.locate_file(file))
            if source.is_file() and source.stat().st_size < 4_000_000:
                relative = Path(name) / Path(*[p for p in parts if p not in ("..", ".")])
                target = root / "dependencies" / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)
                row["notices"].append(str(target.relative_to(root)))
    inventory.append(row)
(root / "dependency-inventory.json").write_text(json.dumps(inventory, indent=2), encoding="utf-8")
print(
    f"Inventoried {len(inventory)} distributions with {sum(len(x['notices']) for x in inventory)} notice files"
)

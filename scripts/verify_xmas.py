#!/usr/bin/env python3
"""扫描场景/资源文件中的新年集市相关对象名。

用法:
  python verify_xmas.py <文件> [文件...]
"""
from __future__ import annotations

import os
import sys

import UnityPy

KEYWORDS = (
    "christmas",
    "ny_bazaar",
    "ny25",
    "snowman",
    "sharmanka",
    "santa",
    "market",
    "xmas",
    "tree",
)


def main() -> int:
    for path in sys.argv[1:]:
        size = os.path.getsize(path)
        print(f"== {os.path.basename(path)}  {size:,} bytes")
        try:
            env = UnityPy.load(path)
        except Exception as exc:  # noqa: BLE001
            print(f"   load failed: {exc}")
            continue
        total = 0
        hits: set[str] = set()
        for obj in env.objects:
            total += 1
            if obj.type.name not in ("GameObject", "Mesh", "Material", "Texture2D", "Transform"):
                continue
            try:
                data = obj.read()
                name = getattr(data, "m_Name", "") or ""
            except Exception:  # noqa: BLE001
                continue
            low = name.lower()
            if any(k in low for k in KEYWORDS):
                hits.add(f"[{obj.type.name}] {name}")
        print(f"   objects={total}  hits={len(hits)}")
        for name in sorted(hits):
            print(f"   - {name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

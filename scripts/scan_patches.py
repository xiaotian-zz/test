#!/usr/bin/env python3
"""扫描 Update 目录内所有补丁包的 patch.conf，列出新增/删除文件。

用法:
  python scan_patches.py <Update目录>
"""
from __future__ import annotations

import glob
import json
import os
import sys
import tempfile

import py7zr


def main() -> int:
    root = sys.argv[1] if len(sys.argv) > 1 else r"F:\RF4\Update"
    for path in sorted(glob.glob(os.path.join(root, "*.7z"))):
        name = os.path.basename(path)
        with tempfile.TemporaryDirectory() as tmp:
            with py7zr.SevenZipFile(path) as z:
                names = z.getnames()
                if "patch.conf" not in names:
                    print(f"{name}: 无 patch.conf，条目 {len(names)}")
                    continue
                z.extract(path=tmp, targets=["patch.conf"])
            with open(os.path.join(tmp, "patch.conf"), encoding="utf-8") as fh:
                conf = json.load(fh)
        patch = conf.get("patch", {})
        added = patch.get("added", [])
        removed = patch.get("removed", [])
        modified = patch.get("modified", [])
        print(
            f"{name}: {conf.get('version_from')} -> {conf.get('version_to')} "
            f"条目={len(names)} modified={len(modified)} added={len(added)} removed={len(removed)}"
        )
        for item in added:
            print(f"    + {item.get('path')}  size={item.get('size')}")
        for item in removed:
            print(f"    - {item}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""打印 AssetBundle 容器路径与预制体子节点数。"""
from __future__ import annotations

import sys

import UnityPy


def main() -> int:
    env = UnityPy.load(sys.argv[1])
    for obj in env.objects:
        if obj.type.name == "AssetBundle":
            d = obj.read()
            try:
                for name in d.m_Container:
                    print("asset:", name)
            except Exception:
                for item in d.m_Container:
                    print("asset:", item)
    counts: dict[str, int] = {}
    for obj in env.objects:
        if obj.type.name == "GameObject":
            d = obj.read()
            counts[d.m_Name] = counts.get(d.m_Name, 0) + 1
    for name, n in counts.items():
        if name.startswith("rf4_xmas"):
            print(f"prefab candidate: {name} x{n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

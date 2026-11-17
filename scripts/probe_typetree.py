#!/usr/bin/env python3
"""打印指定对象的 typetree（截断二进制数据）。

用法:
  python probe_typetree.py <资源文件> <path_id> [path_id...]
"""
from __future__ import annotations

import sys

import UnityPy


def shorten(value, depth: int = 0):
    if depth > 4:
        return "..."
    if isinstance(value, (bytes, bytearray)):
        return f"<{len(value)} bytes>"
    if isinstance(value, list):
        if len(value) > 12:
            return [shorten(v, depth + 1) for v in value[:12]] + [f"...{len(value)}"]
        return [shorten(v, depth + 1) for v in value]
    if isinstance(value, dict):
        return {k: shorten(v, depth + 1) for k, v in value.items()}
    return value


def main() -> int:
    env = UnityPy.load(sys.argv[1])
    wanted = {int(x) for x in sys.argv[2:]}
    for obj in env.objects:
        if obj.path_id not in wanted:
            continue
        print(f"== path_id={obj.path_id} type={obj.type.name}")
        try:
            tree = obj.read_typetree()
        except Exception as exc:  # noqa: BLE001
            print(f"   typetree failed: {exc}")
            continue
        print(shorten(tree))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

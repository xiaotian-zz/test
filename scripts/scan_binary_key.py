#!/usr/bin/env python3
"""在二进制文件中统计关键词出现次数。

用法:
  python scan_binary_key.py <文件...> -- <关键词,逗号分隔>
"""
from __future__ import annotations

import os
import sys


def main() -> int:
    if "--" not in sys.argv:
        print("用法: scan_binary_key.py <文件...> -- <关键词...>")
        return 1
    split = sys.argv.index("--")
    files = sys.argv[1:split]
    keys = [k.encode() for k in sys.argv[split + 1:] if k]
    for path in files:
        try:
            with open(path, "rb") as fh:
                data = fh.read()
        except Exception as exc:  # noqa: BLE001
            print(f"{path}: 读取失败 {exc}")
            continue
        counts = []
        for key in keys:
            counts.append(f"{key.decode()}={data.count(key)}")
        print(f"{os.path.basename(path)}: " + ", ".join(counts))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

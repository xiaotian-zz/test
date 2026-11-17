#!/usr/bin/env python3
"""转储 jdiff 增量文件头部，辅助分析格式。

用法:
  python dump_jdiff.py <文件> [字节数]
"""
from __future__ import annotations

import sys


def main() -> int:
    path = sys.argv[1]
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 256
    with open(path, "rb") as fh:
        data = fh.read(n)
    for i in range(0, len(data), 16):
        chunk = data[i : i + 16]
        hexs = " ".join(f"{b:02x}" for b in chunk)
        text = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
        print(f"{i:08x}  {hexs:<48}  {text}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

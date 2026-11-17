#!/usr/bin/env python3
"""在二进制文件中按关键词搜索，并打印命中位置附近的字符串。

用法:
  python scan_keyword.py <文件> <关键词> [关键词2 ...]
"""
from __future__ import annotations

import mmap
import re
import sys


def printable_around(data: bytes, start: int, end: int, before: int = 96, after: int = 160) -> str:
    lo = max(0, start - before)
    hi = min(len(data), end + after)
    chunk = data[lo:hi]
    return "".join(chr(b) if 32 <= b < 127 else "·" for b in chunk)


def main() -> int:
    path = sys.argv[1]
    keywords = [k.encode("ascii") for k in sys.argv[2:]]
    with open(path, "rb") as fh:
        with mmap.mmap(fh.fileno(), 0, access=mmap.ACCESS_READ) as mm:
            for kw in keywords:
                pattern = re.compile(re.escape(kw), re.IGNORECASE)
                hits = 0
                for m in pattern.finditer(mm):
                    hits += 1
                    print(f"[{kw.decode()}] @0x{m.start():x}")
                    print(printable_around(mm, m.start(), m.end()))
                    print("-" * 100)
                    if hits >= 200:
                        print("... 命中过多，已截断")
                        break
                print(f"== {kw.decode()} 命中 {hits} 处")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

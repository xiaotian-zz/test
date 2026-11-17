#!/usr/bin/env python3
"""尝试解析 jdiff 增量指令流，验证格式假设。

用法:
  python jdiff_probe.py <patch文件>
"""
from __future__ import annotations

import sys


def leb128(data: bytes, pos: int) -> tuple[int, int]:
    result = 0
    shift = 0
    while pos < len(data):
        b = data[pos]
        pos += 1
        result |= (b & 0x7F) << shift
        if not (b & 0x80):
            break
        shift += 7
    return result, pos


def try_parse(data: bytes, tag2: dict[bytes, str]) -> tuple[bool, list[tuple[str, int, int]]]:
    pos = 0
    ops: list[tuple[str, int, int]] = []
    while pos < len(data):
        if pos + 2 > len(data):
            return False, ops
        tag = data[pos : pos + 2]
        kind = tag2.get(tag)
        if kind is None:
            return False, ops
        pos += 2
        length, pos = leb128(data, pos)
        if kind == "insert":
            if pos + length > len(data):
                return False, ops
            ops.append((kind, length, pos))
            pos += length
        else:
            offset, pos = leb128(data, pos)
            ops.append((kind, length, offset))
    return pos == len(data), ops


def main() -> int:
    data = open(sys.argv[1], "rb").read()
    print("size:", len(data))
    # 假设 A: a7a3=insert字面量, a7a6=copy(offset,len)
    for name, tags in (
        ("A a7a3=insert / a7a6=copy", {b"\xa7\xa3": "insert", b"\xa7\xa6": "copy"}),
        ("B a7a3=copy / a7a6=insert", {b"\xa7\xa3": "copy", b"\xa7\xa6": "insert"}),
    ):
        ok, ops = try_parse(data, tags)
        ins = sum(l for k, l, _ in ops if k == "insert")
        cpy = sum(l for k, l, _ in ops if k == "copy")
        print(f"{name}: ok={ok} ops={len(ops)} insert={ins} copy={cpy} end={(ops[-1] if ops else None)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

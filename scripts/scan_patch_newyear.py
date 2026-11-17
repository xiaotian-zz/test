#!/usr/bin/env python3
"""扫描升级包全部条目中的新年/博览会相关字符串，并对比当前客户端文件。

用法:
  python scan_patch_newyear.py <升级包解压目录> <客户端 Data 目录> <报告.md>
"""
from __future__ import annotations

import mmap
import os
import re
import sys
from collections import defaultdict

KEYWORDS = [
    "christmas",
    "new_year",
    "newyear",
    "xmas",
    "bazaar",
    "market",
    "santa",
    "snowman",
    "gift",
    "decor",
    "ny25",
]
PATTERN = re.compile(b"|".join(k.encode() for k in KEYWORDS), re.IGNORECASE)
RUN = re.compile(rb"[\x20-\x7e]{4,}")


def snippets_near(mm: mmap.mmap, start: int, end: int, radius: int = 120, limit: int = 3) -> list[str]:
    lo = max(0, start - radius)
    hi = min(len(mm), end + radius)
    out: list[str] = []
    for m in RUN.finditer(mm[lo:hi]):
        s = m.group().decode("ascii", "replace")
        out.append(s)
        if len(out) >= limit:
            break
    return out


def scan(path: str) -> tuple[dict[str, int], dict[str, list[str]]]:
    counts: dict[str, int] = defaultdict(int)
    samples: dict[str, list[str]] = defaultdict(list)
    with open(path, "rb") as fh:
        size = os.fstat(fh.fileno()).st_size
        if size == 0:
            return counts, samples
        with mmap.mmap(fh.fileno(), 0, access=mmap.ACCESS_READ) as mm:
            for m in PATTERN.finditer(mm):
                key = m.group().decode().lower()
                counts[key] += 1
                if len(samples[key]) < 6:
                    for s in snippets_near(mm, m.start(), m.end()):
                        if s not in samples[key]:
                            samples[key].append(s)
    return counts, samples


def main() -> int:
    patch_root, client_root, out_path = sys.argv[1:4]
    files = []
    for base, _dirs, names in os.walk(patch_root):
        for name in names:
            full = os.path.join(base, name)
            rel = os.path.relpath(full, patch_root)
            files.append((rel, full))
    files.sort()

    lines = ["# 升级包 23847→24205 新年资源扫描报告", ""]
    lines.append(f"- 升级包条目：{len(files)} 个文件")
    lines.append(f"- 客户端目录：`{client_root}`")
    lines.append("")

    hit_rows = []
    detail = []
    for rel, full in files:
        size = os.path.getsize(full)
        counts, samples = scan(full)
        total = sum(counts.values())
        client_path = os.path.join(client_root, rel)
        client_exists = os.path.exists(client_path)
        client_size = os.path.getsize(client_path) if client_exists else None
        if total:
            hit_rows.append((rel, size, total, counts, client_exists, client_size))
            detail.append((rel, samples))

    lines.append("## 一、命中新年版块的升级包条目")
    lines.append("")
    lines.append("| 条目 | 补丁块大小 | 命中数 | 关键词 | 客户端同名文件 | 客户端大小 |")
    lines.append("| --- | ---: | ---: | --- | --- | ---: |")
    for rel, size, total, counts, exists, csize in hit_rows:
        kw = ", ".join(f"{k}×{v}" for k, v in sorted(counts.items(), key=lambda kv: -kv[1]))
        lines.append(
            f"| `{rel}` | {size:,} | {total} | {kw} | {'有' if exists else '**无**'} | "
            f"{csize:,}" if csize is not None else f"| `{rel}` | {size:,} | {total} | {kw} | **无** | - |"
        )
    lines.append("")

    lines.append("## 二、明细字符串")
    lines.append("")
    for rel, samples in detail:
        lines.append(f"### `{rel}`")
        lines.append("")
        for key, items in sorted(samples.items()):
            lines.append(f"- {key}: " + " | ".join(f"`{s}`" for s in items))
        lines.append("")

    with open(out_path, "w", encoding="utf-8", newline="\n") as out:
        out.write("\n".join(lines))
    print(f"report -> {out_path}")
    print(f"hit files: {len(hit_rows)} / {len(files)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

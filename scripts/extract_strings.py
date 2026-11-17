#!/usr/bin/env python3
"""多进程二进制字符串提取器（ASCII + UTF-16LE）。

用法:
  python extract_strings.py -j 8 -o <输出目录> <文件1> [文件2 ...]
产物:
  <输出目录>/<文件名>.strings.txt   每行 "偏移 字符串"（UTF-16 行前缀 "U "）
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import os
import re
import sys

ASCII_RE = re.compile(rb"[\x20-\x7e]{6,}")
UTF16_RE = re.compile(rb"(?:[\x20-\x7e]\x00){6,}")


def extract(path: str, out_dir: str, min_len: int = 6) -> tuple[str, int]:
    with open(path, "rb") as fh:
        data = fh.read()

    base = os.path.basename(path)
    out_path = os.path.join(out_dir, base + ".strings.txt")
    count = 0
    with open(out_path, "w", encoding="utf-8", errors="replace", newline="\n") as out:
        for m in ASCII_RE.finditer(data):
            s = m.group().decode("ascii", "replace")
            if len(s) >= min_len:
                out.write(f"{m.start():08x} {s}\n")
                count += 1
        for m in UTF16_RE.finditer(data):
            s = m.group()[::2].decode("ascii", "replace")
            if len(s) >= min_len:
                out.write(f"{m.start():08x} U {s}\n")
                count += 1
    return out_path, count


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+")
    ap.add_argument("-o", "--out-dir", required=True)
    ap.add_argument("-j", "--jobs", type=int, default=os.cpu_count() or 4)
    ap.add_argument("-m", "--min-length", type=int, default=6)
    args = ap.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)
    workers = max(1, min(args.jobs, len(args.files)))
    with cf.ProcessPoolExecutor(max_workers=workers) as pool:
        futs = {
            pool.submit(extract, p, args.out_dir, args.min_length): p
            for p in args.files
        }
        for fut in cf.as_completed(futs):
            path = futs[fut]
            try:
                out_path, count = fut.result()
                print(f"{path}: {count} strings -> {out_path}")
            except Exception as exc:  # noqa: BLE001
                print(f"{path}: FAILED {exc}", file=sys.stderr)
                return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

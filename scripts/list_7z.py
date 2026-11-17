#!/usr/bin/env python3
"""并行列出 7z 更新包内容（不解压）。

用法:
  python list_7z.py -o <输出目录> <包1.7z> [包2.7z ...]
输出:
  <输出目录>/<包名>.listing.txt   每行 "大小\\t修改时间\\t路径"
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import os
import sys

import py7zr


def list_archive(path: str, out_dir: str) -> tuple[str, int]:
    out_path = os.path.join(out_dir, os.path.basename(path) + ".listing.txt")
    count = 0
    with py7zr.SevenZipFile(path, "r") as archive, open(
        out_path, "w", encoding="utf-8", newline="\n"
    ) as out:
        for info in archive.list():
            out.write(f"{info.uncompressed}\t{info.creationtime}\t{info.filename}\n")
            count += 1
    return out_path, count


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("archives", nargs="+")
    ap.add_argument("-o", "--out-dir", required=True)
    ap.add_argument("-j", "--jobs", type=int, default=8)
    args = ap.parse_args()
    os.makedirs(args.out_dir, exist_ok=True)

    workers = max(1, min(args.jobs, len(args.archives)))
    with cf.ProcessPoolExecutor(max_workers=workers) as pool:
        futs = {pool.submit(list_archive, p, args.out_dir): p for p in args.archives}
        for fut in cf.as_completed(futs):
            path = futs[fut]
            try:
                out_path, count = fut.result()
                print(f"{path}: {count} entries -> {out_path}")
            except Exception as exc:  # noqa: BLE001
                print(f"{path}: FAILED {exc}", file=sys.stderr)
                return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""解压 7z 更新包到指定目录（py7zr）。

用法:
  python extract_7z.py -o <输出目录> <包.7z> [包2.7z ...]
"""
from __future__ import annotations

import argparse
import os
import sys

import py7zr


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("archives", nargs="+")
    ap.add_argument("-o", "--out-dir", required=True)
    args = ap.parse_args()
    os.makedirs(args.out_dir, exist_ok=True)
    for path in args.archives:
        with py7zr.SevenZipFile(path, "r") as archive:
            archive.extractall(path=args.out_dir)
        print(f"extracted {path} -> {args.out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

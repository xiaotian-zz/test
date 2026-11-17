#!/usr/bin/env python3
"""批量解析 Unity AssetBundle（UnityPy，多进程）。

用法:
  python unity_bundle_inspect.py -j 8 -o <输出目录> <bundle1> [bundle2 ...]

每个 bundle 输出一个 JSON:
  { "bundle": ..., "unity_version": ..., "object_count": N,
    "types": {类型: 数量}, "objects": [{"path_id":..., "type":..., "name":...}] }
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import os
import sys
import traceback

import UnityPy

NAME_ATTRS = ("m_Name", "name")


def read_object_name(obj) -> str | None:
    try:
        data = obj.read()
    except Exception:
        return None
    for attr in NAME_ATTRS:
        value = getattr(data, attr, None)
        if isinstance(value, str) and value:
            return value
    return None


def inspect_bundle(path: str) -> dict:
    env = UnityPy.load(path)
    types: dict[str, int] = {}
    objects = []
    for obj in env.objects:
        type_name = obj.type.name
        types[type_name] = types.get(type_name, 0) + 1
        objects.append(
            {
                "path_id": obj.path_id if hasattr(obj, "path_id") else None,
                "type": type_name,
                "name": read_object_name(obj),
            }
        )
    version = None
    try:
        version = env.files[0].version if env.files else None
    except Exception:
        pass
    return {
        "bundle": path,
        "unity_version": version,
        "object_count": len(objects),
        "types": dict(sorted(types.items())),
        "objects": objects,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("bundles", nargs="+")
    ap.add_argument("-o", "--out-dir", required=True)
    ap.add_argument("-j", "--jobs", type=int, default=os.cpu_count() or 4)
    args = ap.parse_args()
    os.makedirs(args.out_dir, exist_ok=True)

    failures = 0
    workers = max(1, min(args.jobs, len(args.bundles)))
    with cf.ProcessPoolExecutor(max_workers=workers) as pool:
        futs = {pool.submit(inspect_bundle, p): p for p in args.bundles}
        for fut in cf.as_completed(futs):
            path = futs[fut]
            try:
                result = fut.result()
            except Exception:
                failures += 1
                print(f"{path}: FAILED\n{traceback.format_exc()}", file=sys.stderr)
                continue
            name = os.path.basename(path) + ".json"
            with open(os.path.join(args.out_dir, name), "w", encoding="utf-8") as fh:
                json.dump(result, fh, ensure_ascii=False, indent=1)
            print(f"{path}: {result['object_count']} objects -> {name}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())

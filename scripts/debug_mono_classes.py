#!/usr/bin/env python3
"""调试：统计 level 中 MonoBehaviour 的脚本类名分布。

用法:
  python debug_mono_classes.py <level文件> [数据目录]
"""
from __future__ import annotations

import collections
import os
import sys

import UnityPy


def main() -> int:
    path = sys.argv[1]
    data_dir = sys.argv[2] if len(sys.argv) > 2 else os.path.dirname(path)
    env = UnityPy.load(path)
    ext = []
    for key, f in env.files.items():
        if os.path.basename(key) == os.path.basename(path):
            ext = [getattr(e, "path", str(e)) for e in (getattr(f, "externals", None) or [])]
            break
    print("externals:", ext)
    envs: dict[int, UnityPy.Environment] = {0: env}

    def script_class(ptr) -> str:
        if ptr is None:
            return "<none>"
        fid, pid = ptr.file_id, ptr.path_id
        if fid not in envs:
            if not (1 <= fid <= len(ext)):
                return f"<bad-file {fid}>"
            p = os.path.join(data_dir, os.path.basename(ext[fid - 1]))
            if not os.path.exists(p):
                return f"<missing {os.path.basename(p)}>"
            envs[fid] = UnityPy.load(p)
        for o in envs[fid].objects:
            if o.path_id == pid:
                try:
                    return getattr(o.read(), "m_ClassName", "") or "<empty>"
                except Exception as exc:  # noqa: BLE001
                    return f"<err {exc}>"
        return f"<notfound {fid}:{pid}>"

    counter = collections.Counter()
    samples = []
    total = 0
    for obj in env.objects:
        if obj.type.name != "MonoBehaviour":
            continue
        total += 1
        try:
            mb = obj.read()
        except Exception as exc:  # noqa: BLE001
            counter[f"<read-fail {type(exc).__name__}>"] += 1
            continue
        name = script_class(getattr(mb, "m_Script", None))
        counter[name] += 1
        if len(samples) < 15:
            samples.append((obj.path_id, name))
    print(f"MonoBehaviour total={total} distinct={len(counter)}")
    for name, cnt in counter.most_common(30):
        print(f"   {cnt:6d}  {name}")
    print("samples:", samples)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

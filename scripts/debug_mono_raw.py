#!/usr/bin/env python3
"""直接解析 MonoBehaviour 原始字节，统计脚本类名（绕过类型树缺失）。

用法:
  python debug_mono_raw.py <level文件> [数据目录]
"""
from __future__ import annotations

import collections
import os
import struct
import sys

import UnityPy


def parse_pptr(raw: bytes, off: int) -> tuple[int, int]:
    file_id, path_id = struct.unpack_from("<iq", raw, off)
    return file_id, path_id


def skip_string(raw: bytes, off: int) -> int:
    (n,) = struct.unpack_from("<i", raw, off)
    off += 4 + n
    return (off + 3) & ~3


def main() -> int:
    path = sys.argv[1]
    data_dir = sys.argv[2] if len(sys.argv) > 2 else os.path.dirname(path)
    env = UnityPy.load(path)
    ext = []
    for key, f in env.files.items():
        if os.path.basename(key) == os.path.basename(path):
            ext = [getattr(e, "path", str(e)) for e in (getattr(f, "externals", None) or [])]
            break
    envs: dict[int, UnityPy.Environment] = {0: env}
    cls_cache: dict[tuple[int, int], str] = {}

    def load_ext(fid: int):
        if fid not in envs:
            if not (1 <= fid <= len(ext)):
                return None
            p = os.path.join(data_dir, os.path.basename(ext[fid - 1]))
            if not os.path.exists(p):
                return None
            envs[fid] = UnityPy.load(p)
        return envs[fid]

    def class_of(fid: int, pid: int) -> str:
        key = (fid, pid)
        if key in cls_cache:
            return cls_cache[key]
        e = load_ext(fid)
        name = "<none>"
        if e is not None:
            for o in e.objects:
                if o.path_id == pid:
                    try:
                        name = getattr(o.read(), "m_ClassName", "") or "<empty>"
                    except Exception as exc:  # noqa: BLE001
                        name = f"<err {type(exc).__name__}>"
                    break
            else:
                name = f"<notfound {fid}:{pid}>"
        cls_cache[key] = name
        return name

    gos = {}
    for obj in env.objects:
        if obj.type.name == "GameObject":
            try:
                gos[obj.path_id] = getattr(obj.read(), "m_Name", "?")
            except Exception:
                pass

    counter = collections.Counter()
    named = []
    total = 0
    for obj in env.objects:
        if obj.type.name != "MonoBehaviour":
            continue
        total += 1
        try:
            raw = obj.get_raw_data()
        except Exception as exc:  # noqa: BLE001
            counter[f"<raw-fail {type(exc).__name__}>"] += 1
            continue
        if len(raw) < 28:
            counter["<short>"] += 1
            continue
        gfile, gpid = parse_pptr(raw, 0)
        sfile, spid = parse_pptr(raw, 16)
        if (sfile, spid) == (0, 0):
            # 尝试其它偏移（不同版本对齐）
            for cand in (12, 20, 24):
                if cand + 12 > len(raw):
                    continue
                cf, cp = parse_pptr(raw, cand)
                if cf or cp:
                    sfile, spid = cf, cp
                    break
        cname = class_of(sfile, spid)
        counter[cname] += 1
        gname = gos.get(gpid, "?")
        low = gname.lower()
        if any(k in low for k in ("shop", "market", "bazaar", "stall", "food", "santa", "snowman", "tree")):
            named.append((gname, cname, obj.path_id, gpid))
    print(f"MonoBehaviour total={total} distinct={len(counter)}")
    for name, cnt in counter.most_common(40):
        print(f"   {cnt:6d}  {name}")
    print("== 名称相关对象")
    for item in named[:80]:
        print("   ", item)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

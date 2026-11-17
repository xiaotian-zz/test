#!/usr/bin/env python3
"""扫描地图中挂载指定脚本（默认 Shop）的 GameObject、世界坐标与内部字符串。

用法:
  python scan_shop_points.py <rf4_x64_Data目录> [类名=Shop] [输出json]
"""
from __future__ import annotations

import json
import os
import re
import struct
import sys

import UnityPy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scan_newyear_maps import world_trs, yaw_of  # noqa: E402

PRINTABLE = re.compile(rb"[\x20-\x7e]{3,}")


def parse_pptr(raw: bytes, off: int) -> tuple[int, int]:
    return struct.unpack_from("<iq", raw, off)


def raw_strings(raw: bytes) -> list[str]:
    out = []
    for m in PRINTABLE.finditer(raw):
        try:
            out.append(m.group().decode("utf-8"))
        except Exception:
            pass
    return out


def main() -> int:
    data_dir = sys.argv[1]
    want = sys.argv[2] if len(sys.argv) > 2 else "Shop"
    out = sys.argv[3] if len(sys.argv) > 3 else os.path.join("artifacts", "shop_points.json")
    levels = sorted(
        [f for f in os.listdir(data_dir) if f.startswith("level") and os.path.isfile(os.path.join(data_dir, f))],
        key=lambda x: int(x[5:] or 0),
    )
    results = []
    for lv in levels:
        path = os.path.join(data_dir, lv)
        env = UnityPy.load(path)
        ext = []
        for key, f in env.files.items():
            if os.path.basename(key) == lv:
                ext = [getattr(e, "path", str(e)) for e in (getattr(f, "externals", None) or [])]
                break
        ext_envs: dict[int, UnityPy.Environment] = {}

        def load_ext(file_id: int):
            if file_id == 0:
                return env
            if file_id in ext_envs:
                return ext_envs[file_id]
            if not (1 <= file_id <= len(ext)):
                return None
            p = os.path.join(data_dir, os.path.basename(ext[file_id - 1]))
            if not os.path.exists(p):
                return None
            e = UnityPy.load(p)
            ext_envs[file_id] = e
            return e

        scripts: dict[tuple[int, int], str] = {}

        def script_class(fid: int, pid: int) -> str:
            key = (fid, pid)
            if key in scripts:
                return scripts[key]
            e = load_ext(fid)
            name = ""
            if e is not None:
                for o in e.objects:
                    if o.path_id == pid:
                        try:
                            name = getattr(o.read(), "m_ClassName", "") or ""
                        except Exception:
                            name = ""
                        break
            scripts[key] = name
            return name

        gos = {}
        gos_parent: dict[int, str] = {}
        nodes = {}
        tr_by_go = {}
        for obj in env.objects:
            if obj.type.name == "GameObject":
                try:
                    gos[obj.path_id] = getattr(obj.read(), "m_Name", "?")
                except Exception:
                    pass
            elif obj.type.name in ("Transform", "RectTransform"):
                d = obj.read()
                p, r, s = d.m_LocalPosition, d.m_LocalRotation, d.m_LocalScale
                nodes[obj.path_id] = type("N", (), {
                    "pos": (p.x, p.y, p.z),
                    "rot": (r.x, r.y, r.z, r.w),
                    "scale": (s.x, s.y, s.z),
                    "father": getattr(d, "m_Father", None),
                    "children": getattr(d, "m_Children", []),
                    "go": d.m_GameObject.path_id,
                })()
                try:
                    tr_by_go[d.m_GameObject.path_id] = obj.path_id
                except Exception:
                    pass

        def parent_chain(gid: int) -> list[str]:
            out = []
            tr_pid = tr_by_go.get(gid)
            cur = nodes.get(tr_pid) if tr_pid else None
            for _ in range(10):
                if cur is None:
                    break
                f = getattr(cur, "father", None)
                if f is None or f.path_id not in nodes:
                    break
                cur = nodes[f.path_id]
                out.append(gos.get(cur.go, "?"))
            return out

        cache: dict[int, tuple] = {}
        hits = []
        for obj in env.objects:
            if obj.type.name != "MonoBehaviour":
                continue
            try:
                raw = obj.get_raw_data()
            except Exception:
                continue
            if len(raw) < 28:
                continue
            gfid, gpid = parse_pptr(raw, 0)
            sfid, spid = parse_pptr(raw, 16)
            if (sfid, spid) == (0, 0):
                for cand in (12, 20, 24):
                    if cand + 12 > len(raw):
                        continue
                    cf, cp = parse_pptr(raw, cand)
                    if cf or cp:
                        sfid, spid = cf, cp
                        break
            if script_class(sfid, spid) != want:
                continue
            tr_pid = tr_by_go.get(gpid)
            wp, wq, ws = world_trs(tr_pid, nodes, cache) if tr_pid else ((0, 0, 0), (0, 0, 0, 1), (1, 1, 1))
            strings = [s for s in raw_strings(raw) if len(s) >= 4 and not s.startswith("$")]
            hits.append({
                "go": gos.get(gpid, "?"),
                "goPathId": gpid,
                "mbPathId": obj.path_id,
                "worldPos": [round(v, 3) for v in wp],
                "worldYaw": round(yaw_of(wq), 1),
                "worldScale": [round(v, 3) for v in ws],
                "parents": parent_chain(gpid),
                "strings": strings[:12],
            })
        if hits:
            print(f"== {lv} ({len(hits)})")
            for h in hits:
                print(
                    f"   {h['go']:<26} world=({h['worldPos'][0]:.2f},{h['worldPos'][1]:.2f},{h['worldPos'][2]:.2f}) "
                    f"yaw={h['worldYaw']} parents={' < '.join(h['parents'])} strings={h['strings']}"
                )
            results.append({"level": lv, "hits": hits})
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(results, fh, ensure_ascii=False, indent=2)
    print(f"写出 {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

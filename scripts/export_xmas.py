#!/usr/bin/env python3
"""从 24205 客户端导出新年集市的网格与贴图。

用法:
  python export_xmas.py <level26> <sharedassets5.assets> <输出目录>
"""
from __future__ import annotations

import json
import os
import struct
import sys

import UnityPy

TARGETS = (
    "christmas_tree_LOD0",
    "christmas_market_02_mesh_LOD0",
    "Snowman_LOD0",
    "chocolate_santa",
)

# Unity VertexAttribute format 0 = Float32；其余暂不处理
ATTRS = {0: ("position", 3, 0), 1: ("normal", 3, 12), 4: ("uv", 2, 44)}
ATTRS_MARKET = {0: ("position", 3, 0), 1: ("normal", 3, 12), 4: ("uv", 2, 40)}


def read_vec(buf: bytes, off: int, dim: int) -> tuple[float, ...]:
    return struct.unpack_from("<" + "f" * dim, buf, off)


def export_obj(mesh, out_path: str) -> int:
    vd = mesh.m_VertexData
    raw = bytes(vd.m_DataSize)
    vcount = vd.m_VertexCount
    stride = len(raw) // vcount if vcount else 0
    layout = ATTRS if stride >= 96 else ATTRS_MARKET
    subs = mesh.m_SubMeshes or []
    idx = bytes(mesh.m_IndexBuffer or b"")
    fmt = getattr(mesh, "m_IndexFormat", 0)
    is32 = fmt == 1 or (idx and len(idx) // max(1, sum(s.indexCount for s in subs)) == 4)

    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(f"# {mesh.m_Name} verts={vcount} stride={stride}\n")
        for i in range(vcount):
            base = i * stride
            p = read_vec(raw, base + layout[0][2], 3)
            n = read_vec(raw, base + layout[1][2], 3)
            uv = read_vec(raw, base + layout[4][2], 2)
            fh.write(f"v {p[0]:.5f} {p[1]:.5f} {p[2]:.5f}\n")
            fh.write(f"vn {n[0]:.5f} {n[1]:.5f} {n[2]:.5f}\n")
            fh.write(f"vt {uv[0]:.5f} {uv[1]:.5f}\n")
        for sm in subs:
            start = sm.firstByte
            count = sm.indexCount
            base_v = getattr(sm, "baseVertex", 0)
            step = 4 if is32 else 2
            code = "<I" if is32 else "<H"
            for k in range(0, count, 3):
                tri = []
                for t in range(3):
                    pos = start + (k + t) * step
                    if pos + step > len(idx):
                        break
                    (vi,) = struct.unpack_from(code, idx, pos)
                    tri.append(vi + base_v + 1)
                if len(tri) == 3:
                    fh.write(f"f {tri[0]}/{tri[0]}/{tri[0]} {tri[1]}/{tri[1]}/{tri[1]} {tri[2]}/{tri[2]}/{tri[2]}\n")
    return vcount


def export_texture(tex, out_dir: str, name: str) -> str | None:
    try:
        img = tex.image
        path = os.path.join(out_dir, f"{name}.png")
        img.save(path)
        return path
    except Exception as exc:  # noqa: BLE001
        print(f"   texture {name} failed: {exc}")
        return None


def main() -> int:
    level, sa5_path, out_dir = sys.argv[1], sys.argv[2], sys.argv[3]
    os.makedirs(out_dir, exist_ok=True)
    env_level = UnityPy.load(level)
    env_sa = UnityPy.load(sa5_path)
    sa_objs = {o.path_id: o for o in env_sa.objects}
    level_objs = {o.path_id: o for o in env_level.objects}
    result = []

    for obj in env_level.objects:
        if obj.type.name != "GameObject":
            continue
        data = obj.read()
        name = getattr(data, "m_Name", "")
        if name not in TARGETS:
            continue
        entry = {"name": name, "children": []}
        for comp in data.m_Component:
            ptr = comp.component if hasattr(comp, "component") else comp
            cobj = level_objs.get(ptr.path_id)
            if cobj is None:
                continue
            if cobj.type.name == "MeshFilter":
                try:
                    mesh_ptr = cobj.read().m_Mesh
                    mesh_obj = sa_objs.get(mesh_ptr.path_id)
                    if mesh_obj is None:
                        continue
                    mesh = mesh_obj.read()
                    obj_path = os.path.join(out_dir, f"{name}.obj")
                    n = export_obj(mesh, obj_path)
                    entry["obj"] = os.path.basename(obj_path)
                    entry["verts"] = n
                    print(f"{name}: obj 已导出 ({n} 顶点)")
                except Exception as exc:  # noqa: BLE001
                    print(f"{name}: mesh 导出失败 {exc}")
            elif cobj.type.name == "MeshRenderer":
                try:
                    rend = cobj.read()
                    for mat_ptr in rend.m_Materials:
                        mat_obj = sa_objs.get(mat_ptr.path_id)
                        if mat_obj is None:
                            continue
                        mat = mat_obj.read()
                        props = getattr(mat, "m_SavedProperties", None)
                        if not props:
                            continue
                        texs = getattr(props, "m_TexEnvs", []) or []
                        for item in texs:
                            if isinstance(item, (tuple, list)) and len(item) >= 2:
                                key, val = item[0], item[1]
                            else:
                                key = getattr(item, "first", None)
                                val = getattr(item, "second", None)
                            if key != "_MainTex":
                                continue
                            tex_ptr = getattr(val, "m_Texture", None)
                            if tex_ptr is None:
                                continue
                            tex_obj = sa_objs.get(tex_ptr.path_id)
                            if tex_obj is None:
                                continue
                            tex = tex_obj.read()
                            tex_name = f"{name}_{getattr(tex,'m_Name','tex')}"
                            p = export_texture(tex, out_dir, tex_name)
                            if p:
                                entry.setdefault("textures", []).append(os.path.basename(p))
                                print(f"{name}: 贴图 {os.path.basename(p)}")
                except Exception as exc:  # noqa: BLE001
                    print(f"{name}: 材质读取失败 {exc}")
        result.append(entry)

    with open(os.path.join(out_dir, "index.json"), "w", encoding="utf-8") as fh:
        json.dump(result, fh, ensure_ascii=False, indent=2)
    print("done:", len(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

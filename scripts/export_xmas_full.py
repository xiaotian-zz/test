#!/usr/bin/env python3
"""按原活动层级导出 level26 的 CHRISTMAS 全部对象（网格/材质/贴图/变换）。

用法:
  py -3.12 scripts/export_xmas_full.py [输出目录]
"""
from __future__ import annotations

import json
import os
import struct
import sys

import UnityPy

BASE = r"D:\Steam\steamapps\content\app_766570\depot_766571\rf4_x64_Data"
LEVEL = os.path.join(BASE, "level26")
ROOT_NAME = "CHRISTMAS"
OUT = r"f:\rea\artifacts\xmas_full"
ONLY = set()


def apply_args() -> None:
    global OUT, ONLY
    args = [a for a in sys.argv[1:] if not a.startswith("--only")]
    if args:
        OUT = args[0]
    for a in sys.argv[1:]:
        if a.startswith("--only="):
            ONLY = set(x for x in a.split("=", 1)[1].split(",") if x)

ATTRS = {
    "pos": (0, 3),
    "nrm": (12, 3),
    "uv": (44, 2),
}


def f3(v) -> list[float]:
    return [round(float(v.x), 5), round(float(v.y), 5), round(float(v.z), 5)]


def f4(v) -> list[float]:
    return [round(float(v.x), 5), round(float(v.y), 5), round(float(v.z), 5), round(float(v.w), 5)]


class Exporter:
    def __init__(self) -> None:
        self.by_path: dict[str, tuple[dict[int, object], list[str]]] = {}
        self.level_objs, self.level_ext = self.load_file(LEVEL)
        self.local = dict(self.level_objs)
        self.gos: dict[int, object] = {}
        self.trs: dict[int, object] = {}
        self.tr_by_go: dict[int, int] = {}
        for pid, obj in self.level_objs.items():
            t = obj.type.name
            if t == "GameObject":
                self.gos[pid] = obj
            elif t in ("Transform", "RectTransform"):
                self.trs[pid] = obj
        for pid, obj in self.gos.items():
            d = obj.read()
            for c in d.m_Component:
                p = c.component if hasattr(c, "component") else c
                if p.path_id in self.trs:
                    self.tr_by_go[pid] = p.path_id
                    break
        self.mesh_ids: dict[tuple, int] = {}
        self.meshes: list[dict] = []
        self.tex_ids: dict[tuple, int] = {}
        self.textures: list[dict] = []
        self.mat_ids: dict[tuple, int] = {}
        self.materials: list[dict] = []

    def load_file(self, path: str) -> tuple[dict[int, object], list[str]]:
        if path in self.by_path:
            return self.by_path[path]
        objs: dict[int, object] = {}
        exts: list[str] = []
        try:
            e = UnityPy.load(path)
            objs = {o.path_id: o for o in e.objects}
            exts = [x.path for x in list(e.files.values())[0].externals]
        except Exception as exc:  # noqa: BLE001
            print(f"   load {path} failed: {exc}")
        self.by_path[path] = (objs, exts)
        return objs, exts

    def ptr_vals(self, ptr) -> tuple[int, int]:
        if isinstance(ptr, dict):
            return int(ptr.get("m_FileID", 0) or 0), int(ptr.get("m_PathID", 0) or 0)
        return int(getattr(ptr, "file_id", 0) or 0), int(getattr(ptr, "path_id", 0) or 0)

    def resolve2(self, owner: str, fid: int, pid: int):
        if fid == 0:
            objs = self.local if owner == LEVEL else self.load_file(owner)[0]
            return objs.get(pid), owner
        exts = self.level_ext if owner == LEVEL else self.load_file(owner)[1]
        if fid > len(exts):
            return None, owner
        p = os.path.join(BASE, exts[fid - 1])
        return self.load_file(p)[0].get(pid), p

    def get_ptr(self, ptr, owner: str):
        fid, pid = self.ptr_vals(ptr)
        return self.resolve2(owner, fid, pid)[0]

    def dump_texture(self, ptr, owner: str) -> int | None:
        fid, pid = self.ptr_vals(ptr)
        obj, path = self.resolve2(owner, fid, pid)
        if obj is None or obj.type.name != "Texture2D":
            return None
        key = (path, pid)
        if key in self.tex_ids:
            return self.tex_ids[key]
        tid = len(self.textures)
        self.tex_ids[key] = tid
        name = f"tex{tid}"
        rel = None
        try:
            img = obj.read().image
            rel = f"textures/{name}.png"
            img.save(os.path.join(OUT, rel))
        except Exception as exc:  # noqa: BLE001
            print(f"   texture {name} failed: {exc}")
        self.textures.append({"id": tid, "file": rel})
        return tid

    def dump_material(self, ptr, owner: str) -> int | None:
        fid, pid = self.ptr_vals(ptr)
        obj, path = self.resolve2(owner, fid, pid)
        if obj is None:
            return None
        key = (path, pid)
        if key in self.mat_ids:
            return self.mat_ids[key]
        mid = len(self.materials)
        self.mat_ids[key] = mid
        entry = {"id": mid, "color": [1.0, 1.0, 1.0, 1.0], "tex": None, "shader": "", "name": ""}
        try:
            t = obj.read_typetree()
            entry["name"] = t.get("m_Name", "")
            sh = self.get_ptr(t.get("m_Shader") or {}, path)
            if sh is not None:
                try:
                    st = sh.read_typetree()
                    entry["shader"] = st.get("m_Name") or (st.get("m_ParsedForm") or {}).get("m_Name", "")
                except Exception:  # noqa: BLE001
                    pass
            sp = t.get("m_SavedProperties") or {}
            for item in sp.get("m_Colors") or []:
                if not isinstance(item, (tuple, list)) or len(item) < 2:
                    continue
                k, v = item[0], item[1]
                if k == "_Color" and isinstance(v, dict):
                    entry["color"] = [round(float(v.get("r", 1)), 4), round(float(v.get("g", 1)), 4), round(float(v.get("b", 1)), 4), round(float(v.get("a", 1)), 4)]
            for item in sp.get("m_TexEnvs") or []:
                if not isinstance(item, (tuple, list)) or len(item) < 2:
                    continue
                k, v = item[0], item[1]
                if k not in ("_MainTex", "_BaseMap") or not isinstance(v, dict):
                    continue
                tp = v.get("m_Texture")
                if not tp:
                    continue
                tid = self.dump_texture(tp, path)
                if tid is not None:
                    entry["tex"] = tid
                    break
        except Exception as exc:  # noqa: BLE001
            print(f"   material {mid} failed: {exc}")
        self.materials.append(entry)
        return mid

    def dump_mesh(self, ptr, sub: int, mat: int | None, owner: str = LEVEL) -> int | None:
        fid, pid = self.ptr_vals(ptr)
        obj = self.get_ptr(ptr, owner)
        if obj is None or obj.type.name != "Mesh":
            return None
        key = (owner, fid, pid, sub)
        if key in self.mesh_ids:
            return self.mesh_ids[key]
        try:
            mesh = obj.read()
            vd = mesh.m_VertexData
            vcount = int(vd.m_VertexCount)
            raw = bytes(vd.m_DataSize)
            if not raw or len(raw) < vcount * 12:
                raw = self.stream_data(mesh)
            stride = len(raw) // vcount if vcount else 0
            if stride <= 0:
                return None
            chans = list(getattr(vd, "m_Channels", []) or [])
            nrm_off, nrm_fmt, nrm_dim = 12, 0, 3
            uv_off, uv_fmt, uv_dim = 44, 0, 2
            try:
                if len(chans) > 1:
                    nrm_off, nrm_fmt = int(chans[1].offset), int(chans[1].format)
                if len(chans) > 4:
                    uv_off, uv_fmt = int(chans[4].offset), int(chans[4].format)
                    d = int(chans[4].dimension)
                    uv_dim = d if 2 <= d <= 4 else 2
            except Exception:  # noqa: BLE001
                pass
            subs = mesh.m_SubMeshes or []
            if sub >= len(subs):
                return None
            sm = subs[sub]
            idx = bytes(mesh.m_IndexBuffer or b"")
            fmt = int(getattr(mesh, "m_IndexFormat", 0) or 0)
            is32 = fmt == 1
            step = 4 if is32 else 2
            code = "<I" if is32 else "<H"
            start = int(sm.firstByte)
            count = int(sm.indexCount)
            base_v = int(getattr(sm, "baseVertex", 0) or 0)
            tris: list[int] = []
            for k in range(0, count - 2, 3):
                ok = True
                for t in range(3):
                    pos = start + (k + t) * step
                    if pos + step > len(idx):
                        ok = False
                        break
                    (vi,) = struct.unpack_from(code, idx, pos)
                    vi += base_v
                    if vi < 0 or vi >= vcount:
                        ok = False
                        break
                    tris.append(vi)
                if not ok:
                    tris = tris[: len(tris) // 3 * 3]
                    break
            if not tris:
                return None
            mid = len(self.meshes)
            self.mesh_ids[key] = mid
            rel = f"meshes/{mid}.bin"
            with open(os.path.join(OUT, rel), "wb") as fh:
                fh.write(struct.pack("<II", vcount, len(tris) // 3))
                for i in range(vcount):
                    fh.write(raw[i * stride : i * stride + 12])
                for i in range(vcount):
                    v = self.read_attr(raw, i * stride + nrm_off, nrm_fmt, nrm_dim)
                    v = (list(v) + [0.0, 0.0, 0.0])[:3]
                    fh.write(struct.pack("<3f", *v))
                for i in range(vcount):
                    v = self.read_attr(raw, i * stride + uv_off, uv_fmt, uv_dim)
                    v = (list(v) + [0.0, 0.0])[:2]
                    fh.write(struct.pack("<2f", *v))
                fh.write(struct.pack("<%di" % len(tris), *tris))
            self.meshes.append({"id": mid, "vcount": vcount, "tcount": len(tris) // 3, "bin": rel, "material": mat, "name": getattr(mesh, "m_Name", "")})
            return mid
        except Exception as exc:  # noqa: BLE001
            print(f"   mesh {getattr(ptr,'path_id','?')} sub{sub} failed: {exc}")
            return None

    def read_attr(self, raw: bytes, base: int, fmt: int, dim: int):
        if fmt == 1:  # Float16
            return struct.unpack_from("<%de" % dim, raw, base)
        if fmt == 2:  # UNorm8
            return tuple(raw[base + i] / 255.0 for i in range(dim))
        if fmt == 3:  # SNorm8
            out = []
            for i in range(dim):
                b = raw[base + i]
                out.append((b - 256 if b > 127 else b) / 127.0)
            return tuple(out)
        return struct.unpack_from("<%df" % dim, raw, base)

    def stream_data(self, mesh) -> bytes:
        sd = getattr(mesh, "m_StreamData", None)
        if not sd:
            return b""
        path = getattr(sd, "path", "") or ""
        if not path:
            return b""
        p = os.path.join(BASE, os.path.basename(path))
        if not os.path.exists(p):
            return b""
        off = int(getattr(sd, "offset", 0))
        size = int(getattr(sd, "size", 0))
        with open(p, "rb") as fh:
            fh.seek(off)
            return fh.read(size)

    def node(self, tr_pid: int) -> dict | None:
        tr_obj = self.trs.get(tr_pid)
        if tr_obj is None:
            return None
        d = tr_obj.read()
        go_pid = d.m_GameObject.path_id
        go = self.gos.get(go_pid)
        if go is None:
            return None
        gd = go.read()
        node = {
            "name": gd.m_Name,
            "pos": f3(d.m_LocalPosition),
            "rot": f4(d.m_LocalRotation),
            "scale": f3(d.m_LocalScale),
            "children": [],
        }
        for c in gd.m_Component:
            p = c.component if hasattr(c, "component") else c
            co = self.local.get(p.path_id)
            if co is None:
                continue
            t = co.type.name
            if t == "MeshFilter":
                try:
                    mf = co.read()
                    mp = mf.m_Mesh
                    rend = self.find_renderer(gd)
                    if rend is not None:
                        mats = list(getattr(rend, "m_Materials", []) or [])
                        for si in range(len(mats) or 1):
                            mat = self.dump_material(mats[si], LEVEL) if si < len(mats) else None
                            mid = self.dump_mesh(mp, si, mat, LEVEL)
                            if mid is not None:
                                node.setdefault("renders", []).append({"mesh": mid, "mat": mat})
                except Exception as exc:  # noqa: BLE001
                    print(f"   mf {gd.m_Name} failed: {exc}")
            elif t == "SkinnedMeshRenderer":
                try:
                    smr = co.read()
                    mats = list(getattr(smr, "m_Materials", []) or [])
                    for si in range(len(mats) or 1):
                        mat = self.dump_material(mats[si], LEVEL) if si < len(mats) else None
                        mid = self.dump_mesh(smr.m_Mesh, si, mat, LEVEL)
                        if mid is not None:
                            node.setdefault("renders", []).append({"mesh": mid, "mat": mat, "skinned": True})
                except Exception as exc:  # noqa: BLE001
                    print(f"   smr {gd.m_Name} failed: {exc}")
        for ch in d.m_Children:
            sub = self.node(ch.path_id)
            if sub is not None:
                node["children"].append(sub)
        return node

    def find_renderer(self, gd):
        for c in gd.m_Component:
            p = c.component if hasattr(c, "component") else c
            co = self.local.get(p.path_id)
            if co is not None and co.type.name == "MeshRenderer":
                try:
                    return co.read()
                except Exception:  # noqa: BLE001
                    return None
        return None


def main() -> int:
    apply_args()
    os.makedirs(os.path.join(OUT, "meshes"), exist_ok=True)
    os.makedirs(os.path.join(OUT, "textures"), exist_ok=True)
    ex = Exporter()
    root_tr = None
    for pid, obj in ex.gos.items():
        if obj.read().m_Name == ROOT_NAME:
            root_tr = ex.tr_by_go.get(pid)
            break
    if root_tr is None:
        print("未找到 CHRISTMAS 根")
        return 1
    tree = ex.node(root_tr)
    if ONLY:
        tree["children"] = [c for c in tree["children"] if c["name"] in ONLY]
    with open(os.path.join(OUT, "manifest.json"), "w", encoding="utf-8") as fh:
        json.dump({"root": tree, "meshes": ex.meshes, "materials": ex.materials, "textures": ex.textures}, fh, ensure_ascii=False, indent=1)

    def count(n):
        return 1 + sum(count(c) for c in n.get("children", []))

    total_v = sum(m["vcount"] for m in ex.meshes)
    total_t = sum(m["tcount"] for m in ex.meshes)
    print(f"objects={count(tree)} meshes={len(ex.meshes)} materials={len(ex.materials)} textures={len(ex.textures)}")
    print(f"verts={total_v} tris={total_t}")
    print("out:", OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

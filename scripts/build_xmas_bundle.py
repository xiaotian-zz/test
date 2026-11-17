#!/usr/bin/env python3
"""以 lures_wta 为骨架，重建只含新年集市所需资源的小型 AssetBundle。

不复制原 depot（那个包很大），只用骨架包的类型表 + manifest 的网格数据重新生成
GameObject / Transform / MeshFilter / MeshRenderer / Mesh / Material 对象。

用法:
  py -3.12 scripts/build_xmas_bundle.py [--mesh-limit N] [--out 路径]
"""
from __future__ import annotations

import copy
import json
import os
import struct
import sys

import UnityPy
from UnityPy.enums import ClassIDType
from UnityPy.files.ObjectReader import ObjectReader
from UnityPy.helpers.TypeTreeHelper import write_typetree
from UnityPy.streams import EndianBinaryWriter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKELETON = r"F:\RF4\Game\rf4_x64_Data\Data\lures_wta"
DATA_DIR = os.path.join(ROOT, "artifacts", "xmas_stalls")
DEFAULT_OUT = os.path.join(ROOT, "artifacts", "xmas_stalls.bundle")
CONTAINER_KEY = "assets/rf4local/xmas_stalls.prefab"

KEEP_CLASSES = (48, 115)  # Shader / MonoScript：材质要引用的基础设施


def pptr(pid: int) -> dict:
    return {"m_FileID": 0, "m_PathID": pid}


class IdGen:
    def __init__(self) -> None:
        self.n = 1000000

    def __call__(self) -> int:
        self.n += 1
        return self.n


def load_skeleton():
    env = UnityPy.load(SKELETON)
    bf = env.file
    sf = list(bf.files.values())[0]
    return bf, sf


def collect_types(sf):
    """class_id -> (type_id, SerializedType)"""
    out = {}
    for i, t in enumerate(sf.types):
        out.setdefault(t.class_id, (i, t))
    return out


def read_mesh(info: dict) -> dict:
    path = os.path.join(DATA_DIR, info["bin"])
    raw = open(path, "rb").read()
    vc, tc = info["vcount"], info["tcount"]
    need = 8 + vc * 32 + tc * 12
    if len(raw) != need:
        raise ValueError(f"mesh {info['id']} 长度不符: {len(raw)} != {need}")
    off = 8
    pos = raw[off:off + vc * 12]
    off += vc * 12
    nrm = raw[off:off + vc * 12]
    off += vc * 12
    uvs = raw[off:off + vc * 8]
    off += vc * 8
    idx = raw[off:off + tc * 12]

    # 逐顶点重排为 stride 32：pos(12) + normal(12) + uv(8)
    buf = bytearray(vc * 32)
    for i in range(vc):
        buf[i * 32:i * 32 + 12] = pos[i * 12:i * 12 + 12]
        buf[i * 32 + 12:i * 32 + 24] = nrm[i * 12:i * 12 + 12]
        buf[i * 32 + 24:i * 32 + 32] = uvs[i * 8:i * 8 + 8]

    xs = [struct.unpack_from("<f", pos, i * 12)[0] for i in range(0, vc, 97)]
    ys = [struct.unpack_from("<f", pos, i * 12 + 4)[0] for i in range(0, vc, 97)]
    zs = [struct.unpack_from("<f", pos, i * 12 + 8)[0] for i in range(0, vc, 97)]
    lo = (min(xs), min(ys), min(zs))
    hi = (max(xs), max(ys), max(zs))
    aabb = {
        "m_Center": {"x": (lo[0] + hi[0]) / 2, "y": (lo[1] + hi[1]) / 2, "z": (lo[2] + hi[2]) / 2},
        "m_Extent": {"x": (hi[0] - lo[0]) / 2, "y": (hi[1] - lo[1]) / 2, "z": (hi[2] - lo[2]) / 2},
    }
    return {
        "vc": vc,
        "tc": tc,
        "vdata": bytes(buf),
        "ibuf": list(idx),
        "aabb": aabb,
    }


def make_channels() -> list:
    ch = [{"stream": 0, "offset": 0, "format": 0, "dimension": 0} for _ in range(14)]
    ch[0] = {"stream": 0, "offset": 0, "format": 0, "dimension": 3}   # position
    ch[1] = {"stream": 0, "offset": 12, "format": 0, "dimension": 3}  # normal
    ch[4] = {"stream": 0, "offset": 24, "format": 0, "dimension": 2}  # uv0
    return ch


def build(sf, manifest, mesh_limit=None):
    types = collect_types(sf)
    tpl = {}
    for pid, o in sf.objects.items():
        cid = int(o.type)
        if cid in (1, 4, 33, 23, 43, 21, 142) and cid not in tpl:
            tpl[cid] = copy.deepcopy(o.read_typetree())

    keep = {}
    for pid, o in sf.objects.items():
        if int(o.type) in KEEP_CLASSES:
            o.data = o.get_raw_data()
            keep[pid] = o

    shader_pid = next(pid for pid, o in sf.objects.items() if int(o.type) == 48)

    idg = IdGen()
    nodes = []
    meshes = {}
    mats = {}

    mesh_infos = {m["id"]: m for m in manifest["meshes"]}
    mat_infos = {m["id"]: m for m in manifest["materials"]}

    used_meshes = set()
    used_mats = set()

    def make_node(node, father_tr):
        go = idg()
        tr = idg()
        rec = {
            "go": go,
            "tr": tr,
            "father": father_tr,
            "name": node["name"],
            "pos": node["pos"],
            "rot": node["rot"],
            "scale": node["scale"],
            "children": [],
            "renders": [],
        }
        for r in node.get("renders", []):
            rec["renders"].append({
                "go": idg(),
                "tr": idg(),
                "mf": idg(),
                "mr": idg(),
                "mesh": r["mesh"],
                "mat": r.get("mat"),
            })
            used_meshes.add(r["mesh"])
            if r.get("mat") is not None:
                used_mats.add(r["mat"])
        for c in node.get("children", []):
            rec["children"].append(make_node(c, tr))
        nodes.append(rec)
        return rec

    root = make_node(manifest["root"], None)

    if mesh_limit:
        used_meshes = set(sorted(used_meshes)[:mesh_limit])

    for mid in sorted(used_meshes):
        meshes[mid] = idg()
    for mid in sorted(used_mats):
        mats[mid] = idg()

    bundle_pid = idg()
    root_go = root["go"]

    objs = []

    def add(pid, cid, tree):
        objs.append((pid, cid, tree))

    # --- 网格 ---
    for mid, pid in meshes.items():
        info = read_mesh(mesh_infos[mid])
        t = copy.deepcopy(tpl[43])
        t["m_Name"] = mesh_infos[mid].get("name") or f"xmas_mesh_{mid}"
        t["m_SubMeshes"] = [{
            "firstByte": 0,
            "indexCount": info["tc"] * 3,
            "topology": 0,
            "baseVertex": 0,
            "firstVertex": 0,
            "vertexCount": info["vc"],
            "localAABB": info["aabb"],
        }]
        t["m_Shapes"] = {"vertices": [], "shapes": [], "channels": [], "fullWeights": []}
        t["m_BindPose"] = []
        t["m_BoneNameHashes"] = []
        t["m_RootBoneNameHash"] = 0
        t["m_BonesAABB"] = []
        t["m_VariableBoneCountWeights"] = {"m_Data": []}
        t["m_MeshCompression"] = 0
        t["m_IsReadable"] = 0
        t["m_KeepVertices"] = 0
        t["m_KeepIndices"] = 0
        t["m_IndexFormat"] = 1
        t["m_IndexBuffer"] = info["ibuf"]
        t["m_VertexData"] = {
            "m_VertexCount": info["vc"],
            "m_Channels": make_channels(),
            "m_DataSize": info["vdata"],
        }
        t["m_LocalAABB"] = info["aabb"]
        t["m_MeshUsageFlags"] = 0
        t["m_CookingOptions"] = 30
        t["m_BakedConvexCollisionMesh"] = []
        t["m_BakedTriangleCollisionMesh"] = []
        t["m_MeshMetrics[0]"] = 1.0
        t["m_MeshMetrics[1]"] = 1.0
        t["m_StreamData"] = {"offset": 0, "size": 0, "path": ""}
        add(pid, 43, t)

    # --- 材质 ---
    for mid, pid in mats.items():
        info = mat_infos[mid]
        t = copy.deepcopy(tpl[21])
        t["m_Name"] = info.get("name") or f"xmas_mat_{mid}"
        t["m_Shader"] = pptr(shader_pid)
        t["m_ValidKeywords"] = []
        t["m_InvalidKeywords"] = []
        props = t.setdefault("m_SavedProperties", {})
        texenvs = props.get("m_TexEnvs") or []
        for pair in texenvs:
            if pair[0] == "_MainTex":
                pair[1]["m_Texture"] = pptr(0)
        props["m_TexEnvs"] = texenvs
        cols = props.get("m_Colors") or []
        r, g, b, a = info.get("color") or [1, 1, 1, 1]
        for pair in cols:
            if pair[0] == "_Color":
                pair[1].update({"r": r, "g": g, "b": b, "a": a})
        props["m_Colors"] = cols
        add(pid, 21, t)

    # --- 节点层级 ---
    def emit(rec):
        comps = [{"component": pptr(rec["tr"])}]
        for r in rec["renders"]:
            comps.append({"component": pptr(r["mf"])})
            comps.append({"component": pptr(r["mr"])})
        for c in rec["children"]:
            comps.append({"component": pptr(c["tr"])})
        go_tree = copy.deepcopy(tpl[1])
        go_tree["m_Component"] = comps
        go_tree["m_Layer"] = 0
        go_tree["m_Name"] = rec["name"]
        go_tree["m_Tag"] = 0
        go_tree["m_IsActive"] = True
        add(rec["go"], 1, go_tree)

        children = [pptr(c["tr"]) for c in rec["children"]] + [pptr(r["tr"]) for r in rec["renders"]]
        tr_tree = copy.deepcopy(tpl[4])
        tr_tree["m_GameObject"] = pptr(rec["go"])
        tr_tree["m_LocalRotation"] = {"x": rec["rot"][0], "y": rec["rot"][1], "z": rec["rot"][2], "w": rec["rot"][3]}
        tr_tree["m_LocalPosition"] = {"x": rec["pos"][0], "y": rec["pos"][1], "z": rec["pos"][2]}
        tr_tree["m_LocalScale"] = {"x": rec["scale"][0], "y": rec["scale"][1], "z": rec["scale"][2]}
        tr_tree["m_Children"] = children
        tr_tree["m_Father"] = pptr(rec["father"]) if rec["father"] else pptr(0)
        add(rec["tr"], 4, tr_tree)

        for r in rec["renders"]:
            rgo = copy.deepcopy(tpl[1])
            rgo["m_Component"] = [
                {"component": pptr(r["tr"])},
                {"component": pptr(r["mf"])},
                {"component": pptr(r["mr"])},
            ]
            rgo["m_Layer"] = 0
            rgo["m_Name"] = f"{rec['name']}_mesh"
            rgo["m_Tag"] = 0
            rgo["m_IsActive"] = True
            add(r["go"], 1, rgo)

            rtr = copy.deepcopy(tpl[4])
            rtr["m_GameObject"] = pptr(r["go"])
            rtr["m_LocalRotation"] = {"x": 0.0, "y": 0.0, "z": 0.0, "w": 1.0}
            rtr["m_LocalPosition"] = {"x": 0.0, "y": 0.0, "z": 0.0}
            rtr["m_LocalScale"] = {"x": 1.0, "y": 1.0, "z": 1.0}
            rtr["m_Children"] = []
            rtr["m_Father"] = pptr(rec["tr"])
            add(r["tr"], 4, rtr)

            rt = r["mat"]
            mesh_pid = meshes.get(r["mesh"], 0)
            mat_pid = mats.get(rt, 0) if rt is not None else 0
            mf = copy.deepcopy(tpl[33])
            mf["m_GameObject"] = pptr(r["go"])
            mf["m_Mesh"] = pptr(mesh_pid)
            add(r["mf"], 33, mf)

            mr = copy.deepcopy(tpl[23])
            mr["m_GameObject"] = pptr(r["go"])
            mr["m_Materials"] = [pptr(mat_pid)] if mat_pid else []
            add(r["mr"], 23, mr)

        for c in rec["children"]:
            emit(c)

    emit(root)

    # --- AssetBundle ---
    ab = copy.deepcopy(tpl[142])
    ab["m_Name"] = "rf4local/xmas_stalls"
    ab["m_PreloadTable"] = [pptr(root_go)]
    ab["m_Container"] = [(CONTAINER_KEY, {
        "preloadIndex": 0,
        "preloadSize": 1,
        "asset": pptr(root_go),
    })]
    ab["m_MainAsset"] = {"preloadIndex": 0, "preloadSize": 1, "asset": pptr(root_go)}
    ab["m_RuntimeCompatibility"] = 1
    ab["m_AssetBundleName"] = "rf4local/xmas_stalls"
    ab["m_Dependencies"] = []
    ab["m_IsStreamedSceneAssetBundle"] = False
    ab["m_ExplicitDataLayout"] = 0
    ab["m_PathFlags"] = 0
    ab["m_SceneHashes"] = []
    add(bundle_pid, 142, ab)

    return objs, keep, types


def main() -> int:
    args = sys.argv[1:]
    mesh_limit = None
    out = DEFAULT_OUT
    for i, a in enumerate(args):
        if a == "--mesh-limit":
            mesh_limit = int(args[i + 1])
        elif a == "--out":
            out = args[i + 1]

    manifest = json.load(open(os.path.join(DATA_DIR, "manifest.json"), encoding="utf-8"))
    bf, sf = load_skeleton()
    objs, keep, types = build(sf, manifest, mesh_limit)
    print(f"新建对象 {len(objs)}，保留 {len(keep)}")

    sf.objects = dict(keep)
    for pid, cid, tree in objs:
        type_id, stype = types[cid]
        w = EndianBinaryWriter(endian=sf.header.endian)
        write_typetree(tree, stype.node, w, sf)
        data = w.bytes
        sf.objects[pid] = ObjectReader(
            sf, sf.reader, pid, type_id, stype, cid,
            ClassIDType(cid), 0, len(data), None, None, data,
        )

    blob = bf.save(packer="none")
    with open(out, "wb") as fh:
        fh.write(blob)
    print(f"输出 {out}  ({len(blob)/1048576:.2f} MB, {len(sf.objects)} 对象)")

    # 自校验：重新加载
    env2 = UnityPy.load(out)
    bf2 = env2.file
    sf2 = list(bf2.files.values())[0]
    counts = {}
    for o in sf2.objects.values():
        counts[int(o.type)] = counts.get(int(o.type), 0) + 1
    print("重载对象数", len(sf2.objects), counts)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

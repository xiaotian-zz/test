#!/usr/bin/env python3
"""原版原样搬运：把 24205 level24 里的 CHRISTMAS 层级 + 依赖闭包整体复制进自建 bundle。

- 跨文件 PPtr 按各自文件的 externals 解析
- path_id 全部重映射
- Texture2D 从 .resS 抽出原始压缩字节内嵌
- 类型树使用源文件自带的，保证字段一致
- MonoBehaviour 无法通用解析，跳过（只影响逻辑，不影响渲染）

输出: F:\\RF4\\Game\\rf4_x64_Data\\Data\\xmas_clone
"""
from __future__ import annotations

import os
import struct
import uuid
from collections import Counter

import UnityPy
from UnityPy.enums import ClassIDType
from UnityPy.files.ObjectReader import ObjectReader
from UnityPy.files.SerializedFile import SerializedType
from UnityPy.helpers.TypeTreeHelper import write_typetree
from UnityPy.streams import EndianBinaryWriter
from UnityPy.helpers.Tpk import get_typetree_node

STEAM = r"D:\Steam\steamapps\content\app_766570\depot_766571\rf4_x64_Data"
LEVEL = os.path.join(STEAM, "level24")
SKEL = r"F:\RF4\Game\rf4_x64_Data\Data\lures_wta"
OUT = os.environ.get("CLONE_OUT", r"F:\RF4\Game\rf4_x64_Data\Data\xmas_clone")
ROOT_PID = int(os.environ.get("CLONE_ROOT", "8634"))

RAW_TYPES = {"Mesh", "Shader", "AnimationClip", "MonoScript", "Avatar", "AnimatorController", "Texture2D"}
SKIP_TYPES = {
    "Camera", "ReflectionProbe", "AudioListener", "FlareLayer",
    "Shader" if os.environ.get("CLONE_NO_SHADER") else "",
    "AudioSource",
}

FILES: dict[str, object] = {}


def load_file(path):
    if path in FILES:
        return FILES[path]
    try:
        sf = UnityPy.load(path).file
        if not hasattr(sf, "objects"):
            sf = None
    except Exception:
        sf = None
    FILES[path] = sf
    return sf


env0 = UnityPy.load(LEVEL)
sf0 = env0.file
FILES[LEVEL] = sf0

_obj_cache = {}
_tree_cache = {}


def resolve(cur, fid):
    if fid == 0:
        return cur
    s = FILES.get(cur)
    if s is None:
        return None
    try:
        ext = s.externals[fid - 1].path
    except Exception:
        return None
    p = os.path.join(STEAM, ext.replace("/", os.sep))
    return p if os.path.exists(p) else None


def get_obj(path, pid):
    k = (path, pid)
    if k in _obj_cache:
        return _obj_cache[k]
    s = load_file(path)
    o = s.objects.get(pid) if s is not None else None
    _obj_cache[k] = o
    return o


def get_tree(path, pid):
    k = (path, pid)
    if k in _tree_cache:
        return _tree_cache[k]
    o = get_obj(path, pid)
    t = None
    if o is not None:
        try:
            t = o.read_typetree()
        except Exception:
            t = None
    _tree_cache[k] = t
    return t


def iter_pptrs(v):
    if isinstance(v, dict):
        if "m_FileID" in v and "m_PathID" in v and len(v) <= 3:
            yield v
            return
        for x in v.values():
            yield from iter_pptrs(x)
    elif isinstance(v, (list, tuple)):
        for x in v:
            yield from iter_pptrs(x)


# ---------- BFS ----------
collected = {}
mb_class = {}
queue = [(LEVEL, ROOT_PID)]
missing = Counter()
while queue:
    key = queue.pop()
    if key in collected:
        continue
    path, pid = key
    o = get_obj(path, pid)
    if o is None:
        missing["no_object"] += 1
        continue
    tname = o.type.name
    collected[key] = None
    if tname == "MonoBehaviour":
        # 无法通用解析，手工读头部；只有 Shop 需要（其余脚本不搬）
        raw = o.get_raw_data()
        if len(raw) >= 28:
            sfid, spid = struct.unpack("<iq", raw[16:28])
            tgt = resolve(path, sfid)
            cls = ""
            if tgt is not None:
                mo = get_obj(tgt, spid)
                if mo is not None:
                    try:
                        cls = mo.read_typetree().get("m_ClassName") or ""
                    except Exception:
                        pass
            if cls == "Shop":
                mb_class[key] = cls
                if spid and tgt is not None and (tgt, spid) not in collected:
                    queue.append((tgt, spid))
        continue
    if tname in RAW_TYPES or tname in SKIP_TYPES:
        continue
    t = get_tree(path, pid)
    if t is None:
        missing["no_tree:" + tname] += 1
        continue
    pp_list = []
    if tname == "Transform":
        for k, v in t.items():
            if k != "m_Father":
                pp_list.extend(iter_pptrs(v))
    else:
        pp_list = list(iter_pptrs(t))
    for pp in pp_list:
        pf, ppid = int(pp.get("m_FileID") or 0), int(pp.get("m_PathID") or 0)
        if not ppid:
            continue
        tgt = resolve(path, pf)
        if tgt is None:
            missing["unresolved_file:" + str(pf)] += 1
            continue
        if (tgt, ppid) not in collected:
            queue.append((tgt, ppid))

print("collected", len(collected), "missing", dict(missing))
cnt = Counter(get_obj(p, i).type.name for p, i in collected if get_obj(p, i) is not None)
print("types", dict(cnt))

# ---------- 类型表 ----------
# ---------- 骨架容器（先加载，取同版本类型条目） ----------
skel_env = UnityPy.load(SKEL)
bf = skel_env.file
sf = [v for v in bf.files.values() if hasattr(v, "objects")][0]
_lures = {t.class_id: t for t in sf.types}
ab_tpl = None
for o in sf.objects.values():
    if o.type.name == "AssetBundle":
        ab_tpl = o.read_typetree()
        break
assert ab_tpl is not None

ver = sf0.version
for t in sf0.types:
    if getattr(t, "node", None) is None:
        try:
            t.node = get_typetree_node(t.class_id, ver)
        except Exception:
            pass

types = []
type_index = {}
for t in list(sf0.types):
    if getattr(t, "node", None) is None or t.class_id in type_index:
        continue
    type_index[t.class_id] = len(types)
    types.append(t)

need = {}
for key in collected:
    o = get_obj(*key)
    if o is not None and int(o.type) not in type_index:
        need[int(o.type)] = o.type.name
for cid in list(need):
    src = _lures.get(cid)
    if src is None:
        continue
    type_index[cid] = len(types)
    types.append(src)
print("types built", len(types), "need", need, "unresolved", [c for c in need if c not in type_index])

# ---------- 重映射 ----------
writable = []
for key in collected:
    o = get_obj(*key)
    if o is None or o.type.name in SKIP_TYPES:
        continue
    if o.type.name == "MonoBehaviour" and key not in mb_class:
        continue
    if int(o.type) not in type_index:
        continue
    writable.append(key)

new_ids = {}
nxt = 5_000_000
for key in writable:
    new_ids[key] = nxt
    nxt += 1
print("writable", len(writable), "of", len(collected))


def rewrite_all(v):
    if isinstance(v, dict):
        if "m_FileID" in v and "m_PathID" in v and len(v) <= 3:
            pf, ppid = int(v.get("m_FileID") or 0), int(v.get("m_PathID") or 0)
            v["m_FileID"] = 0
            v["m_PathID"] = new_ids.get((_cur_path, pf), 0) if False else 0
            return
        for x in v.values():
            rewrite_all(x)
    elif isinstance(v, (list, tuple)):
        for x in v:
            rewrite_all(x)


# ---------- 目标 bundle ----------
ver = sf0.version
no_node = []
for t in sf0.types:
    if getattr(t, "node", None) is None:
        try:
            t.node = get_typetree_node(t.class_id, ver)
        except Exception as e:
            no_node.append((t.class_id, type(e).__name__))
print("unity", sf0.unity_version, "no-node classes", no_node[:20])

for t in sf.types:
    if t.class_id == 142 and 142 not in type_index:
        type_index[142] = len(types)
        types.append(t)

sf.types = types
sf._enable_type_tree = False
sf.objects = {}
sf.externals = []
endian = sf.reader.endian


def remap_one(pp, cur_path):
    pf, ppid = int(pp.get("m_FileID") or 0), int(pp.get("m_PathID") or 0)
    if not ppid:
        pp["m_FileID"] = 0
        pp["m_PathID"] = 0
        return False
    tgt = resolve(cur_path, pf)
    n = new_ids.get((tgt, ppid)) if tgt else None
    pp["m_FileID"] = 0
    pp["m_PathID"] = n or 0
    return bool(n)


def remap_tree(tree, cur_path):
    if isinstance(tree, dict):
        if "m_FileID" in tree and "m_PathID" in tree and len(tree) <= 3:
            remap_one(tree, cur_path)
            return
        if isinstance(tree.get("m_Component"), list):
            keep = []
            for it in tree["m_Component"]:
                c = it.get("component") if isinstance(it, dict) else None
                if c is not None and remap_one(c, cur_path):
                    keep.append(it)
            tree["m_Component"] = keep
        for k, v in tree.items():
            if k == "m_Component":
                continue
            if k == "renderers" and isinstance(v, list):
                keep = []
                for it in v:
                    c = it.get("renderer") if isinstance(it, dict) else None
                    if c is not None and remap_one(c, cur_path):
                        keep.append(it)
                v[:] = keep
                continue
            remap_tree(v, cur_path)
    elif isinstance(tree, (list, tuple)):
        for x in tree:
            remap_tree(x, cur_path)


def res_bytes(src_path, tt):
    stream = tt.get("m_StreamData") or {}
    size = int(stream.get("size") or 0)
    if not size:
        return None
    off = int(stream.get("offset") or 0)
    sp = stream.get("path") or ""
    rp = os.path.join(os.path.dirname(src_path), os.path.basename(sp))
    if not os.path.exists(rp):
        return None
    with open(rp, "rb") as fh:
        fh.seek(off)
        return fh.read(size)


written = 0
tex_bytes = 0
skipped = Counter()
for (path, pid), newpid in new_ids.items():
    o = get_obj(path, pid)
    if o is None:
        continue
    tname = o.type.name
    cid = int(o.type)
    tid = type_index.get(cid)
    if tid is None:
        skipped["no_type:" + tname] += 1
        continue
    if tname in SKIP_TYPES:
        skipped["skip:" + tname] += 1
        continue
    node = types[tid].nodes
    if tname == "MonoBehaviour":
        # Shop：用 25034 的字段顺序重建，仅替换 storeID
        raw = o.get_raw_data()
        gp = struct.unpack("<q", raw[4:12])[0]
        sfid, spid = struct.unpack("<iq", raw[16:28])
        stgt = resolve(path, sfid)
        nlen = struct.unpack("<i", raw[28:32])[0]
        body = raw[32 + nlen:]
        sl = struct.unpack("<i", body[4:8])[0]
        sid = body[8:8 + sl]
        # 原版 body: [0][storeID][kind][...]，取出 kind
        kind = 0
        try:
            off = 8 + sl
            off += (4 - off % 4) % 4
            kind = struct.unpack("<i", body[off:off + 4])[0]
        except Exception:
            pass
        head = (
            struct.pack("<iq", 0, new_ids.get((path, gp), 0))
            + b"\x01\x00\x00\x00"
            + struct.pack("<iq", 0, new_ids.get((stgt, spid), 0) if stgt else 0)
            + struct.pack("<i", 0)
        )
        b = struct.pack("<i", 0) + struct.pack("<i", len(sid)) + sid
        b += b"\x00" * ((4 - len(b) % 4) % 4)
        b += struct.pack("<5i", 0, 0, 0, kind, 0)
        data = head + b
    elif tname in RAW_TYPES and tname != "Texture2D":
        data = o.get_raw_data()
    else:
        t = get_tree(path, pid)
        if t is None:
            skipped["no_tree:" + tname] += 1
            continue
        if tname == "Texture2D":
            raw = res_bytes(path, t)
            if raw is not None:
                t["image data"] = raw
                t["m_CompleteImageSize"] = len(raw)
                t["m_StreamData"] = {"offset": 0, "size": 0, "path": ""}
                tex_bytes += len(raw)
        remap_tree(t, path)
        w = EndianBinaryWriter(endian=endian)
        write_typetree(t, node, w, sf)
        data = w.bytes
    sf.objects[newpid] = ObjectReader(
        sf, sf.reader, newpid, tid, types[tid], cid,
        ClassIDType(cid), 0, len(data), None, None, data,
    )
    written += 1

print("objs written", written, "skipped", dict(skipped), "tex raw MB", round(tex_bytes / 1e6, 1))

# ---------- AssetBundle ----------
root_new = new_ids[(LEVEL, ROOT_PID)]
tag = os.path.splitext(os.path.basename(OUT))[0]
ab = dict(ab_tpl)
ab["m_Name"] = tag
ab["m_PreloadTable"] = [{"m_FileID": 0, "m_PathID": root_new}]
key = f"assets/rf4local/{tag}.prefab"
ab["m_Container"] = [(key, {"preloadIndex": 0, "preloadSize": 1, "asset": {"m_FileID": 0, "m_PathID": root_new}})]
ab["m_MainAsset"] = {"preloadIndex": 0, "preloadSize": 1, "asset": {"m_FileID": 0, "m_PathID": root_new}}
ab["m_AssetBundleName"] = tag
ab["m_Dependencies"] = []
ab["m_IsStreamedSceneAssetBundle"] = False
tid_ab = type_index[142]
w = EndianBinaryWriter(endian=endian)
write_typetree(ab, types[tid_ab].nodes, w, sf)
d = w.bytes
sf.objects[1] = ObjectReader(sf, sf.reader, 1, tid_ab, types[tid_ab], 142, ClassIDType.AssetBundle, 0, len(d), None, None, d)

files_map = dict(bf.files)
old = [k for k in files_map if not k.endswith(".resS")][0]
newcab = "CAB-%s%014x" % (tag, uuid.uuid4().int & 0xFFFFFFFFFFFFFF)
bf.files = {(newcab + k[len(old):]): v for k, v in files_map.items()}
open(OUT, "wb").write(bf.save(packer="lz4hc"))
print("written", OUT, os.path.getsize(OUT), "container", key)

env2 = UnityPy.load(OUT)
sf2 = [v for v in env2.file.files.values() if hasattr(v, "objects")][0]
print("reload objects", len(sf2.objects))

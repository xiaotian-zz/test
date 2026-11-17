#!/usr/bin/env python3
"""从原版 bundle 搬运纹理的原始压缩字节（DXT1/DXT5/BC7），不做任何转码。

输出: F:\\RF4\\Game\\rf4_x64_Data\\Data\\xmas_native
"""
from __future__ import annotations

import json
import os
import uuid

import UnityPy
from UnityPy.enums import ClassIDType
from UnityPy.files.ObjectReader import ObjectReader
from UnityPy.helpers.TypeTreeHelper import write_typetree
from UnityPy.streams import EndianBinaryWriter

DATA = r"F:\rea\artifacts\xmas_stalls"
SRC = r"F:\RF4\Game\rf4_x64_Data\Data\xmas_ok"
DST = os.environ.get("TEX_OUT", r"F:\RF4\Game\rf4_x64_Data\Data\xmas_native")
LURES = r"F:\RF4\Game\rf4_x64_Data\Data\lures_wta"

STEAM = r"D:\Steam\steamapps\content\app_766570\depot_766571\rf4_x64_Data"
SOURCES = [
    os.path.join(STEAM, "Data", "props"),
    os.path.join(STEAM, "sharedassets5.assets"),
]

mani = json.load(open(os.path.join(DATA, "manifest.json"), encoding="utf8"))
want = {m["name"]: m["tex"] for m in mani["materials"] if m.get("tex") is not None}

# 1) 在源文件里建立 材质名 -> (Texture2D typetree, reader, resS key)
found: dict[str, dict] = {}
for src in SOURCES:
    if not os.path.exists(src):
        print("skip", src)
        continue
    env = UnityPy.load(src)
    bf = env.file
    is_bundle = (
        hasattr(bf, "files")
        and isinstance(bf.files, dict)
        and (not bf.files or isinstance(next(iter(bf.files)), str))
    )
    objs = {o.path_id: o for o in env.objects}
    if is_bundle:
        res_readers = {k: v for k, v in bf.files.items() if k.endswith(".resS")}
    else:
        res_readers = {}
    got = 0
    for o in env.objects:
        if o.type.name != "Material":
            continue
        try:
            d = o.read_typetree()
        except Exception:
            continue
        nm = d.get("m_Name")
        if nm not in want or nm in found:
            continue
        tex_pp = None
        for e in d["m_SavedProperties"]["m_TexEnvs"]:
            if e[0] == "_MainTex":
                tex_pp = e[1]["m_Texture"]
                break
        if not tex_pp:
            continue
        to = objs.get(tex_pp.get("m_PathID"))
        if to is None or to.type.name != "Texture2D":
            continue
        tt = to.read_typetree()
        stream = tt.get("m_StreamData") or {}
        data = None
        if stream.get("size"):
            path = stream.get("path", "")
            off = int(stream.get("offset", 0))
            size = int(stream.get("size"))
            if path.startswith("archive:/"):
                cab = path.split("/")[1]
                key = cab + ".resS"
                r = res_readers.get(key)
                if r is not None:
                    r.seek(off)
                    data = bytes(r.read_bytes(size))
            else:
                rp = os.path.join(os.path.dirname(src), os.path.basename(path))
                if os.path.exists(rp):
                    with open(rp, "rb") as fh:
                        fh.seek(off)
                        data = fh.read(size)
        else:
            raw = tt.get("m_ImageData") or b""
            if raw:
                data = bytes(raw)
        if not data:
            continue
        found[nm] = {
            "name": tt.get("m_Name"),
            "w": int(tt.get("m_Width")),
            "h": int(tt.get("m_Height")),
            "fmt": int(tt.get("m_TextureFormat")),
            "mips": int(tt.get("m_MipCount")),
            "data": data,
            "kw": list(d.get("m_ValidKeywords") or []),
        }
        got += 1
    print(src[-40:], "matched", got, "cum", len(found))

print("total matched", len(found), "/", len(want))

# 2) 打包
env = UnityPy.load(SRC)
bf = env.file
sf = [v for v in bf.files.values() if hasattr(v, "objects")][0]
tex_type_id = next(i for i, t in enumerate(sf.types) if t.class_id == 28)
tex_type = sf.types[tex_type_id]
root_node = tex_type.nodes

_env0 = UnityPy.load(LURES)
_sf0 = [v for v in _env0.file.files.values() if hasattr(v, "objects")][0]
PROTO = None
for _o in _sf0.objects.values():
    if _o.type.name == "Texture2D":
        PROTO = _o.read_typetree()
        break


def build_tex(name: str, w: int, h: int, mips: int, fmt: int, data: bytes) -> bytes:
    tpl = dict(PROTO)
    tpl["m_Name"] = name
    tpl["m_Width"] = w
    tpl["m_Height"] = h
    tpl["m_CompleteImageSize"] = len(data)
    tpl["m_TextureFormat"] = fmt
    tpl["m_MipCount"] = mips
    tpl["m_IsReadable"] = False
    tpl["m_StreamingMipmaps"] = False
    tpl["image data"] = data
    tpl["m_StreamData"] = {"offset": 0, "size": 0, "path": ""}
    w2 = EndianBinaryWriter(endian=sf.reader.endian)
    write_typetree(tpl, root_node, w2, sf)
    return w2.bytes


tex_pid: dict[str, int] = {}
total = 0
for nm, info in found.items():
    total += len(info["data"])
    pid = 2100000 + len(tex_pid)
    blob = build_tex(info["name"] or nm, info["w"], info["h"], info["mips"], info["fmt"], info["data"])
    ob = ObjectReader(sf, None, pid, tex_type_id, tex_type, 28, ClassIDType.Texture2D, 0, len(blob), False, False, data=blob)
    sf.objects[pid] = ob
    tex_pid[nm] = pid

print("textures packed", len(tex_pid), "raw MB", round(total / 1e6, 1))

bound = 0
for pid, o in list(sf.objects.items()):
    if o.type.name != "Material":
        continue
    d = o.read_typetree()
    nm = d.get("m_Name")
    if nm not in tex_pid:
        continue
    tp = {"m_FileID": 0, "m_PathID": tex_pid[nm]}
    for item in d["m_SavedProperties"]["m_TexEnvs"]:
        if item[0] == "_MainTex":
            item[1]["m_Texture"] = tp
    d["m_ValidKeywords"] = list(found[nm]["kw"])
    d["m_InvalidKeywords"] = []
    o.save_typetree(d)
    bound += 1
print("materials bound", bound, "objects", len(sf.objects))

tag = os.path.splitext(os.path.basename(DST))[0]
for pid, o in sf.objects.items():
    if o.type.name == "AssetBundle":
        d = o.read_typetree()
        d["m_AssetBundleName"] = tag
        o.save_typetree(d)
files = dict(bf.files)
old = [k for k in files if not k.endswith(".resS")][0]
newcab = "CAB-%s%014x" % (tag, uuid.uuid4().int & 0xFFFFFFFFFFFFFF)
bf.files = {(newcab + k[len(old):]): v for k, v in files.items()}

open(DST, "wb").write(bf.save(packer="lz4hc"))
print("written", os.path.getsize(DST))

env2 = UnityPy.load(DST)
sf2 = [v for v in env2.file.files.values() if hasattr(v, "objects")][0]
cnt = sum(1 for o in sf2.objects.values() if o.type.name == "Texture2D")
print("reload tex", cnt, "total", len(sf2.objects))

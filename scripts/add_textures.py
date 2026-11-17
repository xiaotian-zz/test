#!/usr/bin/env python3
"""把 manifest 里的 PNG 作为 Texture2D 打进 bundle，并绑定到 Material._MainTex。

输出: F:\\RF4\\Game\\rf4_x64_Data\\Data\\xmas_tex
"""
from __future__ import annotations

import io
import json
import os

import UnityPy
from PIL import Image
from UnityPy.enums import ClassIDType
from UnityPy.files.ObjectReader import ObjectReader
from UnityPy.helpers.TypeTreeHelper import write_typetree
from UnityPy.streams import EndianBinaryWriter

DATA = r"F:\rea\artifacts\xmas_stalls"
SRC = r"F:\RF4\Game\rf4_x64_Data\Data\xmas_ok"
DST = os.environ.get("TEX_OUT", r"F:\RF4\Game\rf4_x64_Data\Data\xmas_tex")
MAX = int(os.environ.get("TEX_MAX", "512"))
LIMIT = int(os.environ.get("TEX_LIMIT", "0"))
BIND = int(os.environ.get("TEX_BIND", "1"))

mani = json.load(open(os.path.join(DATA, "manifest.json"), encoding="utf8"))

env = UnityPy.load(SRC)
bf = env.file
sf = [v for v in bf.files.values() if hasattr(v, "objects")][0]
tex_type_id = next(i for i, t in enumerate(sf.types) if t.class_id == 28)
tex_type = sf.types[tex_type_id]
root_node = tex_type.nodes


LURES = r"F:\RF4\Game\rf4_x64_Data\Data\lures_wta"
_env0 = UnityPy.load(LURES)
_sf0 = [v for v in _env0.file.files.values() if hasattr(v, "objects")][0]
PROTO = None
for _o in _sf0.objects.values():
    if _o.type.name == "Texture2D":
        PROTO = _o.read_typetree()
        break
print("proto fields", len(PROTO) if PROTO else 0)


def build_tex(name: str, w: int, h: int, raw: bytes) -> bytes:
    tpl = dict(PROTO)
    tpl["m_Name"] = name
    tpl["m_Width"] = w
    tpl["m_Height"] = h
    tpl["m_CompleteImageSize"] = len(raw)
    tpl["m_TextureFormat"] = 4
    tpl["m_MipCount"] = 1
    tpl["m_IsReadable"] = False
    tpl["m_StreamingMipmaps"] = False
    tpl["image data"] = raw
    tpl["m_StreamData"] = {"offset": 0, "size": 0, "path": ""}
    w2 = EndianBinaryWriter(endian=sf.reader.endian)
    write_typetree(tpl, root_node, w2, sf)
    return w2.bytes


tex_pid: dict[int, int] = {}
total_raw = 0
for t in mani["textures"]:
    if LIMIT and len(tex_pid) >= LIMIT:
        break
    p = os.path.join(DATA, t["file"].replace("/", os.sep))
    if not os.path.exists(p):
        continue
    im = Image.open(p).convert("RGBA")
    w, h = im.size
    if max(w, h) > MAX:
        s = MAX / max(w, h)
        im = im.resize((max(1, int(w * s)), max(1, int(h * s))), Image.LANCZOS)
    im = im.transpose(Image.FLIP_TOP_BOTTOM)
    w, h = im.size
    raw = im.tobytes()
    total_raw += len(raw)
    pid = 2000000 + int(t["id"])
    data = build_tex(os.path.basename(t["file"]), w, h, raw)
    ob = ObjectReader(sf, None, pid, tex_type_id, tex_type, 28, ClassIDType.Texture2D, 0, len(data), False, False, data=data)
    sf.objects[pid] = ob
    tex_pid[int(t["id"])] = pid

print("textures packed", len(tex_pid), "raw MB", round(total_raw / 1e6, 1))

mat_tex = {m["name"]: m["tex"] for m in mani["materials"] if m.get("tex") is not None}
bound = 0
for pid, o in (list(sf.objects.items()) if BIND else []):
    if o.type.name != "Material":
        continue
    d = o.read_typetree()
    tid = mat_tex.get(d.get("m_Name"))
    if tid is None or tid not in tex_pid:
        continue
    tp = {"m_FileID": 0, "m_PathID": tex_pid[tid]}
    env_list = d["m_SavedProperties"]["m_TexEnvs"]
    for item in env_list:
        if item[0] == "_MainTex":
            item[1]["m_Texture"] = tp
    o.save_typetree(d)
    bound += 1

print("materials bound", bound, "objects", len(sf.objects))

import uuid

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

# self check
env2 = UnityPy.load(DST)
bf2 = env2.file
sf2 = [v for v in bf2.files.values() if hasattr(v, "objects")][0]
cnt = sum(1 for o in sf2.objects.values() if o.type.name == "Texture2D")
print("reload tex", cnt, "total", len(sf2.objects))

#!/usr/bin/env python3
"""把 79 张 PNG 转成 DXT5(BC3) + mipmap，打进 bundle（复刻原版纹理格式）。

输出: F:\\RF4\\Game\\rf4_x64_Data\\Data\\xmas_bc
"""
from __future__ import annotations

import json
import os
import subprocess
import uuid

import UnityPy
from PIL import Image
from UnityPy.enums import ClassIDType
from UnityPy.files.ObjectReader import ObjectReader
from UnityPy.helpers.TypeTreeHelper import write_typetree
from UnityPy.streams import EndianBinaryWriter

DATA = r"F:\rea\artifacts\xmas_stalls"
SRC = r"F:\RF4\Game\rf4_x64_Data\Data\xmas_ok"
DST = os.environ.get("TEX_OUT", r"F:\RF4\Game\rf4_x64_Data\Data\xmas_bc")
TEXCONV = r"f:\rea\tools\texconv.exe"
MAXS = int(os.environ.get("TEX_MAX", "256"))
LIMIT = int(os.environ.get("TEX_LIMIT", "0"))

SCALE_DIR = os.path.join(DATA, "bc_src")
BC_DIR = os.path.join(DATA, "bc_dds")
os.makedirs(SCALE_DIR, exist_ok=True)
os.makedirs(BC_DIR, exist_ok=True)

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

# 1) 等比缩放到 max 256
scaled: list[str] = []
for t in mani["textures"]:
    p = os.path.join(DATA, t["file"].replace("/", os.sep))
    if not os.path.exists(p):
        continue
    im = Image.open(p).convert("RGBA")
    w, h = im.size
    s = min(1.0, MAXS / max(w, h))
    nw = max(4, (int(w * s) // 4) * 4)
    nh = max(4, (int(h * s) // 4) * 4)
    if (nw, nh) != (w, h):
        im = im.resize((nw, nh), Image.LANCZOS)
    out = os.path.join(SCALE_DIR, os.path.basename(t["file"]))
    im.save(out)
    scaled.append(out)
print("scaled", len(scaled))

# 2) texconv -> BC3 + mip
cmd = [TEXCONV, "-f", "BC3_UNORM", "-m", "0", "-y", "-nologo", "-o", BC_DIR] + scaled
r = subprocess.run(cmd, capture_output=True, text=True)
print("texconv rc", r.returncode)
if r.returncode != 0:
    print(r.stderr[-800:])
    raise SystemExit(1)


def build_tex(name: str, w: int, h: int, mips: int, data: bytes) -> bytes:
    tpl = dict(PROTO)
    tpl["m_Name"] = name
    tpl["m_Width"] = w
    tpl["m_Height"] = h
    tpl["m_CompleteImageSize"] = len(data)
    tpl["m_TextureFormat"] = 12  # DXT5
    tpl["m_MipCount"] = mips
    tpl["m_IsReadable"] = False
    tpl["m_StreamingMipmaps"] = False
    tpl["image data"] = data
    tpl["m_StreamData"] = {"offset": 0, "size": 0, "path": ""}
    w2 = EndianBinaryWriter(endian=sf.reader.endian)
    write_typetree(tpl, root_node, w2, sf)
    return w2.bytes


tex_pid: dict[int, int] = {}
total_raw = 0
for t in mani["textures"]:
    if LIMIT and len(tex_pid) >= LIMIT:
        break
    stem = os.path.splitext(os.path.basename(t["file"]))[0]
    dds = os.path.join(BC_DIR, stem + ".dds")
    if not os.path.exists(dds):
        continue
    b = open(dds, "rb").read()
    data = b[148:]
    mips = int.from_bytes(b[28:32], "little")
    h = int.from_bytes(b[12:16], "little")
    w = int.from_bytes(b[16:20], "little")
    total_raw += len(data)
    pid = 2000000 + int(t["id"])
    blob = build_tex(stem, w, h, mips, data)
    ob = ObjectReader(sf, None, pid, tex_type_id, tex_type, 28, ClassIDType.Texture2D, 0, len(blob), False, False, data=blob)
    sf.objects[pid] = ob
    tex_pid[int(t["id"])] = pid

print("textures packed", len(tex_pid), "data MB", round(total_raw / 1e6, 2))

mat_tex = {m["name"]: m["tex"] for m in mani["materials"] if m.get("tex") is not None}
bound = 0
for pid, o in list(sf.objects.items()):
    if o.type.name != "Material":
        continue
    d = o.read_typetree()
    tid = mat_tex.get(d.get("m_Name"))
    if tid is None or tid not in tex_pid:
        continue
    tp = {"m_FileID": 0, "m_PathID": tex_pid[tid]}
    for item in d["m_SavedProperties"]["m_TexEnvs"]:
        if item[0] == "_MainTex":
            item[1]["m_Texture"] = tp
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

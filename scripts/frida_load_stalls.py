#!/usr/bin/env python3
"""把导出的两个新年摊位按原世界位姿注入游戏（分批，挂 Shop）。

用法:
  py -3.12 scripts/frida_load_stalls.py <PID> [--tex]
"""
from __future__ import annotations

import json
import math
import os
import sys
import time

import frida

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "artifacts", "xmas_stalls")
ROOT_POS = (233.96, 2.36, 161.63)
ROOT_YAW = 90.7
STORES = {
    "christmas_market_food": "nybaazar_18",
    "christmas_market_fishing_2020": "ny_bazaarStore_18",
}


def qmul(a, b):
    ax, ay, az, aw = a
    bx, by, bz, bw = b
    return (
        aw * bx + ax * bw + ay * bz - az * by,
        aw * by - ax * bz + ay * bw + az * bx,
        aw * bz + ax * by - ay * bx + az * bw,
        aw * bw - ax * bx - ay * by - az * bz,
    )


def qrot(q, v):
    x, y, z, w = q
    vx, vy, vz = v
    # v' = v + 2*cross(q.xyz, cross(q.xyz, v) + w*v)
    cx = y * vz - z * vy
    cy = z * vx - x * vz
    cz = x * vy - y * vx
    tx = cx + w * vx
    ty = cy + w * vy
    tz = cz + w * vz
    return (
        vx + 2 * (y * tz - z * ty),
        vy + 2 * (z * tx - x * tz),
        vz + 2 * (x * ty - y * tx),
    )


def flatten(node, ppos, prot, pscale, out, store=None):
    sx, sy, sz = node["scale"]
    lx, ly, lz = node["pos"]
    rv = qrot(prot, (lx * pscale[0], ly * pscale[1], lz * pscale[2]))
    wpos = (ppos[0] + rv[0], ppos[1] + rv[1], ppos[2] + rv[2])
    wrot = qmul(prot, tuple(node["rot"]))
    wscale = (pscale[0] * sx, pscale[1] * sy, pscale[2] * sz)
    for r in node.get("renders", []):
        out.append({
            "name": node["name"],
            "pos": [round(v, 4) for v in wpos],
            "rot": [round(v, 6) for v in wrot],
            "scale": [round(v, 4) for v in wscale],
            "mesh": r["mesh"],
            "mat": r.get("mat"),
        })
    for c in node.get("children", []):
        flatten(c, wpos, wrot, wscale, out, store)


JS = r"""
const ga=Process.getModuleByName('GameAssembly.dll');const E=n=>ga.getExportByName(n),P=Process.pointerSize;
const f={dom:new NativeFunction(E('il2cpp_domain_get'),'pointer',[]),
 attach:new NativeFunction(E('il2cpp_thread_attach'),'pointer',['pointer']),
 asms:new NativeFunction(E('il2cpp_domain_get_assemblies'),'pointer',['pointer','pointer']),
 asmImg:new NativeFunction(E('il2cpp_assembly_get_image'),'pointer',['pointer']),
 imgName:new NativeFunction(E('il2cpp_image_get_name'),'pointer',['pointer']),
 fromName:new NativeFunction(E('il2cpp_class_from_name'),'pointer',['pointer','pointer','pointer']),
 cType:new NativeFunction(E('il2cpp_class_get_type'),'pointer',['pointer']),
 cMethods:new NativeFunction(E('il2cpp_class_get_methods'),'pointer',['pointer','pointer']),
 mName:new NativeFunction(E('il2cpp_method_get_name'),'pointer',['pointer']),
 mParamCount:new NativeFunction(E('il2cpp_method_get_param_count'),'uint',['pointer']),
 tObj:new NativeFunction(E('il2cpp_type_get_object'),'pointer',['pointer']),
 strNew:new NativeFunction(E('il2cpp_string_new'),'pointer',['pointer']),
 getParam:new NativeFunction(E('il2cpp_method_get_param'),'pointer',['pointer','uint']),
 typeName:new NativeFunction(E('il2cpp_type_get_name'),'pointer',['pointer']),
 objNew:new NativeFunction(E('il2cpp_object_new'),'pointer',['pointer']),
 arrClass:new NativeFunction(E('il2cpp_array_class_get'),'pointer',['pointer','int']),
 arrNew:new NativeFunction(E('il2cpp_array_new'),'pointer',['pointer','uint64'])};
function cs(p){try{return p.isNull()?'':p.readUtf8String();}catch(e){return '';}}
function findMethod(cls,name,argc){if(cls.isNull())return null;const it=Memory.alloc(P);it.writePointer(ptr(0));for(let i=0;i<700;i++){const m=f.cMethods(cls,it);if(m.isNull())break;if(cs(f.mName(m))===name&&(argc===undefined||f.mParamCount(m)===argc))return m.add(P).readPointer();}return null;}
function findMethodType(cls,name,argc,want){if(cls.isNull())return null;const it=Memory.alloc(P);it.writePointer(ptr(0));for(let i=0;i<700;i++){const m=f.cMethods(cls,it);if(m.isNull())break;if(cs(f.mName(m))===name&&f.mParamCount(m)===argc&&cs(f.typeName(f.getParam(m,0)))===want)return m.add(P).readPointer();}return null;}
const dom=f.dom(),cnt=Memory.alloc(8),asms=f.asms(dom,cnt),n=cnt.readUInt();
let game=null,core=null,imgm=null,mscor=null;
for(let i=0;i<n;i++){const a=asms.add(i*P).readPointer(),im=f.asmImg(a),nm=cs(f.imgName(im));
 if(nm==='Assembly-CSharp.dll')game=im;if(nm==='UnityEngine.CoreModule.dll')core=im;
 if(nm==='UnityEngine.ImageConversionModule.dll')imgm=im;if(nm==='mscorlib.dll')mscor=im;}
function cls(ns,nm){return f.fromName(core,Memory.allocUtf8String(ns),Memory.allocUtf8String(nm));}
const GO=cls('UnityEngine','GameObject'),TR=cls('UnityEngine','Transform'),TIME=cls('UnityEngine','Time');
const MESH=cls('UnityEngine','Mesh'),MATERIAL=cls('UnityEngine','Material'),SHADER=cls('UnityEngine','Shader');
const TEX=cls('UnityEngine','Texture2D'),MF=cls('UnityEngine','MeshFilter'),MR=cls('UnityEngine','MeshRenderer'),REND=cls('UnityEngine','Renderer');
const V3=cls('UnityEngine','Vector3'),V2=cls('UnityEngine','Vector2'),COLOR=cls('UnityEngine','Color');
const I32=f.fromName(mscor,Memory.allocUtf8String('System'),Memory.allocUtf8String('Int32'));
const SM=cls('UnityEngine.SceneManagement','SceneManager'),SC=cls('UnityEngine.SceneManagement','Scene');
const IMGCONV=imgm.isNull()?null:f.fromName(imgm,Memory.allocUtf8String('UnityEngine'),Memory.allocUtf8String('ImageConversion'));
const IOFILE=mscor.isNull()?null:f.fromName(mscor,Memory.allocUtf8String('System.IO'),Memory.allocUtf8String('File'));
const SHOP=f.fromName(game,Memory.allocUtf8String('RF4.Client.FishingScene'),Memory.allocUtf8String('Shop'));
let probePatched=false;
try{
 const MP=f.fromName(game,Memory.allocUtf8String('RF4.Client'),Memory.allocUtf8String('MyProbe'));
 if(!MP.isNull()){
  const mi=findMethod(MP,'mipcnipgejd',1);
  if(mi){Interceptor.replace(mi,new NativeCallback(function(){},'void',['pointer','int']));probePatched=true;}
 }
}catch(e){}
send({log:'myprobe patched='+probePatched});
const m={
 meshCtor:findMethod(MESH,'.ctor',0),setV:findMethod(MESH,'set_vertices',1),setN:findMethod(MESH,'set_normals',1),
 setUV:findMethod(MESH,'set_uv',1),setT:findMethod(MESH,'set_triangles',1),recB:findMethod(MESH,'RecalculateBounds',0),
 goCtor:findMethod(GO,'.ctor',1),addComp:findMethodType(GO,'AddComponent',1,'System.Type'),getT:findMethod(GO,'get_transform',0),
 setPos:findMethod(TR,'set_position_Injected',1),setRot:findMethod(TR,'set_rotation_Injected',1),setScale:findMethod(TR,'set_localScale_Injected',1),
 mfSet:findMethod(MF,'set_mesh',1),mrSet:findMethod(REND,'set_sharedMaterial',1),
 matCtor:findMethod(MATERIAL,'.ctor',1),matTex:findMethod(MATERIAL,'set_mainTexture',1),matCol:findMethod(MATERIAL,'set_color',2),
 shFind:findMethod(SHADER,'Find',1),texCtor:findMethod(TEX,'.ctor',4),texCtor2:findMethod(TEX,'.ctor',2),
 loadImg:IMGCONV?findMethod(IMGCONV,'LoadImage',2):null,readAll:IOFILE?findMethod(IOFILE,'ReadAllBytes',1):null,
 tick:['get_deltaTime','get_time','get_realtimeSinceStartup','get_unscaledDeltaTime','get_smoothDeltaTime'].map(x=>findMethod(TIME,x,0)).filter(Boolean),
 objFind:findMethodType(cls('UnityEngine','Object'),'FindObjectsOfType',1,'System.Type'),
 findGO:findMethod(GO,'Find',1)};
send({log:'apis '+JSON.stringify({mesh:!!m.meshCtor,setV:!!m.setV,setN:!!m.setN,setUV:!!m.setUV,setT:!!m.setT,go:!!m.goCtor,add:!!m.addComp,pos:!!m.setPos,rot:!!m.setRot,scale:!!m.setScale,mf:!!m.mfSet,mr:!!m.mrSet,mat:!!m.matCtor,tex:!!m.texCtor,load:!!m.loadImg,read:!!m.readAll,ticks:m.tick.length,shop:!SHOP.isNull()})});
const msp=(function(){for(const mn of ['msvcrt.dll','ucrtbase.dll']){try{return new NativeFunction(Process.getModuleByName(mn).getExportByName('memcpy'),'pointer',['pointer','pointer','uint64']);}catch(e){}}return null;})();
const gchNew=new NativeFunction(E('il2cpp_gchandle_new'),'uint',['pointer','int']);
const gchTgt=new NativeFunction(E('il2cpp_gchandle_get_target'),'pointer',['uint']);
const gchFree=new NativeFunction(E('il2cpp_gchandle_free'),'void',['uint']);
send({log:'msp='+(msp?'ok':'null')});
function V3P(x,y,z){const p=Memory.alloc(12);p.writeFloat(x);p.add(4).writeFloat(y);p.add(8).writeFloat(z);return p;}
let DATA=null,rootGO=null,idx=0,texQ=[],texWait={},meshCache={},matCache={},texCache={},created=0,tickCount=0,stepping=false;
function readAll(p){return new NativeFunction(m.readAll,'pointer',['pointer'])(f.strNew(Memory.allocUtf8String(p)));}
function getMesh(id){
 if(meshCache[id]!==undefined)return meshCache[id];
 const info=DATA.meshes[id];if(!info)return null;
 const vc=info.vc,tc=info.tc;
 let blob=ptr(0);
 try{blob=readAll(info.bin);}catch(e){blob=ptr(0);}
 if(blob.isNull()||blob.compare(ptr(0x10000))<0){meshCache[id]=null;return null;}
 const hb=gchNew(blob,0);
 const src=blob.add(0x28);
 if(!DATA.probed||DATA.probed<2){
  DATA.probed=(DATA.probed||0)+1;
  const expect=8+vc*32+tc*12;
  let al=-1;try{al=blob.add(0x18).readU64().toNumber();}catch(e){}
  let i0=-1,p0=0;try{i0=src.add(vc*32).readInt();p0=src.readFloat();}catch(e){}
  send({log:'probe id='+id+' arrLen='+al+' expect='+expect+' vc='+vc+' tc='+tc+' idx0='+i0+' pos0='+p0});
 }
 if(DATA.probeOnly){gchFree(hb);meshCache[id]=null;return null;}
 let pa,na,ua,ta,mesh,h1=0,h2=0,h3=0,h4=0,h5=0;
 try{
  pa=f.arrNew(f.arrClass(V3,1),vc);na=f.arrNew(f.arrClass(V3,1),vc);ua=f.arrNew(f.arrClass(V2,1),vc);ta=f.arrNew(f.arrClass(I32,1),tc*3);
  if(!pa||pa.isNull()||!ta||ta.isNull()){send({log:'arrNew null id='+id});gchFree(hb);meshCache[id]=null;return null;}
  h1=gchNew(pa,0);h2=gchNew(na,0);h3=gchNew(ua,0);h4=gchNew(ta,0);
 }catch(e){send({log:'arrNew err id='+id+' '+e});gchFree(hb);meshCache[id]=null;return null;}
 try{
  msp(pa.add(0x20),src,vc*12);
  msp(na.add(0x20),src.add(vc*12),vc*12);
  msp(ua.add(0x20),src.add(vc*24),vc*8);
  msp(ta.add(0x20),src.add(vc*32),tc*12);
 }catch(e){send({log:'memcpy err id='+id+' '+e});gchFree(h1);gchFree(h2);gchFree(h3);gchFree(h4);gchFree(hb);meshCache[id]=null;return null;}
 if((DATA.verified||0)<2){
  DATA.verified=(DATA.verified||0)+1;
  try{
   send({log:'verify id='+id+' arr0='+pa.add(0x20).readFloat()+','+pa.add(0x24).readFloat()+','+pa.add(0x28).readFloat()+' idx0='+ta.add(0x20).readInt()+' src0='+src.readFloat()+' srcIdx0='+src.add(vc*32).readInt()});
  }catch(e){send({log:'verify err '+e});}
 }
 try{
  if(id<6)send({log:'ms['+id+'] objNew...'});
  mesh=f.objNew(MESH);
  if(id<6)send({log:'ms['+id+'] objNew='+mesh});
  h5=gchNew(mesh,0);
  if(id<6)send({log:'ms['+id+'] h5='+h5});
  new NativeFunction(m.meshCtor,'void',['pointer'])(mesh);
  if(id<6)send({log:'ms['+id+'] ctor ok'});
  new NativeFunction(m.setV,'void',['pointer','pointer'])(mesh,gchTgt(h1));
  if(id<6)send({log:'ms['+id+'] setV ok'});
  if(m.setN)new NativeFunction(m.setN,'void',['pointer','pointer'])(mesh,gchTgt(h2));
  if(id<6)send({log:'ms['+id+'] setN ok'});
  new NativeFunction(m.setUV,'void',['pointer','pointer'])(mesh,gchTgt(h3));
  if(id<6)send({log:'ms['+id+'] setUV ok'});
  new NativeFunction(m.setT,'void',['pointer','pointer'])(mesh,gchTgt(h4));
  if(id<6)send({log:'ms['+id+'] setT ok'});
  if(m.recB)new NativeFunction(m.recB,'void',['pointer'])(mesh);
  if(id<6)send({log:'ms['+id+'] recB ok'});
  gchFree(h1);gchFree(h2);gchFree(h3);gchFree(h4);gchFree(hb);
  meshCache[id]=mesh;return mesh;
 }catch(e){send({log:'meshSet err id='+id+' '+e});gchFree(h1);gchFree(h2);gchFree(h3);gchFree(h4);gchFree(hb);if(h5)gchFree(h5);meshCache[id]=null;return null;}
}
function loadTex(id){
 if(texCache[id]!==undefined)return texCache[id];
 const path=DATA.textures[id];if(!path){texCache[id]=null;return null;}
 let blob=ptr(0);
 try{blob=readAll(path);}catch(e){blob=ptr(0);}
 const png=blob;
 if(png.isNull()||png.compare(ptr(0x10000))<0){texCache[id]=null;return null;}
 const t=f.objNew(TEX);
 try{new NativeFunction(m.texCtor,'void',['pointer','int','int','int','int'])(t,4,4,4,0);}
 catch(e){new NativeFunction(m.texCtor2,'void',['pointer','int','int'])(t,4,4);}
 try{new NativeFunction(m.loadImg,'int',['pointer','pointer'])(t,png);}catch(e){}
 texCache[id]=t;return t;
}
function getMat(id){
 if(id===null||id===undefined)return null;
 if(matCache[id]!==undefined)return matCache[id];
 const info=DATA.materials[id];if(!info){matCache[id]=null;return null;}
 let sh=ptr(0);
 for(const nm of [info.shader,'Standard','Legacy Shaders/Diffuse','Unlit/Texture']){
  if(!nm)continue;
  const s=new NativeFunction(m.shFind,'pointer',['pointer'])(f.strNew(Memory.allocUtf8String(nm)));
  if(!s.isNull()&&s.compare(ptr(0x10000))>=0){sh=s;break;}
 }
 if(sh.isNull()){matCache[id]=null;return null;}
 const mat=f.objNew(MATERIAL);new NativeFunction(m.matCtor,'void',['pointer','pointer'])(mat,sh);
 if(info.color&&m.matCol){const c=Memory.alloc(16);c.writeFloat(info.color[0]);c.add(4).writeFloat(info.color[1]);c.add(8).writeFloat(info.color[2]);c.add(12).writeFloat(info.color[3]);
  try{new NativeFunction(m.matCol,'void',['pointer','pointer','pointer'])(mat,f.strNew(Memory.allocUtf8String('_Color')),c);}catch(e){}}
 matCache[id]=mat;
 if(info.tex!==null&&info.tex!==undefined){
  const tex=loadTex(info.tex);
  if(tex)new NativeFunction(m.matTex,'void',['pointer','pointer'])(mat,tex);
 }
 return mat;
}
function buildOne(r){
 const stage=DATA.stage||'full';
 let mesh=null;
 if(stage!=='go'){mesh=getMesh(r.mesh);if(!mesh)return false;}
 const go=f.objNew(GO);
 if(go.isNull()||go.compare(ptr(0x10000))<0){send({log:'objNew GO null'});return false;}
 new NativeFunction(m.goCtor,'void',['pointer','pointer'])(go,f.strNew(Memory.allocUtf8String(r.name)));
 const t=new NativeFunction(m.getT,'pointer',['pointer'])(go);
 if(t.isNull()||t.compare(ptr(0x10000))<0){send({log:'transform null'});return false;}
 new NativeFunction(m.setPos,'void',['pointer','pointer'])(t,V3P(r.pos[0],r.pos[1],r.pos[2]));
 const q=Memory.alloc(16);q.writeFloat(r.rot[0]);q.add(4).writeFloat(r.rot[1]);q.add(8).writeFloat(r.rot[2]);q.add(12).writeFloat(r.rot[3]);
 new NativeFunction(m.setRot,'void',['pointer','pointer'])(t,q);
 new NativeFunction(m.setScale,'void',['pointer','pointer'])(t,V3P(r.scale[0],r.scale[1],r.scale[2]));
 if(stage==='go'){return true;}
 const mf=new NativeFunction(m.addComp,'pointer',['pointer','pointer'])(go,f.tObj(f.cType(MF)));
 if(!mf.isNull())new NativeFunction(m.mfSet,'void',['pointer','pointer'])(mf,mesh);
 const mr=new NativeFunction(m.addComp,'pointer',['pointer','pointer'])(go,f.tObj(f.cType(MR)));
 const mat=getMat(r.mat);
 if(!mr.isNull()&&mat)new NativeFunction(m.mrSet,'void',['pointer','pointer'])(mr,mat);
 return true;
}
function step(){
 if(stepping)return;
 stepping=true;
 try{
  try{f.attach(dom);}catch(e){}
 tickCount++;
 if(!DATA)return;
 if(!DATA.sceneOK&&m.findGO){
  let ok=false;
  try{
   const nf=new NativeFunction(m.findGO,'pointer',['pointer']);
   for(const nm of ['Base_outer','Assets','CHRISTMAS']){
    const g=nf(f.strNew(Memory.allocUtf8String(nm)));
    if(!g.isNull()&&g.compare(ptr(0x10000))>=0){ok=true;send({log:'scene node '+nm});break;}
   }
  }catch(e){return;}
  if(!ok)return;
  DATA.sceneOK=true;send({log:'scene ready'});
 }
 if(DATA.meshOnly){
  if(DATA.meshDone)return;
  let n=0;
  while(idx<DATA.renders.length&&n<2){const r=DATA.renders[idx++];send({log:'meshOnly id='+r.mesh});getMesh(r.mesh);n++;}
  DATA.meshDone=true;send({log:'MESHONLY DONE'});return;
 }
 if(DATA.probeOnly){
  if(DATA.probeDone)return;
  let n=0;
  while(idx<DATA.renders.length&&n<2){const r=DATA.renders[idx++];getMesh(r.mesh);n++;}
  DATA.probeDone=true;send({log:'PROBE DONE'});return;
 }
 if(idx<(DATA.limit||DATA.renders.length)){
  const lim=DATA.limit||DATA.renders.length;
  let n=0;
  while(idx<lim&&n<4){const r=DATA.renders[idx++];if(buildOne(r))created++;n++;}
  if(tickCount%20===0)send({log:'progress '+idx+'/'+lim});
  if(idx>=lim&&!DATA.done){DATA.done=true;send({log:'ALL DONE created='+created+'/'+lim+' meshes='+Object.keys(meshCache).length});}
  return;
 }
 if(texQ.length){const id=texQ.shift();loadTex(id);return;}
 if(!DATA.done){DATA.done=true;send({log:'ALL DONE created='+created+'/'+DATA.renders.length+' meshes='+Object.keys(meshCache).length+' texs='+Object.keys(texCache).length});}
 }catch(e){send({log:'step err '+e});}finally{stepping=false;}
}
for(let ti=0;ti<m.tick.length;ti++)Interceptor.attach(m.tick[ti],{onEnter(){step();}});
rpc.exports.feed=function(payload){DATA=payload;idx=0;created=0;send({log:'feed renders='+DATA.renders.length});return true;};
send({log:'ready'});
"""


MAPS = {
    "26": ((233.96, 2.36, 161.63), 90.7, "18"),
    "24": ((233.36, 2.66, 784.36), -42.1, "012"),
}


def main() -> int:
    pid = int(sys.argv[1])
    use_tex = "--tex" in sys.argv
    level = "26"
    for a in sys.argv[1:]:
        if a.startswith("--level="):
            level = a.split("=", 1)[1]
    root_pos, root_yaw, _suffix = MAPS[level]
    manifest = json.load(open(os.path.join(DATA, "manifest.json"), encoding="utf-8"))
    root = manifest["root"]
    half = math.radians(root_yaw) / 2
    root_rot = (0.0, math.sin(half), 0.0, math.cos(half))
    print("level", level, "root", root_pos, "yaw", root_yaw)
    renders: list[dict] = []
    for child in root["children"]:
        flatten(child, root_pos, root_rot, (1.0, 1.0, 1.0), renders)
    meshes = {m["id"]: {"bin": os.path.join(DATA, m["bin"]).replace("\\", "/"), "vc": m["vcount"], "tc": m["tcount"]} for m in manifest["meshes"]}
    materials = {}
    for mat in manifest["materials"]:
        tex = mat.get("tex")
        materials[mat["id"]] = {
            "shader": mat.get("shader", ""),
            "color": mat.get("color"),
            "tex": tex if (use_tex and tex is not None) else None,
        }
    textures = {t["id"]: os.path.join(DATA, t["file"]).replace("\\", "/") for t in manifest["textures"]}
    limit = 0
    for a in sys.argv[1:]:
        if a.startswith("--limit="):
            limit = int(a.split("=", 1)[1])
    stage = "full"
    for a in sys.argv[1:]:
        if a.startswith("--stage="):
            stage = a.split("=", 1)[1]
    payload = {"renders": renders, "meshes": meshes, "materials": materials, "textures": textures, "probeOnly": "--probe" in sys.argv, "meshOnly": "--meshonly" in sys.argv, "limit": limit, "stage": stage}
    print(f"renders={len(renders)} meshes={len(meshes)} materials={len(materials)} textures={len(textures)} tex={use_tex}")

    session = frida.attach(pid)
    script = session.create_script(JS)
    script.on("message", lambda m, d: print(json.dumps(m if m.get("type") != "send" else m.get("payload"), ensure_ascii=False)))
    script.load()
    script.exports_sync.feed(payload)
    time.sleep(int(os.environ.get("XMAS_WAIT", "240")))
    session.detach()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

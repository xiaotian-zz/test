#!/usr/bin/env python3
"""给场景里的 CHRISTMAS(Clone) 注入 PNG 贴图（分帧，主线程）。

用法: py -3.12 scripts/frida_apply_textures.py <PID>
"""
from __future__ import annotations

import json
import os
import sys
import time

import frida

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "artifacts", "xmas_stalls")

mani = json.load(open(os.path.join(DATA, "manifest.json"), encoding="utf8"))
tex_by_id = {t["id"]: t["file"] for t in mani["textures"]}
mapping: dict[str, str] = {}
for m in mani["materials"]:
    tid = m.get("tex")
    if tid is None:
        continue
    rel = tex_by_id.get(tid)
    if not rel:
        continue
    mapping.setdefault(m["name"], os.path.abspath(os.path.join(DATA, rel.replace("/", os.sep))))

MAP_JS = json.dumps(mapping, ensure_ascii=True)

JS = r"""
const ga=Process.getModuleByName('GameAssembly.dll');const E=n=>ga.getExportByName(n),P=Process.pointerSize;
const f={dom:new NativeFunction(E('il2cpp_domain_get'),'pointer',[]),
 asms:new NativeFunction(E('il2cpp_domain_get_assemblies'),'pointer',['pointer','pointer']),
 asmImg:new NativeFunction(E('il2cpp_assembly_get_image'),'pointer',['pointer']),
 imgName:new NativeFunction(E('il2cpp_image_get_name'),'pointer',['pointer']),
 fromName:new NativeFunction(E('il2cpp_class_from_name'),'pointer',['pointer','pointer','pointer']),
 cMethods:new NativeFunction(E('il2cpp_class_get_methods'),'pointer',['pointer','pointer']),
 mName:new NativeFunction(E('il2cpp_method_get_name'),'pointer',['pointer']),
 mParamCount:new NativeFunction(E('il2cpp_method_get_param_count'),'uint',['pointer']),
 isGeneric:new NativeFunction(E('il2cpp_method_is_generic'),'uint',['pointer']),
 strNew:new NativeFunction(E('il2cpp_string_new'),'pointer',['pointer']),
 invoke:new NativeFunction(E('il2cpp_runtime_invoke'),'pointer',['pointer','pointer','pointer','pointer']),
 cType:new NativeFunction(E('il2cpp_class_get_type'),'pointer',['pointer']),
 tObj:new NativeFunction(E('il2cpp_type_get_object'),'pointer',['pointer']),
 objNew:new NativeFunction(E('il2cpp_object_new'),'pointer',['pointer']),
 gchNew:new NativeFunction(E('il2cpp_gchandle_new'),'uint',['pointer','int'])};
function cs(p){try{return p.isNull()?'':p.readUtf8String();}catch(e){return '';}}
function ilstr(p){try{if(p.isNull()||p.compare(ptr(0x10000))<0)return '';return p.add(0x14).readUtf16String(p.add(0x10).readU32());}catch(e){return '';}}
const MAP=__MAP__;
const dom=f.dom();const cnt=Memory.alloc(8),asms=f.asms(dom,cnt),n=cnt.readUInt();
let game=null,core=null,imgm=null,mscor=null;
for(let i=0;i<n;i++){const a=asms.add(i*P).readPointer(),im=f.asmImg(a),nm=cs(f.imgName(im));
 if(nm==='Assembly-CSharp.dll')game=im;if(nm==='UnityEngine.CoreModule.dll')core=im;
 if(nm==='UnityEngine.ImageConversionModule.dll')imgm=im;if(nm==='mscorlib.dll')mscor=im;}
function findMethod(k,meth,argc){if(!k||k.isNull())return null;const it=Memory.alloc(P);it.writePointer(ptr(0));
 for(let i=0;i<600;i++){const mi=f.cMethods(k,it);if(mi.isNull())break;
  if(cs(f.mName(mi))===meth&&f.mParamCount(mi)===argc&&!f.isGeneric(mi))return mi;}return null;}
function inv(mi,obj,args){const exc=Memory.alloc(P);exc.writePointer(ptr(0));
 return f.invoke(mi,obj,args||ptr(0),exc);}
function A(){return Memory.alloc(P);}
function sarg(s){const a=A();a.writePointer(f.strNew(Memory.allocUtf8String(s)));return a;}
const GO=f.fromName(core,Memory.allocUtf8String('UnityEngine'),Memory.allocUtf8String('GameObject'));
const OBJ=f.fromName(core,Memory.allocUtf8String('UnityEngine'),Memory.allocUtf8String('Object'));
const COMP=f.fromName(core,Memory.allocUtf8String('UnityEngine'),Memory.allocUtf8String('Component'));
const REND=f.fromName(core,Memory.allocUtf8String('UnityEngine'),Memory.allocUtf8String('Renderer'));
const MAT=f.fromName(core,Memory.allocUtf8String('UnityEngine'),Memory.allocUtf8String('Material'));
const TEX=f.fromName(core,Memory.allocUtf8String('UnityEngine'),Memory.allocUtf8String('Texture2D'));
const IMGCONV=f.fromName(imgm,Memory.allocUtf8String('UnityEngine'),Memory.allocUtf8String('ImageConversion'));
const IOFILE=f.fromName(mscor,Memory.allocUtf8String('System.IO'),Memory.allocUtf8String('File'));
const findGO=findMethod(GO,'Find',1);
const MR=f.fromName(core,Memory.allocUtf8String('UnityEngine'),Memory.allocUtf8String('MeshRenderer'));
const getComp=findMethod(GO,'GetComponentsInChildren',1);
const getMat=findMethod(REND,'get_sharedMaterial',0);
const setMain=findMethod(MAT,'set_mainTexture',1);
const getName=findMethod(OBJ,'get_name',0);
const texCtor=findMethod(TEX,'.ctor',2);
const loadImg=findMethod(IMGCONV,'LoadImage',2);
const readAll=findMethod(IOFILE,'ReadAllBytes',1);
send({log:'apis find='+!!findGO+' comp='+!!getComp+' mat='+!!getMat+' main='+!!setMain+' tex='+!!texCtor+' img='+!!loadImg+' read='+!!readAll+' map='+Object.keys(MAP).length});
const rendType=f.tObj(f.cType(MR));
let phase=0,arr=null,total=0,idx=0,applied=0,missing=0;
const cache={};
function work(){
 if(phase===0){
  phase=1;
  const go=inv(findGO,ptr(0),sarg('CHRISTMAS(Clone)'));
  send({log:'root='+(go.isNull()?'null':'ok')});
  if(go.isNull()){phase=9;return;}
  const a=A();a.writePointer(rendType);
  arr=inv(getComp,go,a);
  if(arr.isNull()){phase=9;return;}
  total=arr.add(0x18).readU64().toNumber();
  send({log:'renderers(all)='+total});
  phase=1;
  return;
 }
 if(phase===1){
  for(let k=0;k<8&&idx<total;k++,idx++){
   const r=arr.add(0x20).add(idx*P).readPointer();
   if(r.isNull()||r.compare(ptr(0x10000))<0)continue;
   const mat=inv(getMat,r,ptr(0));
   if(mat.isNull())continue;
   let nm=ilstr(inv(getName,mat,ptr(0)));
   nm=nm.replace(' (Instance)','');
   const png=MAP[nm];
   if(!png){missing++;continue;}
   let tex=cache[png];
   if(!tex){
    const b=inv(readAll,ptr(0),sarg(png));
    if(b.isNull()||b.compare(ptr(0x10000))<0)continue;
    f.gchNew(b,0);
    const t=f.objNew(TEX);
    const iw=Memory.alloc(4);iw.writeS32(2);const ih=Memory.alloc(4);ih.writeS32(2);
    const ac=A();ac.writePointer(iw);ac.add(P).writePointer(ih);
    inv(texCtor,t,ac);
    const ai=A();ai.writePointer(t);ai.add(P).writePointer(b);
    inv(loadImg,ptr(0),ai);
    f.gchNew(t,0);
    tex=t;cache[png]=t;
   }
   const am=A();am.writePointer(tex);
   inv(setMain,mat,am);
   applied++;
  }
  if(idx>=total){send({log:'done applied='+applied+' missing='+missing});phase=9;}
 }
}
const TIME=f.fromName(core,Memory.allocUtf8String('UnityEngine'),Memory.allocUtf8String('Time'));
const tm=findMethod(TIME,'get_time',0)||findMethod(TIME,'get_deltaTime',0);
if(tm){Interceptor.attach(ptr(tm.add(P).readPointer()),{onEnter(){work();}});send({log:'hooked'});}
else send({log:'no tick'});
"""

js = JS.replace("__MAP__", MAP_JS)
pid = int(sys.argv[1])
s = frida.attach(pid)
sc = s.create_script(js)
sc.on("message", lambda m, d: print(json.dumps(m.get("payload", m), ensure_ascii=False), flush=True))
sc.load()
time.sleep(20)
s.detach()

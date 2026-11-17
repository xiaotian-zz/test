#!/usr/bin/env python3
"""逐帧遍历 CHRISTMAS(Clone) 层级，把 PNG 贴图挂到 MeshRenderer 材质上。

用法: py -3.12 scripts/frida_apply_textures2.py <PID>
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
let core=null,imgm=null,mscor=null;
for(let i=0;i<n;i++){const a=asms.add(i*P).readPointer(),im=f.asmImg(a),nm=cs(f.imgName(im));
 if(nm==='UnityEngine.CoreModule.dll')core=im;if(nm==='UnityEngine.ImageConversionModule.dll')imgm=im;if(nm==='mscorlib.dll')mscor=im;}
function findMethod(k,meth,argc){if(!k||k.isNull())return null;const it=Memory.alloc(P);it.writePointer(ptr(0));
 for(let i=0;i<600;i++){const mi=f.cMethods(k,it);if(mi.isNull())break;
  if(cs(f.mName(mi))===meth&&f.mParamCount(mi)===argc&&!f.isGeneric(mi))return mi;}return null;}
function inv(mi,obj,args){const exc=Memory.alloc(P);exc.writePointer(ptr(0));
 return f.invoke(mi,obj,args||ptr(0),exc);}
function A(){return Memory.alloc(P);}
function sarg(s){const a=A();a.writePointer(f.strNew(Memory.allocUtf8String(s)));return a;}
function iarg(v){const m=Memory.alloc(4);m.writeS32(v);const a=A();a.writePointer(m);return a;}
function unboxI(r){try{return r.add(0x10).readS32();}catch(e){return -1;}}
const GO=f.fromName(core,Memory.allocUtf8String('UnityEngine'),Memory.allocUtf8String('GameObject'));
const OBJ=f.fromName(core,Memory.allocUtf8String('UnityEngine'),Memory.allocUtf8String('Object'));
const COMP=f.fromName(core,Memory.allocUtf8String('UnityEngine'),Memory.allocUtf8String('Component'));
const TR=f.fromName(core,Memory.allocUtf8String('UnityEngine'),Memory.allocUtf8String('Transform'));
const REND=f.fromName(core,Memory.allocUtf8String('UnityEngine'),Memory.allocUtf8String('Renderer'));
const MAT=f.fromName(core,Memory.allocUtf8String('UnityEngine'),Memory.allocUtf8String('Material'));
const TEX=f.fromName(core,Memory.allocUtf8String('UnityEngine'),Memory.allocUtf8String('Texture2D'));
const IMGCONV=f.fromName(imgm,Memory.allocUtf8String('UnityEngine'),Memory.allocUtf8String('ImageConversion'));
const IOFILE=f.fromName(mscor,Memory.allocUtf8String('System.IO'),Memory.allocUtf8String('File'));
const findGO=findMethod(GO,'Find',1);
const getTc=findMethod(GO,'get_transform',0);
const getGO=findMethod(COMP,'get_gameObject',0);
const getComps=findMethod(GO,'GetComponents',1);
const childCount=findMethod(TR,'get_childCount',0);
const getChild=findMethod(TR,'GetChild',1);
const getMat=findMethod(REND,'get_sharedMaterial',0);
const setMain=findMethod(MAT,'set_mainTexture',1);
const getName=findMethod(OBJ,'get_name',0);
const texCtor=findMethod(TEX,'.ctor',2);
const loadImg=findMethod(IMGCONV,'LoadImage',2);
const readAll=findMethod(IOFILE,'ReadAllBytes',1);
send({log:'apis find='+!!findGO+' tc='+!!getTc+' go='+!!getGO+' comps='+!!getComps+' cc='+!!childCount+' child='+!!getChild+' mat='+!!getMat+' main='+!!setMain+' tex='+!!texCtor+' img='+!!loadImg+' read='+!!readAll});
const mrType=f.tObj(f.cType(REND));
let phase=0,stack=[],visited=0,applied=0,missing=0;
const cache={};
function work(){
 if(phase===0){
  phase=1;
  const go=inv(findGO,ptr(0),sarg('CHRISTMAS(Clone)'));
  if(go.isNull()){send({log:'root null'});phase=9;return;}
  const t=inv(getTc,go,ptr(0));
  stack=[t];
  send({log:'root ok, walk start'});
  return;
 }
 if(phase===1){
  let budget=1;
  while(stack.length&&budget>0){
   budget--;visited++;
   const t=stack.pop();
   try{
    const go=inv(getGO,t,ptr(0));
    if(!go.isNull()){
     const a=A();a.writePointer(mrType);
     const arr=inv(getComps,go,a);
     if(!arr.isNull()){
      const len=arr.add(0x18).readU64().toNumber();
      for(let i=0;i<len;i++){
       const r=arr.add(0x20).add(i*P).readPointer();
       if(r.isNull()||r.compare(ptr(0x10000))<0)continue;
       const mat=inv(getMat,r,ptr(0));
       if(mat.isNull())continue;
       let nm=ilstr(inv(getName,mat,ptr(0))).replace(' (Instance)','');
       const png=MAP[nm];
       if(!png){missing++;continue;}
       let tex=cache[png];
       if(!tex){
        const b=inv(readAll,ptr(0),sarg(png));
        if(b.isNull()||b.compare(ptr(0x10000))<0)continue;
        f.gchNew(b,0);
        const tt=f.objNew(TEX);
        const iw=Memory.alloc(4);iw.writeS32(2);const ih=Memory.alloc(4);ih.writeS32(2);
        const ac=A();ac.writePointer(iw);ac.add(P).writePointer(ih);
        inv(texCtor,tt,ac);
        const ai=A();ai.writePointer(tt);ai.add(P).writePointer(b);
        inv(loadImg,ptr(0),ai);
        f.gchNew(tt,0);
        tex=tt;cache[png]=tt;
       }
       const am=A();am.writePointer(tex);
       inv(setMain,mat,am);
       applied++;
      }
     }
    }
    const cc=unboxI(inv(childCount,t,ptr(0)));
    if(visited<8)send({log:'node '+visited+' cc='+cc+' go='+ilstr(inv(getName,go,ptr(0)))});
    for(let i=0;i<cc;i++){
     const ch=inv(getChild,t,iarg(i));
     if(!ch.isNull())stack.push(ch);
    }
   }catch(e){missing++;}
  }
  if(!stack.length){send({log:'done visited='+visited+' applied='+applied+' missing='+missing});phase=9;}
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
time.sleep(25)
s.detach()

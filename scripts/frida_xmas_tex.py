#!/usr/bin/env python3
"""给已注入的 christmas_tree_LOD0 换带贴图的材质。

用法:
  py -3.12 scripts/frida_xmas_tex.py <PID> [png路径]
"""
from __future__ import annotations

import json
import os
import sys
import time

import frida

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_PNG = os.path.join(ROOT, "artifacts", "xmas_export", "christmas_tree_LOD0_christmas_tree_Atlas.png")
NAME = "christmas_tree_LOD0"

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
 objNew:new NativeFunction(E('il2cpp_object_new'),'pointer',['pointer'])};
function cs(p){try{return p.isNull()?'':p.readUtf8String();}catch(e){return '';}}
function findMethod(cls,name,argc){if(cls.isNull())return null;const it=Memory.alloc(P);it.writePointer(ptr(0));for(let i=0;i<600;i++){const m=f.cMethods(cls,it);if(m.isNull())break;if(cs(f.mName(m))===name&&(argc===undefined||f.mParamCount(m)===argc))return m.add(P).readPointer();}return null;}
function findMethodType(cls,name,argc,want){if(cls.isNull())return null;const it=Memory.alloc(P);it.writePointer(ptr(0));for(let i=0;i<600;i++){const m=f.cMethods(cls,it);if(m.isNull())break;if(cs(f.mName(m))===name&&f.mParamCount(m)===argc&&cs(f.typeName(f.getParam(m,0)))===want)return m.add(P).readPointer();}return null;}
const dom=f.dom(),cnt=Memory.alloc(8),asms=f.asms(dom,cnt),n=cnt.readUInt();
let core=null,imgm=null,mscor=null;
for(let i=0;i<n;i++){const a=asms.add(i*P).readPointer(),im=f.asmImg(a),nm=cs(f.imgName(im));
 if(nm==='UnityEngine.CoreModule.dll')core=im;if(nm==='UnityEngine.ImageConversionModule.dll')imgm=im;
 if(nm==='mscorlib.dll')mscor=im;}
function cls(ns,nm){return f.fromName(core,Memory.allocUtf8String(ns),Memory.allocUtf8String(nm));}
const GO=cls('UnityEngine','GameObject'),TR=cls('UnityEngine','Transform'),TIME=cls('UnityEngine','Time');
const MATERIAL=cls('UnityEngine','Material'),SHADER=cls('UnityEngine','Shader'),TEX=cls('UnityEngine','Texture2D');
const MR=cls('UnityEngine','MeshRenderer'),REND=cls('UnityEngine','Renderer');
const IMGCONV=imgm.isNull()?null:f.fromName(imgm,Memory.allocUtf8String('UnityEngine'),Memory.allocUtf8String('ImageConversion'));
const IOFILE=mscor.isNull()?null:f.fromName(mscor,Memory.allocUtf8String('System.IO'),Memory.allocUtf8String('File'));
const find=findMethod(GO,'Find',1);
const getComp=findMethodType(GO,'GetComponent',1,'System.Type')||findMethodType(GO,'GetComponentInChildren',1,'System.Type');
const getMat=findMethod(REND,'get_sharedMaterial',0);
const setMat=findMethod(REND,'set_sharedMaterial',1);
const matCtor=findMethod(MATERIAL,'.ctor',1);
const shFind=findMethod(SHADER,'Find',1);
const matTex=findMethod(MATERIAL,'set_mainTexture',1);
const texCtor=findMethod(TEX,'.ctor',4),texCtor2=findMethod(TEX,'.ctor',2);
const loadImg=IMGCONV?findMethod(IMGCONV,'LoadImage',2):null;
const readAll=IOFILE?findMethod(IOFILE,'ReadAllBytes',1):null;
const ticks=['get_deltaTime','get_time','get_realtimeSinceStartup'].map(x=>findMethod(TIME,x,0)).filter(Boolean);
send({log:'apis '+JSON.stringify({find:!!find,getComp:!!getComp,getMat:!!getMat,setMat:!!setMat,matCtor:!!matCtor,sh:!!shFind,matTex:!!matTex,tex:!!texCtor,load:!!loadImg,read:!!readAll,ticks:ticks.length})});
let done=false;
if(find&&getComp&&getMat&&matCtor&&shFind&&matTex&&texCtor&&loadImg&&readAll&&ticks.length){
 try{f.attach(dom);}catch(e){}
 function apply(){
  if(done)return;done=true;
  try{
   const go=new NativeFunction(find,'pointer',['pointer'])(f.strNew(Memory.allocUtf8String('__NAME__')));
   if(go.isNull()||go.compare(ptr(0x10000))<0){send({log:'object not found'});return;}
   const mr=new NativeFunction(getComp,'pointer',['pointer','pointer'])(go,f.tObj(f.cType(MR)));
   if(mr.isNull()||mr.compare(ptr(0x10000))<0){send({log:'renderer not found'});return;}
   const png=new NativeFunction(readAll,'pointer',['pointer'])(f.strNew(Memory.allocUtf8String('__PNG__')));
   send({log:'png bytes obj '+png});
   const tex=f.objNew(TEX);
   try{new NativeFunction(texCtor,'void',['pointer','int','int','int','int'])(tex,4,4,4,0);}
   catch(e){if(texCtor2)new NativeFunction(texCtor2,'void',['pointer','int','int'])(tex,4,4);else{send({log:'tex ctor err'});return;}}
   const ok=new NativeFunction(loadImg,'int',['pointer','pointer'])(tex,png);
   send({log:'loadimage '+ok});
   let sh=ptr(0),shname='';
   for(const nm of ['Standard','Legacy Shaders/Diffuse','Unlit/Texture']){
    const s=new NativeFunction(shFind,'pointer',['pointer'])(f.strNew(Memory.allocUtf8String(nm)));
    if(!s.isNull()&&s.compare(ptr(0x10000))>=0){sh=s;shname=nm;break;}
   }
   send({log:'shader '+shname});
   if(sh.isNull())return;
   const mat=f.objNew(MATERIAL);new NativeFunction(matCtor,'void',['pointer','pointer'])(mat,sh);
   new NativeFunction(matTex,'void',['pointer','pointer'])(mat,tex);
   new NativeFunction(setMat,'void',['pointer','pointer'])(mr,mat);
   send({log:'material applied'});
  }catch(e){send({log:'EXC '+e+'\n'+e.stack});}
 }
 for(const t of ticks)Interceptor.attach(t,{onEnter(){apply();}});
 send({log:'hooked'});
}else send({log:'api missing'});
"""


def main() -> int:
    pid = int(sys.argv[1])
    png = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_PNG
    js = JS.replace("__NAME__", NAME).replace("__PNG__", png.replace("\\", "/"))
    session = frida.attach(pid)
    script = session.create_script(js)
    script.on("message", lambda m, d: print(json.dumps(m if m.get("type") != "send" else m.get("payload"), ensure_ascii=False)))
    script.load()
    time.sleep(10)
    session.detach()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

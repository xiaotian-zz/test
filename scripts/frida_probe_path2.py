#!/usr/bin/env python3
"""用正确的 MethodInfo 调用 gpdflailkgp，取得原生拼出的 bundle 路径。

用法: py -3.12 scripts/frida_probe_path2.py <PID>
"""
from __future__ import annotations

import json
import sys
import time

import frida

JS = r"""
const ga=Process.getModuleByName('GameAssembly.dll');const E=n=>ga.getExportByName(n),P=Process.pointerSize;
const f={dom:new NativeFunction(E('il2cpp_domain_get'),'pointer',[]),
 attach:new NativeFunction(E('il2cpp_thread_attach'),'pointer',['pointer']),
 asms:new NativeFunction(E('il2cpp_domain_get_assemblies'),'pointer',['pointer','pointer']),
 asmImg:new NativeFunction(E('il2cpp_assembly_get_image'),'pointer',['pointer']),
 imgName:new NativeFunction(E('il2cpp_image_get_name'),'pointer',['pointer']),
 fromName:new NativeFunction(E('il2cpp_class_from_name'),'pointer',['pointer','pointer','pointer']),
 cMethods:new NativeFunction(E('il2cpp_class_get_methods'),'pointer',['pointer','pointer']),
 mName:new NativeFunction(E('il2cpp_method_get_name'),'pointer',['pointer']),
 mParamCount:new NativeFunction(E('il2cpp_method_get_param_count'),'uint',['pointer']),
 strNew:new NativeFunction(E('il2cpp_string_new'),'pointer',['pointer']),
 invoke:new NativeFunction(E('il2cpp_runtime_invoke'),'pointer',['pointer','pointer','pointer','pointer'])};
function cs(p){try{return p.isNull()?'':p.readUtf8String();}catch(e){return '';}}
function ilstr(p){try{if(p.isNull()||p.compare(ptr(0x10000))<0)return '<null>';return p.add(0x14).readUtf16String(p.add(0x10).readU32());}catch(e){return '<err '+e+'>';}}
const dom=f.dom();try{f.attach(dom);}catch(e){}
const cnt=Memory.alloc(8),asms=f.asms(dom,cnt),n=cnt.readUInt();
let game=null,core=null;
for(let i=0;i<n;i++){const a=asms.add(i*P).readPointer(),im=f.asmImg(a),nm=cs(f.imgName(im));
 if(nm==='Assembly-CSharp.dll')game=im;if(nm==='UnityEngine.CoreModule.dll')core=im;}
// 返回 MethodInfo* 本身（不是 invoker）
function findMethod(image,ns,cls,meth,argc){const k=f.fromName(image,Memory.allocUtf8String(ns),Memory.allocUtf8String(cls));if(k.isNull())return null;
 const it=Memory.alloc(P);it.writePointer(ptr(0));
 for(let i=0;i<400;i++){const mi=f.cMethods(k,it);if(mi.isNull())break;
  if(cs(f.mName(mi))===meth&&f.mParamCount(mi)===argc)return mi;}
 return null;}
function invokeStr(mi,arg){const args=Memory.alloc(P);args.writePointer(arg||ptr(0));const exc=Memory.alloc(P);exc.writePointer(ptr(0));
 const r=f.invoke(mi,ptr(0),args,exc);const ex=exc.readPointer();
 return {v:ilstr(r),exc:ex.isNull()?'':ilstr(ex)};
}
function invokeNoArg(mi){const exc=Memory.alloc(P);exc.writePointer(ptr(0));
 const r=f.invoke(mi,ptr(0),ptr(0),exc);const ex=exc.readPointer();
 return {v:ilstr(r),exc:ex.isNull()?'':ilstr(ex)};}
// 1) Unity 路径属性
for(const [cls,prop] of [['Application','get_streamingAssetsPath'],['Application','get_dataPath'],['Application','get_persistentDataPath']]){
 const mi=findMethod(core,'UnityEngine',cls,prop,0);
 if(mi){const r=invokeNoArg(mi);send({log:cls+'.'+prop+' = "'+r.v+'" '+r.exc});}
 else send({log:cls+'.'+prop+' NOT FOUND'});
}
// 2) gpdflailkgp(静态, 1 个 string 参数)
const mi=findMethod(game,'','lnepoeakhib','gpdflailkgp',1);
send({log:'gpdflailkgp mi='+(mi?mi.toString():'null')});
if(mi){
 for(const nm of ['lures_wta','xmas_stalls','xmas_stalls.bundle']){
  const r=invokeStr(mi,f.strNew(Memory.allocUtf8String(nm)));
  send({log:'gpdflailkgp("'+nm+'") = "'+r.v+'" '+r.exc});
 }
}
send({log:'done'});
"""

pid = int(sys.argv[1])
s = frida.attach(pid)
sc = s.create_script(JS)
sc.on("message", lambda m, d: print(json.dumps(m.get("payload", m), ensure_ascii=False), flush=True))
sc.load()
time.sleep(4)
s.detach()

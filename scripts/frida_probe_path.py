#!/usr/bin/env python3
"""直接调用原生 gpdflailkgp 观察路径拼接结果。

用法: py -3.12 scripts/frida_probe_path.py <PID>
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
let game=null;
for(let i=0;i<n;i++){const a=asms.add(i*P).readPointer(),im=f.asmImg(a);if(cs(f.imgName(im))==='Assembly-CSharp.dll')game=im;}
function findMethod(cls,name,argc){const it=Memory.alloc(P);it.writePointer(ptr(0));for(let i=0;i<400;i++){const mi=f.cMethods(cls,it);if(mi.isNull())break;if(cs(f.mName(mi))===name&&f.mParamCount(mi)===argc)return mi.add(P).readPointer();}return null;}
const K=f.fromName(game,Memory.allocUtf8String(''),Memory.allocUtf8String('lnepoeakhib'));
const mi=findMethod(K,'gpdflailkgp',1);
send({log:'methodInfo='+(mi?mi.toString():'null')});
if(mi){
 const names=['lures_wta','xmas_stalls.bundle','xmas_stalls','F:\\rea\\artifacts\\xmas_stalls.bundle'];
 for(const nm of names){
  const args=Memory.alloc(P);
  args.writePointer(f.strNew(Memory.allocUtf8String(nm)));
  const exc=Memory.alloc(P);exc.writePointer(ptr(0));
  let out=null;
  try{out=f.invoke(mi,ptr(0),args,exc);}catch(e){send({log:'invoke err '+nm+' '+e});continue;}
  const ex=exc.readPointer();
  send({log:'path("'+nm+'") => "'+ilstr(out)+'"'+(ex.isNull()?'':' EXC '+ilstr(ex.add(0x10).readPointer()))});
 }
}
send({log:'done'});
"""

pid = int(sys.argv[1])
s = frida.attach(pid)
sc = s.create_script(JS)
sc.on("message", lambda m, d: print(json.dumps(m.get("payload", m), ensure_ascii=False)))
sc.load()
time.sleep(4)
s.detach()

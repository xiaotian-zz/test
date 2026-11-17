#!/usr/bin/env python3
"""走原生加载并直接检查 AssetBundleCreateRequest 状态。

用法: py -3.12 scripts/frida_native_load2.py <PID> <bundleName>
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
 invoke:new NativeFunction(E('il2cpp_runtime_invoke'),'pointer',['pointer','pointer','pointer','pointer']),
 fieldFromName:new NativeFunction(E('il2cpp_class_get_field_from_name'),'pointer',['pointer','pointer']),
 staticGet:new NativeFunction(E('il2cpp_field_static_get_value'),'void',['pointer','pointer']),
 gchNew:new NativeFunction(E('il2cpp_gchandle_new'),'uint',['pointer','int'])};
function cs(p){try{return p.isNull()?'':p.readUtf8String();}catch(e){return '';}}
function ilstr(p){try{if(p.isNull()||p.compare(ptr(0x10000))<0)return '<null>';return p.add(0x14).readUtf16String(p.add(0x10).readU32());}catch(e){return '<err>';}}
const dom=f.dom();try{f.attach(dom);}catch(e){}
const cnt=Memory.alloc(8),asms=f.asms(dom,cnt),n=cnt.readUInt();
let game=null,core=null,abm=null;
for(let i=0;i<n;i++){const a=asms.add(i*P).readPointer(),im=f.asmImg(a),nm=cs(f.imgName(im));
 if(nm==='Assembly-CSharp.dll')game=im;if(nm==='UnityEngine.CoreModule.dll')core=im;if(nm==='UnityEngine.AssetBundleModule.dll')abm=im;}
function findMethod(k,meth,argc){if(!k||k.isNull())return null;const it=Memory.alloc(P);it.writePointer(ptr(0));
 for(let i=0;i<500;i++){const mi=f.cMethods(k,it);if(mi.isNull())break;
  if(cs(f.mName(mi))===meth&&f.mParamCount(mi)===argc)return mi;}return null;}
function inv(mi,obj,args){const exc=Memory.alloc(P);exc.writePointer(ptr(0));
 const r=f.invoke(mi,obj,args||ptr(0),exc);const ex=exc.readPointer();
 if(!ex.isNull())send({log:'EXC '+ilstr(ex)});return r;}
function unboxBool(r){try{return r.add(0x10).readU8();}catch(e){return -1;}}
const K=f.fromName(game,Memory.allocUtf8String(''),Memory.allocUtf8String('pgohfpicjjd'));
const fld=K.isNull()?null:f.fieldFromName(K,Memory.allocUtf8String('hfcggegmohh'));
let inst=null;
if(fld&&!fld.isNull()){const b=Memory.alloc(P);f.staticGet(fld,b);inst=b.readPointer();}
const L=f.fromName(game,Memory.allocUtf8String(''),Memory.allocUtf8String('lnepoeakhib'));
const gho=findMethod(L,'ghoioimpjia',1);
send({log:'singleton='+(inst?inst.toString():'null')+' gho='+(gho?gho.toString():'null')});
if(inst&&gho){
 const args=Memory.alloc(P*2);
 args.writePointer(inst);
 args.writePointer(f.strNew(Memory.allocUtf8String('__NAME__')));
 const ret=inv(gho,inst,args);
 send({log:'ghoioimpjia -> '+(ret.isNull()?'null':ret.toString())});
 if(!ret.isNull()&&ret.compare(ptr(0x10000))>=0){
  f.gchNew(ret,0);
  const reqPtr=ret.add(0x10).readPointer();
  send({log:'request field = '+reqPtr.toString()});
  const ASYNC=f.fromName(core,Memory.allocUtf8String('UnityEngine'),Memory.allocUtf8String('AsyncOperation'));
  const ACR=f.fromName(abm,Memory.allocUtf8String('UnityEngine'),Memory.allocUtf8String('AssetBundleCreateRequest'));
  const isDone=findMethod(ASYNC,'get_isDone',0);
  const progress=findMethod(ASYNC,'get_progress',0);
  const getBundle=findMethod(ACR,'get_assetBundle',0);
  send({log:'apis isDone='+!!isDone+' progress='+!!progress+' getBundle='+!!getBundle});
  let ticks=0;
  const timer=setInterval(()=>{
   ticks++;
   if(ticks>80){clearInterval(timer);send({log:'timeout'});return;}
   const done=unboxBool(inv(isDone,reqPtr,ptr(0)));
   const prog=unboxBool(inv(progress,reqPtr,ptr(0)));
   if(ticks<=3||done){send({log:'tick'+ticks+' isDone='+done+' prog='+prog});}
   if(done){
    clearInterval(timer);
    const bundle=inv(getBundle,reqPtr,ptr(0));
    send({log:'assetBundle='+(bundle.isNull()?'null':bundle.toString())});
    if(!bundle.isNull()&&bundle.compare(ptr(0x10000))>=0){
     f.gchNew(bundle,0);
     const OBJ=f.fromName(core,Memory.allocUtf8String('UnityEngine'),Memory.allocUtf8String('Object'));
     const gn=findMethod(OBJ,'get_name',0);
     send({log:'bundle name="'+(gn?ilstr(inv(gn,bundle,ptr(0))):'?')+'"'});
    }
   }
  },250);
 }
}
send({log:'setup-done'});
"""

pid = int(sys.argv[1])
name = sys.argv[2]
js = JS.replace("__NAME__", name)
s = frida.attach(pid)
sc = s.create_script(js)
sc.on("message", lambda m, d: print(json.dumps(m.get("payload", m), ensure_ascii=False), flush=True))
sc.load()
time.sleep(8)
s.detach()

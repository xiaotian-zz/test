#!/usr/bin/env python3
"""走原生 lnepoeakhib.ghoioimpjia 加载 xmas_stalls，并等待完成。

用法: py -3.12 scripts/frida_native_load_stall.py <PID>
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
let game=null,core=null;
for(let i=0;i<n;i++){const a=asms.add(i*P).readPointer(),im=f.asmImg(a),nm=cs(f.imgName(im));
 if(nm==='Assembly-CSharp.dll')game=im;if(nm==='UnityEngine.CoreModule.dll')core=im;}
function cls(img,ns,nm){return f.fromName(img,Memory.allocUtf8String(ns),Memory.allocUtf8String(nm));}
function findMethod(k,meth,argc){if(!k||k.isNull())return null;const it=Memory.alloc(P);it.writePointer(ptr(0));
 for(let i=0;i<500;i++){const mi=f.cMethods(k,it);if(mi.isNull())break;
  if(cs(f.mName(mi))===meth&&f.mParamCount(mi)===argc)return mi;}return null;}
function listMethods(k){const it=Memory.alloc(P);it.writePointer(ptr(0));const out=[];
 for(let i=0;i<500;i++){const mi=f.cMethods(k,it);if(mi.isNull())break;out.push(cs(f.mName(mi))+'/'+f.mParamCount(mi));}return out;}
function inv(mi,obj,args){const exc=Memory.alloc(P);exc.writePointer(ptr(0));
 const r=f.invoke(mi,obj,args||ptr(0),exc);const ex=exc.readPointer();
 if(!ex.isNull())send({log:'EXC '+ilstr(ex)});return r;}
function boolRet(r){try{return r.add(0x10).readU8()!==0;}catch(e){return false;}}
// 1) 单例
const K=f.fromName(game,Memory.allocUtf8String(''),Memory.allocUtf8String('pgohfpicjjd'));
const fld=K.isNull()?null:f.fieldFromName(K,Memory.allocUtf8String('hfcggegmohh'));
let inst=null;
if(fld&&!fld.isNull()){const b=Memory.alloc(P);f.staticGet(fld,b);inst=b.readPointer();}
send({log:'singleton='+(inst?inst.toString():'null')+' class='+(K.isNull()?'?':cs(f.mName(K)))});
if(!inst||inst.isNull()||inst.compare(ptr(0x10000))<0){send({log:'no singleton, abort'});}
else {
 const L=f.fromName(game,Memory.allocUtf8String(''),Memory.allocUtf8String('lnepoeakhib'));
 const gho=findMethod(L,'ghoioimpjia',1);
 send({log:'ghoioimpjia='+(gho?gho.toString():'null')});
 const args=Memory.alloc(P*2);
 args.writePointer(inst);
 args.writePointer(f.strNew(Memory.allocUtf8String('xmas_stalls_b')));
 const ret=inv(gho,inst,args);
 send({log:'ghoioimpjia -> '+(ret.isNull()?'null':ret.toString())});
 if(!ret.isNull()&&ret.compare(ptr(0x10000))>=0){
  f.gchNew(ret,0);
  const A=cls(core,'',''); // placeholder
  const PM=f.fromName(game,Memory.allocUtf8String(''),Memory.allocUtf8String('pmonngpimmi'));
  const CI=f.fromName(game,Memory.allocUtf8String(''),Memory.allocUtf8String('ciiamanepjn'));
  send({log:'pmonngpimmi methods: '+JSON.stringify(PM.isNull()?[]:listMethods(PM))});
  send({log:'ciiamanepjn methods: '+JSON.stringify(CI.isNull()?[]:listMethods(CI))});
  const keep=findMethod(CI,'get_keepWaiting',0);
  const ddk=findMethod(CI,'ddkbjcdpelm',0);
  send({log:'keepWait='+(keep?keep.toString():'null')+' ddk='+(ddk?ddk.toString():'null')});
  let ticks=0;
  const timer=setInterval(()=>{
   ticks++;
   if(ticks>150){clearInterval(timer);send({log:'timeout waiting'});return;}
   let waiting=true;
   try{waiting=keep?boolRet(inv(keep,ret,ptr(0))):false;}catch(e){send({log:'keep err '+e});clearInterval(timer);return;}
   if(!waiting){
    clearInterval(timer);
    const bundle=ddk?inv(ddk,ret,ptr(0)):ptr(0);
    send({log:'assetBundle='+(bundle.isNull()?'null':bundle.toString())});
    if(!bundle.isNull()&&bundle.compare(ptr(0x10000))>=0){
     f.gchNew(bundle,0);
     const OBJ=f.fromName(core,Memory.allocUtf8String('UnityEngine'),Memory.allocUtf8String('Object'));
     const getName=findMethod(OBJ,'get_name',0);
     const nm=getName?ilstr(inv(getName,bundle,ptr(0))):'?';
     send({log:'bundle name="'+nm+'"'});
    }
   }
  },200);
 }
}
send({log:'done-setup'});
"""

pid = int(sys.argv[1])
s = frida.attach(pid)
sc = s.create_script(JS)
sc.on("message", lambda m, d: print(json.dumps(m.get("payload", m), ensure_ascii=False), flush=True))
sc.load()
time.sleep(40)
s.detach()

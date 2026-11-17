#!/usr/bin/env python3
"""把 xmas_ok 实例化到相机前方（单点 hook，主线程安全）。

用法: py -3.12 scripts/frida_spawn_ok.py <PID>
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
 gchNew:new NativeFunction(E('il2cpp_gchandle_new'),'uint',['pointer','int']),
 isGeneric:new NativeFunction(E('il2cpp_method_is_generic'),'uint',['pointer']),
 objClass:new NativeFunction(E('il2cpp_object_get_class'),'pointer',['pointer']),
 clsName:new NativeFunction(E('il2cpp_class_get_name'),'pointer',['pointer'])};
function cs(p){try{return p.isNull()?'':p.readUtf8String();}catch(e){return '';}}
function ilstr(p){try{if(p.isNull()||p.compare(ptr(0x10000))<0)return '';return p.add(0x14).readUtf16String(p.add(0x10).readU32());}catch(e){return '';}}
const dom=f.dom();
const cnt=Memory.alloc(8),asms=f.asms(dom,cnt),n=cnt.readUInt();
let game=null,core=null,abm=null;
for(let i=0;i<n;i++){const a=asms.add(i*P).readPointer(),im=f.asmImg(a),nm=cs(f.imgName(im));
 if(nm==='Assembly-CSharp.dll')game=im;if(nm==='UnityEngine.CoreModule.dll')core=im;if(nm==='UnityEngine.AssetBundleModule.dll')abm=im;}
function findMethod(k,meth,argc){if(!k||k.isNull())return null;const it=Memory.alloc(P);it.writePointer(ptr(0));
 for(let i=0;i<600;i++){const mi=f.cMethods(k,it);if(mi.isNull())break;
  if(cs(f.mName(mi))===meth&&f.mParamCount(mi)===argc&&!f.isGeneric(mi))return mi;}return null;}
function inv(mi,obj,args){const exc=Memory.alloc(P);exc.writePointer(ptr(0));
 const r=f.invoke(mi,obj,args||ptr(0),exc);return r;}
function unboxI(r){try{return r.add(0x10).readU8();}catch(e){return -1;}}
const GO=f.fromName(core,Memory.allocUtf8String('UnityEngine'),Memory.allocUtf8String('GameObject'));
const OBJ=f.fromName(core,Memory.allocUtf8String('UnityEngine'),Memory.allocUtf8String('Object'));
const TR=f.fromName(core,Memory.allocUtf8String('UnityEngine'),Memory.allocUtf8String('Transform'));
const CAM=f.fromName(core,Memory.allocUtf8String('UnityEngine'),Memory.allocUtf8String('Camera'));
const AB=f.fromName(abm,Memory.allocUtf8String('UnityEngine'),Memory.allocUtf8String('AssetBundle'));
const inst=findMethod(OBJ,'Instantiate',1);
const loadAsset=findMethod(AB,'LoadAsset',2);
const cType=new NativeFunction(E('il2cpp_class_get_type'),'pointer',['pointer']);
const tObj=new NativeFunction(E('il2cpp_type_get_object'),'pointer',['pointer']);
const goType=tObj(cType(GO));
const getT=findMethod(GO,'get_transform',0);
const COMP=f.fromName(core,Memory.allocUtf8String('UnityEngine'),Memory.allocUtf8String('Component'));
const getTc=findMethod(COMP,'get_transform',0);
const setPos=findMethod(TR,'set_position_Injected',1);
const getPos=findMethod(TR,'get_position_Injected',1);
const getRot=findMethod(TR,'get_rotation_Injected',1);
const camMain=findMethod(CAM,'get_main',0);
const setAct=findMethod(GO,'SetActive',1);
const setRot=findMethod(TR,'set_rotation_Injected',1);
const destroy=findMethod(OBJ,'Destroy',1);
const findObjs=findMethod(OBJ,'FindObjectsOfType',1);
const getName=findMethod(OBJ,'get_name',0);
const TIME=f.fromName(core,Memory.allocUtf8String('UnityEngine'),Memory.allocUtf8String('Time'));
const tickM=findMethod(TIME,'get_time',0)||findMethod(TIME,'get_deltaTime',0)||findMethod(TIME,'get_realtimeSinceStartup',0);
send({log:'apis inst='+!!inst+' load='+!!loadAsset+' pos='+!!setPos+' cam='+!!camMain+' act='+!!setAct+' name='+!!getName});
const iInst=inst?new NativeFunction(inst.add(P).readPointer(),'pointer',['pointer']):null;
const iLoad=loadAsset?new NativeFunction(loadAsset.add(P).readPointer(),'pointer',['pointer','pointer']):null;
const iGetT=getT?new NativeFunction(getT.add(P).readPointer(),'pointer',['pointer']):null;
const iSetPos=setPos?new NativeFunction(setPos.add(P).readPointer(),'void',['pointer','pointer']):null;
const iGetPos=getPos?new NativeFunction(getPos.add(P).readPointer(),'void',['pointer','pointer']):null;
const iGetRot=getRot?new NativeFunction(getRot.add(P).readPointer(),'void',['pointer','pointer']):null;
const iCam=camMain?new NativeFunction(camMain.add(P).readPointer(),'pointer',[]):null;
const iAct=setAct?new NativeFunction(setAct.add(P).readPointer(),'void',['pointer','int']):null;
const iName=getName?new NativeFunction(getName.add(P).readPointer(),'pointer',['pointer']):null;
function V3(x,y,z){const m=Memory.alloc(12);m.writeFloat(x);m.add(4).writeFloat(y);m.add(8).writeFloat(z);return m;}
// bundle 加载状态
const K=f.fromName(game,Memory.allocUtf8String(''),Memory.allocUtf8String('pgohfpicjjd'));
const fld=K.isNull()?null:f.fieldFromName(K,Memory.allocUtf8String('hfcggegmohh'));
let lhb=null;if(fld&&!fld.isNull()){const b=Memory.alloc(P);f.staticGet(fld,b);lhb=b.readPointer();}
const L=f.fromName(game,Memory.allocUtf8String(''),Memory.allocUtf8String('lnepoeakhib'));
const gho=findMethod(L,'ghoioimpjia',1);
const CI=f.fromName(game,Memory.allocUtf8String(''),Memory.allocUtf8String('ciiamanepjn'));
const keep=findMethod(CI,'get_keepWaiting',0);
const ddk=findMethod(CI,'ddkbjcdpelm',0);
const ACR=f.fromName(abm,Memory.allocUtf8String('UnityEngine'),Memory.allocUtf8String('AssetBundleCreateRequest'));
const getBundle=findMethod(ACR,'get_assetBundle',0);
const ASYNC=f.fromName(core,Memory.allocUtf8String('UnityEngine'),Memory.allocUtf8String('AsyncOperation'));
const isDone=findMethod(ASYNC,'get_isDone',0);
send({log:'lhb='+(lhb?lhb.toString():'null')+' gho='+!!gho+' keep='+!!keep+' ddk='+!!ddk});
let phase=0, yld=null, bundle=null, spawned=null, ticks=0;
function work(){
 if(phase===0){
  phase=1;
  if(findObjs&&destroy){
   try{
    const a1=Memory.alloc(P);a1.writePointer(goType);
    const arr=inv(findObjs,ptr(0),a1);
    if(!arr.isNull()){const len=arr.add(0x18).readU64().toNumber();let cnt=0;
     for(let i=0;i<len;i++){const o=arr.add(0x20).add(i*P).readPointer();if(o.isNull()||o.compare(ptr(0x10000))<0)continue;
      const nm=ilstr(inv(getName,o,ptr(0)));
      if(nm.indexOf('CHRISTMAS')>=0){const pd=Memory.alloc(P);pd.writePointer(o);inv(destroy,ptr(0),pd);cnt++;}}
     send({log:'cleaned clones='+cnt});}
   }catch(e){send({log:'clean err '+e});}
  }
  const args=Memory.alloc(P*2);args.writePointer(lhb);args.writePointer(f.strNew(Memory.allocUtf8String('xmas_clone17')));
  yld=inv(gho,lhb,args);
  send({log:'request -> '+(yld.isNull()?'null':yld.toString())});
  return;
 }
 if(phase===1){
  ticks++;
  let cls='';
  try{cls=cs(f.clsName(f.objClass(yld)));}catch(e){}
  if(ticks%20===1)send({log:'tick cls='+cls});
  let ready=false;
  if(cls==='ciiamanepjn'){
   const req=yld.add(0x10).readPointer();
   try{ready=unboxI(inv(isDone,req,ptr(0)))!==0;}catch(e){send({log:'isDone err '+e});phase=9;return;}
   if(ready)bundle=inv(getBundle,req,ptr(0));
  }else{
   ready=true;bundle=yld.add(0x10).readPointer();
  }
  if(ready){
   send({log:'bundle='+(bundle.isNull()?'null':bundle.toString())});
   if(bundle.isNull()){phase=9;return;}
   f.gchNew(bundle,0);
   const pa=Memory.alloc(P*2);pa.writePointer(f.strNew(Memory.allocUtf8String('assets/rf4local/xmas_clone17.prefab')));pa.add(P).writePointer(goType);
   const a=inv(loadAsset,bundle,pa);
   send({log:'asset='+(a.isNull()?'null':a.toString())+' name='+(a.isNull()?'':ilstr(inv(getName,a,ptr(0))))});
   if(a.isNull()){phase=9;return;}
   f.gchNew(a,0);
   const pi=Memory.alloc(P);pi.writePointer(a);
   const obj=inv(inst,ptr(0),pi);
   send({log:'instantiated='+(obj.isNull()?'null':obj.toString())+' name='+(obj.isNull()?'':ilstr(inv(getName,obj,ptr(0))))});
   if(obj.isNull()){phase=9;return;}
   f.gchNew(obj,0);spawned=obj;phase=2;
   try{
    const t=inv(getT,obj,ptr(0));
    const pos=V3(233.36000061035156,2.6600000858306885,784.3599853515625);
    const pv=Memory.alloc(P);pv.writePointer(pos);inv(setPos,t,pv);
    const rot=Memory.alloc(16);rot.writeFloat(0.0026856011245399714);rot.add(4).writeFloat(-0.35955774784088135);rot.add(8).writeFloat(0.0010348404757678509);rot.add(12).writeFloat(0.9331184029579163);
    const pr=Memory.alloc(P);pr.writePointer(rot);inv(setRot,t,pr);
    // 强制激活，否则 prefab 若默认 inactive 会既不渲染也搜不到
    if(iAct){iAct(obj,1);}
    const av=Memory.alloc(12);const ap=Memory.alloc(P);ap.writePointer(av);inv(getPos,t,ap);
    const act=findMethod(GO,'get_activeSelf',0);
    send({log:'placed at '+av.readFloat().toFixed(2)+','+av.add(4).readFloat().toFixed(2)+','+av.add(8).readFloat().toFixed(2)
      +(act?' active='+unboxI(inv(act,obj,ptr(0))):'')});
   }catch(e){send({log:'place err '+e});}
   send({log:'SPAWNED'});
  }
 }
}
const rails=[];
const t1=Interceptor.attach(ptr(tickM.add(P).readPointer()),{onEnter(){work();}});
rails.push(t1);
send({log:'hooked Time tick, waiting...'});
"""

#

pid = int(sys.argv[1])
s = frida.attach(pid)
sc = s.create_script(JS)
sc.on("message", lambda m, d: print(json.dumps(m.get("payload", m), ensure_ascii=False), flush=True))
sc.load()
time.sleep(60)
s.detach()

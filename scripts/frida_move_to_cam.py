#!/usr/bin/env python3
"""把已生成的 CHRISTMAS(Clone) 挪到主相机正前方，并回传相机坐标。

用法: py -3.12 scripts/frida_move_to_cam.py <PID>
"""
from __future__ import annotations

import json
import os
import sys
import time

import frida

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
 strNew:new NativeFunction(E('il2cpp_string_new'),'pointer',['pointer']),
 invoke:new NativeFunction(E('il2cpp_runtime_invoke'),'pointer',['pointer','pointer','pointer','pointer']),
 isGeneric:new NativeFunction(E('il2cpp_method_is_generic'),'uint',['pointer']),
 cType:new NativeFunction(E('il2cpp_class_get_type'),'pointer',['pointer']),
 tObj:new NativeFunction(E('il2cpp_type_get_object'),'pointer',['pointer'])};
function cs(p){try{return p.isNull()?'':p.readUtf8String();}catch(e){return '';}}
function ilstr(p){try{if(p.isNull()||p.compare(ptr(0x10000))<0)return '';return p.add(0x14).readUtf16String(p.add(0x10).readU32());}catch(e){return '';}}
const dom=f.dom();
const cnt=Memory.alloc(8),asms=f.asms(dom,cnt),n=cnt.readUInt();
let core=null,abm=null;
for(let i=0;i<n;i++){const a=asms.add(i*P).readPointer(),im=f.asmImg(a),nm=cs(f.imgName(im));
 if(nm==='UnityEngine.CoreModule.dll')core=im;if(nm==='UnityEngine.AssetBundleModule.dll')abm=im;}
function findMethod(k,meth,argc){if(!k||k.isNull())return null;const it=Memory.alloc(P);it.writePointer(ptr(0));
 for(let i=0;i<600;i++){const mi=f.cMethods(k,it);if(mi.isNull())break;
  if(cs(f.mName(mi))===meth&&f.mParamCount(mi)===argc&&!f.isGeneric(mi))return mi;}return null;}
function inv(mi,obj,args){const exc=Memory.alloc(P);exc.writePointer(ptr(0));
 return f.invoke(mi,obj,args||ptr(0),exc);}
const GO=f.fromName(core,Memory.allocUtf8String('UnityEngine'),Memory.allocUtf8String('GameObject'));
const OBJ=f.fromName(core,Memory.allocUtf8String('UnityEngine'),Memory.allocUtf8String('Object'));
const TR=f.fromName(core,Memory.allocUtf8String('UnityEngine'),Memory.allocUtf8String('Transform'));
const CAM=f.fromName(core,Memory.allocUtf8String('UnityEngine'),Memory.allocUtf8String('Camera'));
const COMP=f.fromName(core,Memory.allocUtf8String('UnityEngine'),Memory.allocUtf8String('Component'));
const goType=f.tObj(f.cType(GO));
const findObjs=findMethod(OBJ,'FindObjectsOfType',1);
const getName=findMethod(OBJ,'get_name',0);
const getTc=findMethod(COMP,'get_transform',0);
const camMain=findMethod(CAM,'get_main',0);
const setPos=findMethod(TR,'set_position_Injected',1);
const getPos=findMethod(TR,'get_position_Injected',1);
const getRot=findMethod(TR,'get_rotation_Injected',1);
const setRot=findMethod(TR,'set_rotation_Injected',1);
const TIME=f.fromName(core,Memory.allocUtf8String('UnityEngine'),Memory.allocUtf8String('Time'));
const tickM=findMethod(TIME,'get_time',0)||findMethod(TIME,'get_deltaTime',0)||findMethod(TIME,'get_realtimeSinceStartup',0);
const getScale=findMethod(TR,'get_localScale_Injected',1);
const MODE=__MODE__;
send({log:'mode='+MODE+' apis find='+!!findObjs+' cam='+!!camMain+' tc='+!!getTc+' pos='+!!setPos+' rot='+!!setRot+' scale='+!!getScale});
const iFind=findObjs?new NativeFunction(findObjs.add(P).readPointer(),'pointer',['pointer']):null;
const iName=getName?new NativeFunction(getName.add(P).readPointer(),'pointer',['pointer']):null;
const iTc=getTc?new NativeFunction(getTc.add(P).readPointer(),'pointer',['pointer']):null;
const iCam=camMain?new NativeFunction(camMain.add(P).readPointer(),'pointer',[]):null;
const iSetPos=setPos?new NativeFunction(setPos.add(P).readPointer(),'void',['pointer','pointer']):null;
const iGetPos=getPos?new NativeFunction(getPos.add(P).readPointer(),'void',['pointer','pointer']):null;
const iGetRot=getRot?new NativeFunction(getRot.add(P).readPointer(),'void',['pointer','pointer']):null;
const iSetRot=setRot?new NativeFunction(setRot.add(P).readPointer(),'void',['pointer','pointer']):null;
const iGetScale=getScale?new NativeFunction(getScale.add(P).readPointer(),'void',['pointer','pointer']):null;
let done=false, tick=0;
function fwd(qx,qy,qz,qw){return [2*(qx*qz+qw*qy), 2*(qy*qz-qw*qx), 1-2*(qx*qx+qy*qy)];}
function readV3(t,mi){const b=Memory.alloc(12);const a=Memory.alloc(P);a.writePointer(b);inv(mi,t,a);
 return [b.readFloat(),b.add(4).readFloat(),b.add(8).readFloat()];}
function writeV3(t,mi,v){const b=Memory.alloc(12);b.writeFloat(v[0]);b.add(4).writeFloat(v[1]);b.add(8).writeFloat(v[2]);
 const a=Memory.alloc(P);a.writePointer(b);inv(mi,t,a);}
function readQ(t,mi){const b=Memory.alloc(16);const a=Memory.alloc(P);a.writePointer(b);inv(mi,t,a);
 return [b.readFloat(),b.add(4).readFloat(),b.add(8).readFloat(),b.add(12).readFloat()];}
function writeQ(t,mi,q){const b=Memory.alloc(16);b.writeFloat(q[0]);b.add(4).writeFloat(q[1]);b.add(8).writeFloat(q[2]);b.add(12).writeFloat(q[3]);
 const a=Memory.alloc(P);a.writePointer(b);inv(mi,t,a);}
function ok(p){return p&&!p.isNull()&&p.compare(ptr(0x10000))>=0;}
function work(){
 tick++;
 if(done||tick>4000)return;
 try{
  const ca=inv(camMain,ptr(0),ptr(0));
  if(!ok(ca)){if(tick%120===1)send({log:'no main camera'});return;}
  const ct=inv(getTc,ca,ptr(0));
  if(!ok(ct)){if(tick%120===1)send({log:'no cam transform'});return;}
  const cp=readV3(ct,getPos), cq=readQ(ct,getRot);
  const cx=cp[0],cy=cp[1],cz=cp[2];
  const F=fwd(cq[0],cq[1],cq[2],cq[3]);
  const D=6.0;
  let tv;
  if(MODE==='world')tv=[233.36,2.66,784.36];
  else if(MODE==='cam')tv=[cx+F[0]*D,cy+F[1]*D,cz+F[2]*D];
  const a1=Memory.alloc(P);a1.writePointer(goType);
  const arr=inv(findObjs,ptr(0),a1);
  if(!ok(arr)){if(tick%120===1)send({log:'no objects array'});return;}
  const len=arr.add(0x18).readU64().toNumber();
  let hit=0, info='';
  for(let i=0;i<len;i++){const o=arr.add(0x20).add(i*P).readPointer();
   if(!ok(o))continue;
   const nm=ilstr(inv(getName,o,ptr(0)));
   if(nm.indexOf('CHRISTMAS')<0)continue;
   hit++;
   const t=inv(getTc,o,ptr(0));
   if(!ok(t))continue;
   if(MODE!=='probe'){writeV3(t,setPos,tv);writeQ(t,setRot,cq);}
   const p=readV3(t,getPos), s=readV3(t,getScale);
   info+=' ['+nm+' pos='+p[0].toFixed(2)+','+p[1].toFixed(2)+','+p[2].toFixed(2)
     +' scale='+s[0].toFixed(3)+','+s[1].toFixed(3)+','+s[2].toFixed(3)+']';
  }
  if(MODE==='probe'){
   if(tick%120===1)send({log:'cam='+cx.toFixed(2)+','+cy.toFixed(2)+','+cz.toFixed(2)+' hits='+hit+info});
  } else if(hit>0&&!done){
   done=true;
   send({log:'MOVED clones='+hit+' to '+tv[0].toFixed(2)+','+tv[1].toFixed(2)+','+tv[2].toFixed(2)+' cam='+cx.toFixed(2)+','+cy.toFixed(2)+','+cz.toFixed(2)+info});
  } else if(tick%120===1&&hit===0)send({log:'no CHRISTMAS found (scanned '+len+')'});
 }catch(e){if(tick%120===1)send({log:'err '+e});}
}
Interceptor.attach(ptr(tickM.add(P).readPointer()),{onEnter(){work();}});
send({log:'hooked, waiting'});
"""

pid = int(sys.argv[1])
mode = os.environ.get("MODE", "probe")
s = frida.attach(pid)
sc = s.create_script(JS.replace("__MODE__", json.dumps(mode)))
sc.on("message", lambda m, d: print(json.dumps(m.get("payload", m), ensure_ascii=False), flush=True))
sc.load()
time.sleep(12)
s.detach()

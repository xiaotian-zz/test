#!/usr/bin/env python3
"""加载 xmas_clone13 实例化，并给两个 shop 节点动态挂 Shop 组件、写入 storeID。

用法: py -3.12 scripts/frida_spawn_shop.py <PID>
"""
from __future__ import annotations

import json
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
 invoke:new NativeFunction(E('il2cpp_runtime_invoke'),'pointer',['pointer','pointer','pointer','pointer']),
 isGeneric:new NativeFunction(E('il2cpp_method_is_generic'),'uint',['pointer']),
 fieldFromName:new NativeFunction(E('il2cpp_class_get_field_from_name'),'pointer',['pointer','pointer']),
 staticGet:new NativeFunction(E('il2cpp_field_static_get_value'),'void',['pointer','pointer']),
 gchNew:new NativeFunction(E('il2cpp_gchandle_new'),'uint',['pointer','int']),
 strNew:new NativeFunction(E('il2cpp_string_new'),'pointer',['pointer']),
 objClass:new NativeFunction(E('il2cpp_object_get_class'),'pointer',['pointer']),
 clsName:new NativeFunction(E('il2cpp_class_get_name'),'pointer',['pointer'])};
function cs(p){try{return p.isNull()?'':p.readUtf8String();}catch(e){return '';}}
function ilstr(p){try{if(p.isNull()||p.compare(ptr(0x10000))<0)return '';return p.add(0x14).readUtf16String(p.add(0x10).readU32());}catch(e){return '';}}
const dom=f.dom();const cnt=Memory.alloc(8),asms=f.asms(dom,cnt),n=cnt.readUInt();
let game=null,core=null,abm=null;
for(let i=0;i<n;i++){const a=asms.add(i*P).readPointer(),im=f.asmImg(a),nm=cs(f.imgName(im));
 if(nm==='Assembly-CSharp.dll')game=im;if(nm==='UnityEngine.CoreModule.dll')core=im;if(nm==='UnityEngine.AssetBundleModule.dll')abm=im;}
function findMethod(k,meth,argc){if(!k||k.isNull())return null;const it=Memory.alloc(P);it.writePointer(ptr(0));
 for(let i=0;i<800;i++){const mi=f.cMethods(k,it);if(mi.isNull())break;
  if(cs(f.mName(mi))===meth&&f.mParamCount(mi)===argc&&!f.isGeneric(mi))return mi;}return null;}
function inv(mi,obj,args){const exc=Memory.alloc(P);exc.writePointer(ptr(0));return f.invoke(mi,obj,args||ptr(0),exc);}
function unboxI(r){try{return r.add(0x10).readU8();}catch(e){return -1;}}
const GO=f.fromName(core,Memory.allocUtf8String('UnityEngine'),Memory.allocUtf8String('GameObject'));
const OBJ=f.fromName(core,Memory.allocUtf8String('UnityEngine'),Memory.allocUtf8String('Object'));
const TR=f.fromName(core,Memory.allocUtf8String('UnityEngine'),Memory.allocUtf8String('Transform'));
const COMP=f.fromName(core,Memory.allocUtf8String('UnityEngine'),Memory.allocUtf8String('Component'));
const AB=f.fromName(abm,Memory.allocUtf8String('UnityEngine'),Memory.allocUtf8String('AssetBundle'));
const SHOP=f.fromName(game,Memory.allocUtf8String('RF4.Client.FishingScene'),Memory.allocUtf8String('Shop'));
const REVERT=f.fromName(game,Memory.allocUtf8String('RF4.Client.FishingScene'),Memory.allocUtf8String('RevertPositionAfterPlayerTeleport'));
const inst=findMethod(OBJ,'Instantiate',1);
const loadAsset=findMethod(AB,'LoadAsset',2);
const cType=new NativeFunction(E('il2cpp_class_get_type'),'pointer',['pointer']);
const tObj=new NativeFunction(E('il2cpp_type_get_object'),'pointer',['pointer']);
const goType=tObj(cType(GO));
const shopType=(SHOP&&!SHOP.isNull())?tObj(cType(SHOP)):null;
const getT=findMethod(GO,'get_transform',0);
const getT2=findMethod(COMP,'get_transform',0);
const getGO=findMethod(COMP,'get_gameObject',0);
const trFind=findMethod(TR,'Find',1);
const addComp=findMethod(GO,'AddComponent',1);
const findGO=findMethod(GO,'Find',1);
const getComps=findMethod(GO,'GetComponents',1);
const getPosI=findMethod(TR,'get_position_Injected',1);
const setPosI=findMethod(TR,'set_position_Injected',1);
const setRotI=findMethod(TR,'set_rotation_Injected',1);
const getChildren=findMethod(GO,'GetComponentsInChildren',1);
const RENDERER=f.fromName(core,Memory.allocUtf8String('UnityEngine'),Memory.allocUtf8String('Renderer'));
const BEHAVIOUR=f.fromName(core,Memory.allocUtf8String('UnityEngine'),Memory.allocUtf8String('Behaviour'));
const setEnabled=findMethod(BEHAVIOUR,'set_enabled',1);
const rendererType=(RENDERER&&!RENDERER.isNull())?tObj(cType(RENDERER)):null;
const findObjs=findMethod(OBJ,'FindObjectsOfType',1);
const getName=findMethod(OBJ,'get_name',0);
const destroy=findMethod(OBJ,'Destroy',1);
const TIME=f.fromName(core,Memory.allocUtf8String('UnityEngine'),Memory.allocUtf8String('Time'));
const CAM=f.fromName(core,Memory.allocUtf8String('UnityEngine'),Memory.allocUtf8String('Camera'));
const camMain=findMethod(CAM,'get_main',0);
const tickM=findMethod(TIME,'get_time',0);
send({log:'apis shop='+(shopType?shopType.toString():'null')+' find='+!!trFind+' add='+!!addComp+' gg='+!!getGO+' of='+!!findObjs});
const iInst=inst?new NativeFunction(inst.add(P).readPointer(),'pointer',['pointer']):null;
const iLoad=loadAsset?new NativeFunction(loadAsset.add(P).readPointer(),'pointer',['pointer','pointer']):null;
const iGetT=getT?new NativeFunction(getT.add(P).readPointer(),'pointer',['pointer']):null;
const iFind=trFind?new NativeFunction(trFind.add(P).readPointer(),'pointer',['pointer','pointer']):null;
const iGetGO=getGO?new NativeFunction(getGO.add(P).readPointer(),'pointer',['pointer']):null;
const iAdd=addComp?new NativeFunction(addComp.add(P).readPointer(),'pointer',['pointer','pointer']):null;
const iFindGO=findGO?new NativeFunction(findGO.add(P).readPointer(),'pointer',['pointer']):null;
const iGetComps=getComps?new NativeFunction(getComps.add(P).readPointer(),'pointer',['pointer','pointer']):null;
const iGetPos=getPosI?new NativeFunction(getPosI.add(P).readPointer(),'void',['pointer','pointer']):null;
const iSetPos=setPosI?new NativeFunction(setPosI.add(P).readPointer(),'void',['pointer','pointer']):null;
const iSetRot=setRotI?new NativeFunction(setRotI.add(P).readPointer(),'void',['pointer','pointer']):null;
const iGetChildren=getChildren?new NativeFunction(getChildren.add(P).readPointer(),'pointer',['pointer','pointer']):null;
const iSetEnabled=setEnabled?new NativeFunction(setEnabled.add(P).readPointer(),'void',['pointer','int']):null;
const iCam=camMain?new NativeFunction(camMain.add(P).readPointer(),'pointer',[]):null;
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
let phase=0,yld=null,bundle=null,spawned=null,ticks=0;
function arg1(p){const a=Memory.alloc(P);a.writePointer(p);return a;}
function work(){
 if(phase===0){
  phase=1;
  if(findObjs&&destroy){
   try{
    const arr=inv(findObjs,ptr(0),arg1(goType));
    if(!arr.isNull()){const len=arr.add(0x18).readU64().toNumber();let c=0;
     for(let i=0;i<len;i++){const o=arr.add(0x20).add(i*P).readPointer();if(o.isNull()||o.compare(ptr(0x10000))<0)continue;
      if(ilstr(inv(getName,o,ptr(0))).match(/CHRISTMAS|Sea_bait_shop_12.*\(Clone\)/)){inv(destroy,ptr(0),arg1(o));c++;}}
     send({log:'cleaned '+c});}
   }catch(e){send({log:'clean err '+e});}
  }
  const args=Memory.alloc(P*2);args.writePointer(lhb);args.writePointer(f.strNew(Memory.allocUtf8String('xmas_clone13')));
  yld=inv(gho,lhb,args);
  send({log:'request '+(yld.isNull()?'null':yld.toString())});
  return;
 }
 if(phase===1){
  ticks++;
  let cls='';try{cls=cs(f.clsName(f.objClass(yld)));}catch(e){}
  let ready=false;
  if(cls==='ciiamanepjn'){
   const req=yld.add(0x10).readPointer();
   ready=unboxI(inv(isDone,req,ptr(0)))!==0;
   if(ready)bundle=inv(getBundle,req,ptr(0));
  }else{ready=true;bundle=yld.add(0x10).readPointer();}
  if(ready){
   if(bundle.isNull()){send({log:'bundle null'});phase=9;return;}
   f.gchNew(bundle,0);
   const pa=Memory.alloc(P*2);pa.writePointer(f.strNew(Memory.allocUtf8String('assets/rf4local/xmas_clone13.prefab')));pa.add(P).writePointer(goType);
   const a=inv(loadAsset,bundle,pa);
   if(a.isNull()){send({log:'asset null'});phase=9;return;}
   f.gchNew(a,0);
   const obj=inv(inst,ptr(0),arg1(a));
   if(obj.isNull()){send({log:'inst null'});phase=9;return;}
   f.gchNew(obj,0);spawned=obj;
   const t=inv(getT,obj,ptr(0));
   const pos=Memory.alloc(12);pos.writeFloat(233.36000061035156);pos.add(4).writeFloat(2.6600000858306885);pos.add(8).writeFloat(784.3599853515625);
   inv(setPosI,t,arg1(pos));
   const rot=Memory.alloc(16);rot.writeFloat(0.0026856011245399714);rot.add(4).writeFloat(-0.35955774784088135);rot.add(8).writeFloat(0.0010348404757678509);rot.add(12).writeFloat(0.9331184029579163);
   if(iSetRot)inv(setRotI,t,arg1(rot));
   send({log:'SPAWNED '+ilstr(inv(getName,obj,ptr(0)))});
   phase=2;
  }
 }
 if(phase===2){
  phase=3;
  try{
   let cfg=ptr(0);
   if(findObjs&&shopType){
    const arr=inv(findObjs,ptr(0),arg1(shopType));
    if(!arr.isNull()){const len=arr.add(0x18).readU32();
     for(let i=0;i<len;i++){const o=arr.add(0x20).add(i*P).readPointer();
      if(o.isNull()||o.compare(ptr(0x10000))<0)continue;
      const c=o.add(104).readPointer();
      if(!c.isNull()&&c.compare(ptr(0x10000))>=0){cfg=c;break;}}}
   }
   send({log:'cfg='+cfg});
   const root=inv(getT,spawned,ptr(0));
   const src=iFindGO?iFindGO(f.strNew(Memory.allocUtf8String('Sea_bait_shop_12_interact'))):null;
   send({log:'src='+((src&&!src.isNull())?src.toString():'null')});
   if(!src||src.isNull()){send({log:'no src interact'});}
   else{
    const jobs=[['ny_bazaarStore_012',0,237.57,2.57,792.03],
                ['nybaazar_012',1,237.75,2.52,789.00]];
    for(const j of jobs){
     const wpos=Memory.alloc(12);wpos.writeFloat(j[2]);wpos.add(4).writeFloat(j[3]);wpos.add(8).writeFloat(j[4]);
     const ag=inv(inst,ptr(0),arg1(src));
     if(ag.isNull()){send({log:'agent null '+j[0]});continue;}
     f.gchNew(ag,0);
     const at=inv(getT,ag,ptr(0));
     inv(setPosI,at,arg1(wpos));
     let patched=0;
     if(REVERT&&!REVERT.isNull()&&iGetComps&&destroy){
      const rv=iGetComps(ag,tObj(cType(REVERT)));
      if(rv&&!rv.isNull()){const ln=rv.add(0x18).readU32();
       for(let k=0;k<ln;k++){const c=rv.add(0x20).add(k*P).readPointer();
        if(c.isNull()||c.compare(ptr(0x10000))<0)continue;
        inv(destroy,ptr(0),arg1(c));}}
     }
     if(iGetComps&&shopType){
      const comps=iGetComps(ag,shopType);
      if(comps&&!comps.isNull()){const ln=comps.add(0x18).readU32();
       for(let k=0;k<ln;k++){const c=comps.add(0x20).add(k*P).readPointer();
        if(c.isNull()||c.compare(ptr(0x10000))<0)continue;
        c.add(80).writePointer(f.strNew(Memory.allocUtf8String(j[0])));
        c.add(96).writeInt(j[1]);
        c.add(104).writePointer(ptr(0));
        patched++;}}
     }
     send({log:'agent '+j[0]+' type='+j[1]+' patched='+patched+' pos='+j[2]+','+j[3]+','+j[4]});
    }
   }
  }catch(e){send({log:'shop err '+e});}
  send({log:'DONE'});
 }
}
if(tickM){
 Interceptor.attach(tickM.add(P).readPointer(),{onEnter(){work();}});
 send({log:'hooked'});
}else send({log:'no tick'});
"""


def main():
    pid = int(sys.argv[1])
    s = frida.get_local_device().attach(pid)
    sc = s.create_script(JS)

    def on_msg(m, d):
        payload = m.get("payload") if m.get("type") == "send" else m
        print(json.dumps(payload, ensure_ascii=False), flush=True)
        if isinstance(payload, dict) and payload.get("log") == "DONE":
            time.sleep(0.5)
            s.detach()

    sc.on("message", on_msg)
    sc.load()
    time.sleep(20)


if __name__ == "__main__":
    main()

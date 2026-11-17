"""加载本地 xmas-stalls 资源包，在玩家附近生成新年博览会摊位并挂 Shop。

用法:
  py -3.12 scripts/frida_spawn_xmas_stall.py [PID]
"""
import frida
import json
import sys
import time

PID = int(sys.argv[1]) if len(sys.argv) > 1 else 25668

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
};
function cs(p){try{return p.isNull()?'':p.readUtf8String();}catch(e){return '';}}
function ilstr(p){try{if(p.isNull()||p.compare(ptr(0x10000))<0)return '';const n=p.add(0x10).readU32();return p.add(0x14).readUtf16String(n);}catch(e){return '';}}
function findMethod(cls,name,argc){const it=Memory.alloc(P);it.writePointer(ptr(0));for(let i=0;i<512;i++){const m=f.cMethods(cls,it);if(m.isNull())break;if(cs(f.mName(m))===name&&(argc===undefined||f.mParamCount(m)===argc))return m.add(P).readPointer();}return null;}
function findMethodType(cls,name,argc,want){const it=Memory.alloc(P);it.writePointer(ptr(0));for(let i=0;i<512;i++){const m=f.cMethods(cls,it);if(m.isNull())break;if(cs(f.mName(m))===name&&f.mParamCount(m)===argc&&cs(f.typeName(f.getParam(m,0)))===want)return m.add(P).readPointer();}return null;}
const dom=f.dom(),cnt=Memory.alloc(8),asms=f.asms(dom,cnt),n=cnt.readUInt();let game=null,core=null,abm=null;
for(let i=0;i<n;i++){const a=asms.add(i*P).readPointer(),im=f.asmImg(a),nm=cs(f.imgName(im));if(nm==='Assembly-CSharp.dll')game=im;if(nm==='UnityEngine.CoreModule.dll')core=im;if(nm==='UnityEngine.AssetBundleModule.dll')abm=im;}
const GO=f.fromName(core,Memory.allocUtf8String('UnityEngine'),Memory.allocUtf8String('GameObject'));
const OBJ=f.fromName(core,Memory.allocUtf8String('UnityEngine'),Memory.allocUtf8String('Object'));
const TR=f.fromName(core,Memory.allocUtf8String('UnityEngine'),Memory.allocUtf8String('Transform'));
const CAM=f.fromName(core,Memory.allocUtf8String('UnityEngine'),Memory.allocUtf8String('Camera'));
const TIME=f.fromName(core,Memory.allocUtf8String('UnityEngine'),Memory.allocUtf8String('Time'));
const SHOP=f.fromName(game,Memory.allocUtf8String('RF4.Client.FishingScene'),Memory.allocUtf8String('Shop'));
const AB=f.fromName(abm,Memory.allocUtf8String('UnityEngine'),Memory.allocUtf8String('AssetBundle'));
const find=findMethod(GO,'Find',1),inst=findMethod(OBJ,'Instantiate',1),setAct=findMethod(GO,'SetActive',1);
const getT=findMethod(GO,'get_transform',0),addComp=findMethodType(GO,'AddComponent',1,'System.Type');
const getPosI=findMethod(TR,'get_position_Injected',1),setPosI=findMethod(TR,'set_position_Injected',1);
const getFwdI=findMethod(TR,'get_forward_Injected',1),setRotI=findMethod(TR,'set_rotation_Injected',1),getRotI=findMethod(TR,'get_rotation_Injected',1);
const camMain=findMethod(CAM,'get_main',0),tick=findMethod(TIME,'get_time',0);
const abLoad=findMethod(AB,'LoadFromFile',1),abAsset=findMethod(AB,'LoadAsset',2);
const objFind=findMethodType(OBJ,'FindObjectsOfType',1,'System.Type'),getName=findMethod(OBJ,'get_name',0);
send({log:'apis '+JSON.stringify({find:!!find,inst:!!inst,act:!!setAct,add:!!addComp,gp:!!getPosI,sp:!!setPosI,fwd:!!getFwdI,rot:!!getRotI,cam:!!camMain,tick:!!tick,abLoad:!!abLoad,abAsset:!!abAsset})});
let done=false;
if(find&&inst&&setAct&&addComp&&getPosI&&setPosI&&getRotI&&camMain&&tick&&abLoad&&abAsset&&!SHOP.isNull()){
 const NFfind=new NativeFunction(find,'pointer',['pointer']);
 const NFin=new NativeFunction(inst,'pointer',['pointer']);
 const NFgt=new NativeFunction(getT,'pointer',['pointer']);
 const NFadd=new NativeFunction(addComp,'pointer',['pointer','pointer']);
 const NFset=new NativeFunction(setAct,'void',['pointer','int']);
 const NFgp=new NativeFunction(getPosI,'void',['pointer','pointer']);
 const NFsp=new NativeFunction(setPosI,'void',['pointer','pointer']);
 const NFrot=new NativeFunction(getRotI,'void',['pointer','pointer']);
 const NFcam=new NativeFunction(camMain,'pointer',[]);
 const NFload=new NativeFunction(abLoad,'pointer',['pointer']);
 const NFasset=new NativeFunction(abAsset,'pointer',['pointer','pointer','pointer']);
 const NFname=new NativeFunction(getName,'pointer',['pointer']);
 function V3(x,y,z){const m=Memory.alloc(12);m.writeFloat(x);m.add(4).writeFloat(y);m.add(8).writeFloat(z);return m;}
 try{f.attach(dom);}catch(e){}
 function spawn(){
  if(done)return;done=true;
  const bundle=NFload(f.strNew(Memory.allocUtf8String('F:\\RF4\\Game\\.rf4-local\\xmas-stalls100.bundle')));
  send({log:'bundle '+(bundle.isNull()?'null':'ok')});
  if(bundle.isNull())return;
  const names=['assets/rf4local/xmas_goods_stall.prefab','assets/rf4local/xmas_food_stall.prefab'];
  const cam=NFcam(); if(cam.isNull()){send({log:'no camera'});return;}
  const camT=NFgt(cam); const cp=Memory.alloc(12),rr=Memory.alloc(16);
  NFgp(camT,cp); NFrot(camT,rr);
  const px=cp.readFloat(),py=cp.add(4).readFloat(),pz=cp.add(8).readFloat();
  const qx=rr.readFloat(),qy=rr.add(4).readFloat(),qz=rr.add(8).readFloat(),qw=rr.add(12).readFloat();
  const fx=2*(qx*qz+qw*qy),fy=2*(qy*qz-qw*qx),fz=1-2*(qx*qx+qy*qy);
  // 取当前地图商店后缀
  let suffix='18',cfg=ptr(0),shops=[];
  if(objFind){const a2=new NativeFunction(objFind,'pointer',['pointer'])(f.tObj(f.cType(SHOP)));
   if(!a2.isNull()&&a2.compare(ptr(0x10000))>=0){const arr=a2;const len=arr.add(0x18).readU64().toNumber();
    for(let i=0;i<len;i++){const o=arr.add(0x20).add(i*P).readPointer();if(o.isNull()||o.compare(ptr(0x10000))<0)continue;
     const sid=ilstr(o.add(80).readPointer());const m=sid.match(/_(\d+)$/);if(m){suffix=m[1];cfg=o.add(104).readPointer();break;}}}}
  send({log:'suffix '+suffix});
  for(let k=0;k<names.length;k++){
   const asset=NFasset(bundle,f.strNew(Memory.allocUtf8String(names[k])),f.tObj(f.cType(GO)));
   send({log:'asset '+names[k]+' '+(asset.isNull()?'null':'ok')});
   if(asset.isNull())continue;
   const obj=NFin(asset);
   if(obj.isNull()||obj.compare(ptr(0x10000))<0){send({log:'instantiate failed'});continue;}
   const t=NFgt(obj);
   const x=px+fx*4.0+(k*2.5-1.0), z=pz+fz*4.0+(k*1.0), y=py-1.2;
   NFsp(t,V3(x,y,z));
   NFset(obj,1);
   const comp=NFadd(obj,f.tObj(f.cType(SHOP)));
   const cok=!comp.isNull()&&comp.compare(ptr(0x10000))>=0;
   if(cok){comp.add(80).writePointer(f.strNew(Memory.allocUtf8String('ny_bazaarStore_'+suffix)));if(!cfg.isNull())comp.add(104).writePointer(cfg);}
   send({log:'spawned '+names[k]+' shop='+cok+' at '+x.toFixed(1)+','+y.toFixed(1)+','+z.toFixed(1)});
  }
 }
 Interceptor.attach(tick,{onEnter(){spawn();}});
 send({log:'hooked'});
}else send({log:'api missing'});
"""

s = frida.attach(PID)
sc = s.create_script(JS)
sc.on('message', lambda m, d: print(json.dumps(m if m.get('type') != 'send' else m.get('payload'), ensure_ascii=False)))
sc.load()
time.sleep(10)
s.detach()

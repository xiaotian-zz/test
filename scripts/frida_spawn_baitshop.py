"""主线程复制 Sea_bait_shop_12 作为博览会摊位，改子 Shop 的 storeID。"""
import frida, sys, json, time
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
const dom=f.dom(),cnt=Memory.alloc(8),asms=f.asms(dom,cnt),n=cnt.readUInt();let game=null,core=null;
for(let i=0;i<n;i++){const a=asms.add(i*P).readPointer(),im=f.asmImg(a),nm=cs(f.imgName(im));if(nm==='Assembly-CSharp.dll')game=im;if(nm==='UnityEngine.CoreModule.dll')core=im;}
const GO=f.fromName(core,Memory.allocUtf8String('UnityEngine'),Memory.allocUtf8String('GameObject'));
const OBJ=f.fromName(core,Memory.allocUtf8String('UnityEngine'),Memory.allocUtf8String('Object'));
const TR=f.fromName(core,Memory.allocUtf8String('UnityEngine'),Memory.allocUtf8String('Transform'));
const CAM=f.fromName(core,Memory.allocUtf8String('UnityEngine'),Memory.allocUtf8String('Camera'));
const TIME=f.fromName(core,Memory.allocUtf8String('UnityEngine'),Memory.allocUtf8String('Time'));
const SHOP=f.fromName(game,Memory.allocUtf8String('RF4.Client.FishingScene'),Memory.allocUtf8String('Shop'));
const find=findMethod(GO,'Find',1),inst=findMethod(OBJ,'Instantiate',1),setAct=findMethod(GO,'SetActive',1);
const getT=findMethod(GO,'get_transform',0),addComp=findMethodType(GO,'AddComponent',1,'System.Type');
const getChildren=findMethodType(GO,'GetComponentsInChildren',1,'System.Type');
const getPosI=findMethod(TR,'get_position_Injected',1),setPosI=findMethod(TR,'set_position_Injected',1),getRotI=findMethod(TR,'get_rotation_Injected',1);
const camMain=findMethod(CAM,'get_main',0),camRender=findMethod(TIME,'get_time',0),objFind=findMethodType(OBJ,'FindObjectsOfType',1,'System.Type'),getName=findMethod(OBJ,'get_name',0);
send({log:'apis '+JSON.stringify({find:!!find,inst:!!inst,setAct:!!setAct,add:!!addComp,gc:!!getChildren,gp:!!getPosI,sp:!!setPosI,cam:!!camMain,render:!!camRender,of:!!objFind})});
let done=false;
if(camRender&&find&&inst&&addComp&&getPosI&&setPosI&&camMain&&!SHOP.isNull()){
 const NFfind=new NativeFunction(find,'pointer',['pointer']);
 const NFin=new NativeFunction(inst,'pointer',['pointer']);
 const NFgt=new NativeFunction(getT,'pointer',['pointer']);
 const NFadd=new NativeFunction(addComp,'pointer',['pointer','pointer']);
 const NFset=new NativeFunction(setAct,'void',['pointer','int']);
 const NFgp=new NativeFunction(getPosI,'void',['pointer','pointer']);
 const NFsp=new NativeFunction(setPosI,'void',['pointer','pointer']);
 const NFgr=new NativeFunction(getRotI,'void',['pointer','pointer']);
 const NFcam=new NativeFunction(camMain,'pointer',[]);
 const NFgc=getChildren?new NativeFunction(getChildren,'pointer',['pointer','pointer']):null;
 const NFname=new NativeFunction(getName,'pointer',['pointer']);
 try{f.attach(dom);}catch(e){}
 function spawn(){
  if(done)return;done=true;
   let go=NFfind(f.strNew(Memory.allocUtf8String('Sea_bait_shop_12')));
   if(go.isNull()) go=NFfind(f.strNew(Memory.allocUtf8String('outdoor_table')));
   if(go.isNull()) go=NFfind(f.strNew(Memory.allocUtf8String('table_04')));
   send({log:'model '+(go.isNull()?'null':ilstr(NFname(go)))});
   if(go.isNull()) return;
   // 地图后缀与配置
   let suffix='012',cfg=ptr(0);
   if(objFind){const a2=new NativeFunction(objFind,'pointer',['pointer'])(f.tObj(f.cType(SHOP)));
    if(!a2.isNull()&&a2.compare(ptr(0x10000))>=0){const arr=a2;const len=arr.add(0x18).readU64().toNumber();
     for(let i=0;i<len;i++){const o=arr.add(0x20).add(i*P).readPointer();if(o.isNull()||o.compare(ptr(0x10000))<0)continue;const sid=ilstr(o.add(80).readPointer());const m=sid.match(/_(\d+)$/);if(m){suffix=m[1];cfg=o.add(104).readPointer();break;}}}}
   const storeID='ny_bazaarStore_'+suffix;
   send({log:'suffix '+suffix});
   let shops=[];
   send({log:'before gc'});
   if(NFgc){const arr=NFgc(go,f.tObj(f.cType(SHOP)));if(!arr.isNull()&&arr.compare(ptr(0x10000))>=0){const len=arr.add(0x18).readU64().toNumber();for(let i=0;i<len;i++){const s=arr.add(0x20).add(i*P).readPointer();if(!s.isNull()&&s.compare(ptr(0x10000))>=0)shops.push(s);}}}
   send({log:'child shops '+shops.length});
   if(shops.length===0){const comp=NFadd(go,f.tObj(f.cType(SHOP)));if(!comp.isNull()&&comp.compare(ptr(0x10000))>=0)shops.push(comp);}
   for(const s of shops){s.add(80).writePointer(f.strNew(Memory.allocUtf8String(storeID)));if(!cfg.isNull())s.add(104).writePointer(cfg);}
   send({log:'patched '+storeID+' shops='+shops.length});
 }
 Interceptor.attach(camRender,{onEnter(){spawn();}});
 send({log:'hooked'});
}else send({log:'api missing'});
"""
s=frida.attach(PID);sc=s.create_script(JS)
sc.on('message',lambda m,d: print(json.dumps(m if m.get('type')!='send' else m.get('payload'),ensure_ascii=False)))
sc.load();time.sleep(12);s.detach()

"""主线程生成博览会摊位（复制场景模型 + 挂 Shop），避免 GC unknown thread。"""
import frida, sys, json, time

PID = int(sys.argv[1]) if len(sys.argv) > 1 else 25668

JS = r"""
const ga=Process.getModuleByName('GameAssembly.dll');
const E=n=>ga.getExportByName(n), P=Process.pointerSize;
const f={
 dom:new NativeFunction(E('il2cpp_domain_get'),'pointer',[]),
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
};
function cs(p){try{return p.isNull()?'':p.readUtf8String();}catch(e){return '';}}
function ilstr(p){try{if(p.isNull())return '';const n=p.add(0x10).readU32();return p.add(0x14).readUtf16String(n);}catch(e){return '';}}
function findMethod(cls,name,argc){
  const it=Memory.alloc(P);it.writePointer(ptr(0));
  for(let i=0;i<512;i++){const m=f.cMethods(cls,it);if(m.isNull())break;
    if(cs(f.mName(m))===name && (argc===undefined||f.mParamCount(m)===argc)) return m.add(P).readPointer();}
  return null;
}
const dom=f.dom(),cnt=Memory.alloc(8),asms=f.asms(dom,cnt),n=cnt.readUInt();
let game=null,core=null;
for(let i=0;i<n;i++){const a=asms.add(i*P).readPointer(),im=f.asmImg(a),nm=cs(f.imgName(im));
  if(nm==='Assembly-CSharp.dll')game=im; if(nm==='UnityEngine.CoreModule.dll')core=im;}
const GO=f.fromName(core,Memory.allocUtf8String('UnityEngine'),Memory.allocUtf8String('GameObject'));
const OBJ=f.fromName(core,Memory.allocUtf8String('UnityEngine'),Memory.allocUtf8String('Object'));
const TR=f.fromName(core,Memory.allocUtf8String('UnityEngine'),Memory.allocUtf8String('Transform'));
const CAM=f.fromName(core,Memory.allocUtf8String('UnityEngine'),Memory.allocUtf8String('Camera'));
const SHOP=f.fromName(game,Memory.allocUtf8String('RF4.Client.FishingScene'),Memory.allocUtf8String('Shop'));
const find=findMethod(GO,'Find',1), inst=findMethod(OBJ,'Instantiate',1);
const getT=findMethod(GO,'get_transform',0), setAct=findMethod(GO,'SetActive',1);
const addComp=findMethod(GO,'AddComponent',1);
const getPosI=findMethod(TR,'get_position_Injected',1), setPosI=findMethod(TR,'set_position_Injected',1);
const getRotI=findMethod(TR,'get_rotation_Injected',1);
const camMain=findMethod(CAM,'get_main',0);
const camRender=findMethod(CAM,'Render',0);
const objFind=findMethod(OBJ,'FindObjectsOfType',1);
send({log:'apis '+JSON.stringify({find:!!find,inst:!!inst,setAct:!!setAct,add:!!addComp,gp:!!getPosI,sp:!!setPosI,gr:!!getRotI,cam:!!camMain,render:!!camRender,of:!!objFind})});
let done=false;
if(camRender && find && inst && addComp && getPosI && setPosI && camMain && !SHOP.isNull()){
  const NFfind=new NativeFunction(find,'pointer',['pointer']);
  const NFin=new NativeFunction(inst,'pointer',['pointer']);
  const NFgt=new NativeFunction(getT,'pointer',['pointer']);
  const NFadd=new NativeFunction(addComp,'pointer',['pointer','pointer']);
  const NFset=new NativeFunction(setAct,'void',['pointer','int']);
  const NFgp=new NativeFunction(getPosI,'void',['pointer','pointer']);
  const NFsp=new NativeFunction(setPosI,'void',['pointer','pointer']);
  const NFgr=new NativeFunction(getRotI,'void',['pointer','pointer']);
  const NFcam=new NativeFunction(camMain,'pointer',[]);
  const NFinObj=new NativeFunction(inst,'pointer',['pointer']);
  try{ f.attach(dom); }catch(e){}
  function spawn(){
    if(done) return; done=true;
    try{
      // 找可用模型
      let go=NFfind(f.strNew(Memory.allocUtf8String('cartbox_big_cl')));
      if(go.isNull()) go=NFfind(f.strNew(Memory.allocUtf8String('fair_furnitures')));
      if(go.isNull()) go=NFfind(f.strNew(Memory.allocUtf8String('cartbox_med_cl')));
      send({log:'model '+(go.isNull()?'null':ilstr(new NativeFunction(findMethod(OBJ,'get_name'),'pointer',['pointer'])(go)))});
      if(go.isNull()){ send({log:'无可用模型'}); return; }
      // 取当前地图后缀与配置
      let suffix='012', cfg=ptr(0);
      if(objFind){
        const arr=new NativeFunction(objFind,'pointer',['pointer'])(f.tObj(f.cType(SHOP)));
        if(!arr.isNull()){
          const len=arr.add(0x18).readU64().toNumber();
          for(let i=0;i<len;i++){
            const o=arr.add(0x20).add(i*P).readPointer();
            const sid=ilstr(o.add(80).readPointer());
            const m=sid.match(/_(\d+)$/);
            if(m){ suffix=m[1]; cfg=o.add(104).readPointer(); break; }
          }
        }
      }
      const storeID='ny_bazaarStore_'+suffix;
      const dup=NFin(go);
      if(dup.isNull()){ send({log:'instantiate null'}); return; }
      NFset(dup,0);
      const tr=NFgt(dup);
      const c=NFcam();
      if(!c.isNull()){
        const ct=NFgt(c); const b=Memory.alloc(16); NFgp(ct,b);
        const cx=b.readFloat(),cy=b.add(4).readFloat(),cz=b.add(8).readFloat();
        const rb=Memory.alloc(16); NFgr(ct,rb);
        const qx=rb.readFloat(),qy=rb.add(4).readFloat(),qz=rb.add(8).readFloat(),qw=rb.add(12).readFloat();
        const fx=2*(qx*qz+qw*qy),fy=2*(qy*qz-qw*qx),fz=1-2*(qx*qx+qy*qy);
        const v=Memory.alloc(16);
        v.writeFloat(cx+fx*3); v.add(4).writeFloat(cy+fy*3-1.2); v.add(8).writeFloat(cz+fz*3);
        NFsp(tr,v);
      }
      const comp=NFadd(dup,f.tObj(f.cType(SHOP)));
      if(comp.isNull()){ send({log:'addcomponent null'}); return; }
      comp.add(80).writePointer(f.strNew(Memory.allocUtf8String(storeID)));
      if(!cfg.isNull()) comp.add(104).writePointer(cfg);
      NFset(dup,1);
      send({log:'spawned '+storeID});
    }catch(e){ send({log:'err '+e}); }
  }
  Interceptor.attach(camRender,{onEnter(){ spawn(); }});
  send({log:'hook camera render'});
}else{
  send({log:'API 不完整，未安装'});
}
"""
s=frida.attach(PID);sc=s.create_script(JS)
sc.on('message',lambda m,d: print(json.dumps(m.get('payload'),ensure_ascii=False)))
sc.load();time.sleep(12);s.detach()

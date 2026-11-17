"""在 level18 复制圣诞树并 DontDestroyOnLoad，改名 ny_fair_tree_carrier。"""
import frida, sys, json, time
PID = int(sys.argv[1]) if len(sys.argv) > 1 else 25668
JS = r"""
const ga=Process.getModuleByName('GameAssembly.dll');const E=n=>ga.getExportByName(n),P=Process.pointerSize;
const f={dom:new NativeFunction(E('il2cpp_domain_get'),'pointer',[]),
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
const dom=f.dom(),cnt=Memory.alloc(8),asms=f.asms(dom,cnt),n=cnt.readUInt();let core=null;
for(let i=0;i<n;i++){const a=asms.add(i*P).readPointer(),im=f.asmImg(a);if(cs(f.imgName(im))==='UnityEngine.CoreModule.dll')core=im;}
const GO=f.fromName(core,Memory.allocUtf8String('UnityEngine'),Memory.allocUtf8String('GameObject'));
const OBJ=f.fromName(core,Memory.allocUtf8String('UnityEngine'),Memory.allocUtf8String('Object'));
const TIME=f.fromName(core,Memory.allocUtf8String('UnityEngine'),Memory.allocUtf8String('Time'));
const RES=f.fromName(core,Memory.allocUtf8String('UnityEngine'),Memory.allocUtf8String('Resources'));
const find=findMethod(GO,'Find',1),inst=findMethodType(OBJ,'Instantiate',1,'UnityEngine.Object');
const ddl=findMethod(OBJ,'DontDestroyOnLoad',1),setName=findMethod(OBJ,'set_name',1),setAct=findMethod(GO,'SetActive',1);
const tick=findMethod(TIME,'get_time',0),findAll=findMethodType(RES,'FindObjectsOfTypeAll',1,'System.Type'),getName=findMethod(OBJ,'get_name',0);
send({log:'apis'+JSON.stringify({find:!!find,inst:!!inst,ddl:!!ddl,setName:!!setName,setAct:!!setAct,tick:!!tick,findAll:!!findAll})});
if(find&&inst&&ddl&&setName&&setAct&&tick){
 const NFfind=new NativeFunction(find,'pointer',['pointer']),NFin=new NativeFunction(inst,'pointer',['pointer']);
 const NFddl=new NativeFunction(ddl,'void',['pointer']),NFname=new NativeFunction(setName,'void',['pointer','pointer']);
 const NFset=new NativeFunction(setAct,'void',['pointer','int']);
 let done=false;
 Interceptor.attach(tick,{onEnter(){
  if(done)return;done=true;
  let go=NFfind(f.strNew(Memory.allocUtf8String('christmas_tree_interior_optimised')));
  if(go.isNull()&&findAll){
    const arr=new NativeFunction(findAll,'pointer',['pointer'])(f.tObj(f.cType(GO)));
    if(!arr.isNull()&&arr.compare(ptr(0x10000))>=0){const len=arr.add(0x18).readU64().toNumber();const NFgn=new NativeFunction(getName,'pointer',['pointer']);
      for(let i=0;i<len;i++){const o=arr.add(0x20).add(i*P).readPointer();if(o.isNull()||o.compare(ptr(0x10000))<0)continue;if(ilstr(NFgn(o))==='christmas_tree_interior_optimised'){go=o;break;}}}
  }
  send({log:'tree '+(go.isNull()?'null':go)});
  if(go.isNull())return;
  const dup=NFin(go);
  if(dup.isNull()||dup.compare(ptr(0x10000))<0){send({log:'dup fail '+dup});return;}
  NFddl(dup);
  NFname(dup,f.strNew(Memory.allocUtf8String('ny_fair_tree_carrier')));
  NFset(dup,0);
  send({log:'carried'});
 }});
 send({log:'hooked'});
}
"""
s=frida.attach(PID);sc=s.create_script(JS)
sc.on('message',lambda m,d: print(json.dumps(m if m.get('type')!='send' else m.get('payload'),ensure_ascii=False)))
sc.load();time.sleep(15);s.detach()

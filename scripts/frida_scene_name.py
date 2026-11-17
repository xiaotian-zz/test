"""读取当前场景名与圣诞树是否存在。"""
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
const SM=f.fromName(core,Memory.allocUtf8String('UnityEngine.SceneManagement'),Memory.allocUtf8String('SceneManager'));
const SC=f.fromName(core,Memory.allocUtf8String('UnityEngine.SceneManagement'),Memory.allocUtf8String('Scene'));
const find=findMethod(GO,'Find',1),tick=findMethod(TIME,'get_time',0),getActive=findMethod(SM,'GetActiveScene',0),getName=findMethod(SC,'get_name',0);
send({log:'apis'+JSON.stringify({find:!!find,getActive:!!getActive,getName:!!getName})});
if(find&&tick&&getActive&&getName){
 const NFfind=new NativeFunction(find,'pointer',['pointer']);
 let done=false;
 Interceptor.attach(tick,{onEnter(){
  if(done)return;done=true;
  try{
   const ret=Memory.alloc(32);
   new NativeFunction(getActive,'void',['pointer'])(ret);
   const nm=ilstr(new NativeFunction(getName,'pointer',['pointer'])(ret));
   send({log:'scene '+nm});
  }catch(e){send({log:'scene err '+e});}
  for(const nm of ['christmas_tree_interior_optimised','christmas_tree','tree_stand','decoration_lights','Sea_bait_shop_12']){
   const g=NFfind(f.strNew(Memory.allocUtf8String(nm)));
   send({log:nm+' -> '+(g.isNull()?'null':g)});
  }
 }});
 send({log:'hooked'});
}
"""
s=frida.attach(PID);sc=s.create_script(JS)
sc.on('message',lambda m,d: print(json.dumps(m if m.get('type')!='send' else m.get('payload'),ensure_ascii=False)))
sc.load();time.sleep(10);s.detach()

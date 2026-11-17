"""诊断：枚举已加载 AssetBundle，并尝试再次 LoadFromFile。"""
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
 cMethods:new NativeFunction(E('il2cpp_class_get_methods'),'pointer',['pointer','pointer']),
 mName:new NativeFunction(E('il2cpp_method_get_name'),'pointer',['pointer']),
 mParamCount:new NativeFunction(E('il2cpp_method_get_param_count'),'uint',['pointer']),
 strNew:new NativeFunction(E('il2cpp_string_new'),'pointer',['pointer']),
};
function cs(p){try{return p.isNull()?'':p.readUtf8String();}catch(e){return '';}}
function ilstr(p){try{if(p.isNull()||p.compare(ptr(0x10000))<0)return '';const n=p.add(0x10).readU32();return p.add(0x14).readUtf16String(n);}catch(e){return '';}}
function findMethod(cls,name,argc){const it=Memory.alloc(P);it.writePointer(ptr(0));for(let i=0;i<400;i++){const m=f.cMethods(cls,it);if(m.isNull())break;if(cs(f.mName(m))===name&&(argc===undefined||f.mParamCount(m)===argc))return m.add(P).readPointer();}return null;}
const dom=f.dom(),cnt=Memory.alloc(8),asms=f.asms(dom,cnt),n=cnt.readUInt();let core=null,abm=null;
for(let i=0;i<n;i++){const a=asms.add(i*P).readPointer(),im=f.asmImg(a),nm=cs(f.imgName(im));if(nm==='UnityEngine.CoreModule.dll')core=im;if(nm==='UnityEngine.AssetBundleModule.dll')abm=im;}
const OBJ=f.fromName(core,Memory.allocUtf8String('UnityEngine'),Memory.allocUtf8String('Object'));
const TIME=f.fromName(core,Memory.allocUtf8String('UnityEngine'),Memory.allocUtf8String('Time'));
const AB=f.fromName(abm,Memory.allocUtf8String('UnityEngine'),Memory.allocUtf8String('AssetBundle'));
const getName=findMethod(OBJ,'get_name',0),tick=findMethod(TIME,'get_time',0);
const getAll=findMethod(AB,'GetAllLoadedAssetBundles',0),load=findMethod(AB,'LoadFromFile',1);
send({log:'getAll='+!!getAll+' load='+!!load});
let done=false;
Interceptor.attach(tick,{onEnter(){
 if(done)return;done=true;
 if(getAll){
  const arr=new NativeFunction(getAll,'pointer',[])();
  if(!arr.isNull()&&arr.compare(ptr(0x10000))>=0){
   const len=arr.add(0x18).readU64().toNumber();
   const NFn=new NativeFunction(getName,'pointer',['pointer']);
   let names=[];
   for(let i=0;i<len&&i<100;i++){const o=arr.add(0x20).add(i*P).readPointer();if(o.isNull()||o.compare(ptr(0x10000))<0)continue;names.push(ilstr(NFn(o)));}
   send({log:'loaded bundles '+len,names});
  }else send({log:'getall null'});
 }
 if(load){
  const NFload=new NativeFunction(load,'pointer',['pointer']);
  const p=f.strNew(Memory.allocUtf8String('F:\\RF4\\Game\\.rf4-local\\xmas-stalls100.bundle'));
  const b=NFload(p);
  send({log:'loadfromfile '+(b.isNull()?'null':'ok')});
 }
}});
"""

s = frida.attach(PID)
sc = s.create_script(JS)
sc.on('message', lambda m, d: print(json.dumps(m if m.get('type') != 'send' else m.get('payload'), ensure_ascii=False)))
sc.load()
time.sleep(8)
s.detach()

"""运行时以 Additive 方式加载湖泊小屋场景(level18)，取出室内圣诞树并保留。

用法:
  py -3.12 scripts/frida_load_house_tree.py [PID]
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
 strNew:new NativeFunction(E('il2cpp_string_new'),'pointer',['pointer']),
 getParam:new NativeFunction(E('il2cpp_method_get_param'),'pointer',['pointer','uint']),
 typeName:new NativeFunction(E('il2cpp_type_get_name'),'pointer',['pointer']),
};
function cs(p){try{return p.isNull()?'':p.readUtf8String();}catch(e){return '';}}
function ilstr(p){try{if(p.isNull()||p.compare(ptr(0x10000))<0)return '';const n=p.add(0x10).readU32();return p.add(0x14).readUtf16String(n);}catch(e){return '';}}
function findMethod(cls,name,argc){const it=Memory.alloc(P);it.writePointer(ptr(0));for(let i=0;i<512;i++){const m=f.cMethods(cls,it);if(m.isNull())break;if(cs(f.mName(m))===name&&(argc===undefined||f.mParamCount(m)===argc))return m.add(P).readPointer();}return null;}
function findMethodType(cls,name,argc,want){const it=Memory.alloc(P);it.writePointer(ptr(0));for(let i=0;i<512;i++){const m=f.cMethods(cls,it);if(m.isNull())break;if(cs(f.mName(m))===name&&f.mParamCount(m)===argc&&cs(f.typeName(f.getParam(m,0)))===want)return m.add(P).readPointer();}return null;}
const dom=f.dom(),cnt=Memory.alloc(8),asms=f.asms(dom,cnt),n=cnt.readUInt();let core=null;
for(let i=0;i<n;i++){const a=asms.add(i*P).readPointer(),im=f.asmImg(a),nm=cs(f.imgName(im));if(nm==='UnityEngine.CoreModule.dll')core=im;}
const GO=f.fromName(core,Memory.allocUtf8String('UnityEngine'),Memory.allocUtf8String('GameObject'));
const OBJ=f.fromName(core,Memory.allocUtf8String('UnityEngine'),Memory.allocUtf8String('Object'));
const TR=f.fromName(core,Memory.allocUtf8String('UnityEngine'),Memory.allocUtf8String('Transform'));
const TIME=f.fromName(core,Memory.allocUtf8String('UnityEngine'),Memory.allocUtf8String('Time'));
const SM=f.fromName(core,Memory.allocUtf8String('UnityEngine.SceneManagement'),Memory.allocUtf8String('SceneManager'));
const RES=f.fromName(core,Memory.allocUtf8String('UnityEngine'),Memory.allocUtf8String('Resources'));
const find=findMethod(GO,'Find',1),getT=findMethod(GO,'get_transform',0),getName=findMethod(OBJ,'get_name',0);
const setAct=findMethod(GO,'SetActive',1);
const findAll=findMethodType(RES,'FindObjectsOfTypeAll',1,'System.Type');
const loadAsync=findMethod(SM,'LoadSceneAsync',2);
const ddo=findMethod(OBJ,'DontDestroyOnLoad',1);
const getPosI=findMethod(TR,'get_position_Injected',1),getTname=findMethod(SM,'GetActiveScene',0);
send({log:'apis '+JSON.stringify({find:!!find,getT:!!getT,load:!!loadAsync,ddo:!!ddo,pos:!!getPosI,all:!!findAll,act:!!setAct})});
let state=0,t0=0;
if(findAll&&loadAsync&&ddo&&getPosI&&setAct&&find){
 Interceptor.attach(findMethod(TIME,'get_time',0),{onEnter(){
  const now=Date.now()/1000;
  if(state===0){state=1;t0=now;
   try{const NFload=new NativeFunction(loadAsync,'pointer',['pointer','int']);
    const op=NFload(f.strNew(Memory.allocUtf8String('level_001_lake_house')),1);
    send({log:'loadscene op '+(op.isNull()?'null':'ok')});}catch(e){send({log:'load err '+e});}
   return;
  }
  if(state===1&&now-t0>10){state=2;
   const NFall=new NativeFunction(findAll,'pointer',['pointer']);
   const NFname=new NativeFunction(getName,'pointer',['pointer']);
   const arr=NFall(f.tObj(f.cType(GO)));
   let g=ptr(0),total=0;
   if(!arr.isNull()&&arr.compare(ptr(0x10000))>=0){
    const len=arr.add(0x18).readU64().toNumber();total=len;
    for(let i=0;i<len;i++){const o=arr.add(0x20).add(i*P).readPointer();if(o.isNull()||o.compare(ptr(0x10000))<0)continue;
     const nm=ilstr(NFname(o));if(nm.indexOf('christmas_tree')>=0){g=o;send({log:'match '+nm});break;}}
   }
   send({log:'scan total '+total+' tree '+(g.isNull()?'null':'found')});
   if(!g.isNull()){
    new NativeFunction(ddo,'void',['pointer'])(g);
    const t=new NativeFunction(getT,'pointer',['pointer'])(g);
    const pos=Memory.alloc(12);
    new NativeFunction(getPosI,'void',['pointer','pointer'])(t,pos);
    send({log:'tree pos '+pos.readFloat().toFixed(1)+','+pos.add(4).readFloat().toFixed(1)+','+pos.add(8).readFloat().toFixed(1)});
   }
  }
 }});
 send({log:'hooked'});
}else send({log:'api missing'});
"""

s = frida.attach(PID)
sc = s.create_script(JS)
sc.on('message', lambda m, d: print(json.dumps(m if m.get('type') != 'send' else m.get('payload'), ensure_ascii=False)))
sc.load()
time.sleep(14)
s.detach()

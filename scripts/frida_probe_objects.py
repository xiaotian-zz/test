"""主线程遍历当前场景 GameObject，列出可用作摊位的模型。"""
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
};
function cs(p){try{return p.isNull()?'':p.readUtf8String();}catch(e){return '';}}
function ilstr(p){try{if(p.isNull())return '';const n=p.add(0x10).readU32();return p.add(0x14).readUtf16String(n);}catch(e){return '';}}
function findMethod(cls,name,argc){const it=Memory.alloc(P);it.writePointer(ptr(0));for(let i=0;i<256;i++){const m=f.cMethods(cls,it);if(m.isNull())break;if(cs(f.mName(m))===name&&(argc===undefined||f.mParamCount(m)===argc))return m.add(P).readPointer();}return null;}
const dom=f.dom(),cnt=Memory.alloc(8),asms=f.asms(dom,cnt),n=cnt.readUInt();let core=null;
for(let i=0;i<n;i++){const a=asms.add(i*P).readPointer(),im=f.asmImg(a);if(cs(f.imgName(im))==='UnityEngine.CoreModule.dll')core=im;}
const RES=f.fromName(core,Memory.allocUtf8String('UnityEngine'),Memory.allocUtf8String('Resources'));
const GO=f.fromName(core,Memory.allocUtf8String('UnityEngine'),Memory.allocUtf8String('GameObject'));
const OBJ=f.fromName(core,Memory.allocUtf8String('UnityEngine'),Memory.allocUtf8String('Object'));
const CAM=f.fromName(core,Memory.allocUtf8String('UnityEngine'),Memory.allocUtf8String('Camera'));
const findAll=findMethod(RES,'FindObjectsOfTypeAll',1), getName=findMethod(OBJ,'get_name',0), camRender=findMethod(CAM,'Render',0);
if(!findAll||!getName||!camRender){send({log:'api missing'});}else{
 const NFall=new NativeFunction(findAll,'pointer',['pointer']), NFname=new NativeFunction(getName,'pointer',['pointer']);
 let done=false;
 Interceptor.attach(camRender,{onEnter(){
   if(done)return;done=true;
   try{
     const arr=NFall(f.tObj(f.cType(GO)));
     const len=arr.add(0x18).readU64().toNumber();
     const kws=['cart','box','tent','table','bench','fair','shop','barrel','crate','stall'];
     let out=[];
     for(let i=0;i<len;i++){
       const o=arr.add(0x20).add(i*P).readPointer();
       const nm=ilstr(NFname(o)); const low=nm.toLowerCase();
       if(kws.some(k=>low.indexOf(k)>=0)) out.push(nm);
     }
     send({log:'total '+len, hits:out.slice(0,150)});
   }catch(e){send({log:'err '+e});}
 }});
 send({log:'hooked'});
}
"""
s=frida.attach(PID);sc=s.create_script(JS)
sc.on('message',lambda m,d: print(json.dumps(m.get('payload'),ensure_ascii=False)))
sc.load();time.sleep(10);s.detach()

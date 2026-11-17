"""Hook Shop.Start，在初始化前把挪威海鱼饵店的 storeID 换成博览会。"""
import frida, sys, json, time
PID = int(sys.argv[1]) if len(sys.argv) > 1 else 25668
DUR = int(sys.argv[2]) if len(sys.argv) > 2 else 90
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
};
function cs(p){try{return p.isNull()?'':p.readUtf8String();}catch(e){return '';}}
function ilstr(p){try{if(p.isNull()||p.compare(ptr(0x10000))<0)return '';const n=p.add(0x10).readU32();return p.add(0x14).readUtf16String(n);}catch(e){return '';}}
function findMethod(cls,name,argc){const it=Memory.alloc(P);it.writePointer(ptr(0));for(let i=0;i<256;i++){const m=f.cMethods(cls,it);if(m.isNull())break;if(cs(f.mName(m))===name&&(argc===undefined||f.mParamCount(m)===argc))return m.add(P).readPointer();}return null;}
const dom=f.dom(),cnt=Memory.alloc(8),asms=f.asms(dom,cnt),n=cnt.readUInt();let game=null;
for(let i=0;i<n;i++){const a=asms.add(i*P).readPointer(),im=f.asmImg(a);if(cs(f.imgName(im))==='Assembly-CSharp.dll')game=im;}
const SHOP=f.fromName(game,Memory.allocUtf8String('RF4.Client.FishingScene'),Memory.allocUtf8String('Shop'));
const start=findMethod(SHOP,'Start',0);
send({log:'start '+start});
if(start){
 Interceptor.attach(start,{onEnter(args){
  try{
   const self=args[0];
   const sid=ilstr(self.add(80).readPointer());
   if(sid) send({log:'Shop.Start '+sid});
   if(sid==='craft_baits_012'||sid==='fishingstore_012'||sid==='foodstore_012'){
     self.add(80).writePointer(f.strNew(Memory.allocUtf8String('ny_bazaarStore_012')));
     send({log:'patched '+sid+' -> ny_bazaarStore_012'});
   }
  }catch(e){}
 }});
}
"""
s=frida.attach(PID);sc=s.create_script(JS)
sc.on('message',lambda m,d: print(json.dumps(m if m.get('type')!='send' else m.get('payload'),ensure_ascii=False)))
sc.load()
t=time.time()
while time.time()-t<DUR: time.sleep(1)
s.detach()

import frida, json, sys, time

PID = int(sys.argv[1]) if len(sys.argv) > 1 else 19924
JS = r"""
const ga = Process.getModuleByName('GameAssembly.dll');
const E = n => ga.getExportByName(n);
const P = Process.pointerSize;
const dom = new NativeFunction(E('il2cpp_domain_get'),'pointer',[])();
const cnt = Memory.alloc(8);
const asms = new NativeFunction(E('il2cpp_domain_get_assemblies'),'pointer',['pointer','pointer'])(dom,cnt);
const n = cnt.readUInt();
const asmImg = new NativeFunction(E('il2cpp_assembly_get_image'),'pointer',['pointer']);
const imgName = new NativeFunction(E('il2cpp_image_get_name'),'pointer',['pointer']);
const fromName = new NativeFunction(E('il2cpp_class_from_name'),'pointer',['pointer','pointer','pointer']);
const cMethods = new NativeFunction(E('il2cpp_class_get_methods'),'pointer',['pointer','pointer']);
const mName = new NativeFunction(E('il2cpp_method_get_name'),'pointer',['pointer']);
const mTok = new NativeFunction(E('il2cpp_method_get_token'),'uint',['pointer']);
function cs(p){try{return p.isNull()?'':p.readUtf8String();}catch(e){return '';}}
let img0=null;
for(let i=0;i<n;i++){
  const a=asms.add(i*P).readPointer();
  const im=asmImg(a);
  if(cs(imgName(im))==='Assembly-CSharp.dll'){ img0=im; break; }
}
if(!img0){ send({error:'no image'}); } else {
  for(const cname of ['bbpmdcodcee','RF4.Client.FishingScene.Shop','RF4.Client.FishingScene.ShopWorkshop']){
    const k=fromName(img0,Memory.allocUtf8String(''),Memory.allocUtf8String(cname));
    if(k.isNull()){ send({cls:cname,found:false}); continue; }
    const ms=[]; const it=Memory.alloc(P); it.writePointer(ptr(0));
    for(let g=0;g<1024;g++){
      const m=cMethods(k,it); if(m.isNull()) break;
      ms.push({name:cs(mName(m)), tok:mTok(m), p0:m.readPointer().toString(),
               p1:m.add(P).readPointer().toString(), p2:m.add(P*2).readPointer().toString()});
    }
    send({cls:cname,found:true,count:ms.length,methods:ms});
  }
  send({done:true});
}
"""
session = frida.attach(PID)
script = session.create_script(JS)
state = {"done": False}
def on_msg(m, d):
    if m.get("type") != "send":
        print("[frida]", m, file=sys.stderr); return
    p = m.get("payload") or {}
    if p.get("done"):
        state["done"] = True; return
    print(json.dumps(p, ensure_ascii=False)[:12000])
script.on("message", on_msg)
script.load()
t=time.time()
while not state["done"] and time.time()-t < 30:
    time.sleep(0.2)
session.detach()

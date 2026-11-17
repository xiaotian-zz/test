"""Hook UnityEngine.Object.Instantiate，记录预制体名称与调用方托管方法。"""
import frida, json, sys, time

PID = int(sys.argv[1])
DURATION = int(sys.argv[2]) if len(sys.argv) > 2 else 180
LOG = sys.argv[3] if len(sys.argv) > 3 else r"f:\rea\artifacts\instantiate.log"

JS = r"""
const ga = Process.getModuleByName('GameAssembly.dll');
const E = n => ga.getExportByName(n);
const P = Process.pointerSize;
const f = {
  dom: new NativeFunction(E('il2cpp_domain_get'),'pointer',[]),
  asms: new NativeFunction(E('il2cpp_domain_get_assemblies'),'pointer',['pointer','pointer']),
  asmImg: new NativeFunction(E('il2cpp_assembly_get_image'),'pointer',['pointer']),
  imgName: new NativeFunction(E('il2cpp_image_get_name'),'pointer',['pointer']),
  imgCount: new NativeFunction(E('il2cpp_image_get_class_count'),'uint',['pointer']),
  imgClass: new NativeFunction(E('il2cpp_image_get_class'),'pointer',['pointer','uint']),
  cName: new NativeFunction(E('il2cpp_class_get_name'),'pointer',['pointer']),
  cNs: new NativeFunction(E('il2cpp_class_get_namespace'),'pointer',['pointer']),
  cMethods: new NativeFunction(E('il2cpp_class_get_methods'),'pointer',['pointer','pointer']),
  mName: new NativeFunction(E('il2cpp_method_get_name'),'pointer',['pointer']),
  fromName: new NativeFunction(E('il2cpp_class_from_name'),'pointer',['pointer','pointer','pointer']),
  objGetClass: new NativeFunction(E('il2cpp_object_get_class'),'pointer',['pointer']),
};
function cs(p){try{return p.isNull()?'':p.readUtf8String();}catch(e){return '';}}
function ilstr(p){try{if(p.isNull())return '';const n=p.add(0x10).readU32();return p.add(0x14).readUtf16String(n);}catch(e){return '';}}
const dom=f.dom(), cnt=Memory.alloc(8);
const asms=f.asms(dom,cnt), n=cnt.readUInt();
let gameImg=null, coreImg=null;
for(let i=0;i<n;i++){
  const a=asms.add(i*P).readPointer(), im=f.asmImg(a), nm=cs(f.imgName(im));
  if(nm==='Assembly-CSharp.dll') gameImg=im;
  if(nm==='UnityEngine.CoreModule.dll') coreImg=im;
}
// 托管方法指针表（仅 Assembly-CSharp）
let table=[];
if(gameImg){
  const cn=f.imgCount(gameImg);
  for(let ci=0;ci<cn;ci++){
    const k=f.imgClass(gameImg,ci); if(k.isNull()) continue;
    const ns=cs(f.cNs(k)), nm=cs(f.cName(k));
    const it=Memory.alloc(P); it.writePointer(ptr(0));
    for(let gi=0;gi<2048;gi++){
      const m=f.cMethods(k,it); if(m.isNull()) break;
      let mp; try{mp=m.add(P).readPointer();}catch(e){continue;}
      if(mp.isNull()||mp.compare(ga.base)<0||mp.compare(ga.base.add(ga.size))>=0) continue;
      table.push({a:mp, n:ns+'.'+nm+'.'+cs(f.mName(m))});
    }
  }
}
table.sort((x,y)=>x.a.compare(y.a));
send({log:'table '+table.length});
function resolve(addr){
  let lo=0, hi=table.length-1, best=-1;
  while(lo<=hi){const mid=(lo+hi)>>1; if(table[mid].a.compare(addr)<=0){best=mid;lo=mid+1;}else hi=mid-1;}
  if(best<0) return '';
  const d=addr.sub(table[best].a).toInt32();
  return d>=0 && d<0x8000 ? table[best].n+' +0x'+d.toString(16) : '';
}
if(!coreImg){ send({log:'no core module'}); } else {
  const oc=f.fromName(coreImg,Memory.allocUtf8String('UnityEngine'),Memory.allocUtf8String('Object'));
  if(oc.isNull()){ send({log:'no UnityEngine.Object'}); } else {
    // 找 Object.get_name 与 Instantiate
    let getName=null, inst=[];
    const it=Memory.alloc(P); it.writePointer(ptr(0));
    for(let gi=0;gi<4096;gi++){
      const m=f.cMethods(oc,it); if(m.isNull()) break;
      const mn=cs(f.mName(m));
      let mp; try{mp=m.add(P).readPointer();}catch(e){continue;}
      if(mp.isNull()) continue;
      if(mn==='get_name') getName=mp;
      if(mn==='Instantiate') inst.push(mp);
    }
    send({log:'instantiate overloads '+inst.length+' get_name '+!!getName});
    let NFname=null;
    if(getName) NFname=new NativeFunction(getName,'pointer',['pointer']);
    const seen=new Set();
    for(const p of inst){
      try{
        Interceptor.attach(p,{onEnter(args){
          let name='';
          try{ if(NFname) name=ilstr(NFname(args[0])); }catch(e){}
          const bt=Thread.backtrace(this.context,Backtracer.ACCURATE).slice(0,8).map(a=>resolve(a)).filter(x=>x);
          if(!name) return;
          if(seen.has(name)) return;
          seen.add(name);
          send({name:name, bt:bt});
        }});
      }catch(e){ send({log:'attach fail '+e}); }
    }
  }
}
"""

session = frida.attach(PID)
script = session.create_script(JS)
out = open(LOG, "w", encoding="utf-8")

def on_msg(m, d):
    if m.get("type") != "send":
        out.write("[frida] %r\n" % (m,)); out.flush(); return
    p = m.get("payload") or {}
    if "log" in p:
        out.write("[log] %s\n" % p["log"]); out.flush(); return
    out.write("%s\n" % p.get("name"))
    for x in p.get("bt") or []:
        out.write("    <- %s\n" % x)
    out.flush()

script.on("message", on_msg)
script.load()
t = time.time()
while time.time() - t < DURATION:
    time.sleep(0.5)
out.close()
session.detach()
print("done", LOG)

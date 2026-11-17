import frida, json, sys

PID = int(sys.argv[1]) if len(sys.argv) > 1 else 19924

JS = r"""
const ga = Process.getModuleByName('GameAssembly.dll');
const E = n => ga.getExportByName(n);
const domain = new NativeFunction(E('il2cpp_domain_get'), 'pointer', [])();
const cnt = Memory.alloc(8);
const asms = new NativeFunction(E('il2cpp_domain_get_assemblies'), 'pointer', ['pointer','pointer'])(domain, cnt);
const n = cnt.readUInt();
const asmImg = new NativeFunction(E('il2cpp_assembly_get_image'), 'pointer', ['pointer']);
const imgName = new NativeFunction(E('il2cpp_image_get_name'), 'pointer', ['pointer']);
const imgCount = new NativeFunction(E('il2cpp_image_get_class_count'), 'uint', ['pointer']);
function cstr(p){try{return p.isNull()?'':p.readUtf8String();}catch(e){return '';}}
let out=[];
for (let i=0;i<n;i++){
  const a=asms.add(i*Process.pointerSize).readPointer();
  const img=asmImg(a);
  if(img.isNull()) continue;
  out.push({i, name:cstr(imgName(img)), classes:imgCount(img)});
}
send({assemblies:out});
"""

session = frida.attach(PID)
script = session.create_script(JS)
script.on("message", lambda m, d: print(json.dumps(m, ensure_ascii=False)))
script.load()
session.detach()

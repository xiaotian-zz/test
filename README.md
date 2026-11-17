# RF4 新年集市移植到 25034 客户端 —— 完整过程记录

> 最后更新：2026-11-18
> 用途：为后期继续开发保留全部关键结论、路径、代码位置、踩坑记录。
> 约定：全文中文。凡标 `[未验证]` 的条目表示当时没有跑通或没有实测，不能当作结论使用。

---

## 0. 一句话总结

目标是在**不修改任何客户端原文件**的前提下，让 25034 版客户端的「挪威海」地图里出现 RF4 新年集市的两个摊位（食品店 `nybaazar_012`、博览会 `ny_bazaarStore_012`），并挂上 Shop 组件实现按 E 开店。

最终选定路线：**从 Steam 老版本资源包里把 Mesh / Material / Texture 抽出来，用 UnityPy 重新打一个自建 AssetBundle，放在 `Data` 目录，靠游戏原生加载器（`lnepoeakhib`）加载，再用 Frida 调 IL2CPP 完成实例化与定位。**

当前进度：
- 无贴图版 `xmas_ok`：加载 + 实例化 + 定位 → **已稳定，不闪退**。
- 带贴图版：`xmas_bc`（texconv 重编码 DXT5）已产出未验证；`xmas_native`（搬原版 DXT1 原生字节）已产出 **但静态读回失败，尚未修好**。
- Shop 组件：未开始。

---

## 1. 目标与硬约束

### 1.1 目标
1. 新年集市两个摊位模型在客户端里出现（位置固定在挪威海）。
2. 材质/贴图尽量与原版一致（用户原话：「完全按照原版的来」）。
3. 摊位可交互：按 E 打开商店。

### 1.2 约束
- **不修改客户端任何原文件**。只允许在 `F:\RF4\Game\rf4_x64_Data\Data` 下新增自制文件。
- 不允许使用 `F:\RF4\Game\.rf4-local` 这个目录（已废弃的旧方案）。
- 不依赖 Unity 编辑器（机器上没有），所有 bundle 靠 UnityPy 手工构造。
- 资源必须来自 **Steam 目录下的老版本**，不是 `D:\RF4`：
  `D:\Steam\steamapps\content\app_766570\depot_766571\rf4_x64_Data`
- 用户明确要求：只取需要的少量资源「重新制作」，不能整包复制（原包 1~2 GB）。

### 1.3 为什么走「自建 AssetBundle + 原生加载器」
- 直接改客户端 `sharedassets*.assets`：文件巨大且有校验风险，违反「不改原文件」。
- 运行时内存里拼 Mesh：需要逐字段调用 IL2CPP，极不稳定（早期做法，已放弃）。
- 自建 bundle：游戏本来就有一套按名字从 `Data` 目录加载 bundle 的逻辑，只要包名和格式对，就等于「官方资源」。这是最稳的路线。

---

## 2. 环境清单

| 项目 | 值 |
|---|---|
| 工作目录 | `f:\rea`（子目录：`artifacts`、`scripts`、`reports`、`tools`、`.screenshots`） |
| 当前客户端 | `F:\RF4\Game\rf4_x64_Data`，版本 **4.0.25034** |
| 当前客户端 exe | `F:\RF4\Game\rf4_x64.exe`，进程名 `rf4_x64` |
| Steam 老版本 | `D:\Steam\steamapps\content\app_766570\depot_766571\rf4_x64_Data`，版本 **24205** |
| 私服 | `F:\rf4_server` |
| Python | `py -3.12` |
| UnityPy | 1.25.4 |
| Frida | Python 绑定 `frida`，注入本机进程 |
| Ghidra | `f:\rea\tools\ghidra_12.2`，需 `JAVA_HOME=f:\rea\tools\jdk21` |
| texconv | `f:\rea\tools\texconv.exe`（DirectXTex 2026.5.8.1，966,480 B，支持 BC7/DXT5） |

> 注意：当前机器上常年残留一堆 `rf4_x64` 僵尸进程（`Threads=0`、`WorkingSet=0`），是历次闪退留下的。实测它们不影响新开游戏，但 `frida.attach` 时**必须挑有线程的那个 PID**，否则连不上。

---

## 3. 原版资源到底在哪（重要结论）

对 Steam 老版本目录做了全盘二进制扫描（171 个非 `.resS` 文件，共约 23.33 GB），结论如下。

### 3.1 关键文件体积

| 文件 | 体积 |
|---|---|
| `Data\props` | **1,909,672,144 B（约 1.9 GB）** |
| `sharedassets5.assets` | 221,349,668 B（约 221 MB） |
| `sharedassets5.assets.resS` | 1,779,264,016 B（约 1.78 GB） |
| `sharedassets5.resource` | 101,362,240 B |

- `Data\props` 是 **AssetBundle**（不是裸 SerializedFile），内含 **22083 个对象、1078 个 Material**，新年集市的大部分材质在这里。
- `sharedassets5.assets` 是**独立 SerializedFile**（`sf.types is None`，类型树由 UnityPy 内置生成），纹理数据走同目录的 `sharedassets5.assets.resS`。

### 3.2 已排除的文件
`resources.assets`、`level24`、`sharedassets24.assets` 里**没有** christmas 相关材质，不要浪费时间再扫。

### 3.3 材质名 → 所属文件（另一轮全盘搜索的结果）

| 材质名 | 所在文件 |
|---|---|
| `bob_25186` | `Data\bobbers`、`globalgamemanagers`、`level10` |
| `Branches_0` | `sharedassets10.assets`、`sharedassets11.assets`、`sharedassets12.assets` |
| `Ground_Snow_Albedo` | `sharedassets3.assets`、`sharedassets5.assets` |
| `Snowman_01` | `sharedassets5.assets` |
| `bigsamovar_AlbedoTransparency` | `sharedassets5.assets` |
| `baranki_diff` | `Data\props`、`sharedassets5.assets` |

> 推论：`add_textures_native.py` 只扫了 `Data\props` + `sharedassets5.assets` 就命中 81/83，
> 说明没命中的那 **2 个** 极可能就是 **`Branches_0`** 和 **`bob_25186`**。
> 要补它们，需把 `sharedassets10/11/12.assets`、`Data\bobbers`、`level10`、`globalgamemanagers` 加进 `SOURCES`。

---

## 4. 原版加载链路（Ghidra 反编译确认）

### 4.1 涉及的 IL2CPP 类（都在 `Assembly-CSharp.dll`，命名空间为空）

| 类名 | 作用 |
|---|---|
| `lnepoeakhib` | bundle 加载器（单例） |
| `pgohfpicjjd` | 静态包装/门面类 |
| `ciiamanepjn` | 异步加载的 yield 对象，实现 `pmonngpimmi` |
| `pmonngpimmi` | 协程等待接口（`get_keepWaiting`） |
| `iijbggbaomp` | 资源异步加载协程 |
| `gpdflailkgp` | 路径拼接方法 |

### 4.2 两个缓存字典
- `hfcggegmohh: Dictionary<string, AssetBundle>` —— 已加载成功的包
- `gccjemmebdm: Dictionary<string, AssetBundleCreateRequest>` —— 正在加载的请求

静态字段 `pgohfpicjjd.hfcggegmohh` 可以通过 `il2cpp_field_static_get_value` 直接拿到（Frida 脚本就是这么做的），拿到后即 `lhb`。

### 4.3 异步路径
```
lnepoeakhib.ghoioimpjia(name)
  → gpdflailkgp(name)                     // 拼成 <Data 目录>/<name>
  → AssetBundle.LoadFromFileAsync(path, 0, 0)
  → 包成 ciiamanepjn : pmonngpimmi
```
- `ciiamanepjn.ddkbjcdpelm()` 返回 `request.assetBundle`
- `ciiamanepjn.get_keepWaiting` 用于协程轮询
- `ciiamanepjn` 内部字段 `+0x10` 是 `AssetBundleCreateRequest`

### 4.4 同步路径
```
lnepoeakhib.pejbciknlni(name)
  → gpdflailkgp(name)
  → AssetBundle.LoadFromFile(path, 0, 0)
  → 写入 hfcggegmohh 并返回
```

### 4.5 资源加载
```
iijbggbaomp 协程 → bundle.LoadAssetAsync(assetId) → assetRequest.asset
```

### 4.6 静态泛型包装
```csharp
pgohfpicjjd.lcoiijaoppd<T>(bundle, assetId)
pgohfpicjjd.gccllnckgck<T>(bundle, assetId)
```
> **泛型方法在 Frida 里不可直接 invoke**，所以全部绕开，直接调非泛型的 `AssetBundle.LoadAsset(string, Type)`。

### 4.7 由此得到的结论
只要把自制包放到 `Data` 目录、命名成 `xmas_xxx`，`ghoioimpjia("xmas_xxx")` 就能加载。
**这就是「走原生」的全部秘密**，也是放包路径必须是 `F:\RF4\Game\rf4_x64_Data\Data\` 的原因。

---

## 5. AssetBundle 重打包的硬性约束（血泪）

UnityPy 手工造出来的 bundle，Unity 运行时是**会严格校验**的。以下每条都是实测必需的，缺一个就加载失败：

1. **AssetBundle 对象的 `path_id` 必须 = 1**。
2. **必须 `bf.save(packer="lz4hc")`**。`packer='none'` 会被运行时直接拒绝。
3. **CAB 名必须每次换新**，例如 `CAB-xmas_native<14位hex>`。
   否则第二次加载会报 "The same files" 之类的错误。
4. **`m_AssetBundleName` 必须唯一**（与包文件名一致最省事）。
5. 包的路径/文件名不能和已有资源重名。
6. `m_IndexBuffer` 长度必须等于所有 submesh 的 `indexCount` 之和，否则加载即崩。
7. 重建对象后必须**修复所有 PPtr**：
   - Material 的贴图引用要指向 in-bundle 的新 `path_id`（`m_FileID = 0`）；
   - 否则运行时拿到 NULL。
8. 修改 Material 的贴图时，**只能改 `item[1]["m_Texture"]`**（即 `m_Texture` 这个 PPtr 本身）。
   **直接替换整个 map 元素会崩**（UnityPy 写回结构错位）。
9. 打包后要做的静态校验：
   - 坏引用数 = 0；
   - IndexBuffer 长度与 submesh 汇总一致；
   - 重新 `UnityPy.load` 能读出对象数量。

### 5.1 mesh bin 格式（自己导出的中间格式）
```
[8 字节头] + pos(vc*12) + normal(vc*12) + uv(vc*8) + index(tc*12)
```
长度已全部校验通过。

---

## 6. 素材清单（`f:\rea\artifacts\xmas_stalls`）

`manifest.json` 结构：

| key | 内容 |
|---|---|
| `root` | 树形节点 `{name, pos, rot, scale, children}` |
| `meshes` | 167 个，`{id, name, vcount, tcount, bin, material}` |
| `materials` | 95 个，`{id, name, color, tex, shader}` |
| `textures` | 79 个，**只有 `{id, file: "textures/texN.png"}`，没有原始纹理名** |

- 95 个材质里有 **83 个带 tex**（即需要贴图）。
- 贴图为 79 张 PNG（从老版本导出时转过一次）。

> 注意：`textures` 没有原名，是后期材质→纹理匹配效率低的一个原因。
> 现在 `add_textures_native.py` 改为「按材质名去原包里找 `_MainTex` 的 PPtr」，绕过了这个问题。

---

## 7. 纹理：原版真实格式（关键突破）

### 7.1 实测样本

| 材质 | 纹理 | 尺寸 | 格式 | mip | m_StreamData |
|---|---|---|---|---|---|
| `tangerin_mat` | `tangerin_AlbedoTransparency` | 1024×1024 | **10 = DXT1** | 11 | offset=551324432, size=699064, path=`archive:/CAB-90733f0febaeb64d0930402de8477656/CAB-90733f0febaeb64d0930402de8477656.resS` |
| `christmas_cup_mat` | — | 512×512 | DXT1 | 10 | offset=98642192, size=174776 |
| `christmas_dish_mat` | — | 512×512 | DXT1 | 10 | offset=200966608, size=174776 |

`sharedassets24.assets` 里纹理格式分布（参考）：(12=DXT5, 12 mips) ×76、(12,10) ×67、(10,10) ×56、(10,12) ×55，另有 28/29（crunch 压缩）。

**结论：原版不是 RGBA32，而是 DXT1/DXT5 + 全 mip 链 + resS 流式存储。**
之前用 RGBA32 + 单 mip 重打包，与原生差异巨大。

### 7.2 从 bundle 里读 resS 的正确写法

```python
r = bf.files['CAB-xxxxxxxx.resS']   # 注意：取到的是 EndianBinaryReader 本身
r.seek(offset)
data = r.read_bytes(size)           # 实测可读到 699064 字节
```
- `bf.files[k]` **本身是 reader，不是 node**，没有 `.reader` 属性。
- 对于独立 SerializedFile（如 `sharedassets5.assets`），resS 是**独立文件**，直接用 `open(...).seek(offset).read(size)`。

### 7.3 搬运策略（`add_textures_native.py`）
1. 遍历源包里所有 Material，读 typetree 拿 `m_Name`；
2. 若名字在 manifest 的「带贴图材质」集合里，取 `_MainTex` 的 PPtr；
3. 找到对应 `Texture2D`，读 typetree 拿 `m_StreamData`；
4. 按 offset/size 从 resS 读出**原始压缩字节**；
5. `build_tex(name, w, h, mips, fmt, data)` 用它重建 Texture2D：
   - `m_TextureFormat` **保持原生**（10/12/28/29…）；
   - `m_MipCount` **保持原生**；
   - `m_CompleteImageSize = len(data)`；
   - `image data` 直接塞原始字节；
   - `m_StreamData` 置空（`{offset:0,size:0,path:""}`）→ 改为内嵌，不依赖外部 .resS；
   - `m_IsReadable=False`、`m_StreamingMipmaps=False`。

### 7.4 首跑结果（2026-11-18 04:2x）
```
props           matched 34  cum 34
sharedassets5   matched 47  cum 81
total matched 81 / 83
textures packed 81  raw MB 86.1
materials bound 76  objects 3683
written 50,293,039
reload tex 81  total 3683
```
- 输出文件：`F:\RF4\Game\rf4_x64_Data\Data\xmas_native`（**50.3 MB**）
- 注意：`materials bound 76`，与「81 张纹理」不同——因为 5 个材质可能共用纹理或材质名对不上。

### 7.5 重要推论（需要修正旧结论）
原版这 81 张纹理的**未压缩等价体积就是 86.1 MB**，说明：
- 之前「RGBA32 版 79~82 MB 显存导致闪退」的判断**很可能是错的**；
- 游戏本身就要吃这么多显存来渲染这个集市；
- 真正导致闪退的更可能是 **Texture2D 对象构造不合法**，而不是显存峰值。

此结论待 `xmas_native` 跑通后最终确认。

---

## 8. 已产出的包与状态

（都在 `F:\RF4\Game\rf4_x64_Data\Data`）

| 包名 | 大小 | 内容 | 状态 |
|---|---|---|---|
| `xmas_ok` | 8,475,487 B | 3602 对象，无贴图 | **稳定**：加载 + 实例化 + 定位均通过，不闪退 |
| `xmas_bc` | 10,903,999 B | 3681 对象，79 张 DXT5 256²+mip，76 材质绑定 | 已打包，**未做运行时验证** |
| `xmas_native` | 50,293,039 B | 3683 对象，81 张原生 DXT1/DXT5+全mip，76 材质绑定 | 已打包，**静态读回失败，待修** |
| 其它 | — | `xmas_t*`、`xmas_fix`、`xmas_min*`、`xmas_np`、`xmas_mrt`、`native_*`、`lures_*` 等 | 全部是历史实验产物，稳定后要清理 |

---

## 9. 运行时注入（Frida + IL2CPP）

### 9.1 原理
1. `frida.attach(pid)` 注入；
2. 从 `GameAssembly.dll` 拿 `il2cpp_*` 导出函数；
3. 遍历 assemblies 找到 `Assembly-CSharp.dll` / `UnityEngine.CoreModule.dll` / `UnityEngine.AssetBundleModule.dll`；
4. `il2cpp_class_from_name` 拿到类，`il2cpp_class_get_methods` 枚举方法；
5. 用 `il2cpp_runtime_invoke(MethodInfo*, obj, args, exc)` 调用。

### 9.2 关键坑（必读）

1. **`il2cpp_runtime_invoke` 第一个参数必须是 `MethodInfo*`**
   —— 就是 `il2cpp_class_get_methods` 返回的那个指针**本身**。
   **不是** `mi.add(P).readPointer()`（那是 methodPointer / invoker 地址，只在 hook 时用）。
   > 之前所有 invoke 崩溃退出码 `0xffffffffffffffff`，根因就是这个。

2. **`get_transform` 要在 `GameObject` 上找**。
   root 是 `GameObject`；在 `Renderer` 上找不到。`Camera` 的情况相反。

3. **泛型方法一律不可用**：
   `GameObject.GetComponentsInChildren<T>()` 是全泛型。
   替代方案：`GameObject.GetComponents(Type)`（argc=1，非泛型）+ 自己用 `Transform` 递归。

4. **`Transform.get_childCount` 返回 boxed int**，取值要 `boxed.add(0x10).readInt32()`。

5. **IL2CPP 字符串**：对象 `+0x10` 是长度（int32），`+0x14` 是 UTF-16 数据。

6. **数组**：`+0x18` 是 length（UInt64），`+0x20` 是数据起始。

7. **每次注入必须重启游戏**。
   同进程重复注入会污染 Bundle 全局缓存（`hfcggegmohh` 里留着旧状态），第二次 `LoadFromFile` 恒返回 NULL。

8. **不要全量 hook 所有 `Update`**（试过 420 个，游戏直接卡死）。
   现在只 hook 单个 `Time.get_time` / `get_deltaTime` 之类，用 tick 驱动状态机。

### 9.3 放置坐标（挪威海）
```
position = (233.36, 2.66, 784.36)
rotation = (0, -0.35917, 0, 0.93327)   // 四元数
```
- 地图：挪威海 = level24；铜湖 = level26。
- 定位方式：`Object.Find("CHRISTMAS(Clone)")`，先 `Destroy` 掉旧的同名克隆再生成新的，保证可重复。

### 9.4 脚本清单（`f:\rea\scripts`）

| 脚本 | 作用 |
|---|---|
| `frida_spawn_ok.py` | **主注入脚本**。加载指定包 → `LoadAsset("assets/rf4local/xmas_stalls.prefab", GameObject)` → `Instantiate` → 定位到挪威海。目前里面包名写死为 `xmas_bc`，**需要改成 `xmas_native`** |
| `frida_apply_textures2.py` | 运行时给已生成对象按需挂贴图（Transform 递归 + `GetComponents(Type)`，每帧 budget=1）。**遍历不完整：只访问到 33/426 节点，`childCount` 读取疑似有问题，已加日志但未重跑** |
| `frida_apply_textures.py` | 上一版运行时贴图脚本 |
| `frida_native_load*.py` / `frida_load_bundle.py` / `frida_load_stalls.py` | 早期各种加载验证 |
| `frida_analyze_loader.py` / `frida_disasm_loader.py` / `frida_probe_path*.py` / `frida_trace_load.py` / `frida_dump_rva.py` | 逆向加载链路用 |
| `add_textures.py` | 旧方案：PNG → RGBA32 贴图（**闪退根源，勿用**） |
| `add_textures_bc.py` | PNG → texconv 转 256² DXT5 + mip → 打包 |
| `add_textures_native.py` | **当前主打包脚本**：原版压缩字节搬运 |
| `build_xmas_bundle.py` | 从 manifest 生成无贴图 bundle |
| `unity_bundle_inspect.py` / `verify_xmas.py` / `scan_bundle_names.py` / `dump_skeleton_types.py` / `scan_shop_points.py` | 辅助检查 |

---

## 10. 崩溃史与根因梳理

| 阶段 | 现象 | 结论 |
|---|---|---|
| 早期内存拼 Mesh | 各种报错/崩溃 | IL2CPP 逐字段构造不可行，放弃 |
| `xmas_fix` / `xmas_min2` / `xmas_np` / `xmas_tb2` | 加载或实例化时闪退 | 全部与「带纹理」有关 |
| `add_textures.py`（RGBA32 / 单 mip） | 实例化必闪退 | 曾归因为显存峰值（79~82 MB vs 原版估计 7 MB）；**该归因现在看很可能是错的** |
| bundle 重打包 | Unity 拒绝加载 | path_id 必须 = 1、必须 LZ4HC、CAB 名要换、`m_AssetBundleName` 要唯一 |
| Frida invoke | 退出码 `0xffffffffffffffff` | 传了 invoker 地址而不是 `MethodInfo*` |
| 全量 hook Update | 游戏卡死 | 改为单点 hook |
| `get_transform` 找错类 | 崩溃 | 改到 `GameObject` 上找 |

### 10.1 `xmas_native` 当前故障（未解决）
- 现象：打包脚本自己 reload 时只按 `type.name` 计数（`reload tex 81`），**没有真正解析 typetree**。
- 用独立脚本真正 `read_typetree()` 时，81 个 Texture2D **全部** 抛：
  ```
  EOFError: read_str out of bounds
  ```
- 已排查：
  - `xmas_ok` 与 `lures_wta` 的 Texture2D 类型树结构 dump 出来**完全一致**（46 行相同，含 `m_MipmapLimitGroupName`、`m_PlatformBlob`、`image data`、`m_StreamData`）。
  - 内存里 `write_typetree` 写出的 blob 长度 = 数据长度 + 124 B 头（例：699188 = 699064 + 124），用 `read_value` 能完整读回（只是 `check_read` 的 `byte_size` 参数没传对）。
  - 也就是说：**写出去的内容本身自洽，是「保存进 bundle 再读回」这一步出了问题**。
- 待验证假设（按可能性排序）：
  1. 保存时新增对象的 `byte_size` 与实际数据长度不一致（例如 `image data` 的 `TypelessData` 长度计算方式与写入不一致）。
  2. `m_StreamData.path` 空字符串 + 原生 `m_StreamData` 结构在不同版本下的字段顺序差异。
  3. 对象顺序/对齐问题（`align_stream` 之后 byte_start 偏移错位）。
  4. `xmas_ok` 的类型树里 `Texture2D` 的 `type_id` 与实际写入用的不一致。
- 下一步诊断手段：
  ```python
  o = sf.objects[2100000]
  print(o.byte_size, o.byte_start)
  raw = o.get_raw_data(); print(len(raw), raw[:16].hex())
  # 再用 xmas_ok 的 node 手动 read_value，看在哪一步越界
  ```

---

## 11. 待办清单（按优先级）

1. **修 `xmas_native` 的 Texture2D 读回失败**（见 10.1）。
   - 若最终确认 UnityPy 写 Texture2D 不可靠，备选：用 `texconv` 生成标准 DDS 后续块（`xmas_bc` 路线），但要把 mip 链补全、格式对齐原版。
2. **补齐最后 2 个材质**：`Branches_0`、`bob_25186`。
   - 把 `sharedassets10/11/12.assets`、`Data\bobbers`、`level10`、`globalgamemanagers` 加进 `add_textures_native.py` 的 `SOURCES`。
3. **运行时验证带贴图包**：把 `frida_spawn_ok.py` 里的包名改成目标包 → 加载 → Instantiate → 在 `233.36, 2.66, 784.36` 出现且**不闪退**。
4. **若仍然闪退**：改走「无贴图包 + 运行时按需挂贴图」路线，修 `frida_apply_textures2.py` 的 Transform 遍历（33/426 问题）。
5. **挂 Shop 组件**：
   - 食品店 storeID：`nybaazar_012`
   - 博览会 storeID：`ny_bazaarStore_012`
   - 方案：从现有 Shop MonoBehaviour 复制一份，改 config（偏移 **+104**），挂到摊位对应 GameObject 上。
   - 验证：走到摊位前按 E 能开店。
6. **清理 `Data` 目录**：稳定后删掉临时包
   `xmas_stalls`、`xmas_c*`、`xmas_l*`、`xmas_fix`、`xmas_min*`、`xmas_t*`、`xmas_np`、`xmas_tnb`、`xmas_mrt`、`lures_x1`、`lures_x2`、`lures_del1`、`native_*`。
7. （可选）给 launcher 加「服务端开关触发本地注入」链路，免得每次手动跑 Frida。

---

## 12. 复现步骤（命令速查）

```powershell
# 1) 生成无贴图包
py -3.12 f:\rea\scripts\build_xmas_bundle.py

# 2) 从原版搬原生纹理（产出 xmas_native）
py -3.12 f:\rea\scripts\add_textures_native.py

# 3) 用 texconv 重编码（产出 xmas_bc）
py -3.12 f:\rea\scripts\add_textures_bc.py

# 4) 检查包结构
py -3.12 f:\rea\scripts\unity_bundle_inspect.py

# 5) 注入（先确认有线程的 PID）
Get-Process -Name rf4_x64 | Select-Object Id,Threads
py -3.12 f:\rea\scripts\frida_spawn_ok.py <PID>
```

Ghidra 反编译环境：
```powershell
$env:JAVA_HOME = "f:\rea\tools\jdk21"
f:\rea\tools\ghidra_12.2\support\analyzeHeadless.bat ...
```

---

## 13. 附录

### 13.1 字节/结构速查
| 项目 | 格式 |
|---|---|
| IL2CPP string | `+0x10` len(int32)，`+0x14` UTF-16 |
| IL2CPP array | `+0x18` len(UInt64)，`+0x20` data |
| boxed int | `+0x10` int32 |
| `ciiamanepjn` | `+0x10` = AssetBundleCreateRequest |
| Texture2D format 10 | DXT1（每 4×4 块 8 B） |
| Texture2D format 12 | DXT5（每 4×4 块 16 B） |
| Texture2D format 28/29 | Crunch 压缩（不可直接搬？待验证） |
| DDS 头 | 128 B；`mipCount` 在 offset 28 |
| texconv 输出 DDS | 数据从 offset 148 开始（含 DX10 扩展头时） |

### 13.2 临时诊断脚本（在 `%TEMP%`，不属于工程）
- `rf4_verify_native.py` —— 校验 `xmas_native` 里 Texture2D 的 w/h/fmt/mip 与字节数是否自洽
- `rf4_dump_texnode.py` —— dump 并 diff 两个文件的 Texture2D 类型树
- `rf4_test_writetree.py` —— `write_typetree` 内存 roundtrip 测试
- `rf4_test2.py` —— 从 `xmas_native` 读回单个 Texture2D 并打印 byte_size/raw 头（**被中断，未跑**）

### 13.3 曾经的错误归因（写下来防止重犯）
- ❌「显存 79 MB 所以崩」→ 原版 81 张纹理就已经是 86 MB 未压缩等价，显存不是主因。
- ❌「`bf.files[k].reader`」→ 不存在，`bf.files[k]` 本身就是 reader。
- ❌「`il2cpp_runtime_invoke` 传 methodPointer」→ 必须传 MethodInfo*。
- ❌「`get_transform` 从 Renderer 上取」→ 要在 GameObject 上取。
- ❌「RGBA32 单 mip 就行」→ 与原版差异过大，且极可能本身就是崩溃源。

---

## 14. 原版原样搬运（clone 系列）迭代记录

### 14.1 方案
从 Steam 24205 `level24`（挪威海场景）里定位根对象 `CHRISTMAS`（path_id **8634**，位置 `233.36, 2.66, 784.36`，四元数 `(0.0026856, -0.3595577, 0.0010348, 0.9331184)`），
把它整个 Transform 层级 + 组件 + 依赖闭包原样复制进自建 bundle。

- 依赖跨 3 个文件：`level24` 自身、`sharedassets5.assets`（210 个）、`sharedassets3.assets`（9 个）
- 规模：**1207 GameObject / 1207 Transform / 543 MeshFilter+MeshRenderer / 110 LODGroup / 98 Material / 213 Texture2D / 143 Mesh / 7 Shader**
- 脚本：`f:\rea\scripts\build_xmas_clone.py`，输出 `F:\RF4\Game\rf4_x64_Data\Data\xmas_cloneN`

### 14.2 已踩平的 5 个致命坑
1. **跨文件 PPtr 的 m_FileID 是相对于各自文件的 externals**，不能统一用 level24 的索引 → 必须按 (文件路径, path_id) 跟踪。
2. **`Transform.m_Father` 绝不能清零**。BFS 时为了不把整个场景拖进来改了它，结果污染缓存，1206 个 Transform 父指针全丢，Instantiate 直接 `access violation 0x38`。正确做法：遍历时跳过该字段，不修改数据。
3. **空组件必须从 `GameObject.m_Component` 里删除**，不能留 PathID=0。同理 LODGroup 的 `m_LODs[].renderers`。
4. **new_ids 只能分配给真正写入包内的对象**。给被跳过类型也分配 id → 悬空引用 → 崩。
5. **类型表**：level24 是无类型树文件（node 全空），用 `UnityPy.helpers.Tpk.get_typetree_node(class_id, sf.version)` 补；**Texture2D(28)/Shader(48) 直接复用 lures_wta 的同版本 SerializedType**（手工构造的 hash 全 0 会导致 bundle 加载失败 `bundle=null`）；`sf._enable_type_tree = False` 保存。

### 14.3 各版本结果
| 版本 | 内容 | 大小 | 结果 |
|---|---|---|---|
| clone6 | 全量（含 Shader/粒子/树/骨骼/光照/碰撞/脚本） | 144.5 MB | **外观完全正常，但闪退**（Windows BEX64 `0xc0000409`） |
| clone7 | 去掉 Shader + 粒子/树/骨骼/光照/碰撞 | 115.8 MB | 洋红（无 shader），未作为外观基线 |
| **clone8** | **保留 Shader+材质+纹理，去掉粒子/树/骨骼/光照/碰撞/脚本** | 118.2 MB | **显示正常、不闪退（用户确认）** |
| **clone9** | clone8 + **粒子系统**（ParticleSystem/Renderer，6 套） | 118.2 MB | **不闪退（用户确认）** |
| **clone10** | clone9 + **SpeedTree**（Tree×4、BillboardRenderer×1；BillboardAsset 缺类未打包） | 119.6 MB | **不闪退（用户确认）** |
| **clone11** | clone10 + **骨骼动画**（SkinnedMeshRenderer×11、Animator×3、Animation×5；Avatar/AnimatorController 缺类） | 144.5 MB | **不闪退，两个雪人正常出现（用户确认）** |
| **clone12** | clone11 + **光照**（Light×2） | 144.5 MB | **正常（用户确认）** |
| **clone13** | clone12 + **碰撞体**（Box×5、Capsule×2、Mesh×1） | 144.5 MB | **显示正常，但无交互（MonoBehaviour 仍被跳过）** |

> 结论：从 clone8 → clone13，逐组加回粒子、SpeedTree、骨骼动画、光照、碰撞体，**全部不闪退**。
> clone6 的闪退不是这些组件引起的，最可能是「38 个 MonoBehaviour 全部丢失导致 GameObject 组件槽异常」或 Shader 相关，待验证。
> 目前唯一缺失项：**MonoBehaviour（38 个脚本，含商店交互逻辑）**。

### 14.6 clone14（含 MonoBehaviour）失败 —— 重要结论
- 做法：手工按固定头部改写 `m_GameObject` / `m_Script` 两个 PPtr，其余字节 raw 拷贝；同时收集 9 个 MonoScript。
- 结果：`Instantiate` 抛 `Error: breakpoint triggered`（Unity IL2CPP 断言），重试一次后成功 `SPAWNED`，但**进程随即崩溃**。
- 结论：**24205 的 MonoBehaviour 自定义字段布局与 25034 不兼容**，raw 搬运会导致反序列化错位 → 断言/崩溃。MonoBehaviour 不能直接搬。
- 因此交互（按 E 开店）需要另走「运行时补挂」路线，而不是把原版脚本打进包。

### 14.7 Shop 组件重建（关键数据）
服务端 `F:\rf4_server\wt-icons\internal\store\assets\shop_kind_defs.json` 确认两个 ID 都存在：
- `nybaazar_012`（第 1064 行）：`kind=1`、`brands=[ny_bazaar, lapshin_brewery]`、`map_key=level_012_north_sea`
- `ny_bazaarStore_012`（第 984 行）：`kind=0`、`brands=[chernomorets, pomor]`、`map_key=level_012_north_sea`

**25034 的 Shop MonoBehaviour 字节布局**（head 32 字节之后）：
```
[int 0][string storeID][pad][int 0][int 0][int X][int 0]
```
`X` = 商店类型，实测对照：
| 商店 | X |
|---|---|
| fishingstore_012 | 0 |
| foodstore_012 | 1 |
| boatstation_012 | 4 |
| atm_012 | 6 |
| tool_store_012 | 7 |
| craft_baits_012 | 11 |

而 24205 的布局是 `[int 0][string storeID][kind][5][3008][0][0]`，字段顺序不同，**不能 raw 搬运**。

**正确重建法**：用 25034 模板，`X` 填服务端的 kind。
- `nybaazar_012` → `[0,0,0,1,0]`（与 foodstore_012 同构）
- `ny_bazaarStore_012` → `[0,0,0,0,0]`（与 fishingstore_012 同构）

失败记录：
- clone15：X 写死成 11（当成了 craft_baits），且 kind 放在第 1 个 int → 无交互
- clone16：kind 放第 1 个 int + 多余 11 → **UnityPlayer.dll 崩溃 `0xc0000005`**（Awake 里按索引越界）
- clone17：`[0,0,0,kind,0]` 完全同构 → 待验证

### 14.8 运行时补交互（最终可用方案）
包内 MonoBehaviour 必然崩（`UnityPlayer.dll +0x7e6aac`），改为运行时补挂。

**Shop 类**：`Assembly-CSharp` / 命名空间 **`RF4.Client.FishingScene`** / 类名 `Shop`

**字段真实类型**（IL2CPP 实测）：
| 偏移 | 字段 | 类型 |
|---|---|---|
| +80 | storeID | System.String |
| +88 | musicOverride | UnityEngine.AudioClip |
| +96 | storeType | lcjoplghgif（枚举/引用，**只能写 int 值**） |
| +104 | coffdfkgfaa | bikcadfljfo（配置对象引用） |
| +112 | disableReturns | System.Boolean |

**方法**：`Awake()` / `Start()` / `egcphdmelae(System.String)` / `fgmbdkjipka()` / `ipneakjbohn()` 等，**没有 Update**（交互由外部 Collider 扫描驱动）。

**可用的正确流程**（已实测能打开正确的新年集市食品店）：
1. `GameObject.Find("Sea_bait_shop_12_interact")` 克隆一份（Transform + Shop + BoxCollider + RevertPositionAfterPlayerTeleport，无 Renderer）
2. 移到目标坐标
3. `GetComponents(ShopType)` 找到 Shop
4. 写 `+80` = storeID，`+96` = kind（int），`+104` = **null**
5. **不要调用 `egcphdmelae`** —— 它会按 storeType/config 重置，导致变回钓具店

**最终坐标（已验证，两个都能正常开店）**：
| 商店 | 世界坐标 | storeType |
|---|---|---|
| 博览会 `ny_bazaarStore_012` | `237.57, 2.57, 792.03` | 0 |
| 食品店 `nybaazar_012` | `237.75, 2.52, 789.00` | 1 |

**高度是坑**：代理的 y 必须接近玩家站立高度（约 `相机 y - 1.5`）。之前一直用 `y=0.10`，与玩家差 4 米，BoxCollider 完全不重叠，所以按钮不出现。

**完整可复现流程**：
1. 原生加载 `xmas_clone13`（144 MB，完整外观）→ `Instantiate` → 位置 `233.36, 2.66, 784.36`、旋转 `(0.0027, -0.3596, 0.0010, 0.9331)`
2. 克隆 `Sea_bait_shop_12_interact` 两份
3. 分别放到上表坐标
4. **移除**克隆体上的 `RevertPositionAfterPlayerTeleport`（否则玩家靠近会触发传送逻辑，导致 `0xc0000409` 崩溃）
5. `GetComponents(ShopType)` → 写 `+80`=storeID、`+96`=storeType、`+104`=null
6. 不调用 `egcphdmelae`

**清理**：每次注入前删除名字匹配 `CHRISTMAS|Sea_bait_shop_12.*\(Clone\)` 的对象，否则多次注入会堆叠代理和悬空模型。

---

# 第 15 章 最终可用方案（完整复现手册）

## 15.1 成果
在 **25034 客户端**的挪威海（level24）中，原版 `CHRISTMAS` 新年集市被完整还原：
- 完整外观：1207 个 GameObject、98 个材质、213 张原版纹理、原版 Shader、粒子、SpeedTree、雪人、灯光、碰撞体
- 两个可交互商店：按 E 打开「新年博览会」和「新年集市食品店」
- 全程**不修改任何客户端原文件**，只在 `Data` 目录新增一个 bundle，运行时由游戏原生加载器加载

## 15.2 完整流程（从零复现）

### 第 1 步：准备素材
从 Steam 老版本（`D:\Steam\steamapps\content\app_766570\depot_766571\rf4_x64_Data`）提取：
- `level24`（scene）→ 定位 `CHRISTMAS` 层级
- `Data\props`（1.9 GB，含 1078 个 Material + 新年集市纹理）
- `sharedassets5.assets` + `.resS`
- `globalgamemanagers.assets`（MonoScript 表）

### 第 2 步：构建 bundle
```powershell
$env:CLONE_OUT='F:\RF4\Game\rf4_x64_Data\Data\xmas_clone13'
py -3.12 f:\rea\scripts\build_xmas_clone.py
```
产出：**144.5 MB、4110 个对象**的 `xmas_clone13`，包含：
- 全部 GameObject / Transform / Mesh / MeshRenderer / Material / Texture2D / Shader / AnimationClip / ParticleSystem / Tree / Light / Collider
- **排除**：MonoBehaviour（包内必崩）、BillboardAsset（客户端类型库无此类型）

### 第 3 步：注入
```powershell
$p=Get-Process rf4_x64 | Where-Object {$_.Threads.Count -gt 3} | Select-Object -First 1
py -3.12 f:\rea\scripts\frida_spawn_shop.py $p.Id
```
脚本做的事：
1. 清理旧的 `CHRISTMAS` / `Sea_bait_shop_12*(Clone)`
2. 走原生加载器 `lnepoeakhib.ghoioimpjia("xmas_clone13")` → `AssetBundle.LoadFromFileAsync`
3. `LoadAsset("assets/rf4local/xmas_clone13.prefab")` → `Instantiate`
4. 设位置 `233.36, 2.66, 784.36`、旋转 `(0.0027, -0.3596, 0.0010, 0.9331)`
5. 克隆 `Sea_bait_shop_12_interact` 两份，放到固定坐标
6. 移除克隆体上的 `RevertPositionAfterPlayerTeleport`
7. 写 Shop：`+80` storeID、`+96` storeType、`+104` null

## 15.3 坐标与字段（核心数据）

### 摊位与交互点
| 项 | 世界坐标 |
|---|---|
| CHRISTMAS 根节点 | `233.36, 2.66, 784.36` |
| 根节点旋转（四元数） | `(0.0026856011245399714, -0.35955774784088135, 0.0010348404757678509, 0.9331184029579163)` |
| 博览会交互点 | `237.57, 2.57, 792.03` |
| 食品店交互点 | `237.75, 2.52, 789.00` |

### Shop 组件（`RF4.Client.FishingScene.Shop`）
| 偏移 | 字段 | 类型 | 写入值 |
|---|---|---|---|
| +80 | storeID | System.String | `ny_bazaarStore_012` / `nybaazar_012` |
| +88 | musicOverride | AudioClip | 不写 |
| +96 | storeType | lcjoplghgif | 博览会 0、食品店 1 |
| +104 | coffdfkgfaa | bikcadfljfo | **null** |
| +112 | disableReturns | Boolean | 不写 |

### storeType 对照表（25034 实测）
| 商店 | storeType |
|---|---|
| fishingstore_012 | 0 |
| foodstore_012 | 1 |
| boatstation_012 | 4 |
| atm_012 | 6 |
| tool_store_012 | 7 |
| craft_baits_012 | 11 |

### 服务端配置（`F:\rf4_server\wt-icons\internal\store\assets\shop_kind_defs.json`）
- `nybaazar_012`（第 1064 行）：`kind=1`、`brands=[ny_bazaar, lapshin_brewery]`、`map_key=level_012_north_sea`
- `ny_bazaarStore_012`（第 984 行）：`kind=0`、`brands=[chernomorets, pomor]`、`map_key=level_012_north_sea`

## 15.4 踩过的坑（按类别）

### 打包层
1. **字节序**：`EndianBinaryWriter()` 默认大端，必须 `endian=sf.reader.endian`，否则所有 Texture2D 数据反序，Unity 读到天文数字长度直接崩
2. AssetBundle 对象 `path_id` 必须 = 1
3. 必须 `bf.save(packer="lz4hc")`，`none` 会被拒绝
4. CAB 名必须换新，`m_AssetBundleName` 必须唯一
5. Material 图集绑定只能改 `item[1]["m_Texture"]`，替换整个 map 元素会崩
6. 重建对象后必须修所有 PPtr
7. `m_IndexBuffer` 长度必须等于所有 submesh 的 `indexCount` 之和
8. 纹理要用原生格式（DXT1/DXT5）+ 完整 mip，RGBA32 无 mip 会闪退

### MonoBehaviour 层
9. **包内 MonoBehaviour 必崩**：`UnityPlayer.dll +0x7e6aac`、`0xc0000005`。原因是自建 bundle 无类型树，Unity 无法反序列化脚本字段。必须改为运行时补挂
10. 24205 与 25034 的脚本字段布局不同，不能 raw 搬运
11. `storeType` 不是 int，写坏指针会导致变回钓具店或崩溃

### 运行时层
12. `il2cpp_runtime_invoke` 第一个参数必须是 **MethodInfo\***，不是 invoker 地址（否则 `0xffffffffffffffff`）
13. `get_transform` 在 GameObject 上找；Camera/Renderer 这类 Component 要用 `Component.get_transform`
14. `GameObject.GetComponentsInChildren(Type)` 在 IL2CPP 里**不存在非泛型版本**，只能用 `GetComponents(Type)` 或递归 Transform
15. 克隆**整个** `Sea_bait_shop_12` 模型会在空中生成大量红/蓝集装箱（必须只克隆 `_interact`）
16. 克隆体上的 `RevertPositionAfterPlayerTeleport` 在玩家靠近时触发，导致 `0xc0000409` 崩溃，必须移除
17. **代理 y 必须接近站立高度**（相机 y − 1.5）。用 y=0.10 与玩家差 4 米，Collider 不重叠，按钮不出现
18. 不要调用 `Shop.egcphdmelae(storeID)`，它会按 storeType/config 重置，把商店变回钓具店
19. 同进程重复注入会污染 Bundle 全局状态，每次测试前重启游戏

## 15.5 文件清单（`f:\rea\scripts\`）
| 文件 | 作用 |
|---|---|
| `build_xmas_clone.py` | 从 level24 抽取 CHRISTMAS 层级构建 bundle |
| `frida_spawn_shop.py` | **最终注入脚本**（加载 + 实例化 + 补交互） |
| `frida_campos.py` | 读取当前相机世界坐标（用于对齐交互点） |
| `frida_shop_probe.py` | 探测 Shop 字段偏移/方法/实例 |
| `add_textures_native.py` | 原生纹理字节搬运（历史方案） |
| `add_textures_bc.py` | texconv DXT5 方案（历史方案） |
| `frida_spawn_ok.py` | 早期纯外观注入脚本 |

## 15.6 常用命令
```powershell
# 构建 bundle
$env:CLONE_OUT='F:\RF4\Game\rf4_x64_Data\Data\xmas_clone13'; py -3.12 f:\rea\scripts\build_xmas_clone.py

# 重启游戏后注入
$p=Get-Process rf4_x64 | Where-Object {$_.Threads.Count -gt 3} | Select-Object -First 1
py -3.12 f:\rea\scripts\frida_spawn_shop.py $p.Id

# 读相机坐标（调整交互点用）
py -3.12 f:\rea\scripts\frida_campos.py <PID>

# 查 Shop 状态
py -3.12 f:\rea\scripts\frida_shop_probe.py <PID>
```

## 15.7 重启后恢复
注入是运行时的，**每次重启游戏都要重跑 `frida_spawn_shop.py`**。
产物 `xmas_clone13` 常驻在 `F:\RF4\Game\rf4_x64_Data\Data\`，不会随重启消失。

## 15.8 后续可做
1. 把注入接进启动器，实现进游戏自动执行
2. 清理 `Data` 目录下的历史测试包（`xmas_*`、`lures_*`、`native_*` 等），只保留 `xmas_clone13`
3. 若要让两个摊位有真实的摊位模型交互（而非隐形代理），需要继续逆向 `Shop` 的 UI 打开入口

**两个坑**：
- 克隆**整个** `Sea_bait_shop_12` 模型会在空中生成大量红/蓝集装箱（必须只克隆 `_interact`）
- 多次注入会堆叠代理，清理正则必须覆盖 `CHRISTMAS|Sea_bait_shop_12.*\(Clone\)`，否则残留导致画面错乱

**脚本**：`f:\rea\scripts\frida_spawn_shop.py`

clone8 保留：GameObject/Transform/MeshFilter/MeshRenderer/LODGroup/Mesh/Material/Texture2D/Shader（4013 对象，221 MB 原版纹理）。

### 14.4 日志线索（clone6 闪退当次）
```
Shader 'Standard': fallback shader 'VertexLit' not found
Shader 'Nature/SpeedTree': fallback shader 'Transparent/Cutout/VertexLit' not found
Shader 'Nature/SpeedTree': dependency 'BillboardShader' shader 'Nature/SpeedTree Billboard' not found
Shader 'Standard (Specular setup)': fallback shader 'VertexLit' not found
```
说明打包的 shader 其 fallback PPtr 被置 0（fallback 在 `Library/unity default resources`，不在闭包内）。
**待验证**：闪退是否由 SpeedTree/粒子/骨骼引起，而非 shader 本身（clone8 也带 shader 却稳定 → shader 大概率不是主因）。

### 14.5 下一步：逐组加回
顺序（每次只加一组，注入后观察是否闪退）：
1. 粒子：`ParticleSystem` + `ParticleSystemRenderer`
2. SpeedTree：`Tree` + `TreeData` + `BillboardRenderer` + `BillboardAsset`
3. 骨骼动画：`SkinnedMeshRenderer` + `Animator` + `Avatar` + `Animation` + `AnimatorController`
4. 光照：`Light`
5. 碰撞体：`BoxCollider`/`CapsuleCollider`/`MeshCollider`/`Rigidbody`
6. 脚本：`MonoBehaviour`
7. 全量（= clone6）

注入脚本：`f:\rea\scripts\frida_spawn_ok.py`，包名/资源路径需与输出名一致；位置固定为 `V3(233.3600006, 2.6600001, 784.3599854)`、旋转用原版四元数。
同一进程内可连续注入不同包名，无需重启游戏。

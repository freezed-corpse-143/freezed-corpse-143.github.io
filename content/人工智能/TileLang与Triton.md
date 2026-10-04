# 先花三分钟建立直觉

Triton 和 TileLang 都不是"用 Python 写 CUDA"。它们是**两个站得高度不同的 kernel 编译器前端**：

```text
                    PyTorch / 训练框架
                           │
         ┌─────────────────┴──────────────────┐
         │                                    │
   图书馆路线                              编译器路线
   cuBLAS / cuDNN                     ┌───────┴────────┐
   （拿来就用，改不了）               │                │
                                    Triton           TileLang
                              （你描述"块"） （你描述"块 + 内存层级 + 流水线"）
                                      │                │
                                      └───────┬────────┘
                                              ▼
                                        CUDA C / PTX / cubin
                                              │
                                          NVIDIA GPU
```

**一句话对照：**

| 层次           | 编程单位                | 谁决定线程怎么映射 | 谁决定数据放哪                                         |
| :----------- | :------------------ | :-------- | :---------------------------------------------- |
| CUDA         | 线程（thread）          | 你         | 你（`__shared__`、寄存器变量）                           |
| **Triton**   | **逻辑块（block）**      | 编译器       | 编译器（有 `num_stages` 等旋钮）                         |
| **TileLang** | **tile（块）+ 显式内存层级** | 编译器       | **你显式声明 `T.alloc_shared` / `T.alloc_fragment`** |

这个"谁决定"三列表，就是这两份代码库 90% 的设计动机来源。Triton 的官方编程指南把这叫 blocked program vs. blocked threads——CUDA 是 **(scalar program, blocked threads)**，Triton 是 **(blocked program, scalar threads)**（`triton/docs/programming-guide/chapter-1/introduction.rst`）。TileLang 则在 README 与 `tilelang/docs/get_started/overview.md` 里把自己定义成"tile 级领域语言"：tile 是一等对象，内存位置由用户显式指定（`overview.md` 的 "Explicit Hardware Memory Allocation" 一节）。

再看一个务实的差别：**Triton 是"语言 + 编译器"，TileLang 是"语言 + 编译器 + 一套 tile 库 + 一次 pass 序列"**。前者希望你自己写循环和指针算术；后者希望你写 `T.copy(A[...], A_shared)` 和 `T.gemm(A_shared, B_shared, C_local)`，把 tiling / swizzle / 流水线 / barrier 交给编译器的 pass 去做。

# 统一框架

把"kernel 编译器"这层也拆成面，和拆推理框架一样：

```text
kernel 编译器栈
├─ 接入面：Python API / @jit 装饰器 / 显式 compile / AOT 工具 / CLI 二进制
├─ 前端语言层：DSL 构件（block、tile、指针、内存空间、循环原语）
├─ 前端降级面：Python AST → 前端 IR（TTIR / TIRX）
├─ 编译控制面：pass 流水线、布局推导、流水线规划、自动调优搜索
├─ 数据面：IR → 目标源码 → 机器码（CUDA/PTX/cubin，HIP/amdgcn/hsaco）
├─ 平台面：CUDA / HIP / Metal / CPU / WebGPU / Ascend
├─ 运行时面：kernel 句柄、launch、编译缓存、profiler、解释执行
└─ 产物面：cubin / hsaco、生成的 C/CUDA 源码、AOT 自包含宿主
```

这两个项目真正的根本区别，不是"支持哪些卡"，而是**把哪一层当自己的核心抽象**：

- **Triton：以"逻辑块 + 自动布局"为中心的 MLIR 编译器**（Python 只是前端皮肤，真正的设计在 `lib/Dialect/`）。
- **TileLang：以"tile 程序 + 显式内存层级 + 可读的 pass 序列"为中心的 TVM 派生编译器**（Python 侧就写完了整条 pass 流水线，是学习成本最低的观察窗口）。

## "编译期"不等于"无状态"

编译器里真正接近无状态的是：

```text
输出 = f(IR 模块，编译选项)     ← 纯函数，给定输入必得同样的 IR
```

例如：canonicalize、CSE、布局推导、向量化、unroll、codegen。这些 pass 一个个都是 `IRModule -> IRModule` 的纯变换。

但**编译"会话"必然有状态**：

| 状态 | Triton | TileLang |
| :--- | :--- | :--- |
| 编译常量表 | 参数特化 key（dtype/对齐/constexpr） | shape 与编译期参数 |
| 缓存状态 | `TRITON_CACHE_DIR` + `FileCacheManager` | `~/.tilelang/cache` 内核缓存 + CUDA 二进制缓存 |
| 后端句柄 | `Backend` / `DriverBase` 单例（entry point 发现） | `BackendModule` / `BackendContext` 注册表 |
| 目标状态 | `GPUTarget(backend, arch, warp_size)` | `Target`（`auto` 时探测 CUDA/HIP/Metal/Ascend） |
| 调优状态 | `Autotuner` 的 config 与最佳时间 | `autotune` 的 config 组与 benchmark 结果 |
| 运行时状态 | `CompiledKernel` + launcher（动态编译出的 host 侧 .so/.dll） | `JITKernel` + 执行后端（tvm_ffi / nvrtc / cython / cutedsl / torch / pto） |

所以判断标准是：**一个能力如果同时影响前端、pass、布局、缓存和运行时，它就是切面，别塞进某个单一"engine"类里理解。**

# 接入面

| | Triton | TileLang |
| :--- | :--- | :--- |
| 语言入口 | `import triton.language as tl`（`python/triton/language/__init__.py`） | `import tilelang.language as T`（`tilelang/language/__init__.py`，静态选 CUDA 方言） |
| JIT 装饰器 | `@triton.jit`（`python/triton/runtime/jit.py:968`） | `@tilelang.jit`（`tilelang/jit/__init__.py:588`）、`@T.prim_func` |
| 内核函数体 | 普通 Python + `tl.*` 原语 | 普通 Python + `T.*` 原语 |
| 启动方式 | `kernel[grid](args..., BLOCK=1024)`（`runtime/jit.py:733`） | `kernel(A, B, C)`（`tilelang/jit/kernel.py:206`） |
| 显式编译 | `triton.compile(src, target, options)`（`compiler/compiler.py:226`） | `tilelang.compile(...)`（`jit/__init__.py:94`）、`par_compile`（`:176`） |
| 离线 / AOT | `python/triton/tools/compile.py`（把 cubin 嵌进自包含 C 源码）、`tools/link.py` | `python -m tilelang.tools.compile_only`（默认 target 是 `c`，要显式 `--target cuda`） |
| CLI 二进制 | `bin/triton-opt`、`triton-lsp`、`triton-reduce`、`triton-tensor-layout` | 无独立二进制，只有 `python -m tilelang.tools.*` |

**重点：接入面不是编译器。** 你换掉 `@triton.jit` 的写法、换掉 launch 方式，编译器内部那套 IR 与 pass 完全不动。学习时先把"装饰器 → 前端降级"和"IR → 机器码"两段分开看。

两者都没有 HTTP/RPC 接入——它们是进程内库。这一点和推理框架完全不同：**没有"请求"这个概念，只有"编译"和"launch"两个动作。**

## 最小可运行示例（两边都实机跑过）

Triton，来自 `triton/python/tutorials/01-vector-add.py:26-72`：

```python
import torch, triton, triton.language as tl

@triton.jit
def add_kernel(x_ptr, y_ptr, output_ptr, n_elements, BLOCK_SIZE: tl.constexpr):
    pid = tl.program_id(axis=0)                 # 1D grid
    offsets = pid * BLOCK_SIZE + tl.arange(0, BLOCK_SIZE)
    mask = offsets < n_elements                 # 越界保护
    x = tl.load(x_ptr + offsets, mask=mask)
    y = tl.load(y_ptr + offsets, mask=mask)
    tl.store(output_ptr + offsets, x + y, mask=mask)

def add(x, y):
    out = torch.empty_like(x)
    n = out.numel()
    grid = lambda meta: (triton.cdiv(n, meta["BLOCK_SIZE"]),)
    add_kernel[grid](x, y, out, n, BLOCK_SIZE=1024)
    return out
```

注意三件事，它们定义了 Triton 的手感：

1. **没有 `threadIdx`**。`tl.arange(0, BLOCK_SIZE)` 是一个"块内元素编号"的张量，不是线程号。
2. **没有 `__shared__`**。`x`、`y` 是寄存器/片上存储里的块，放哪由编译器决定。
3. **`mask` 是你自己写的**。块大小和问题规模不整除是常态，边界由你负责。

TileLang，来自 `tilelang/examples/quickstart.py`（GEMM + 融合 ReLU）：

```python
import tilelang, tilelang.language as T

@tilelang.jit
def matmul_relu(A, B, block_M: int, block_N: int, block_K: int):
    M, N, K = T.const("M, N, K")
    A: T.Tensor((M, K), T.float16)
    B: T.Tensor((K, N), T.float16)
    C = T.empty((M, N), T.float16)

    with T.Kernel(T.ceildiv(N, block_N), T.ceildiv(M, block_M), threads=128) as (bx, by):
        A_shared = T.alloc_shared((block_M, block_K), T.float16)     # ← 显式放 shared
        B_shared = T.alloc_shared((block_K, block_N), T.float16)
        C_local  = T.alloc_fragment((block_M, block_N), T.float32)   # ← 显式放寄存器

        T.clear(C_local)
        for ko in T.Pipelined(T.ceildiv(K, block_K), num_stages=3):  # ← 显式要流水
            T.copy(A[by * block_M, ko * block_K], A_shared)
            T.copy(B[ko * block_K, bx * block_N], B_shared)
            T.gemm(A_shared, B_shared, C_local)                      # ← tile 级 GEMM

        for i, j in T.Parallel(block_M, block_N):
            C_local[i, j] = T.max(C_local[i, j], 0)                  # 融合 ReLU

        T.copy(C_local, C[by * block_M, bx * block_N])
    return C
```

手感对照：

| Triton 写法 | TileLang 对应物 | 差别 |
| :--- | :--- | :--- |
| `tl.arange` + 指针算术 | `T.Parallel(i, j)` / `T.copy(A[...], A_shared)` | TileLang 让你描述"搬哪一块"，不写索引表达式 |
| 无 shared 概念 | `T.alloc_shared` / `T.alloc_fragment` | TileLang 把内存层级提到语言层 |
| `num_stages` 编译选项 | `T.Pipelined(..., num_stages=3)` | TileLang 的流水线是**语言构造**，不是全局旋钮 |
| `tl.dot` | `T.gemm` | 语义相近，TileLang 分派到 CUTE/MMA/TCGEN5 等更多后端 |
| 手写 `mask` | `T.copy` 自动处理边界 | TileLang 的安全边界由 pass 补齐（`LegalizeSafeMemoryAccess`） |

# 前端语言层：Python 怎么变成 IR

这一层在推理框架里对应"模型工件与加载层"的位置——但这里没有文件要读，**"工件"就是你的 Python 函数**。

## Triton：AST 直接降级

```text
@triton.jit 的函数
  → code_generator.py 遍历 Python AST       （python/triton/compiler/code_generator.py）
  → TTIR                                     （ASTSource.ext = "ttir"，compiler/compiler.py:57）
```

`code_generator.py` 是 Triton 的前端：它不是"解释执行"你的函数，而是把 AST 里的每个节点（赋值、`for`、`if`、函数调用）翻译成 MLIR 操作。所以 Triton kernel 里能用什么 Python 语法是有明确边界的：能用的走 `tl.*` builtin，不能用的（比如随意的 `dict`、动态循环上界）会在降级期报错。

一个值得记住的设计：`tl.*` 里的每个原语都有个 `_semantic` 后端对象（`core.py:35` 的 `@builtin`、`:51` 的 `@_tensor_member_fn`），**同一套 API 同时驱动两套实现**——MLIR codegen 和 NumPy 解释器。这就是 `TRITON_INTERPRET=1` 能让你在没有 GPU（甚至没有编译）的情况下跑逻辑的原因（`runtime/interpreter.py:1665`）。

## TileLang：Python 构造 TVM IR

```text
@tilelang.jit / @T.prim_func 的函数
  → tilelang/language/ 里的构件记录成 TIRX（TVM 的 IR）
  → IRModule
```

TileLang 走的是 TVM 的老路：`T.Kernel(...)` 是一个"帧"（frame），`with` 块里的每条语句都在往当前 frame 里追加 IR 节点。看 `tilelang/language/kernel.py:155`（`KernelLaunchFrame` 类）和 `:431`（`Kernel` 工厂）就能明白它本质是一台 **IR 构造器**，不是解释器。

它同时保留了一条更接近 TVM 原味的写法：`@T.prim_func`（`tilelang/language/tir/entry.py:10`）。所以 TileLang 里有两套膜：

- **eager/装饰器风格**：`@T.prim_func` 里写 Python，构造 IR；
- **dialect 风格**：`T.*` 构件按目标方言（cuda/rocm/metal/cpu）静态选择（`tilelang/backend/README.md` 的 "Language Dialects" 段）。

## 语言构件并排表

| 语义 | Triton | TileLang |
| :--- | :--- | :--- |
| 块/网格索引 | `tl.program_id(axis)` `core.py:1826`、`tl.num_programs` `:1845` | `with T.Kernel(gx, gy, threads=128) as (bx, by)` `language/kernel.py:431` |
| 块内元素编号 | `tl.arange(start, end)` `core.py:1862` | `T.Parallel(m, n)` 双下标 `language/loop.py:13` |
| 显式内存空间 | 无 | `T.alloc_shared` `allocate.py:49`、`T.alloc_fragment` `:81`、`T.alloc_local` `:67`、`T.alloc_barrier` `:194`（需 sm_90+） |
| 搬运 | `tl.load` `core.py:2405` / `tl.store` `:2465` | `T.copy` `copy_op.py:59`、`T.fill`/`T.clear` `fill_op.py:11,48` |
| 矩阵乘 | `tl.dot` `core.py:2233` | `T.gemm` `gemm_op.py:160` |
| 流水线 | 编译选项 `num_stages` | `T.Pipelined(count, num_stages=k)` `loop.py:112` |
| 普通循环 | `for` / `tl.static_range` `:3610` / `tl.range` `:3650` | `T.serial` / `T.vectorized` / `T.unroll` `language/common.py:202-211` |
| 张量类型 | `block_type` `core.py:720`、`pointer_type` `:678`、`constexpr` `:221` | `T.Tensor(shape, dtype)`、`T.const` / `T.dynamic` `language/symbolics.py:13` |
| 描述符 | `tl.make_tensor_descriptor` `core.py:2527` | `T.tma_copy` / `T.copy`（TMA 由 `cuda` 方言提供） |
| 归约 | `tl.reduce` `:3017`、`tl.sum` | `T.reduce_*` `reduce_op.py`、`T.reduce_max` 等 |
| 原子 | `tl.atomic_add/max/cas` `:2594+` | `T.atomic_add` 等 `language/atomic.py` |

**注意一条已废弃的写法**：Triton 里 `tl.make_block_ptr` 现在直接抛错——"Block pointers have been removed. Use a tensor descriptor instead."（`core.py:2504-2507`）。网上 2024 年以前的 Triton 教程大量用 block pointer，照抄会失败。

# 编译控制面：IR 怎么一步步变成机器码

这是两个项目**最容易看出设计哲学差异**的一层。

## Triton：阶段字典 + MLIR PassManager

驱动在 `python/triton/compiler/compiler.py:226` 的 `compile()`：

```python
stages = dict()
backend.add_stages(stages, options, src.language)     # :291
first_stage = list(stages.keys()).index(src.ext)      # :292
for ext, compile_ir in list(stages.items())[first_stage:]:   # :326
    next_module = compile_ir(module, metadata)
    metadata_group[f"{file_name}.{ext}"] = fn_cache_manager.put(next_module, ...)
```

阶段字典由后端填。NVIDIA 后端在 `third_party/nvidia/backend/compiler.py:659-672`：

```text
ttir  → make_ttir    :286   前端降级：inliner / canonicalize / cse / loop_unroll / rewrite_tensor_descriptor
ttgir → make_ttgir   :302   布局与指令选择：add_convert_to_ttgpuir / coalesce / accelerate_matmul / pipeline
llir  → make_llir    :417   LLVM IR（dialect 转换完成，落到 LLVM 世界）
ptx   → make_ptx     :541   LLVM → PTX
cubin → make_cubin   :575   ptxas 汇编成二进制
```

AMD 后端同一套骨架换产物名：`ttir → ttgir → llir → amdgcn → hsaco`（`third_party/amd/backend/compiler.py:831-838`）。

IR 家族住在 C++ 侧：

```text
lib/Dialect/Triton/              前端 IR（ttir）
lib/Dialect/TritonGPU/           布局与 GPU 抽象（ttgir）
lib/Dialect/TritonNvidiaGPU/     NVIDIA 专属（TMA、TMEM、wgmma）
lib/Dialect/Gluon/               新的 block 级显式语言层
lib/Conversion/TritonToTritonGPU/    ttir → ttgir
lib/Conversion/TritonGPUToLLVM/      ttgir → llir
```

**理解要点：TTGIR 是 Triton 的"灵魂阶段"。**"块"这个抽象到 LLIR 就没了，剩下的全是线程级操作。你想知道 Triton 把你的 kernel 编译成了什么，就看 TTGIR——布局（layout）、coalesce、MMA 选择、软件流水线全在这里发生。

## TileLang：把 pass 序列直接写成 Python 列表

TileLang 的编译入口是 `tilelang/engine/lower.py:216` 的 `lower()`：

```text
lower(func_or_mod, target, ...)
  → create_backend_context()              解析唯一一个后端上下文（engine/lower.py:237）
  → lower_to_host_device_ir()             按 calling_conv 切成 host / device 两个 module
  → device_codegen() / host_codegen()     设备侧生成 CUDA/HIP/…，宿主侧生成 C/LLVM
```

真正的 pass 序列**逐行写在 Python 里**，按后端分文件。CUDA 的在 `tilelang/tilelang/cuda/pipeline.py`：

```text
CUDAPassPipelineBodyPrologue                                    :68 起
  MaterializeKernelLaunch → AnnotateDeviceBoundTmaCopies → LetInline
  → AddWrapperForSingleBufStore → LegalizeNegativeIndex → VerifyParallelLoop
  → InjectAssumes → Simplify → CanonicalizeLegacyReducer → VerifyReducerEpoch
  → VerifyBufferInit → [warp specialization] → LowerBlackwell2SM → IfStmtBinding
  → UnrollLoop → PipelinePlanning → InjectSoftwarePipeline → Simplify
  → LayoutInference                       ← 关键：推导 fragment/shared 布局
  → ReducerPlanAndMaterialize → LowerTileOp   ← 关键：tile 级算子降成低层算子
  → LowerL2Persistent → DecoupleTypeCast → LegalizeVectorizedLoop
  → LegalizeSafeMemoryAccess → LowerAccessPtr → Simplify → HoistNonRestrictParams

CUDAPassPipelineBody                                            :168 起
  LowerSharedTmem → PlanAndUpdateBufferAllocationLocation → LowerSharedBarrier
  → HoistGlobalBufferAllocations → LowerOpaqueBlock → Simplify → NarrowDataType(32)
  → FlattenBuffer → ConfigIndexBitwidth → VectorizeLoop → StorageRewrite
  → LoopUnswitching → UnrollLoop → LowerThreadAllreduce → LowerLDGSTG → LowerHopperIntrin
  → AnnotateDeviceRegions → SplitHostDevice          ← 关键：这一刻宿主/设备分离
  → MarkCudaSyncCalls → AnnotateReadOnlyParams
  → MergeSharedMemoryAllocations                      ← shared 内存复用
  → InjectFenceProxy → ThreadSync("shared") → ThreadSync("shared.dyn")
  → InjectTcgen05Fence → MergeIfStmt → [warp specialization 寄存器标注]
  → MakePackedAPI → Simplify → LowerDeviceKernelLaunch → PersistThreadblock
```

每个 pass 的 C++ 实现在 `tilelang/src/transform/`（`lower_tile_op.cc`、`inject_pipeline.cc`、`layout_inference/`、`pipeline_planning.cc`、`thread_storage_sync.cc`、`flatten_buffer.cc`、`make_packed_api.cc`…），Python 侧只是薄包装（`tilelang/tilelang/transform/__init__.py`）。

**这是 TileLang 给新手最大的礼物**：你不必先学会 MLIR 的 PassManager 才能知道编译器干了什么。把 `pipeline.py` 从上到下读一遍，就是完整的编译流程图；中间插一行 `print` 或者用 pass 可视化工具，就能看到 IR 的每一步变化。

## 并排对比

| | Triton | TileLang |
| :--- | :--- | :--- |
| 前端 IR | TTIR（自研 MLIR dialect） | TIRX（TVM 的 `PrimFunc` / `IRModule`） |
| pass 描述位置 | C++（`lib/` + `Passes.td`），Python 侧只注册阶段 | **Python**（`tilelang/<backend>/pipeline.py`） |
| pass 引擎 | MLIR PassManager | TVM Pass + 自定义 `PassPipeline` |
| 布局推导 | TTGIR 阶段由 `add_convert_to_ttgpuir` / `coalesce` / `remove_layout_conversions` 完成 | 独立 `LayoutInference` pass + `layout_cost_model` + swizzle |
| 流水线 | `num_stages` → pipeliner（TTGIR 阶段） | `T.Pipelined` → `PipelinePlanning` + `InjectSoftwarePipeline` |
| 宿主/设备分离 | 无此概念（Triton 只生成设备 kernel，宿主侧 launcher 由运行时动态编译 C 得到） | `SplitHostDevice` 显式切分，宿主侧走 C/LLVM codegen |
| 产物 | `cubin`（+ 可选 `.sass`） | 设备源码 → `cubin`；宿主模块 `CompiledArtifact`（带 `kernel_source`） |

# 平台适配应该拆成三层看

## 能力发现与策略选择

回答：当前是什么设备？支持哪些 dtype？选哪个后端？

- **Triton**：`triton.runtime.driver.active.get_current_target()` → `GPUTarget(backend='cuda', arch=86, warp_size=32)`。后端通过 entry point 组 `triton.backends` 发现（`python/triton/backends/__init__.py:42-62`，`TRITON_BACKENDS_IN_TREE=1` 可走树内快速路径），树内后端固定为 `nvidia` 与 `amd`（`setup.py:401`）。外部后端靠 `TRITON_PLUGIN_DIRS`（`setup.py:113-126`）。
- **TileLang**：`target="auto"` 按 CUDA → HIP → Metal 顺序探测（`tilelang/docs/get_started/targets.md:13-22`）；后端是 `BackendModule` 注册项（`tilelang/backend/module.py:29` 定义、`:238` 注册、`:310` 建上下文）。用户可见 target：`auto / cuda / cutedsl / hip / metal / llvm / webgpu / c`。

## 统一运行接口

回答：怎么分配 buffer、怎么提交计算、怎么同步？

- **Triton**：没有对用户暴露的"buffer 分配"接口。tensor 由 PyTorch 持有，Triton 只接指针；kernel 内块级变量由编译器分配寄存器/shared。launch 走 `CompiledKernel._init_handles`（`compiler/compiler.py:452`）造出来的 launcher，并在这里检查 shared memory 上限，超了直接抛 `OutOfResources`（`:468-474`）。
- **TileLang**：`T.alloc_shared` / `T.alloc_fragment` / `T.alloc_local` / `T.alloc_barrier` 是语言级接口；底层由 `MergeSharedMemoryAllocations`（`src/transform/merge_shared_memory_allocations.cc`）与 `StorageRewrite` 落地。

## kernel 与构建适配

| | Triton | TileLang |
| :--- | :--- | :--- |
| 设备代码生成 | LLVM → PTX → `ptxas` → cubin | 生成 CUDA/HIP C 源码 → `nvcc`/`hipcc` → cubin |
| 宿主代码 | 运行时用 `cc -shared -fPIC` 现编 launcher（`runtime/build.py:76`） | `host_codegen` 生成 C 或 LLVM（`engine/lower.py:65`） |
| 后端目录 | `third_party/{nvidia,amd,proton,f2reduce}` | `tilelang/{cuda,rocm,metal,cpu,webgpu,ascend}` + `src/{cuda,rocm,…}` |
| 模板库 | 无（全走 LLVM） | `src/tl_templates/{cuda,hip,cpu,ascend}`（`tcgen_05.h`、`copy_sm90.h`、`barrier.h`…） |
| 语言扩展 | `triton.language.extra.cuda.libdevice`（`third_party/nvidia/language/cuda/`） | 各方言的 `language/` 子模块 |

一个重要的对称观察：**Triton 把"宿主"这一侧推给了运行时（现编 C），TileLang 把宿主侧也纳入编译（`SplitHostDevice` + host codegen）。** 这也解释了为什么 Triton 的 Windows 适配这么难——见文末。

# 切面层

| 切面 | Triton | TileLang |
| :--- | :--- | :--- |
| **布局** | 编译器自动：`coalesce`、`remove_layout_conversions`、`optimize_thread_locality`（`third_party/nvidia/backend/compiler.py:314-325`） | `LayoutInference` pass + `tilelang/layout/swizzle.py` + `src/layout/`；可视化 `examples/plot_layout` |
| **流水线** | 编译期 `num_stages` → pipeliner；Hopper warp specialization | 语言级 `T.Pipelined` → `PipelinePlanning` + `InjectSoftwarePipeline`；自动 warp specialization |
| **内存治理** | shared memory 上限检查 + `set_allocator`（`runtime/_allocation.py`） | `MergeSharedMemoryAllocations`、`PlanAndUpdateBufferAllocationLocation`、`StorageRewrite` |
| **自动调优** | `@triton.autotune(configs, key=...)`（`runtime/autotuner.py:424`）、`Config`（`:343`，含 `num_warps/num_stages/num_ctas`）、`@triton.heuristics`（`:506`）；无 configs 时默认 `num_warps=4, num_stages=3`（`:33`） | `tilelang.autotune()`（`autotuner/tuner.py:1318`），支持并行编译 + 多 GPU benchmark |
| **缓存** | `TRITON_CACHE_DIR` → `FileCacheManager`（`runtime/cache.py:36`、`get_cache_manager` `:260`），key = `triton_key()` + 源码 hash | `~/.tilelang/cache`（`env.py:368`）、`kernel_cache.py`、`cuda_binary_cache.py`（跨主机 CUDA 二进制缓存） |
| **可观测性** | `TRITON_KERNEL_DUMP` / `TRITON_DUMP_DIR` / `TRITON_STORE_BINARY_ONLY`（`knobs.py:358-362`）；Proton profiler（`third_party/proton/`）；编译阶段计时 | `get_profiler().do_bench()`（`profiler/bench.py:31`，支持 event/cupti/cudagraph/wall/msprof）；pass 计时（`tools/pass_timing.py`） |
| **调试** | `TRITON_INTERPRET=1` → NumPy 解释执行（`runtime/interpreter.py:1665`）；`TRITON_DEBUG`；编译器崩溃可导出 MLIR reproducer，用 `triton-opt --run-reproducer` 复现（`triton/AGENTS.md:27`） | `T.print`；pass 可视化 `tools/pass_visualizer/`；IR 逐 pass 追踪 `tools/lower_trace/`；`utils/pass_diff.py`；AutoDD 自动插桩定位（`tilelang/autodd.py`） |
| **参数特化** | 按 dtype/对齐/constexpr 生成 specialization key（`runtime/jit.py:757`），自动缓存 | `@tilelang.jit` 按 shape 与编译期参数特化 |
| **异步编译** | `AsyncCompileMode` / `FutureKernel`（`python/triton/__init__.py:21`） | `par_compile`（`jit/__init__.py:176`）+ autotune 的 grouped_compile |
| **容错** | `CompilationError`（带 MLIR reproducer）；shared 超限 → `OutOfResources` | 编译期硬校验（如 `T.alloc_barrier` 在 sm_90 以下直接 `ValueError`，`cuda/pipeline.py:186-195`） |

判断标准（沿用在推理框架上用的那一条）：

> 如果一个能力同时影响前端语言、pass、布局、缓存和运行时，它通常是切面，别塞进单一类里理解。

# I/O 层

把这两者当"推理框架"来找 I/O 会扑空——它们**不读模型、不服务请求**。但把 I/O 分类后仍能看清瓶颈来源：

1. **调用协议 I/O**：两者都是进程内函数调用。Triton 用 `kernel[grid](...)`；TileLang 用 `kernel(args...)`。没有 HTTP，没有 JSON，没有 SSE。唯一的"序列化"是 AOT 产物（Triton 生成自包含 C 宿主，TileLang 生成 `kernel_source` + 宿主模块）。
2. **工件 I/O**：**没有**。它们不解析 safetensors/GGUF。权重由 PyTorch 加载成显存里的 tensor，kernel 只拿到指针。
3. **进程与节点 I/O**：**都没有集合通信层**（两个仓库里都找不到 nccl/进程组）。多卡依赖上层 `torch.distributed`，kernel 只按 launch grid 并行。这点和 vLLM/SGLang 是反面——**kernel 编译器不管分布式，分布式是推理框架的事**。
4. **内存与设备 I/O**：这块是真正的性能战场。层级是 `Host → Global(显存) → Shared/L2 → Register`。Triton 里 global↔register 的搬运由编译器调度；TileLang 里你必须显式写 `T.copy(global, shared)`，因此路径一眼可见。
5. **结果 I/O**：结果直接落回 PyTorch tensor，没有 detokenize/编码环节。

调试性能时的正确分类：

```text
算得慢            ← 指令数 / MMA 利用率 / 占用率
≠ 搬得慢          ← global↔shared 带宽、coalescing、swizzle
≠ 同步太少        ← 缺 barrier、race
≠ 同步太多        ← 过度 ThreadSync / 缺 num_stages
≠ launch 太多     ← grid 太细、没做 persistent kernel
≠ 编译太久        ← JIT 未命中缓存、autotune 搜索太宽
```

最后一条是 kernel 编译器独有的、推理框架没有的瓶颈类别：**编译时间本身是产品指标**。所以 Triton 有 `AsyncCompileMode`，TileLang 有 `par_compile` 和二进制缓存。

# 两个项目的核心差异

| 维度 | Triton | TileLang |
| :--- | :--- | :--- |
| 一句话定位 | 语言 + 编译器，让 Python 产出接近手写 CUDA 的 kernel | tile 级 DSL，在 TVM 之上快速写高性能 tile 内核 |
| 中心抽象 | 逻辑块（`tl.tensor`）+ 编译器自动布局 | tile 程序（`T.Kernel`）+ 显式内存层级 |
| 对照 CUDA | Blocked program / scalar threads | Tile 声明 + 显式 shared/register + 编译器推导 thread binding |
| 前端降级 | Python AST → TTIR | Python 构造 TIRX IRModule |
| IR 栈 | TTIR → TTGIR → LLIR → PTX → cubin | TIRX → 后端 pass 序列 → CUDA C / PTX → cubin |
| 编译器骨架 | 自有 MLIR dialect（Triton/TritonGPU/TritonNvidiaGPU/Gluon） | TVM（fork 的 `3rdparty/tvm`）+ 自定义 pass |
| pass 写在哪 | C++，`Passes.td` 声明 + `lib/` 实现 | **Python**，`tilelang/<backend>/pipeline.py` 逐行写出 |
| 内存层级 | 隐式（编译器决定） | 显式（`alloc_shared/fragment/local/barrier`） |
| 流水线 | 编译选项 `num_stages` | 语言构造 `T.Pipelined` |
| 后端注册 | entry point `triton.backends` + `TRITON_PLUGIN_DIRS` | `register_backend` + `BackendModule` 注册表 |
| 树内后端 | nvidia、amd | cuda、rocm、metal、cpu、webgpu、ascend |
| GEMM 实现路径 | `tl.dot` → `accelerate_matmul` → MMA | `T.gemm` → cute / MMA / TCGEN5 / MFMA / WMMA / Cube 分派 |
| 宿主侧 | 运行时现编 C launcher（POSIX `cc`） | 编译期 `SplitHostDevice` + host codegen |
| 执行后端 | 自研 launcher（dlopen cubin） | 可插拔：tvm_ffi / nvrtc / cython / cutedsl / torch / pto |
| 调试入口 | `TRITON_INTERPRET=1`（NumPy）、IR dump、MLIR reproducer | pass 可视化、lower trace、pass diff、`do_bench` |
| 官方平台 | **仅 Linux**（README:294-300；驱动层硬编码 `libcuda.so.1` + `ldconfig`） | Linux / Windows / macOS 都有预编译 wheel |
| 最值得学习 | 从语言到硬件指令的完整 MLIR 降级链；"块"抽象如何消失 | 一条可读的 tile 编译流水线；layout inference 与 tile op 降级 |

# 各自的核心技术

## Triton

1. **块级编程模型**：程序以 block 为单位，`tl.tensor` 是唯一的数据结构（`language/core.py:871`）。
2. **AST 直接降级**：`code_generator.py` 把 Python AST 翻成 TTIR，不做解释执行。
3. **多级 IR**：TTIR（前端）→ TTGIR（布局与指令选择）→ LLIR → PTX/cubin；TTGIR 是灵魂阶段。
4. **`_semantic` 双后端**：同一套 `tl.*` 同时驱动 MLIR codegen 和 NumPy 解释器，`TRITON_INTERPRET=1` 因此可行。
5. **自动布局与合并**：`coalesce` / `remove_layout_conversions` / `optimize_thread_locality`，用户完全不用管 layout。
6. **张量核自动接入**：`accelerate_matmul` + `min_dot_size` 约束决定 MMA 形状。
7. **软件流水线**：`num_stages` 驱动的 `assign_latencies` / `schedule_loops` / `pipeline`。
8. **Hopper/Blackwell 专属路径**：warp specialization、TMA tensor descriptor、Blackwell TMEM 的 promote/hoist/remove。
9. **参数自动特化 + 磁盘缓存**：按 dtype/对齐/constexpr 生成 key，命中即跳过编译。
10. **可插拔后端**：entry point 发现 `BaseBackend` / `DriverBase` 对。
11. **AOT 与跨语言嵌入**：把 cubin 嵌进自包含 C 源码，脱离 Python 也能调。
12. **解释器调试**：纯 NumPy 语义，先验逻辑再上 GPU。

## TileLang

1. **tile 级 launch 抽象**：`T.Kernel` 目标中立（CUDA 上是 `blockIdx`，CPU 上是外层循环），线程映射交给编译器。
2. **显式内存层级**：`alloc_shared` / `alloc_fragment` / `alloc_local` / `alloc_barrier` 直接映射 shared / 寄存器 / mbarrier。
3. **Layout Inference + swizzle**：编译期为 fragment 与 shared 推导布局，另有 cost model 与可视化工具。
4. **软件流水线**：`T.Pipelined(num_stages=)` 触发 `PipelinePlanning` + `InjectSoftwarePipeline`。
5. **`T.gemm` 多后端分派**：同一原语降到 cute / MMA / TCGEN5 / MFMA / WMMA / Cube。
6. **`T.copy` 作用域感知搬运 + TMA**：自动选路径（普通 load/store、cp.async、TMA），并补齐安全边界。
7. **后端注册表与垂直切片**：一个 target 后端拥有自己的 dialect + pipeline + codegen。
8. **可插拔执行后端**：tvm_ffi / nvrtc / cython / cutedsl / torch / pto，同一份 IR 换运行方式。
9. **双层缓存**：内核缓存 + 跨主机 CUDA 二进制缓存。
10. **Autotune**：config 组搜索、并行编译、多 GPU benchmark。
11. **自动 warp specialization**：`AutoWarpSpecialization` / `ProducerConsumerWarpSpecialized`。
12. **可读的 pass 流水线 + 调试工具链**：pass 可视化、IR lower trace、pass diff、AutoDD、z3 驱动的 `Simplify` / `InjectAssumes`。

# 并行学习方法

学这两个项目最省力的方式是**把问题横切，而不是把仓库横着读完**。下面每一节都是一个可以独立完成的观察任务，两个项目各做一遍，然后对照。

## 追踪一个最小 kernel

同一个问题：**从 Python 函数到 GPU 上跑的机器码，中间经过哪些人？**

Triton：

1. `@triton.jit` 包成 `JITFunction`（`runtime/jit.py:635`）。
2. 第一次 `kernel[grid](...)` 时算 specialization key（`:759`），未命中就 `_do_compile`（`:770`）。
3. `triton.compile` 走阶段字典（`compiler/compiler.py:291,326`）。
4. `CompiledKernel` 造 launcher（`:452`），之后每次 launch 直接调它（`:783-788`）。

TileLang：

1. `@tilelang.jit` 返回 `JITImpl`（`jit/__init__.py:270`）。
2. 函数体执行时构造 TIRX IRModule。
3. `lower()`（`engine/lower.py:216`）解析后端上下文并跑 `pipeline.py` 里的 pass 序列。
4. `device_codegen` 产出 CUDA 源码 → `nvcc` → cubin；`JITKernel.__call__`（`jit/kernel.py:206`）负责 launch。

**记录格式**（做完一次就懂了）：

```text
外部调用在哪进入？ → 函数什么时候被"降级"？ → 中间 IR 长什么样？
→ 谁决定下一次变换？ → 谁调 nvcc/ptxas？ → 结果怎么回到 tensor？
```

## 只研究布局

同一个问题：**一个 fp16 GEMM，A 的 tile 该放在哪、按什么顺序，谁说了算？**

- Triton：写一个 `03-matrix-multiplication.py` 风格的 kernel，dump TTGIR，看 `#ttg.blocked` / `#ttg.dot_op` / `#ttg.shared` 三种 layout 在 `tl.dot` 前后怎么传播，`convert_layout` 出现在哪。
- TileLang：给 `examples/gemm/example_gemm.py` 加 `T.annotate_layout`，或者用 `examples/plot_layout` + `tools/pass_visualizer` 看 `LayoutInference` 前后的 IR 差异。

对照点：Triton 的 layout 是**编译器推出来的不变量**；TileLang 的 layout 是**可以被用户指定的自由变量**。这就是"Blocked Program"和"Tile DSL"在实现上的分水岭。

## 只 dump IR

- Triton：`TRITON_ALWAYS_COMPILE=1 TRITON_KERNEL_DUMP=1 TRITON_DUMP_DIR=./dump python your_kernel.py`，然后按 `*.ttir / *.ttgir / *.llir / *.ptx` 逐个看。
- TileLang：打开 pass 可视化（`tilelang/tools/pass_visualizer/`），或者 `tools/lower_trace/` 逐 pass 追踪，或者 `utils/pass_diff.py` 对比两个 pass 之间的变化。

这是整个学习方法里**性价比最高的一步**：一次 dump 胜过读十遍源码。

## 只研究内存层级

- Triton：`tl.load(..., cache_modifier=".cg")`（`core.py:2427-2432`）这类旋钮，加上编译器自动插入的 shared 使用。**问：我能不能强制某块数据进 shared？**（答案：不能直接说，只能让布局推导帮你决定。）
- TileLang：`T.alloc_shared` / `T.alloc_fragment` 的区别，`MergeSharedMemoryAllocations` 怎么复用 buffer，`PlanAndUpdateBufferAllocationLocation` 把分配点挪到哪。

## 只研究流水线

同一个问题：**`num_stages=3` 到底做了什么？**

- Triton：在 TTGIR 里看 `ttg.async_copy` / `ttg.cp_async_commit_group` / `ttg.wait_group` 怎么被插入。
- TileLang：看 `InjectSoftwarePipeline` 改变 IR 前后的差异；`T.Pipelined` 的 `num_stages` 与 `order/stage/group` 参数。

## 只研究自动调优

- Triton：`@triton.autotune` 的 `key` 决定"什么时候重新调"，`Config` 决定"调什么"。写一个 `num_warps ∈ {4,8}`、`BLOCK_SIZE ∈ {512,1024,2048}` 的搜索，看它怎么选。
- TileLang：`tilelang.autotune` 的 grouped/parallel compile —— 注意它把**编译时间**也当成本优化。

## 只研究一个后端

挑一个非主流后端，看"平台适配三件事"分别落在哪：

```text
能力发现 → 后端选择 → 代码生成 → 运行时
```

- Triton：读 `third_party/amd/backend/compiler.py` 的 `add_stages`（`:831-838`）和 HIP 的 driver。
- TileLang：读 `tilelang/metal/backend.py` 或 `tilelang/cpu/backend.py`，对照 `cuda/backend.py`，看 `BackendModule` 要求你填哪几个字段。**能读懂新增一个后端要写什么，说明你理解了 TileLang 的架构。**

## 只研究扩展点

- Triton 加一个后端：`third_party/<name>/backend/{compiler.py,driver.py}` + entry point（`setup.py:74-101,548`）。
- TileLang 加一个后端：`register_backend` + 一份 `pipeline.py` + codegen（`tilelang/backend/README.md`）。

两者都设计成"语法/IR 稳定，后端可换"。这是编译器类项目的通用架构选择，值得单独记住。

## 30 分钟上手路径（新手版）

```text
0-5   min  改 BLOCK_SIZE 跑 vector-add，理解 mask 为什么必须自己写
5-10  min  改 num_warps / num_stages，看耗时变化
10-15 min  把 vector-add 改成 tilelang 版，感受 T.Parallel 的写法差异
15-25 min  跑通 quickstart GEMM（两边各一份），对着 torch 参考值验证
25-30 min  dump 一次 IR，找出"块/tile 抽象消失的那一刻"
```

# 本机怎么跑起来（Windows + RTX 3080，已实测）

## 环境事实

| 项 | 值 |
| :--- | :--- |
| GPU | NVIDIA GeForce RTX 3080 Laptop GPU，16 GB，compute capability **8.6** |
| 驱动 | 610.62 |
| CUDA Toolkit | 13.3（`nvcc` 在 PATH 上） |
| Python | 3.14.5（`C:\Users\y86133\AppData\Local\Python\pythoncore-3.14-64`） |
| PyTorch | 2.13.0+cu130 |
| 本地源码 | `C:/Projects/triton`（HEAD `6fe3348e6e`，`__version__ = 3.9.0`）<br>`C:/Projects/tilelang`（HEAD `d82101ff`，`VERSION = 0.1.15`） |

**默认都未安装**（`pip list` 里既没有 `triton` 也没有 `tilelang`）。在 `C:/Projects` 下 `import triton` 会成功，但那是因为同名目录被当成了命名空间包（`__file__` 为 `None`），不是真装上了。

## 两条命令

两个包都装进隔离的 venv，并复用系统里已有的 CUDA 版 PyTorch：

```powershell
# 关键：venv 必须基于"有 CUDA torch 的那个解释器"
& "$env:LOCALAPPDATA\Python\pythoncore-3.14-64\python.exe" -m venv --system-site-packages C:/Projects/Temp/.venv-tl2
uv pip install --python C:/Projects/Temp/.venv-tl2 tilelang
uv pip uninstall --python C:/Projects/Temp/.venv-tl2 torch     # ← 见下面的坑 2

& "$env:LOCALAPPDATA\Python\pythoncore-3.14-64\python.exe" -m venv --system-site-packages C:/Projects/Temp/.venv-tr2
uv pip install --python C:/Projects/Temp/.venv-tr2 triton-windows
```

Triton 在 Windows 上要用社区移植版 `triton-windows`（PyPI，本文写作时是 `3.8.0.post29`，周下载量 ~91K），官方仓库只支持 Linux。

## 两个必须知道的坑

**坑 1：`pip install tilelang` 在 Windows 会顺带装一个 CPU 版 torch。**

uv/pip 解析 `torch`（无版本约束）时从默认索引拿到的是 `+cpu` 构建，它会**盖住**你已有的 `2.13.0+cu130`。表现是 `torch.cuda.is_available()` 变成 `False`。装完 `pip uninstall torch` 让系统那份 CUDA torch 生效即可（前提是 venv 用了 `--system-site-packages`）；或者一开始就用 PyTorch 的 CUDA 索引显式装 torch。

**坑 2：如果你 PATH 上有 `clang-cl.exe`，tilelang 会选中它当 nvcc 的宿主编译器，然后编译失败。**

报错长这样：

```text
nvcc fatal   : Host compiler targets unsupported OS.
Command: ...\nvcc -ccbin=...\clang+llvm-23.1.1-x86_64-pc-windows-msvc\bin\clang-cl.exe --cubin -O3 ...
```

原因是 `tilelang/contrib/msvc.py:91-104`：`_resolve_windows_compiler` 默认优先找 `clang-cl`，找不到才退回 `cl.exe`。修法就是那个开关（`msvc.py:26-28`）：

```powershell
$env:TILELANG_DISABLE_CLANG_CL = "1"
```

设了之后 tilelang 会去找 `cl.exe`（必要时自己调 `VsDevCmd.bat`），实测正常编译。

## 实测结果

```text
tilelang 0.1.15 + torch 2.13.0+cu130 + sm_86
  GEMM+ReLU (M=N=K=1024, block 128/128/32, T.Pipelined num_stages=3)
  → 与 torch.relu(a @ b) 一致（rtol/atol 1e-2）
  → target = {"kind":"cuda", "arch":"sm_86", "max_num_threads":1024, "thread_warp_size":32}
  → 生成 CUDA 源码 148 行，do_bench ≈ 0.663 ms

triton-windows 3.8.0 + torch 2.13.0+cu130 + sm_86
  vector-add (n=98432, BLOCK_SIZE=1024)
  → 与 torch 参考一致
  → GPUTarget(backend='cuda', arch=86, warp_size=32)
```

一次编译大约 6 秒（tilelang GEMM，含 nvcc），首次运行会明显慢——那是编译时间，不是 kernel 时间。`do_bench` 报的才是 kernel 时间。

验证脚本留在 `C:/Projects/Temp/_tilelang_smoke.py` 与 `C:/Projects/Temp/_triton_smoke.py`，venv 留在 `C:/Projects/Temp/.venv-tl2`、`.venv-tr2`。

## 相关限制（RTX 3080 = sm_86）

- `T.alloc_barrier()` 需要 sm_90（Hopper）及以上，在 sm_86 上编译期直接抛 `ValueError`（`tilelang/cuda/pipeline.py:186-195`）。
- TMA / WGMMA / Blackwell TMEM 相关的路径在 sm_86 上不可用；`T.gemm` 会落到普通 MMA。
- Triton 官方要求 compute capability ≥ 8.0，sm_86 在范围内。
- `triton-windows` 的版本（3.8.x）落后本地源码（3.9.0）。要对着源码读，两者会有细节出入——**以本地源码为准，以 pip 版为运行环境**。

# 最终的认知

kernel 编译器本质上解决三个问题：

1. **语义正确性**：正确地把 Python 语义翻译成 IR，再翻译成机器语义，边界/同步/内存复用都成立。
2. **硬件映射**：把语言层写的"块"和"tile"，映射到真实的 warp、shared memory、MMA、TMA 上。
3. **时间优化**：减少空转、减少搬运、让搬运和计算重叠、减少编译时间。

两个项目分别提供两个最佳观察窗口：

```text
Triton
  → 看"一个块级语言如何被一步步降解成线程级指令"
  → 看 TTGIR 阶段：抽象消失、布局诞生

TileLang
  → 看"一条 tile 编译流水线长什么样"
  → 看 LayoutInference 与 LowerTileOp：tile 算子如何落到真实硬件原语
```

最值得坚持的元学习问题（和推理框架那条是同一个）：

> 它管理什么状态、作出什么决策、消耗什么资源、把什么不稳定性隔离在了哪一层。

用到这两个项目上，具体化成一串可以随时自问的问题：

- **这个 pass 改变了 IR 的哪个不变量？**（布局？内存空间？线程绑定？）
- **这个抽象在哪一步消失？**（Triton 的 block 在 TTGIR→LLIR 消失；TileLang 的 tile 在 `LowerTileOp` 消失）
- **这一步是谁决定的？**（用户显式声明，还是编译器推导？——这是 Triton 与 TileLang 全部分歧的源头）
- **慢了是算得慢、搬得慢、同步错了，还是编译慢？**

---

参考：`C:/Projects/triton`、`C:/Projects/tilelang`、`C:/Projects/jojo-blog/content/人工智能/推理框架.md`、`C:/Projects/jojo-blog/content/人工智能/TVM.md`

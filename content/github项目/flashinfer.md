# 基础定位

可以把它理解成：**专门为 LLM 推理/Serving 提供高性能 GPU 算子的基础设施库**。

如果你最近在理解 CUDA Graph、算子融合、TVM，那么 FlashInfer 正好处在这条技术栈里，而且比 TVM 更贴近 **LLM inference 这个具体场景**。官方现在把自己定义为 “High-Performance GPU Kernels for Inference”，提供 Attention、GEMM、MoE 等统一接口，并在底层接入 FlashAttention、CUTLASS、cuDNN、TensorRT-LLM 等实现。[GitHub](https://github.com/flashinfer-ai/flashinfer)

## 放到整个 LLM 推理栈里看

大致可以画成：

```
            LLM 应用 / API
                  │
                  ▼
        vLLM / SGLang / TensorRT-LLM
           「推理 Serving Engine」
                  │
                  ▼
              FlashInfer
        「高性能 GPU 算子层」
                  │
        ┌─────────┼──────────┐
        ▼         ▼          ▼
    Attention    GEMM        MoE
    Sampling     RoPE       RMSNorm
        │
        ▼
 CUDA / CUTLASS / cuDNN / Tensor Core
        │
        ▼
      NVIDIA GPU
```

所以它**不是一个完整的 LLM Serving 系统**。你不会主要拿 FlashInfer 来做 HTTP API、请求队列、模型调度这些事情。

它解决的是更底层的问题：

> **“推理引擎已经决定下一步要计算 Attention / GEMM / MoE 了，怎么让这个计算在 GPU 上尽可能快？”**

这和你之前问的“算子融合为什么能加速”直接联系起来。

## FlashInfer 具体负责什么？

目前它覆盖的东西已经非常广。[GitHub](https://github.com/flashinfer-ai/flashinfer)

| 类别                   | FlashInfer 提供                       |
| -------------------- | ----------------------------------- |
| Attention            | Prefill / Decode Attention          |
| KV Cache             | Paged / Ragged KV Cache             |
| Attention 算法         | FlashAttention 2/3、Sparse Attention |
| DeepSeek             | MLA Attention                       |
| GEMM                 | BF 16 / FP 8 / FP 4 GEMM            |
| MoE                  | Fused MoE、Top-K routing             |
| Sampling             | Top-K / Top-P / Min-P               |
| Speculative decoding | speculative sampling                |
| Normalization        | RMSNorm / LayerNorm                 |
| Activation           | SiLU / GELU / fused gating          |
| Position encoding    | RoPE                                |
| 通信                   | AllReduce / NVSHMEM                 |

例如普通 Transformer decode 的一次 token：

```
输入 token
   │
   ▼
Embedding
   │
   ▼
RMSNorm       ← FlashInfer kernel
   │
   ▼
QKV GEMM      ← FlashInfer / CUTLASS
   │
   ▼
RoPE          ← FlashInfer kernel
   │
   ▼
Paged Attention
   ↑
KV Cache      ← FlashInfer 的核心强项
   │
   ▼
Output GEMM
   │
   ▼
MoE           ← fused MoE kernels
   │
   ▼
Sampling      ← FlashInfer sampling kernel
   │
   ▼
下一个 token
```

它尤其关注 **prefill 和 decode 的实际 serving workload**，而不只是写一个理论上很快的矩阵乘法。官方也明确把 optimized prefill、decode 和 mixed batching 作为核心能力。[GitHub](https://github.com/flashinfer-ai/flashinfer)

## FlashInfer 出现的原因（为什么不能直接全部用 Pytorch）

比如你写：

```
scores = q @ k.Tscores = scores / sqrt(d)scores = softmax(scores)output = scores @ v
```

逻辑上完全正确。

但真正做 LLM serving 时，你还会遇到：

```
不同请求长度不同
       ↓
KV Cache 长度不同
       ↓
Paged KV Cache
       ↓
continuous batching
       ↓
prefill / decode 混合
       ↓
GQA / MQA / MLA
       ↓
FP8 / FP4
       ↓
CUDA Graph
```

于是“调用几个 PyTorch op”很容易产生大量 kernel launch、HBM 数据搬运、中间 Tensor，以及不适合 decode workload 的 GPU occupancy。

FlashInfer 做的事情就是把这些模式变成**针对 LLM serving 特化的 GPU kernel**。

例如官方的 sampling API 直接提供 fused GPU sampling kernel：

```
logits
   │
   ├─ softmax
   ├─ top-k
   ├─ top-p
   └─ sampling
        ↓
      token
```

而不是让上层框架自己拼一串 GPU operation。[FlashInfer](https://docs.flashinfer.ai/api/sampling.html?utm_source=chatgpt.com)

## 与 FlashAttention 的关系

这两个非常容易混淆。

**FlashAttention 更像一个著名的高效 Attention 算法/Kernel 家族；FlashInfer 更像面向整个 LLM inference 的 Kernel Library。**

所以：

```
FlashAttention
      │
      │ Attention 计算优化
      ▼
 ┌────────────────────────────┐
 │         FlashInfer         │
 │                            │
 │ Attention                  │
 │ ├─ FlashAttention 2/3      │
 │ ├─ Paged Attention         │
 │ ├─ Sparse Attention        │
 │ └─ MLA                     │
 │                            │
 │ GEMM / MoE / Sampling      │
 │ RoPE / RMSNorm / AllReduce │
 └────────────────────────────┘
```

官方当前接口实际上可以在 FlashAttention-2/3、cuDNN、CUTLASS、TensorRT-LLM 等 backend 之间选择。[GitHub](https://github.com/flashinfer-ai/flashinfer)

## 与 TVM 的关系

这个区别更重要。

你可以粗略理解成：

```
TVM
│
├─ 通用编译器
├─ Graph / Tensor IR
├─ Schedule
├─ Code Generation
└─ CPU / GPU / 各种 accelerator


FlashInfer
│
├─ 专注 LLM inference
├─ Attention
├─ KV Cache
├─ GEMM
├─ MoE
├─ Sampling
└─ NVIDIA GPU 高性能 Kernel
```

也就是说，**TVM 更像“如何自动生成/优化计算程序”的编译器基础设施；FlashInfer 更像“LLM inference 中这些最重要的算子，我直接给你高度优化好的实现和调度框架”。**

FlashInfer 现在甚至会根据模型架构、精度、GPU 世代和 serving workload 选择不同 kernel 配置；2026 年 9 月的 v 0.7 更新还进一步强化了 kernel selection/autotuning。[FlashInfer](https://flashinfer.ai/2026/09/22/flashinfer-v07.html?utm_source=chatgpt.com)

## 在 LLM 推理系统体系中的位置

```
算法
FlashAttention / PagedAttention / MLA
            ↓
Kernel
CUDA / Triton / CUTLASS
            ↓
LLM Kernel Library
FlashInfer
            ↓
Serving Engine
vLLM / SGLang / TensorRT-LLM
            ↓
系统级优化
Continuous Batching
Prefix Caching
Speculative Decoding
CUDA Graph
Disaggregated Prefill/Decode
```

**FlashInfer 正好是连接“CUDA Kernel 优化”和“LLM Serving 系统”的那一层。**

---

# 补充：从“知道它在哪”到“能用它、改它”

上面七个章节回答的是**定位**：它是什么、在栈的哪一层、为什么出现、和谁是什么关系。这部分回答剩下的三个问题：

```text
它由什么构成    （内容）
怎么用它        （使用）
怎么维护和优化它（演进）
```

三条都对着本地仓库 `C:/Projects/flashinfer`（v0.7.1，HEAD `ac30abf`）核实过。

## 边界：定位的产物，不是独立的一问

原文有痛点，但没写边界。

先立一条原则：

> **边界不是“再查一遍”，而是“关系的补集”。每一条关系都划出一条边界。**
> **定位做完，边界自动落地；定位没做，边界只能靠猜。**

所以问“它的边界在哪”时，不要另起一个问题清单，而是回到四种关系上逐条问：

| 关系 | 划出的边界 | 取证方式 | FlashInfer 的答案 |
| --- | --- | --- | --- |
| **上游依赖** | 能力边界（哪些必须自己做） | 依赖清单 + 核心能力能否由上游直接提供 | 自己写 kernel，同时把 attention 实现当可换 backend（FA-2/3、cuDNN、CUTLASS、TensorRT-LLM） |
| **上游约束** | 设备与环境边界 | 官方支持矩阵 + 环境类异常 | SM 7.5–12.1，且“not all features across all compute capabilities”；异常体系里有 `GPUArchitectureError` / `BackendSupportedError` |
| **下游契约** | 职责边界 | 看下游怎么用它 + 官方兼容承诺 | 不做 HTTP / 队列 / 调度；保证两个 minor 版本的 API 兼容 |
| **横向竞品** | 能力边界（相对） | 竞品对照表 | 与 FlashAttention 是包含关系，与 TVM 是分层关系 |
| **历史** | 兼容边界 | deprecation 记录 | 废弃 API 保留两个 minor 版本 |

### 场景边界：最实用的一种

用反推法——**痛点在什么条件下才发作，反例就是它的边界**：

| 触发条件 | 反例（不需要 FlashInfer） |
| --- | --- |
| 请求长度不一 + KV Cache 分页 | 离线批处理、定长输入 |
| continuous batching、prefill/decode 混合 | 单请求、纯 prefill |
| decode 阶段每请求只算 1 个 token，GPU occupancy 极低 | compute-bound 的 prefill 主导负载 |
| 需要 softmax/top-k/top-p/min-p 融合采样 | 贪心解码 |
| 要压掉 kernel launch 数量与中间 tensor | 模型小、launch 开销占比低 |

→ **适用边界 = serving 场景**。离线、定长、单请求时，它的复杂度收益显著下降。

### 设备与环境边界

机器边界不能只看支持矩阵（README 的 GPU Support 表本身带一句警告）：

```text
支持 SM 7.5 (Turing) 到 SM 12.1 (Blackwell)
但 README 明确写着：Not all features are supported across all compute capabilities
```

也就是：**“支持这个 GPU” ≠ “这个 GPU 上所有 kernel 都能用”**。选 kernel 前要先确认算力等级。

### 六种边界：一份可复用清单

把上面散落的边界归成六类，下次分析任何项目都按这个清单过一遍：

| # | 边界 | 问题 | 主要来源 |
| --- | --- | --- | --- |
| 1 | **能力边界** | 它能做什么、明确不做什么 | 上游依赖 + 横向竞品 |
| 2 | **职责边界** | 它该做什么（不由它做的是什么） | 下游契约 |
| 3 | **场景边界** | 在什么负载形态下才划算 | 痛点结构 |
| 4 | **设备与环境边界** | 能在什么硬件/软件上跑，哪些特性受限 | 平台矩阵 |
| 5 | **性能边界** | 多大规模才值得用它（小规模时反而更慢） | 开销结构（编译/launch/dispatch） |
| 6 | **兼容边界** | 什么不能改、要等几个版本 | 历史 + 下游契约 |

**第 5 条最容易被忽略**：FlashInfer 首次使用要编译/下载 kernel，规模太小时**编译开销压过收益**。这就是为什么它要单独发 `flashinfer-cubin` / `flashinfer-jit-cache`——那些包的存在本身就是“性能边界”的工程化对策。

**边界最有价值的形式是“什么时候不要用它”**，因为它直接指导决策；“它擅长什么”只是宣传。

## 边界从哪里看：内侧声明 vs 外侧证据

这是本补充里最值得抄走的一段。

```text
从内侧看（它自己说的）：
  README 的限制说明、docs 的 caveat、异常类型
  → 有营销偏差。作者会弱化限制、强调能力

从外侧看（关系推出来的）：
  下游框架自己补了什么、包了什么、搬了什么
  → 没有偏差。下游的工程量是诚实的
```

### 一条强启发式

> **下游自己写的那一层，就是上游的边界。**
> 下游写得越厚、分得越细、越需要 vendored 代码，说明上游的边界越硬。

### 用 SGLang 验证这条启发式

SGLang 是 FlashInfer 的下游之一（README 的 Adoption 列表第一位）。在本地仓库 `C:/Projects/sglang` 里数一下：

```text
python/sglang/srt/ 下引用 flashinfer 的文件数：196
```

再看这些文件长什么样——**四类证据，各自指向一种边界**：

| 观察 | 指向哪种边界 |
| --- | --- |
| 每个领域一个适配文件：`layers/attention/flashinfer_backend.py`、`flashinfer_mla_backend.py`、`layers/moe/token_dispatcher/flashinfer.py`、`flashinfer_comm_fusion.py` … | **能力边界**：FlashInfer 的“统一 API”统一在**接口层**，实现层是分叉的（GQA / MLA / MoE / 通信各一套），下游必须自己选型 |
| MoE 有**三个**并列 runner：`moe_runner/flashinfer_{cutedsl,cutlass,trtllm}.py` | **能力边界**（更硬）：同一个功能有多条实现路线并存，选哪条由下游决定，不由 FlashInfer 决定 |
| `model_executor/runner/flashinfer_autotune.py` 在 **SGLang 里**，不在 FlashInfer 里 | **职责边界**：FlashInfer 提供调优**设施**，调优的**触发时机与策略**归框架。谁能决定“什么时候值得花时间去 tune”，谁才掌握调度权 |
| `python/sglang/kernels/ops/moe/trtllm_lora_temp/data/include/flashinfer/`（含 `trtllm/`、`fused_moe/`、`DevKernel.h`、`runner.h`）——把 FlashInfer 的头文件**搬进自己仓库** | **兼容边界被打破**：下游不得不 fork/vendor 一部分上游源码，说明那里是硬边界（上游不肯为这个场景改动，或改动的节奏跟不上） |
| 一大批 `srt/arg_groups/*_hook.py`（`attention_hook` / `cuda_graph_hook` / `kv_cache_hook` / `mamba_hook` …） | **配置边界**：参数空间由下游组织。上游暴露的是旋钮，下游决定这些旋钮怎么被用户的命令行映射 |

**结论**：FlashInfer 的边界不是从它的 README 里读出来的，而是从 SGLang 的 196 个文件里**数出来的**。

这条启发式还能反向用：

```text
下游很薄、只 import 几个符号   → 上游边界清晰、API 收敛
下游很厚、每个领域一个适配层  → 上游边界模糊，接口还没定型
下游出现 vendored 代码        → 上游边界与下游需求已发生硬冲突
```

所以，**想判断一个库成熟不成熟，去看它的下游有多厚**——比看它自己的版本号可靠得多。这也顺带解释了原文的那句话为什么成立：FlashInfer 处在“CUDA Kernel 优化”和“LLM Serving 系统”之间，而**这一层的边界天然由两侧共同定义**，它自己说不完整。

## 它的内容是什么

### 名词体系：Wrapper 与 Plan

读一个库的“内容”，先读它对外承诺了哪些**概念**（不是逐个类）。

`flashinfer/__init__.py` 用逐行 `X as X` 的方式重导出，这份清单就是它的公开名词体系。抽出来其实只有三类：

| 名词 | 含义 | 实例 |
| --- | --- | --- |
| **Wrapper** | 一次“工作负载形态”的适配器 | `BatchDecodeWithPagedKVCacheWrapper`（`flashinfer/decode.py:967`）、`BatchPrefillWithPagedKVCacheWrapper`、`MultiLevelCascadeAttentionWrapper`（`cascade.py:226`）、`PODWithPagedKVCacheWrapper`（`pod.py:61`） |
| **Plan** | 一次执行的事前规划（把决策移出运行期） | `CakeFmhaRequestOrderedDecodePlan`（`cake_fmha.py:50`）、`CakeVsaSm90Plan`（`cake_vsa_sm90.py:1072`）、`_LaunchPlan`（`cake_sampling.py:1052`） |
| **per-op 函数** | 不需要跨调用保持状态的单次算子 | `single_decode_with_kv_cache`（`decode.py:731`）、`silu_and_mul`、`rmsnorm`、`rope`… |

**真正有价值的是从命名反推关系**，这一步才叫“理解内容”，列能力清单不叫：

| 观察到的命名 | 反推出的关系 |
| --- | --- |
| 几乎每个实体都叫 `...WithPagedKVCacheWrapper` | 上游约束：必须适配分页 KV Cache 的内存布局 |
| 存在 `CUDAGraph...Wrapper` **子类**（`decode.py:2977`） | 约束升级成了类型：CUDA Graph 捕获期有额外禁忌，所以单独派生一个类 |
| `...WithSharedPrefix...`（`cascade.py:576/829`） | 下游场景特化：前缀共享 |
| `...PODWith...`（`pod.py:61/728`） | 下游场景特化：prefill/decode 解耦（POD = Prefill-Only-Decode / 分离式部署） |
| `Plan` 与 `_LaunchPlan` 成对出现 | 时间优化：把“怎么跑”从运行期提前到事前 |

**Wrapper 的调用形态也印证了这一点**：

```python
decode_wrapper = flashinfer.BatchDecodeWithPagedKVCacheWrapper(
    workspace_buffer,   # ← 构造时就要交出 workspace，资源约束进 API
    "NHD",              # ← 布局作为参数，因为上游有 NHD / HND 两种排布
)
decode_wrapper.plan(...)   # decode.py:1524
decode_wrapper.run(...)    # decode.py:2306（forward 在 :2280）
```

`workspace_buffer` 出现在构造函数里，说明**资源治理不是内部细节，而是被提到了 API 表面**。

### 垂直四层

| 层 | FlashInfer 的实情 |
| --- | --- |
| **类型层** | `Wrapper` / `Plan` / per-op 函数（见上） |
| **实体层** | `Wrapper` 的 8+ 个实现（decode / prefill / cascade / pod / cudagraph…），`Plan` 按 kernel 家族各有一套 |
| **模块层** | `flashinfer/` 下 **32 个子系统目录**（`attention/` `gemm/` `fused_moe/` `mla/` `moe_ep/` `norm/` `quantization/` `comm/` `mamba/` `kda_kernels/` `logits_processor/` …）＋ **75 个扁平模块文件**；`csrc/` 下 **168 个扁平 `.cu/.h`** ＋ **46 个子目录**（多为 `cake_*` 命名） |
| **应用层** | `examples/`（很薄，只有 `pytorch/`、`experimental/` 和两个脚本）＋ **`tests/`（厚，结构与子系统一一对应**：`tests/attention/`、`tests/moe/`、`tests/mla/`、`tests/kda/` …） |

**一个可复用的判据**：`examples/` 薄而 `tests/` 厚，说明这个项目的“典型用法”**不在仓库里，而在下游框架里**——它的正确用法是“被 vLLM/SGLang 调用”，不是“自己写 demo”。看 `tests/` 比看 `examples/` 更能学到真实用法。

### 模块边界看发布包，不看目录树

目录树告诉你代码怎么放；**发布包**告诉你作者认为什么应该一起交付：

| 包 | 装什么 | 解决什么 |
| --- | --- | --- |
| `flashinfer-python` | 主代码，**首次使用时编译/下载 kernel** | 装了就能跑 |
| `flashinfer-cubin` | 覆盖所有支持架构的**预编译二进制** | 免编译、可离线 |
| `flashinfer-jit-cache` | 安装特定架构预编译 kernel provider 的 shim | 只装自己那张卡需要的 |
| `flashinfer-jit-cache-provider` | 缓存的提供者（可共享/服务化） | 多机/CI 复用编译产物 |

这一刀切出的问题意识是：**“编译产物如何分发”**。加上 `pip install flashinfer-python[cu13]` 这个 extra（Blackwell CuTe DSL kernel），可以看出它把“架构相关”这件事单独当成一条产品线在做。

**判据**：一个库如果为“编译产物”单独发了包，说明它的编译成本已经高到必须被工程化解决——这是判断它“重不重”的硬指标。

### 横切面：工程化的那一半

垂直面给了骨架，横切面给了肌肉。逐类扫一遍（每条都有仓库里的证据）：

| 横切面 | 证据 |
| --- | --- |
| **配置** | `FLASHINFER_LOGLEVEL`、`FLASHINFER_LOGDEST`、`FLASHINFER_JIT_CACHE_PROVIDER_ARCH`（README + `flashinfer/api_logging.py:70-71`） |
| **可观测性** | `flashinfer/api_logging.py`（**2764 行**）、`@flashinfer_api` 装饰器（`api_logging.py:2400`）、`docs/logging.rst`（764 行）、`flashinfer/trace/` + `trace_apply/`、`docs/fi_trace.rst`（381 行） |
| **异常管理** | `flashinfer/utils.py:83-95` 的三个基类：`GPUArchitectureError` / `LibraryError` / `BackendSupportedError`；子系统级：`CudnnCaptureUnsafeError`、`CudnnWorkspaceTooSmallInCaptureError`、`MissingJITCacheError`、`DAResourceLeaseConflict`、`LegalizationError` |
| **资源治理** | `workspace_buffer` 进构造函数；`CudnnWorkspaceTooSmallInCaptureError` 把“资源不足”做成可识别异常 |
| **缓存** | `autotune_cache.py`、`flashinfer-jit-cache` 独立发版 |
| **校验与合法化** | `flashinfer/logits_processor/validators.py` + `legalization.py` |
| **生命周期** | `Plan` 的预规划阶段；CUDA Graph 捕获期约束独立成类 |
| **兼容性** | `experimental/` + `docs/experimental.rst`；`docs/deprecation_survey_v0.7.0.md` |

**免费学到的一条领域知识**：把异常类名排在一起看——

```text
CudnnCaptureUnsafeError            gemm/gemm_base.py:155
CudnnWorkspaceTooSmallInCaptureError  gemm/gemm_base.py:162
CudnnPlanBuildInCaptureError       gemm/gemm_base.py:3870
```

共同后缀 `Capture` 告诉你：**CUDA Graph 捕获期是一个独立的约束维度——期间不能建 workspace、不能建 plan、有些操作不安全**。这是从 `grep "^class .*Error"` 里白拿的领域知识，五分钟就能做完：

```bash
grep -rn "^class .*Error\|^class .*Exception" <repo> | sort
```

### 日志是横切面里最重的一块

`api_logging.py` 有 2764 行，远超“打日志”的合理体积。读一下它的设计约束就明白为什么：

```text
FLASHINFER_LOGLEVEL = 0（默认）时必须是真正零开销
```

因为它是**被调用在每一次 kernel launch 上的装饰器**（`@flashinfer_api`）。这个约束还引出别的约束：日志不能在 CUDA Graph 捕获期做会破坏图捕获的事（代码里专门处理了 `FLASHINFER_LOGLEVEL=10 inside torch.cuda.graph(...)` 的情况）。

**可复用的判断**：一个装饰器的开销决定它能不能挂在热路径上。看到“零开销”这类断言，去读它怎么实现（这里是等级 0 时直接短路，不做任何格式化）。

**这就是“横切面决定设计”的典型样本**：日志这一格看起来无害，但因为它在热路径上，它反过来约束了日志本身的实现方式。

## 一次 decode 在代码里的真实路径

把上面两张刀合起来用（十字扫描），选一个端到端动作走一遍：

```text
用户侧（README 最小示例）：
  flashinfer.single_decode_with_kv_cache(q, k, v)     decode.py:731
        │  不需要跨调用状态 → 走 per-op 快路径
        ▼
生产侧（大批量、分页 KV）：
  构造：BatchDecodeWithPagedKVCacheWrapper(workspace_buffer, "NHD")   decode.py:1034
        │                              ↑ 资源在这里交出
        ▼
  plan(...)     decode.py:1524   ← 事前规划：页表、分块、kernel 选择
        │                          （结果可被缓存/复用）
        ▼
  run(...)      decode.py:2306   ← 热路径，被每步调用
  ／ forward(...) decode.py:2280
        │
        ▼
  csrc/batch_decode*.cu  +  csrc/batch_decode_*_kernel_inst.jinja
        │  ← 这里才真正进 CUDA；模板化生成多个特化版本
        ▼
  可选：被 CUDA Graph 捕获 → 那就必须用
       CUDAGraphBatchDecodeWithPagedKVCacheWrapper  decode.py:2977
```

**横切面在这条路径上插进来的位置**：`@flashinfer_api` 装饰器（日志/trace）包住每次 `run`；`plan` 里做 kernel 选择（调优缓存）；`workspace` 在构造时确定（资源）；失败时抛的是分层的异常类型。

**这条路径本身就是“怎么用它”的答案**：不是背 API，而是知道**决策发生在 plan，执行发生在 run，约束在构造时交出**。

## 怎么用它

### 先装对：四个包 + 一个 extra

```bash
pip install flashinfer-python                 # 装了就能跑：首次使用时编译/下载 kernel
flashinfer install-cubin-wheel                # 预编译二进制：免编译、可离线
flashinfer install-jit-cache-wheel            # 只装自己那张卡需要的 kernel provider
pip install flashinfer-python[cu13]           # Blackwell (SM100+) CuTe DSL kernel
```

验证：

```bash
flashinfer show-config
```

**这里有个容易踩的坑**：`pip install flashinfer-python` 只是“能跑”，**每次遇到新 shape/新架构都要现编译**。生产环境应该把 `cubin` 和 `jit-cache` 一起装好，否则首 token 时间会被编译吃掉。这也是“性能边界”的工程化对策。

### 最小可用：两条路径，别混用

```python
import torch, flashinfer

# 路径一：per-op 快路径（无跨调用状态）
q = torch.randn(32, 128, device="cuda", dtype=torch.float16)
k = torch.randn(2048, 32, 128, device="cuda", dtype=torch.float16)
v = torch.randn(2048, 32, 128, device="cuda", dtype=torch.float16)
out = flashinfer.single_decode_with_kv_cache(q, k, v)      # decode.py:731

# 路径二：Wrapper 生产路径（有状态、可复用、可被 CUDA Graph 捕获）
ws = torch.zeros(128 * 1024 * 1024, dtype=torch.uint8, device="cuda:0")   # workspace
decode = flashinfer.BatchDecodeWithPagedKVCacheWrapper(ws, "NHD")          # decode.py:1034
decode.plan(kv_page_indices, kv_page_indptr, kv_last_page_len, ...)        # decode.py:1524
out = decode.run(q, kv_cache_at_layer, ...)                                # decode.py:2306
```

| | per-op 函数 | Wrapper |
| --- | --- | --- |
| 状态 | 无 | 有（内部缓存页表/规划结果） |
| 何时用 | 单请求、实验、先跑通 | 生产、批量、要走 CUDA Graph |
| 布局 | 直接传 tensor | 构造时声明 `"NHD"` / `"HND"` |
| 决策时机 | 每次调用 | 一次 `plan`，多次 `run` |

**最小示例的作用是“跑通”，不是“会用”**。生产用法的关键在 `plan` 与 `run` 的分离：`plan` 里做页表解析与 kernel 选择，`run` 只做执行。把这条记住，比记 20 个 API 名有用。

### 入口的入口：CLI 会告诉你作者认为你第一步该干什么

```text
flashinfer show-config           # 诊断：装对了吗
flashinfer list-modules          # 诊断：有哪些模块
flashinfer module-status         # 诊断：模块状态
flashinfer download-cubin        # 产物
flashinfer install-cubin-wheel   # 产物
flashinfer install-jit-cache-wheel  # 产物
flashinfer download-kernels      # 产物
flashinfer clear-cache           # 产物
flashinfer export-compile-commands  # 开发（IDE 集成）
```

**注意：9 个子命令里，没有一个是在“跑推理”。**

这是一个高信息量的信号：作者认为用户的第一痛点是**“装不对 / 编译不出 / 缓存对不上”**，而不是“kernel 不够快”。

**可复用的动作**：拿到任何带 CLI 的项目，先看它的子命令清单——

```text
子命令集中在“运维/诊断”  → 项目的真实痛点在部署与产物管理
子命令集中在“跑业务”      → 项目的真实痛点在功能覆盖
```

### 接口地图（按任务索引，不按 API 名索引）

| 我要做 | 去看 |
| --- | --- |
| Prefill / Decode attention | `flashinfer/attention/`、`decode.py`、`prefill.py` |
| 典型用法（真实参数组合） | **`tests/attention/`、`tests/moe/`、`tests/mla/`**（比 examples 厚得多） |
| 分页 KV / 页表布局 | `flashinfer/page.py`、`docs/tutorials/kv_layout`、`BatchDecodeWithPagedKVCacheWrapper` 的 docstring |
| 级联 / 前缀共享 | `flashinfer/cascade.py` |
| Prefill-Decode 分离 | `flashinfer/pod.py` |
| MoE | `flashinfer/fused_moe/`、`flashinfer/moe_ep/`、`docs/api/fused_moe.rst` |
| MLA | `flashinfer/mla/`、`docs/api/` |
| 采样与 logits 处理 | `flashinfer/logits_processor/`、`cake_sampling*` |
| 量化（FP8/FP4/MXFP4） | `flashinfer/quantization/`、`fp8_quantization.py`、`fp4_quantization.py` |
| 调 kernel 选择 / 调优 | `flashinfer/autotuner/`、`tuning_configs/`、`docs/autotuning.rst` |
| 查为什么慢 | `flashinfer/profiler/`、`flashinfer/trace/`、`docs/fi_trace.rst` |
| 自定义 attention 变体 | `tests/utils/test_jit_example.py`（README 指的就是这里） |
| 离线编译 / AOT | `flashinfer/aot.py` |
| 查环境与缓存 | `flashinfer/__main__.py`、`docs/cli.rst` |

**注意第 2 行**：`examples/` 只有几个脚本，`tests/` 有 **30 个子目录**且与子系统一一对应。

**这是本项目的用法特征**：它是**被集成**的库，不是**被直接使用**的库。学用法要去 `tests/` 看真实参数组合，要去下游（SGLang 的 196 个文件）看真实集成方式，而不是等仓库给你 demo。

## 怎么维护和优化它

### 反馈错误：用项目自己的异常分类做分层定位

报错来了不要直接读源码，先定位它在哪一层。而**分层表不用自己造**——项目已有的异常分类就是它：

```text
现象
 │
 ├─ 环境层？   GPUArchitectureError / BackendSupportedError   utils.py:83-95
 │             → 硬件不支持，或该特性在这个算力等级上没实现
 ├─ 编译层？   MissingJITCacheError                            jit/core.py:35
 │             → 缓存缺失/对不上，去看 flashinfer show-config 与 clear-cache
 ├─ 资源层？   CudnnWorkspaceTooSmallInCaptureError            gemm/gemm_base.py:162
 ├─ 捕获期？   CudnnCaptureUnsafeError / CudnnPlanBuildInCaptureError
 │             → 你正在 CUDA Graph 里做不该做的事
 ├─ 输入层？   LegalizationError / validators 里的错误
 └─ 后端选择？ BackendSupportedError，或“只找到实验性 backend”的报错
                → 需要 FLASHINFER_ALLOW_EXPERIMENTAL_AUTO_BACKENDS=1 或显式 backend=
```

四类根因对应四个动作：

| 层 | 先做什么 |
| --- | --- |
| 环境层 | 确认算力等级；确认该特性支持矩阵 |
| 编译层 | `flashinfer show-config` / `module-status` / `clear-cache` |
| 资源与捕获期 | 检查 workspace 大小；检查是否在 CUDA Graph 捕获期做了建 plan/建 workspace 的事 |
| 后端选择 | 显式指定 `backend=`，或显式打开实验性自动选择 |

**注意最后一行**：报错信息本身会“点名变量并建议显式 `backend=`”（`docs/experimental.rst` 明确这么设计）。**好的错误信息会直接给出修复动作**，这也是判断项目成熟度的一个点。

### 迭代优化：可调旋钮 ≠ 可优化点

| 类别 | 在哪 | 怎么用 |
| --- | --- | --- |
| **可调旋钮**（作者给的） | `flashinfer/autotuner/`、`tuning_configs/`、`docs/autotuning.rst`（440 行） | 换 config、跑 autotune、复用已有 tuning 结果 |
| **可优化点**（自己找的） | `flashinfer/profiler/`、`flashinfer/trace/`、`benchmarks/`（`README.md` 有 **61.6 KB**，是一份完整的基准指南） | 先度量、再假设、再改 |

一个值得注意的细节：`tuning_configs/` 里是按 **GPU 型号**命名的（`v0_1_trtllm_fused_moe_NVIDIA_B200.py`、`..._GB200.py`）。

**这说明调优结果是资产，被版本化了**——换了 GPU 不能直接复用，但可以参考。判断一个项目在性能上认不认真，看它有没有把 tuning 结果当代码管理，比看它宣称的加速比靠谱。

### 场景特化：实验区的进入门槛就是“边界”的另一面

FlashInfer 对场景特化的处理很规范（`docs/experimental.rst`）：

```text
实验性 API   = 公开接口，但可能变更或消失，用 @flashinfer_experimental_api 标记
实验性 backend = 实现，但还不到稳定支持的程度

使用方式：显式 opt-in（调用标记过的 API，或显式 backend="sm12x_cute"）
          → 触发一次 ExperimentalWarning

自动选择被 gate：
  backend="auto" 时，稳定 API 只会考虑稳定 backend，
  除非设置 FLASHINFER_ALLOW_EXPERIMENTAL_AUTO_BACKENDS=1

用户契约：实验性 API/backend 不提供兼容或长期支持保证，
          主要面向 main 分支用户、社区容器、本地框架集成，
          不应在受支持的框架发行版中默认启用
```

**这段政策本身就是一条可复用的工程手法**：

> 实验区必须有**两道闸**——标记（让人知道）+ 显式放行（让人同意）。
> 而且**自动路径默认不选实验性实现**，否则稳定性会被静默侵蚀。

对你自己的行动：

| 你的需求 | 该走哪条路 |
| --- | --- |
| 上层包装能解决 | 用稳定 API，别碰实验区 |
| 需要实验性 kernel | 显式 `backend=` + 自己承担不兼容风险 |
| 需要它没有的能力 | 提 PR（README 要求优化类 PR 附性能数字）；或放你自己的 `experimental` 层 |

### 兼容纪律：一张表把下游拉进来

`docs/deprecation_survey_v0.7.0.md` 是这份文档里最值得抄走的一页。

规则：

```text
被判废弃的公开 API，保证存在两个 minor 版本，之后可删
0.5.x 或更早废弃 → 0.7.0 可以删；0.6.x 废弃 → 等 0.8
```

取证方式（这就是它的纪律）：

```bash
git log -S'<精确标记>' --reverse     # 找到引入废弃的那次提交
git tag --contains <commit>          # 找最早的正式 tag
```

但**最关键的机制在于它的表长这样**（该文件第 73 行）：

```text
| # | symbol | deprecated in | replacement | vLLM | SGLang | risk | suggested |
```

**专门有两列在问“vLLM 用不用、SGLang 用不用”。**

这就是边界那条原则的最终落地形态：

> **兼容边界不是自己定的，是被下游使用情况定义的。**
> 所以决定“能不能删”的不是版本号，而是一张写着下游名字的表。

这同时解释了前面那个问题：为什么 FlashInfer 要承诺两个 minor 的兼容期？**因为它的下游是 vLLM 和 SGLang 这样的长期服务框架，它们的升级节奏不由 FlashInfer 决定。**

### 复用：把可迁移的东西抽出来

按“换个领域还成立吗”分三类：

**通用工程手法（换任何项目都能用）**

1. **编译产物独立发布**：主代码 / 预编译二进制 / JIT 缓存 / 缓存提供者 拆成四个包。任何“首次使用要编译”的项目都该这么切。
2. **实验区两道闸**：标记 + 显式放行，且自动路径默认不选实验性实现。
3. **异常分类即失败模式清单**：先写异常类名，再写代码。`grep "^class .*Error"` 是五分钟拿到领域知识的最快方式。
4. **可观测性零开销**：挂在热路径上的可观测性必须能在关闭时真正短路（`FLASHINFER_LOGLEVEL=0`）。
5. **废弃台账带下游使用情况**：删接口前先查下游有没有用。
6. **错误信息给修复动作**：不只是“失败了”，而是“设置 X 或传 `backend=`”。

**领域知识（换项目也成立，换领域不成立）**

1. **CUDA Graph 捕获期是一个独立的约束维度**：期间不能建 workspace、不能建 plan、部分操作不安全。
2. **分页 KV Cache 的三件套**：`kv_page_indices` / `kv_page_indptr` / `kv_last_page_len`（页表的标准表示）。
3. **决策前置**：`plan` 一次、`run` 多次——把能提前算的都提前。
4. **serving 负载的形态决定 kernel 设计**：长度不一、batch 混合、decode 阶段 occupancy 低。

**项目特有（只在它这里成立，别当规律用）**

- `cake_*` 命名体系、按模型特化的 kernel（`cake_minimax_h3`、`cake_kimi_k3_*`、`cake_dsv4`）
- 四个发布包的具体切法
- 命名里哪些词是概念（`Wrapper` / `Plan`）哪些是内部代号

**最后的检验**（前面说过，这里落到具体条目上）：

```text
“Wrapper 适配外部负载形态”      → 换领域也成立 → 通用手法
“分页 KV 用三件套页表”          → 换领域不成立 → 领域知识
“cake_ 前缀命名”                → 只在这里成立 → 项目特有
```

## 小结：这份文档现在答了什么

| 问题 | 原文档 | 补充后 |
| --- | --- | --- |
| Q0 它是什么 | ✅ | — |
| Q1 解决什么问题 | ⚠️ 有痛点 | ✅ 加了场景边界（什么时候不需要） |
| Q2 在体系中的位置 | ✅ 纵向完整 | ✅ 加了四种关系 + 下游硬证据 |
| Q3 为什么出现 | ✅ 三个“为什么不是” | — |
| **边界** | ❌ | ✅ **六种边界 + 外侧取证法** |
| Q4 内容是什么 | ⚠️ 只有能力清单 | ✅ 名词体系 / 垂直四层 / 横切面 / 发布包边界 |
| Q5 怎么用 | ❌ | ✅ 两条路径 + CLI 信号 + 按任务索引的接口地图 |
| Q6 怎么维护 | ❌ | ✅ 分层定位 + 调优设施 + 实验区政策 + 废弃纪律 |

**一句话收束整份文档**：

```text
FlashInfer 是什么，取决于它和谁在一起：
  上游给它能力边界，下游给它职责边界，
  竞品给它相对边界，历史给它兼容边界。
所以它的边界不可能在它自己的 README 里读全——
要去 SGLang 的 196 个文件里数，
要去 deprecation 台账的 vLLM / SGLang 两列里看。
```

这也是原文那句话的完整版：它处于“CUDA Kernel 优化”和“LLM Serving 系统”之间，**这一层的位置由两侧共同定义，边界也由两侧共同定义**。

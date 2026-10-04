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

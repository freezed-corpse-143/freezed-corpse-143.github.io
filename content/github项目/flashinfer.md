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


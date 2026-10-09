TVM 可以理解成一个**专门给深度学习做“编译优化”的编译器栈**。

如果你刚刚在理解「算子融合、CUDA Graph、GPU Kernel」，那么 TVM 正好处在它们上面一层：

> **PyTorch / ONNX 等模型 → TVM 编译优化 → 高效 CPU/GPU Kernel → 硬件执行**

# TVM 的应用场景

TVM 可以理解成一个**专门给深度学习做“编译优化”的编译器栈**。

如果你刚刚在理解「算子融合、CUDA Graph、GPU Kernel」，那么 TVM 正好处在它们上面一层：

> **PyTorch / ONNX 等模型 → TVM 编译优化 → 高效 CPU/GPU Kernel → 硬件执行**

Apache TVM

## 1. TVM 到底解决什么问题？

假设神经网络里有：

$$ Y = \operatorname{ReLU}(XW+b) $$

最朴素的执行可能是：

```
MatMul
  ↓
写回显存
  ↓
Bias Add
  ↓
写回显存
  ↓
ReLU
  ↓
写回显存
```

这存在很多优化空间。

TVM 会尝试把模型看成一个**计算程序**，然后通过编译器技术决定：

```
计算图怎么改？
        ↓
算子怎么融合？
        ↓
循环怎么拆？
        ↓
线程怎么映射到 GPU？
        ↓
数据放寄存器/shared memory/显存哪里？
        ↓
最后生成什么 Kernel？
```

所以 TVM 并不是 CUDA 的替代品。

更准确地说：

```
             PyTorch / ONNX / TensorFlow
                       │
                       ▼
                   模型计算图
                       │
                       ▼
                  ┌─────────┐
                  │   TVM   │
                  └─────────┘
                       │
        ┌──────────────┼──────────────┐
        ▼              ▼              ▼
      CUDA          LLVM CPU        Metal
        │              │              │
        ▼              ▼              ▼
      NVIDIA           CPU           Apple
```

# 核心思想

如果只记一句话：

> **TVM = 把“深度学习模型如何执行”变成一个编译器优化问题。**

传统框架经常把：

```
Conv
ReLU
Add
MatMul
Softmax
...
```

当成一个个算子。

而编译器会进一步问：

> 这些算子内部其实不就是循环、索引、访存和算术吗？

例如矩阵乘法：

$$ C_{ij} = \sum_k A_{ik}B_{kj} $$

本质就是：

```
for i
    for j
        for k
            C[i][j] += A[i][k] * B[k][j]
```

于是问题就变成：

**这个循环应该怎么执行最快？**

比如可以：

```
loop tiling
vectorization
unrolling
parallelization
thread binding
memory reuse
operator fusion
```

这就是 TVM 最重要的视角。

# Schedule

TVM 会把两个问题尽量分开：

```
What to compute
       +
How to compute
```

例如数学上：

$$ C=A\times B $$

这是 **What**。

但：

```
tile = 32×32
每个 block 计算一个 tile
A/B 搬进 shared memory
K 维循环展开
warp 并行
结果保存在 register
```

这是 **How**。

同一个：

$$ C=A B $$

可能对应几百上万种执行方法。

TVM 的重要工作之一就是：

> **寻找在特定硬件上最快的 How。**

所以它跟普通深度学习框架的思维方式非常不同。

# TVM 的 层次

它实际上涉及多个层次：

```
模型级
────────────────────
constant folding
dead code elimination
layout transformation
operator fusion
graph rewriting

        ↓

Tensor / Loop 级
────────────────────
tiling
loop fusion
loop splitting
reorder
vectorization
unrolling

        ↓

硬件映射
────────────────────
CPU threads
SIMD
CUDA blocks
CUDA threads
warp
shared memory
register

        ↓

代码生成
────────────────────
LLVM
CUDA
Metal
Vulkan
...
```

所以 TVM 更接近：

> **深度学习领域的 LLVM + 自动性能优化系统。**

这个类比并不完全严格，但非常适合建立第一层直觉。

# 与 Pytorch 的区别

PyTorch 更偏：

> **我要方便地定义、训练和运行模型。**

TVM 更偏：

> **模型已经确定了，我怎么把它编译成针对目标硬件高度优化的程序？**

例如同一个模型部署到：

```
NVIDIA GPU
AMD GPU
Intel CPU
ARM CPU
Apple GPU
嵌入式设备
```

最佳实现完全不同。

甚至同样是 NVIDIA GPU：

```
A100
RTX 4090
H100
```

最优的：

```
tile size
block size
warp 数量
shared memory 使用方式
```

都可能不同。

TVM 希望：

$$ \text{Model} + \text{Target Hardware} \rightarrow \text{Optimized Program} $$


# Auto-Tuning

这是 TVM 很有代表性的思想。

假设矩阵乘法可以：

```
方案 A:
tile = 8×8

方案 B:
tile = 16×16

方案 C:
tile = 32×32

方案 D:
tile = 64×64
```

人不一定知道哪个最快。

TVM 可以产生很多候选 Schedule：

$$ S_1,S_2,\dots,S_n $$

然后：

```
生成候选
   ↓
实际硬件运行
   ↓
测量 latency
   ↓
性能模型预测
   ↓
继续搜索
   ↓
找到高性能 schedule
```

这就是 TVM 体系里 **AutoTVM / Ansor / MetaSchedule** 这一系列工作的核心背景。

# 推理体系位置

```
                    PyTorch
                       │
                 模型 / 计算图
                       │
          ┌────────────┴────────────┐
          │                         │
      编译优化路线               Library 路线
          │                         │
    TorchInductor                  cuDNN
       / TVM                       cuBLAS
          │
          ▼
     Kernel generation
          │
     ┌────┴─────┐
     ▼          ▼
   Triton      CUDA
     │          │
     └────┬─────┘
          ▼
      GPU Kernel
          │
          ▼
     NVIDIA GPU
```

当然真实的软件栈比这个复杂很多，但这个心智模型已经很好用了。

其中：

**CUDA**：GPU 编程平台/底层生态。

**cuBLAS/cuDNN**：NVIDIA 手工高度优化好的算子库。

**Triton**：让人更容易编写高性能 GPU kernel 的 DSL/编译器。

**TVM**：从更高层的 tensor/模型表达出发，进行程序变换、调度、搜索和代码生成。

**PyTorch**：用户主要用来定义、训练、执行模型的框架。
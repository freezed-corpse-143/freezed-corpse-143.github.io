# 多 namespace

多次出现 `namespace { ... }`，是在反复打开同一个“当前编译单元内部的命名空间”，并没有创建多个相互隔离的空间。

它主要用于：把内部辅助代码留在本文件里，同时让辅助代码靠近使用它的地方。

我们拆开来看。

**1. 文件与 namespace 解决的是两种不同的问题**

| 机制                          | 主要解决什么问题                                             |
| ----------------------------- | ------------------------------------------------------------ |
| 文件 `.cpp`、`.h`             | 源码怎么存放、包含和分别编译                                 |
| 命名空间 `namespace model {}` | 名字属于谁，例如 `model::load()`                             |
| 匿名命名空间 `namespace {}`   | 实现细节只属于当前编译单元，避免与其他编译单元的同名实体冲突 |

所以，一个文件不需要只对应一个 namespace；一个有名字的 namespace 也可以分散在多个文件里。

**2. 你的代码使用的是“匿名命名空间”**

例如文件开头：

```
namespace {

std::string join(...) { ... }

struct Session { ... };

Session& session() { ... }

void check_cuda(...) { ... }

} // namespace
```

作者表达的意图是：

> `Session`、`session()`、`join()`、`check_cuda()` 都是这个实现文件的内部工具。

假设另一个 `.cpp` 也写了：

```
namespace {

void check_cuda(...) { ... }

}
```

两边的 `check_cuda` 是各自的内部函数，不会因为重名而在链接时冲突。

严格说，边界是**编译单元**，即 `.cpp` 展开所包含的头文件后的整体。初学时，可以先按“当前 `.cpp` 内部”理解。

**3. 为什么要关闭，再重新打开？**

因为作者想把代码按功能排布：

```
namespace {
    // 模型管理需要的内部工具
    struct Session { ... };
    Session& session() { ... }
}

// 接口函数
void open_model(...) { ... }
void close_model(...) { ... }

namespace {
    // 跨进程共享需要的内部工具
    std::string hex_encode(...) { ... }
    void hex_decode(...) { ... }
}

// 接口函数
void share_weights(...) { ... }
void open_model_ipc(...) { ... }
```

这样阅读“跨进程共享”部分时，相关的编码、解码工具就在旁边，不必跳到文件开头寻找。

**反复打开匿名 namespace，兼顾了内部封装和代码阅读顺序。**

如果只打开一次，也可以工作，但所有内部工具可能都要堆在一起，距离使用位置很远。

**4. 不同的匿名 namespace 块可以互相使用吗？**

**可以，但仍要遵守先声明、后使用的规则。**

```
namespace {
    int value = 10;
}

void update() {
    value += 1;          // 可以访问
}

namespace {
    int read() {
        return value;    // 也可以访问
    }
}
```

注意两个容易混淆的点：

- 后面的匿名 namespace 块与前面的属于同一个空间。
- namespace 外面的本文件代码也能使用里面的名字。

所以它**不是**类似类中 `private:` 的访问控制：不是只有花括号里面的代码才能使用，而是限制这些实体的跨编译单元链接。

**5. 这和 Python 接口又是什么关系？**

你的文件最后通过：

```
PYBIND11_MODULE(TORCH_EXTENSION_NAME, m) {
    m.def("share_weights", &share_weights);
    m.def("open_model_ipc", &open_model_ipc);
}
```

决定哪些函数能被 Python 调用。

这有两个独立的边界：

| 边界                                   | 由什么决定                |
| -------------------------------------- | ------------------------- |
| C++ 实体是否属于当前编译单元的内部实现 | 匿名 namespace 等链接规则 |
| Python 能调用哪些函数                  | `m.def(...)` 注册         |

**即使一个函数放在匿名 namespace 内，也可以在同一文件中通过 `m.def` 注册给 Python。** 你这份代码把接口函数放在外面，是一种组织选择，并非 pybind 11 的硬性要求。

你可以把这份代码的写法理解成：

> **每个功能段先放一小组本文件内部工具，再放使用这些工具的接口函数；匿名 namespace 可以随时重新打开，不必把所有内部工具集中到文件顶部。**

# pybind 为 python 绑定 C++

**pybind 11 的核心工作是：给 C++ 函数生成一层 Python 能调用的包装，并将它编译成 Python 扩展模块。**

Python 调用时，执行的仍然是编译后的 C++ 机器码。

先看最小例子：

```
#include <pybind11/pybind11.h>

namespace py = pybind11;

int add(int a, int b) {
    return a + b;
}

PYBIND11_MODULE(example, m) {
    m.def("add", &add, "两个整数相加");
}
```

编译成扩展模块后，Python 就能这样使用：

```
import exampleresult = example.add(2, 3)print(result)  # 5
```

这里有三个需要分别理解的部分。

**1. `PYBIND11_MODULE`：提供模块初始化入口**

```
PYBIND11_MODULE(example, m) {
    // 注册模块里的内容
}
```

其中：

|内容|含义|
|---|---|
| `example` |Python 扩展模块的名字|
| `m` |代表当前模块的 C++ 对象，变量名可以自定|
|花括号里的代码|模块初始化时执行的注册操作|

宏会生成 Python 加载扩展所需要的入口；对这个例子而言，入口名是 `PyInit_example`。Python 导入模块时，通过这个入口完成初始化。[pybind11 documentation](https://pybind11.readthedocs.io/en/stable/reference.html?utm_source=chatgpt.com)

**2. `m.def`：把 Python 名字关联到 C++ 函数**

```
m.def("add", &add, "两个整数相加");
```

可以读成：

> 在模块 `m` 中，创建一个名为 `"add"` 的 Python 可调用对象，背后调用 C++ 函数 `add`。

这里：

```
"add"  // Python 侧使用的名字
&add   // C++ 函数指针
```

两边名字甚至可以不同：

```
m.def("sum_numbers", &add);
```

于是 Python 写：

```
example.sum_numbers(2, 3)
```

底层执行的仍然是 C++ 的 `add(2, 3)`。`m.def` 会生成暴露该函数所需的绑定代码。[pybind11 documentation](https://pybind11.readthedocs.io/en/stable/basics.html?source=post_page-----e52479c3fb7---------------------------------------&utm_source=chatgpt.com)

**3. 包装层：处理两种语言之间的调用差异**

Python 与 C++ 的整数不是同一种内存对象：

```
a = 2       # Python 的 int 对象
```

```
int a = 2;  // C++ 的 int 值
```

因此不能把 Python 的参数直接原样交给 C++。一次调用大致经过：

```
example.add(2, 3)
    ↓
pybind11 包装层检查参数、转换类型
    ↓
调用 C++ add(int, int)
    ↓
把 C++ 返回值转换成 Python 对象
    ↓
Python 得到整数 5
```

你可以把包装层想象成下面的伪代码：

```
PythonObject wrapper(PythonObject a, PythonObject b) {
    int cpp_a = convert_to_cpp_int(a);
    int cpp_b = convert_to_cpp_int(b);

    int result = add(cpp_a, cpp_b);

    return convert_to_python_int(result);
}
```

**这些包装代码不需要你逐个手写，pybind 11 根据函数类型生成。**

**结合你上传的代码看**

你的代码最后写了：

```
PYBIND11_MODULE(TORCH_EXTENSION_NAME, m) {
    m.def("share_weights", &share_weights);

    m.def("open_model", &open_model,
          py::arg("model_dir"),
          py::arg("weights") = "bf16",
          py::arg("math") = "mma");
}
```

它建立的是这些关联：

|Python 侧|C++ 侧|
|---|---|
| `模块.share_weights()` | `share_weights()` |
| `模块.open_model(...)` | `open_model(...)` |
|参数 `model_dir` |对应位置上的 C++ 参数|
|默认参数 `weights="bf16"` |省略时由绑定层提供|
|默认参数 `math="mma"` |省略时由绑定层提供|

`TORCH_EXTENSION_NAME` 是构建时设置的宏，展开成实际的模块名。

例如实际模块名设为 `cuda_project`，Python 就可以写：

```
import cuda_projectcuda_project.open_model(    model_dir="./model",    weights="bf16",    math="mma",)
```

对于其中的 `torch::Tensor` 参数，PyTorch 提供的类型转换支持将 Python Tensor 接到 C++ Tensor 接口上。**传参本身通常不需要复制整块张量数据，更不意味着要把 GPU 数据搬到 CPU。**

**最后，还必须经过编译**

只写 `m.def` 并不会让 Python 直接读取 `.cpp`。完整过程是：

1. 编写 C++ 实现和绑定代码。
2. 用构建工具编译、链接成 Python 扩展模块，Linux 通常是 `.so`，Windows 通常是 `.pyd`。
3. Python 用 `import` 加载模块。
4. 调用已注册的函数。[pybind11 documentation](https://pybind11.readthedocs.io/en/stable/compiling.html?utm_source=chatgpt.com)

这也解释了上一轮匿名 namespace 的问题：**Python 通过包装层保存的函数关联调用 C++，所以目标函数即使位于匿名 namespace，也可以在同一编译单元中注册给 Python；并不要求每个目标函数都对外导出一个链接符号。**

# OPS 结构

这份文件可以理解为一个 **“Python 接口 + 模型状态管理 + CUDA 推理调度”实现文件**。下面是按职责整理的逻辑目录，**并非实际拆分后的文件目录**。

**代码功能目录**

- **1. 文件说明与依赖引入**（第 1–24 行）
  - **接口契约注释**
    - 说明 Tensor 的设备、连续性、数据类型、错误处理和 CUDA Stream 要求。
  - **第三方依赖**
    - `torch/extension.h`：PyTorch Tensor 与 Python 扩展支持。
    - `nlohmann/json.hpp`：JSON 序列化与解析。
    - CUDA 相关头文件：错误检查、Stream 管理。
  - **项目内部依赖**
    - `kernel/kernels.h`：GPU 算子的启动接口。
    - `loader/config.h`：模型配置。
    - `loader/safetensors.h`：权重文件读取。
    - `loader/weights.h`：权重注册与 GPU 权重管理。
- **2. 基础设施与模型内部状态**（第 26–306 行，匿名 namespace）
  - **路径工具**
    - `join()`：拼接目录和文件名。
  - **会话状态**
    - `Session`：集中保存当前模型的运行状态。
      - `file`、`registry`、`spec`：权重文件、权重注册表、模型配置。
      - `weights`、`f32`、`quant`：不同格式的权重与视图。
      - `qkv_w`、`qkv_scale`、`qkv_b`：融合后的 Q/K/V 权重和偏置。
      - `own`、`ipc`：本进程分配和跨进程映射的显存指针。
      - `ev_start`、`ev_stop` 等：耗时与内存统计状态。
      - `pos_dev`、`attn_ws`：CUDA Graph 位置参数和 Attention 工作区。
      - `k_cache`、`v_cache`：各层 KV Cache。
      - `clear_weights()`：清理权重视图及相关显存资源。
    - `session()`：取得共享的 `Session` 实例。
  - **参数检查与错误处理**
    - `strict_mode()`：读取严格检查开关。
    - `fail()`：抛出包含函数名的异常。
    - `has_weights()`：检查是否存在可用权重。
    - `require_file()`：检查当前模式是否支持访问权重文件。
    - `check_cuda_tensor()`：检查 CUDA 设备与内存连续性。
    - `check_dtype()`、`check_f 32()`：检查数据类型。
    - `check_cuda()`：将 CUDA 错误转换成 C++ 异常。
  - **配置转换**
    - `spec_to_dict()`：将模型配置转换为 Python 字典。
  - **权重访问与格式适配**
    - `Weight`：统一表示权重 Tensor 和可选的量化 scale。
    - `weight_bf 16()`：获取 BF 16 权重视图。
    - `weight_matrix()`：统一获取普通或 INT 8 量化权重。
    - `weight_f 32()`：转换、反量化并缓存 FP 32 权重。
    - `layer_weight()`：按层号和后缀获取权重。
    - `layer_bias()`：获取 FP 32 偏置。
  - **输入嵌入**
    - `embedding_lookup()`：根据 token ID 查表，生成 FP 32 激活。
- **3. 最小 GPU 功能测试**（第 308–317 行）
  - `add_one()`：调用加一 kernel，检查扩展和 CUDA 调用链是否可用。
- **4. 模型加载与权重检查**（第 319–450 行）
  - `inspect_model()`：读取配置和权重元数据，不分配模型 GPU 权重。
  - `open_model()`：建立模型会话，加载权重，设置权重格式和计算模式。
  - `verify_weights()`：检查 GPU 权重与文件内容是否一致。
  - `tensor_bytes()`：导出某个权重的原始设备字节。
  - `export_weight_f 32()`：导出推理实际使用的 FP 32 权重，便于调试。
- **5. 基础算子的 C++ 调用接口**（第 452–610 行）
  - **归一化**
    - `rms_norm()`：检查参数、分配输出、启动 RMSNorm kernel。
  - **位置编码**
    - `apply_rope_impl()`：RoPE 内部实现，支持从设备内存读取位置。
    - `apply_rope()`：对外的 RoPE 接口。
  - **计算模式控制**
    - `set_math()`：切换 Tensor Core 路径与 exact 路径。
  - **注意力**
    - `attention()`：启动 GQA Attention 计算。
  - **线性层**
    - `dense(x, Weight, bias)`：根据权重格式选择 FP 32、BF 16 或 INT 8 kernel。
    - `dense(x, Tensor, bias)`：接受普通 Tensor 的入口。
    - `linear_int 8()`：接受量化权重和 scale 的入口。
  - **激活与门控**
    - `silu_mul()`：计算 `SiLU(gate) × up`。
- **6. Attention 张量布局工具**（第 614–625 行，匿名 namespace）
  - `to_heads()`：将投影结果整理为多头 Attention 布局。
  - `from_heads()`：将多头结果合并回隐藏状态布局。
- **7. KV Cache 管理**（第 627–707 行）
  - **内部工具**
    - `cache_bytes()`：统计 KV Cache 占用字节数。
    - `cache_write()`：将当前 K/V 写入指定缓存位置。
  - **输入检查**
    - `check_id_range()`：在严格模式下检查 token ID 范围。
  - **缓存接口**
    - `alloc_cache()`：分配各层 KV Cache 和相关工作区。
    - `cache_info()`：返回缓存容量、使用情况等信息。
    - `reset_cache()`：重置缓存有效长度。
- **8. Transformer 核心计算流程**（第 709–828 行，匿名 namespace）
  - **投影融合准备**
    - `build_qkv_fused()`：拼接 Q/K/V 权重和偏置，减少投影启动次数。
  - **共享层循环**
    - `run_layers()`：供完整前向、Prefill 和 Decode 共用。
      - 输入 RMSNorm。
      - 融合 Q/K/V 投影。
      - 拆分多头并应用 RoPE。
      - 按需写入 KV Cache。
      - 执行完整序列 Attention 或缓存 Decode Attention。
      - 输出投影与残差相加。
      - MLP：归一化、Gate/Up 投影、SiLU 门控、Down 投影。
      - MLP 残差相加。
      - 按需提前返回某层隐藏状态。
      - 最终归一化与词表投影，生成 logits。
  - **序列补齐**
    - `pad_ids()`：将序列补齐至 Attention kernel 所需的块大小。
- **9. 带 KV Cache 的推理入口**（第 830–874 行）
  - `prefill()`：处理整段提示词，填充 KV Cache，返回 logits。
  - `decode()`：处理新 token，追加 KV Cache，返回 logits。
- **10. CUDA Graph 支持**（第 876–928 行）
  - `set_pos()`：将当前位置和有效 key 数写入设备内存。
  - `decode_graph_step()`：提供适合被 CUDA Graph 捕获的单步 Decode。
  - `decode_split()`：计算 Decode Attention 使用的切分数量。
- **11. 无 KV Cache 的前向与中间结果接口**（第 930–967 行）
  - `forward_stop()`：执行前向，支持停在指定层或只输出最后位置。
  - `forward()`：完整模型前向。
  - `forward_hidden()`：获取指定层后的隐藏状态。
- **12. 统计、调试与资源释放**（第 969–1012 行）
  - `stats()`：读取调用计数、CUDA Event 耗时和内存统计。
  - `reset_stats()`：重置统计状态。
  - `debug_cuda_error()`：主动制造 CUDA 错误，验证错误处理。
  - `close_model()`：释放模型权重及相关计算资源。
- **13. 跨进程 GPU 权重共享**（第 1014–1189 行）
  - **内部序列化工具**（匿名 namespace）
    - `spec_to_json()`：模型配置转 JSON。
    - `spec_from_json()`：从 JSON 恢复模型配置。
    - `hex_encode()`：将 CUDA IPC 句柄编码为十六进制字符串。
    - `hex_decode()`：将字符串还原为句柄字节。
  - **生产者接口**
    - `share_weights()`：导出权重的 CUDA IPC 句柄和元数据。
  - **消费者接口**
    - `open_model_ipc()`：映射另一进程的 GPU 权重，建立本地 Tensor 视图。
- **14. Kernel 启动开销探测**（第 1191–1199 行）
  - `launch_probe()`：在 C++ 循环中连续启动简单 kernel，便于测量启动开销。
- **15. Python 模块注册入口**（第 1201 行至文件末尾）
  - `PYBIND 11 _MODULE(TORCH_EXTENSION_NAME, m)`：定义 Python 扩展模块初始化入口。
  - `m.def(...)`：注册 Python 可以调用的函数。
    - 注册模型加载、算子、前向、缓存、统计和 IPC 接口。
    - 设置 Python 参数名、默认值和说明文字。
    - 将 C++ `dense()` 以 Python 名称 `linear` 暴露。
    - 通过函数指针类型转换，选择需要注册的 `dense()` 重载。
    - 注册部分底层控制接口，例如 `set_split_k`。

读代码时，可以先抓住这几个层级关系：

| 层级         | 对应代码                                      | 职责                    |
| ---------- | ----------------------------------------- | --------------------- |
| Python 入口层 | `PYBIND11_MODULE`、`m.def`                 | 让 Python 找到并调用接口      |
| 用例入口层      | `open_model`、`forward`、`prefill`、`decode` | 组织一次完整操作              |
| 模型计算层      | `run_layers`                              | 串起 Transformer 各层计算   |
| 算子调度层      | `dense`、`attention`、`rms_norm` 等          | 检查参数、分配输出、启动 kernel   |
| 状态与数据层     | `Session`、权重访问、KV Cache                   | 保存模型运行所需的数据           |
| 底层依赖       | `loader/*`、`kernel/*`                     | 实际文件加载和 GPU kernel 实现 |

**这个文件承担的职责已经超出“绑定”：pybind 11 注册只是末尾一段，大部分代码实际负责模型推理的组织和运行状态管理。**
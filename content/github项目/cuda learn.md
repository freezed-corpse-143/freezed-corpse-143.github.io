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
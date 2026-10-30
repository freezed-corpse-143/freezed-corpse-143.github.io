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
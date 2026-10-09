# C++ 学习之路

> 本文是 [[RUST & C++混合学习之路]] 的 C++ 侧展开，把路线里每个主题落到 C++ 的具体机制和写法上。
> 主线用一本系统教材（如 *C++ Primer* / *Effective Modern C++*），实践准则查 [C++ Core Guidelines](https://isocpp.github.io/CppCoreGuidelines/CppCoreGuidelines)。
> 基线：**以 C++20 为主线，遇到需要再补 C++23**。

C++ 的价值在于**对对象、资源、内存和性能的精确控制**。学习重点是理解“语言承诺了什么、哪些是未定义行为、谁负责释放资源”，而不是背语法。

---

# 1．基础：能编写、构建、调试小程序

## 1.1 基本语法

- 声明与定义分离，`const` / `constexpr` 表达不可变。
- 函数、控制流是语句，`if constexpr`（C++17）可做编译期分支。
- 初始化优先用**花括号初始化**，避免窄化转换。

```cpp
#include <iostream>

int max(int a, int b) { return a > b ? a : b; }

int main() {
    constexpr int x = 5;
    int count{0};
    ++count;
    std::cout << max(x, count) << '\n';
}
```

## 1.2 基本类型与转换

| 类别 | C++ | 要点 |
|---|---|---|
| 整数 | `short`/`int`/`long`/`long long`，`std::int32_t` 等 | **用定宽类型**避免平台差异 |
| 浮点 | `float`/`double`/`long double` | 默认 `double` |
| 字符 | `char`、`char8_t`(C++20)、`char16_t`/`char32_t` | `char` 的符号性是实现定义的 |
| 布尔 | `bool` | 整数可隐式转 `bool`（易错点） |
| 定长数组 | `std::array<T, N>`、C 数组 | 优先 `std::array` |

转换要点：
- 隐式转换（整型提升、算术转换、用户定义转换）**容易丢信息**。
- `static_cast` 明确表达有意的转换；`dynamic_cast` 做运行期类型检查；`reinterpret_cast` / `const_cast` 应极少使用。
- **列表初始化 `{}` 会拒绝窄化转换**：

```cpp
double d = 3.9;
// int a{d};            // 编译错误：窄化
int b = static_cast<int>(d);   // 显式，明确意图
```

> 学习问题：这次转换会不会丢信息？会不会触发隐式用户定义转换？

## 1.3 数据建模：`struct` / `class` / `enum class`

```cpp
struct Point { double x{}, y{}; };

class Counter {
public:
    explicit Counter(int start) : value_{start} {}
    void increment() { ++value_; }
    int value() const { return value_; }
private:
    int value_{};
};

enum class Color { Red, Green, Blue };   // 强类型枚举，不隐式转 int
```

- `struct` 与 `class` 唯一区别是默认访问权限。
- **`enum class` 优于裸 `enum`**：有作用域、不隐式转换。
- 用类型和不变量表达“合法状态”，把非法状态挡在构造函数之外。

## 1.4 间接访问：指针与引用

| 表达 | 含义 |
|---|---|
| `T*` | 可空、可重新指向，可能拥有也可能不拥有 |
| `T&` | 不可空、不可重新绑定 |
| `const T&` | 只读访问，避免复制 |
| `T&&` | 右值引用，用于移动/完美转发 |
| `std::span<T>`(C++20) | 非拥有连续视图（指针 + 长度） |

```cpp
void print(const std::vector<int>& v);   // 只读，不复制
void fill(std::vector<int>& v);          // 需要修改才用非 const 引用
```

**用引用表达“一定有效”，用指针表达“可空”**；所有权不要用裸指针表达（见 2.5）。

## 1.5 资源管理：构造、析构与 RAII

**RAII**：资源在构造函数中获取，在析构函数中释放，从而与作用域绑定。

```cpp
class File {
public:
    explicit File(const std::string& path) : fp_{std::fopen(path.c_str(), "r")} {
        if (!fp_) throw std::runtime_error("open failed");
    }
    ~File() { if (fp_) std::fclose(fp_); }
    File(const File&) = delete;            // 不可复制
    File& operator=(const File&) = delete;
private:
    std::FILE* fp_{};
};
```

**Rule of 0 / 3 / 5**：
- 优先 **Rule of 0**：用成员（`std::string`、`std::vector`、智能指针）自动管理，不写析构/拷贝/移动。
- 若自定义析构，通常也要处理**拷贝构造、拷贝赋值**（Rule of 3）。
- 需要移动语义时补齐**移动构造、移动赋值**（Rule of 5）。

**析构函数要 `noexcept`**；`throw` 出析构会导致 `std::terminate`。

## 1.6 项目组织：头文件、源文件、命名空间

```cpp
// counter.h
#pragma once
namespace app {
class Counter { /* 声明 */ };
}

// counter.cpp
#include "counter.h"
namespace app { /* 定义 */ }
```

- **声明放头文件，定义放 `.cpp`**；用 `#pragma once` 或 include guard。
- 命名空间避免符号冲突；不要 `using namespace std;` 于头文件。
- C++20 **module** 试图替代头文件（`import` / `export`），可渐进了解。
- 前置声明可减少头文件依赖、加快编译。

## 1.7 开发工具

| 工具 | 用途 |
|---|---|
| 编译器 | GCC / Clang / MSVC，**开启警告**（`-Wall -Wextra`） |
| 构建 | CMake（事实标准）、Ninja |
| 依赖管理 | vcpkg / Conan / CMake FetchContent |
| 调试 | gdb / lldb / VS 调试器，配合 ASan / UBSan |
| 静态分析 | clang-tidy、cppcheck；格式化 clang-format |
| 内存检查 | AddressSanitizer、Valgrind |

**练习**：命令行通讯录（增删查 + 文件保存）。完成标准是能拆分模块、处理输入错误、设置断点，并说清主要对象的生命周期。

---

# 2．标准库：按用途学，不背 API

## 2.1 容器与视图

| 用途 | C++ | 复杂度/布局要点 |
|---|---|---|
| 连续容器 | `std::vector`、`std::array` | 堆连续 / 栈内联；扩容后指针、引用、迭代器失效 |
| 双端队列 | `std::deque` | 分段连续，两端 O(1) |
| 哈希表 | `std::unordered_map` / `_set` | 平均 O(1)，最坏 O(n) |
| 有序容器 | `std::map` / `std::set`（红黑树） | 有序、O(log n) |
| 字符串 | `std::string`、`std::string_view` | 拥有 / 非拥有视图 |
| 非拥有序列 | `std::span<T>`(C++20) | 指针 + 长度 |

每学一个容器固定检查五件事：**内存布局、主要操作复杂度、插入/删除/扩容对引用的影响、元素是否复制/移动、何时换容器**。

**迭代器失效**是 C++ 高频 bug：`vector` 扩容后所有迭代器/引用失效；`unordered_map` rehash 后迭代器失效但引用仍有效。

## 2.2 字符串与编码

**`std::string` 只是字节序列，不保证 UTF-8，也不保证以 `\0` 结尾（但 `c_str()` 会补）。**

```cpp
#include <string>
#include <string_view>

std::string s = "你好";
std::string_view sv = s;      // 非拥有视图，s 失效后 sv 悬垂
size_t bytes = s.size();      // 字节数
```

- `std::string_view` 很轻，但**生命周期必须由调用者保证**，不能返回指向临时对象的 view。
- 处理 Unicode 需要额外库（ICU、utf8cpp），**字节数 ≠ 字符数 ≠ 字素数**。

## 2.3 迭代器、算法与 ranges

```cpp
#include <algorithm>
#include <ranges>
#include <vector>

std::vector<int> v{1, 2, 3, 4};
auto evens = v | std::views::filter([](int x){ return x % 2 == 0; })
               | std::views::transform([](int x){ return x * x; });
for (int x : evens) std::cout << x << ' ';   // 4 16
```

- `<algorithm>` 提供 `sort` / `find` / `accumulate` / `transform` 等。
- C++20 **ranges** 支持管道式懒求值，写法接近 Rust 迭代器。
- 优先用标准算法而非手写循环（更清晰、更易优化）。

## 2.4 可选值与多种状态

- `std::optional<T>`（C++17）：可能没有值。
- `std::variant<Ts...>`（C++17）：类型安全的联合，用 `std::visit` 访问。
- `std::any`：任意类型（少用）。

```cpp
#include <optional>
#include <variant>

std::optional<int> parse(const std::string& s);
struct Circle { double r; };
struct Rect   { double w, h; };
using Shape = std::variant<Circle, Rect>;

double area(const Shape& s) {
    return std::visit([](auto&& sh) -> double {
        using T = std::decay_t<decltype(sh)>;
        if constexpr (std::is_same_v<T, Circle>)
            return 3.14159 * sh.r * sh.r;
        else
            return sh.w * sh.h;
    }, s);
}
```

## 2.5 错误处理

C++ 没有统一的错误处理；常用三种：

1. **异常**：构造失败、不可恢复错误；配合 RAII 保证清理。注意**异常安全保证**（见 5.3）。
2. **错误码 / `std::error_code`**：性能敏感或无异常环境。
3. **`std::expected<T, E>`（C++23）**：返回成功值或错误，语义最接近 Rust 的 `Result`。

```cpp
#include <expected>
std::expected<int, std::string> to_int(const std::string& s) {
    try { return std::stoi(s); }
    catch (...) { return std::unexpected("not a number"); }
}
```

**析构函数、移动操作应 `noexcept`**；异常跨 ABI / FFI 边界要小心。

## 2.6 所有权指针

| 类型 | 语义 | 场景 |
|---|---|---|
| `std::unique_ptr<T>` | 独占所有权，不可复制、可移动 | 默认首选 |
| `std::shared_ptr<T>` | 引用计数共享 | 多方共享生命周期 |
| `std::weak_ptr<T>` | 不增加计数，打破循环 | 观察者、缓存 |
| `T*` / `T&` | **非拥有**观察 | 传参、观察 |

```cpp
#include <memory>
auto p = std::make_unique<Widget>(args);   // 优于 new
auto sp = std::make_shared<Widget>(args);  // 一次分配，优于 shared_ptr(new)
```

**用 `unique_ptr` 表达独占，只有确实需要共享才用 `shared_ptr`**；`shared_ptr` 有原子计数开销和循环引用风险。

## 2.7 文件与路径

- `std::fstream`：`ifstream` / `ofstream`，配合 RAII 自动关闭。
- `<filesystem>`（C++17）：`std::filesystem::path` / `directory_iterator` 处理跨平台路径。

```cpp
#include <filesystem>
#include <fstream>
namespace fs = std::filesystem;
for (auto& e : fs::recursive_directory_iterator(".")) {
    if (e.is_regular_file()) std::cout << e.path() << '\n';
}
```

## 2.8 线程与同步

| 用途 | C++ |
|---|---|
| 线程 | `std::thread`、`std::jthread`(C++20，自动 join + 可停止) |
| 互斥 | `std::mutex`、`std::shared_mutex`、`std::lock_guard`、`std::unique_lock` |
| 条件变量 | `std::condition_variable` |
| 原子 | `std::atomic<T>` |
| 一次性 | `std::once_flag` / `std::call_once` |

```cpp
#include <thread>
#include <mutex>
std::mutex m;
int counter = 0;
auto work = [&]{ for (int i = 0; i < 1000; ++i) { std::lock_guard lk{m}; ++counter; } };
std::thread a{work}, b{work};
a.join(); b.join();
```

C++ 标准库**没有 channel**，需要 `moodycamel::ConcurrentQueue` 等第三方库或自己实现。

**练习**：目录文本统计器（递归遍历、词频、排序、错误报告）。完成标准是能解释容器选型、避免无意义复制、正确处理文件错误与字符串边界。

---

# 3．高阶第一层：泛型、接口与类型设计

## 3.1 模板与 concepts

```cpp
#include <concepts>

template <std::integral T>
T gcd(T a, T b) { return b == 0 ? a : gcd(b, a % b); }

// C++20 concepts：把“类型必须满足的能力”写成可检查的约束
template <typename T>
concept Printable = requires(T t) { std::cout << t; };
```

- concepts 让模板报错更早、更清晰，替代 SFINAE 技巧。
- `requires` 表达式描述对类型的要求。

## 3.2 静态分派：模板实例化

- 模板在**编译期实例化**，每个实参类型生成一份代码。
- 优点：内联、无运行期开销；代价：代码膨胀、编译慢、错误信息长。

## 3.3 动态分派：虚函数与类型擦除

```cpp
struct Shape {
    virtual ~Shape() = default;             // 多态基类必须有虚析构
    virtual double area() const = 0;
};
struct Circle : Shape { double r; double area() const override { return 3.14*r*r; } };

void print(const Shape& s) { std::cout << s.area(); }   // 运行期分派
```

- 虚函数通过虚表（vtable）分派；基类指针删除派生对象**必须虚析构**。
- **类型擦除**：`std::function`、`std::any`、基于 `unique_ptr<Concept>` 的手写方案，在运行期替换实现而不暴露模板。
- 经验：**性能敏感用模板/concepts，需要异构集合或稳定 ABI 用虚函数/类型擦除**。

## 3.4 函数对象：lambda、捕获与 `std::function`

```cpp
int n = 10;
auto add = [n](int x) { return x + n; };     // 按值捕获
auto inc = [&n] { ++n; };                     // 按引用捕获
std::function<int(int)> f = add;              // 类型擦除，可能堆分配
```

- 捕获方式决定生命周期风险：**按引用捕获悬垂引用是最常见 bug**。
- 泛型 lambda（`[](auto x){...}`）等价于模板 operator()。
- `std::function` 有开销，能用模板就直接用模板。

## 3.5 运算符重载与转换

```cpp
struct Meters {
    double v;
    Meters operator+(Meters o) const { return {v + o.v}; }
    explicit operator double() const { return v; }   // 显式转换，防意外
};
```

- 重载运算符要有直觉语义，别滥用。
- **转换构造函数/转换运算符加 `explicit`** 防隐式转换陷阱。
- `operator<=>`（C++20）可一次生成全部比较运算符。

## 3.6 编译期机制

- `constexpr` / `consteval` / `constinit`（C++20）：编译期求值与强制编译期。
- 模板元编程（TMP）：类型计算、`if constexpr`、`std::tuple` 等。
- 宏（`#define`）是预处理文本替换，**最后手段**；优先 `constexpr`、模板、`inline`。

原则：**先掌握普通函数、泛型和组合，宏与重型 TMP 放后面**。

## 3.7 状态约束：类型、`variant`、受控构造

- 用 `enum class` / `std::variant` 让状态合法取值有限。
- 构造函数建立不变量；`explicit`、删除特殊成员函数来阻止非法用法。
- **typestate**：用类型参数编码状态，在编译期禁止非法转换。

**练习**：可替换存储后端的小系统（内存 / 文件），分别用模板（编译期选择）和虚接口（运行期选择）实现。完成标准是能解释接口设计理由，以及分派对扩展性、编译、运行性能的影响。

---

# 4．高阶第二层：并发、异步与性能

## 4.1 线程、共享数据、锁与条件变量

- `std::mutex` + `std::lock_guard` / `std::unique_lock`；**永远用 RAII 锁，别手动 lock/unlock**。
- `std::condition_variable` 配 `unique_lock`，等待谓词用 `wait(lock, pred)` 防伪唤醒。
- **确保锁的顺序一致以避免死锁**；可用 `std::scoped_lock` 一次锁多个 mutex。

```cpp
std::mutex m; std::condition_variable cv; bool ready = false;
// 等待方
std::unique_lock lk{m};
cv.wait(lk, [&]{ return ready; });
// 通知方
{ std::lock_guard lk{m}; ready = true; }
cv.notify_one();
```

## 4.2 任务队列、线程池、关闭与背压

- 有界队列 + 生产者/消费者；要设计**关闭流程**（停止标志 + 唤醒所有等待者）和**背压**（队列满时阻塞或拒绝）。
- C++20 `std::jthread` + `std::stop_token` 提供协作式取消。
- 线程池需自行实现或用库；注意**任务异常不能逃出线程函数**，否则 `std::terminate`。

## 4.3 原子操作与内存序

```cpp
#include <atomic>
std::atomic<int> counter{0};
counter.fetch_add(1, std::memory_order_relaxed);   // 只保证原子性

std::atomic<bool> ready{false};
int data = 0;
// 写者
data = 42; ready.store(true, std::memory_order_release);
// 读者
while (!ready.load(std::memory_order_acquire)) {}
assert(data == 42);   // release/acquire 建立 happens-before
```

- `relaxed` / `acquire` / `release` / `acq_rel` / `seq_cst`。
- **默认先用 `seq_cst` 或加锁保证正确，再按需放松**；放松内存序的错误极难复现。
- `volatile` **不是**同步原语，只表示“不要优化掉这个访问”。

## 4.4 阻塞 I/O → 非阻塞 → 事件循环

- 阻塞 socket：一连接一线程，扩展性差。
- 非阻塞 + `epoll` / `kqueue` / IOCP：事件循环 + 状态机。
- **C++20 协程**（`co_await` / `co_yield` / `co_return`）提供无栈协程语言支持，但**标准库没有执行器**，需要库或自写。

## 4.5 异步 I/O 与协程

- **Boost.Asio** 是主流异步 I/O 框架，提供 io_context、定时器、异步 socket，并支持 `co_await`。
- 理解：任务如何调度、回调如何组合、取消如何传播、生命周期如何保证（`enable_shared_from_this` 常见）。
- Rust 的 Tokio 与 Asio 定位类似，可对照学习。

## 4.6 性能

- 先 **profiling**（perf、VTune、Tracy）再优化；别猜。
- **分配与复制**：`reserve`、`emplace_back`、按移动传递、`string_view` 免拷贝。
- **缓存局部性**：`vector` 优于 `list`；结构体按访问热度排列（SoA vs AoS）。
- 减少间接层与虚调用；批处理。
- 编译期：`-O2`、LTO、PGO；注意 Debug 与 Release 行为差异（UB 在优化下更明显）。

完成标准：能解释**任务如何退出、错误如何传播、队列满了怎么办、性能瓶颈的测量依据**。

---

# 5．高阶第三层：底层机制与跨语言边界

## 5.1 内存与对象模型

- **对齐与 padding**：`alignof` / `offsetof`；`struct` 大小受字段顺序影响。
- **对象生命周期**：存储期、生存期；访问已结束生命周期的对象是 UB。
- **严格别名（strict aliasing）**：用不兼容类型访问同一内存是 UB，需 `memcpy` 或 `std::bit_cast`。
- **未定义行为（UB）**：溢出（有符号）、越界、悬垂引用、数据竞争——编译器可做任意假设。

## 5.2 值类别、移动与完美转发

| 类别 | 含义 |
|---|---|
| 左值 lvalue | 有名字、可取地址 |
| 纯右值 prvalue | 临时值 |
| 将亡值 xvalue | 可被移动的对象 |

```cpp
#include <utility>

void sink(std::string s);
std::string s = "hi";
sink(std::move(s));      // 转换，不移动；之后 s 有效但状态未指定

template <class T>
void wrapper(T&& arg) { sink(std::forward<T>(arg)); }   // 完美转发
```

- **`std::move` 只是到右值引用的转换**，真正“移动”发生在移动构造/赋值被选中时。
- 与 Rust 对比：Rust 移动后**原绑定不可再用**（编译器强制）；C++ 移动后原对象仍可用，只是“有效但未指定状态”，需自行约定。
- **`std::forward` 用于转发引用**，保留值类别。

## 5.3 异常安全

- 四个保证：**无抛出 / 强保证 / 基本保证 / 不保证**。
- 用 **copy-and-swap** 实现强保证；析构函数与移动操作 `noexcept`。
- 析构中抛异常 = 灾难；异常安全依赖 RAII。

## 5.4 分配器

- `std::allocator`、`pmr`（多态内存资源，C++17）、内存池/arena。
- 目标：减少分配次数、提高局部性、控制生命周期。
- 学 Rust 的 allocator 设计可对照理解“分配策略”如何注入。

## 5.5 编译、链接与 ABI

`.cpp → .o（目标文件）→ 静态库 .a/.lib | 动态库 .so/.dll → 可执行文件`

- **符号**：`nm` 查看；`extern "C"` 关闭名称修饰，用于 FFI。
- **静态库**在链接期编入；**动态库**在加载/运行期解析，有 ABI 兼容问题。
- **ABI**：调用约定、名称修饰、对象布局、异常传播；**跨编译器/版本混用需谨慎**。
- 常见链接错误：未定义符号、重复定义、ODR 违反、inline/模板定义缺失。

## 5.6 系统接口

- 文件描述符、`socket`、`mmap`、`fork`/`exec`、系统调用。
- 理解**用户态/内核态边界**与 syscall 开销；`strace` 可观察。
- 语言承诺（标准）与硬件行为（内存模型、cache）的差距要单独实验验证。

## 5.7 跨语言调用

- **C ABI 是通用接口**：`extern "C"` + 稳定数据布局（`repr(C)` 对应物）。
- 边界上必须明确：谁分配/释放、字符串如何传、错误如何返回、是否保存引用。
- 用 [CXX](https://github.com/dtolnay/cxx) 与 Rust 桥接，可安全共享类型与所有权。

**综合练习**：C++ 计算库导出 C ABI（或经 CXX），由 Rust 命令行程序调用，写清分配/释放与错误契约。

---

# 6．常用库：随项目引入

| 用途 | C++ 入口 |
|---|---|
| 格式化输出 | [fmt](https://github.com/fmtlib/fmt)、`std::format`(C++20) |
| 单元测试 | [GoogleTest](https://github.com/google/googletest)、Catch2 |
| 序列化 | nlohmann/json、RapidJSON、protobuf |
| 命令行解析 | CLI11、cxxopts、Boost.ProgramOptions |
| 异步网络 | [Boost.Asio](https://www.boost.org/library/latest/asio/) |
| 日志 | spdlog |
| 基准测试 | Google Benchmark |
| 跨语言桥接 | 与 Rust 共用 CXX |

工程工具链要掌握：**CMake（target、依赖、install）** 和一种依赖管理（vcpkg / Conan / FetchContent）；clang-format + clang-tidy 纳入 CI。

---

# 7．落到一个持续迭代的项目

推荐“目录文本搜索工具”，与 Rust 侧对照实现：

| 版本 | 功能 | 主要学习内容 |
|---|---|---|
| V1 | 搜索单个文件 | 语法、字符串、文件 I/O |
| V2 | 递归搜索目录 | `vector`、迭代器/算法、错误处理 |
| V3 | 模块化搜索策略 | 模板 / concepts、接口、数据建模 |
| V4 | 并行搜索 | `thread`、队列、`mutex`、退出 |
| V5 | 配置、结果序列化、测试 | fmt、JSON、GoogleTest、CMake |
| V6 | 测量并优化 | 分配、复制、缓存局部性、profiling |
| V7 | 作为 C++ 库被 Rust 调用 | FFI、ABI、所有权边界 |

每轮固定循环：**读概念 → 写最小例子 → 故意制造一个错误 → 用 ASan / 调试器 / 编译器警告定位 → 加进项目 → 和 Rust 实现对照**。

要能随时回答路线里的四个问题：
1. 这个对象放在哪、什么时候析构？
2. 当前操作是复制、移动，还是借用？
3. 引用/指针会不会比对象活得更久？
4. 容器扩容后，原来的指针、引用、迭代器还有效吗？

# Rust 学习之路

> 本文是 [[RUST & C++混合学习之路]] 的 Rust 侧展开，把路线里每个主题落到 Rust 的具体概念和写法上。
> 主线：[The Rust Programming Language](https://doc.rust-lang.org/book/)，练习用 [Rust By Example](https://doc.rust-lang.org/rust-by-example/)，查询用标准库文档。

Rust 的核心不是“内存安全的 C++”，而是**把资源与并发的约束写进类型系统**：所有权、借用、生命周期、`Send` / `Sync` 让很多错误在编译期就被拒绝。学习重点是理解这些约束**为什么存在**，而不是绕过它们。

---

# 1．基础：能编写、构建、调试小程序

## 1.1 基本语法

- 变量默认**不可变**：`let x = 5;`，需要修改才写 `let mut x = 5;`。
- 函数体是**表达式导向**：`if`、`match`、块 `{}` 都产生值，最后一个表达式不加分号即为返回值。
- **遮蔽（shadowing）** 与 `mut` 不同：`let x = x + 1;` 会创建新绑定，类型也可以改变。

```rust
fn max(a: i32, b: i32) -> i32 {
    if a > b { a } else { b }   // 表达式，无 return
}

fn main() {
    let x = 5;
    let x = x * 2;      // shadowing，新绑定
    let mut count = 0;
    count += 1;
    println!("{x} {count} {}", max(x, count));
}
```

## 1.2 基本类型与转换

| 类别 | Rust | 要点 |
|---|---|---|
| 整数 | `i8`…`i128`、`u8`…`u128`、`isize`/`usize` | 位宽明确，`usize` 用于索引和长度 |
| 浮点 | `f32`、`f64` | 默认 `f64` |
| 布尔 | `bool` | 条件必须是 `bool`，没有隐式整数真值 |
| 字符 | `char` | Unicode 标量值，4 字节 |
| 元组/数组 | `(T, U)`、`[T; N]` | 长度是类型的一部分 |

**转换是显式的**，`as` 是截断/重解释式转换，可能丢信息：

```rust
let a: u8 = 300u32 as u8;   // 截断为 44
let b = i64::from(42u32);   // 无损、可检查的转换优先用 From
```

整数溢出：**debug 构建会 panic，release 构建会回绕**。要确定性行为就显式用：

```rust
let x: u8 = 255;
x.checked_add(1);     // None
x.wrapping_add(1);    // 0
x.saturating_add(1);  // 255
x.overflowing_add(1); // (0, true)
```

> 学习问题：这次转换会不会丢信息？答不上来就不要用 `as`，改用 `TryFrom` / `From`。

## 1.3 数据建模：`struct`、`enum`、`match`

Rust 的 `enum` 是**带标签联合**，每个变体可携带不同数据，这是表达“合法状态”的核心工具。

```rust
struct Point { x: f64, y: f64 }
struct Celsius(f64);          // newtype，元组结构体

enum Shape {
    Circle { r: f64 },
    Rect { w: f64, h: f64 },
}

fn area(s: &Shape) -> f64 {
    match s {
        Shape::Circle { r } => std::f64::consts::PI * r * r,
        Shape::Rect { w, h } => w * h,
    }   // match 必须穷尽
}
```

`Option<T>` 和 `Result<T, E>` 本身就是标准库里的 `enum`——没有 `null`，没有未检查的“空”。

## 1.4 间接访问：借用

- `&T`：共享/不可变借用，可同时存在多个。
- `&mut T`：可变借用，**同一时刻只能有一个**，且不能与共享借用共存。
- 借用是对已有值的**临时访问**，不转移所有权。

```rust
fn len(s: &str) -> usize { s.len() }

fn push(mut v: Vec<i32>) { v.push(1); } // 拿走所有权

fn push_ref(v: &mut Vec<i32>) { v.push(1); }
```

**借用检查器**保证：引用不会比被引用对象活得更久（生命周期），也不会在持有借用时移动/修改该对象。

## 1.5 资源管理：所有权、移动与 `Drop`

- 每个值有唯一**所有者**；所有者离开作用域时，值被 `Drop`（不是 GC，也不是手动 `free`）。
- 赋值/传参**默认移动**，移动后原绑定失效：

```rust
let s1 = String::from("hi");
let s2 = s1;            // s1 被移动，此后使用 s1 会编译错误
println!("{s2}");
```

- **`Copy`** 类型（整数、`bool`、`char`、仅含 `Copy` 的元组/数组、共享引用）赋值是复制，不失效。
- 需要深拷贝要**显式** `.clone()`。
- 移动只是所有权转移，不是“把内存搬走”；这与 C++ 的 `std::move`（一个转换，之后仍可用、处于有效但未指定状态）**语义不同**。

```rust
struct Guard;
impl Drop for Guard {
    fn drop(&mut self) { println!("released"); }
}
```

## 1.6 项目组织：module / crate / 可见性

- **crate**：编译单元，`bin` 或 `lib`。
- **module**：用 `mod` 组织命名空间，默认私有，`pub` 对外暴露；`pub(crate)` 限定在 crate 内。
- 路径用 `use` 引入，`crate::` / `super::` / `self::` 定位。

```rust
mod net {
    pub mod tcp {
        pub fn connect() {}
    }
}
use net::tcp::connect;
```

- **workspace** 把多个 crate 放在一个 Cargo 工程里统一管理。

## 1.7 开发工具

| 工具 | 用途 |
|---|---|
| `cargo build/run/test` | 构建、运行、测试 |
| `cargo check` | 只做类型检查，比 build 快 |
| `cargo fmt` / rustfmt | 格式化 |
| `cargo clippy` | 静态 lint，教 idiom |
| `rust-analyzer` + 调试器 | 跳转、补全、断点 |
| `cargo doc --open` | 生成文档 |

**练习**：命令行通讯录（增删查 + 文件保存）。完成标准是能拆分模块、处理 `Result` 错误、设断点，并说清每个 `String` / `Vec` 的所有者是谁。

---

# 2．标准库：按用途学，不背 API

## 2.1 容器与视图

| 用途 | Rust | 复杂度/布局要点 |
|---|---|---|
| 连续容器 | `Vec<T>`、`[T; N]` | 堆连续 / 栈内联；扩容后旧引用失效 |
| 双端队列 | `VecDeque<T>` | 环形缓冲，两端 O(1) |
| 哈希表 | `HashMap`、`HashSet` | 无序，默认 SipHash |
| 有序容器 | `BTreeMap`、`BTreeSet` | B 树，范围查询 O(log n) |
| 字符串 | `String`、`&str` | 拥有 / 借用 |
| 非拥有视图 | `&[T]`（slice） | 指针 + 长度 |

每学一个容器固定检查五件事：**内存布局、主要操作复杂度、插入/扩容对引用的影响、元素是否移动/复制、何时换容器**。

`Vec` 扩容会重新分配，**此前借出的 `&T` 一律失效**——这是借用检查器会抓的经典场景。

## 2.2 字符串：`String` 与 `&str`

**`String` 保证是有效 UTF-8**，因此不能用整数下标随机访问字符：

```rust
let s = String::from("你好");
assert_eq!(s.len(), 6);                    // 字节数
assert_eq!(s.chars().count(), 2);          // Unicode 标量值数
let slice = &s[0..3];                       // 按字节切片，必须落在边界上
for c in s.chars() { /* c: char */ }
```

区分三个单位：**字节（byte）→ Unicode 标量值（`char`）→ 用户感知的字素（需要 unicode-segmentation 等库）**。

## 2.3 迭代器

```rust
let v = vec![1, 2, 3, 4];
let sum: i32 = v.iter().filter(|&&x| x % 2 == 0).map(|&x| x * x).sum();
let out: Vec<_> = v.iter().copied().map(|x| x + 1).collect();
```

- `iter()` 借出 `&T`，`into_iter()` 消费得到 `T`，`iter_mut()` 借出 `&mut T`。
- 适配器是**惰性的**，`collect` / `sum` / `for` 等消费者才触发。
- 手写 `for` 循环和迭代器一般性能相同。

## 2.4 可选值与错误处理

- `Option<T>`：`unwrap` / `unwrap_or` / `?` 不适用于它（`?` 也可用于返回 `Option` 的函数）。
- `Result<T, E>` + `?`：错误沿调用链传播，`?` 会在 `Err` 时提前返回并做 `From` 转换。

```rust
use std::fs;
use std::num::ParseIntError;

fn read_num(path: &str) -> Result<i32, ParseIntError> {
    let text = fs::read_to_string(path).unwrap_or_default();
    let n: i32 = text.trim().parse()?;   // ? 传播 ParseIntError
    Ok(n + 1)
}
```

自定义错误推荐实现 `std::error::Error`，或用 `anyhow`（应用层）/ `thiserror`（库层）。**不要为“没写错误处理”而到处 `unwrap`**。

## 2.5 所有权指针：`Box`、`Rc`、`Arc`、`Weak`

| 类型 | 语义 | 场景 |
|---|---|---|
| `Box<T>` | 独占、堆分配 | 递归类型、`dyn Trait`、大对象 |
| `Rc<T>` | 单线程引用计数共享 | 图结构、共享只读数据 |
| `Arc<T>` | 原子引用计数，跨线程共享 | 多线程共享 |
| `Weak<T>` | 不增加强计数的弱引用 | 打破循环，避免泄漏 |

```rust
enum List { Cons(i32, Box<List>), Nil }   // 递归类型必须间接

use std::rc::Rc;
let a = Rc::new(vec![1, 2, 3]);
let b = Rc::clone(&a);                     // 计数 +1
```

`Rc` / `Arc` 本身**只读**，要修改需配合内部可变性（见 5.2）。

## 2.6 文件、路径与 I/O

- `std::fs`：`read_to_string`、`write`、`File`、`read_dir`。
- `std::io`：`Read` / `Write` / `BufReader` / `BufWriter`，`io::Result`。
- `std::path`：`Path` / `PathBuf` 处理平台差异，**不要手拼 `\` / `/`**。

```rust
use std::fs::File;
use std::io::{BufRead, BufReader};
let f = File::open("data.txt")?;
for line in BufReader::new(f).lines() {
    let line = line?;
    println!("{line}");
}
```

## 2.7 线程与同步

| 用途 | 类型 |
|---|---|
| 线程 | `std::thread::spawn`、`JoinHandle` |
| 互斥 | `Mutex<T>`、`RwLock<T>` |
| 原子 | `AtomicUsize` 等 + `Ordering` |
| 通道 | `std::sync::mpsc::channel`、`crossbeam` |
| 一次/惰性 | `OnceLock`、`LazyLock` |

```rust
use std::sync::{Arc, Mutex};
let counter = Arc::new(Mutex::new(0));
let handles: Vec<_> = (0..4).map(|_| {
    let c = Arc::clone(&counter);
    std::thread::spawn(move || { *c.lock().unwrap() += 1; })
}).collect();
for h in handles { h.join().unwrap(); }
```

**练习**：目录文本统计器（递归遍历、词频、排序、错误报告）。完成标准是能解释容器选型、避免无意义 `.clone()`、正确处理 `io::Error` 与 UTF-8 边界。

---

# 3．高阶第一层：泛型、接口与类型设计

## 3.1 泛型与 trait bound

```rust
fn largest<T: PartialOrd + Copy>(list: &[T]) -> T {
    let mut max = list[0];
    for &x in &list[1..] { if x > max { max = x; } }
    max
}
// where 子句在约束复杂时更清晰
fn print_all<T>(v: &[T]) where T: std::fmt::Debug { /* ... */ }
```

trait 描述“一个类型必须具备的能力”，为类型提供共享行为：

```rust
trait Summary { fn summarize(&self) -> String; }   // 也可带默认实现
```

## 3.2 静态分派与单态化

- 泛型在编译期**单态化**：每个具体类型生成一份代码。
- 优点：内联、零运行开销；代价：代码膨胀、编译更慢。

## 3.3 动态分派：`dyn Trait`

```rust
fn render(items: &[Box<dyn Summary>]) {
    for it in items { println!("{}", it.summarize()); }
}
```

- 运行期通过虚表（vtable）分派，接受异构集合、减少代码膨胀。
- 需要对象安全（object-safe）的 trait。
- 经验：**先用泛型/静态分派，确有多态集合需求再用 `dyn`**。

## 3.4 闭包与 `Fn` / `FnMut` / `FnOnce`

| trait | 调用方式 | 捕获 |
|---|---|---|
| `FnOnce` | 消耗 self，调用一次 | 可移动捕获 |
| `FnMut` | `&mut self` | 可修改捕获 |
| `Fn` | `&self` | 只读捕获 |

```rust
fn apply<F: Fn(i32) -> i32>(f: F, x: i32) -> i32 { f(x) }
let n = 10;
let add = |x| x + n;          // 借用 n，实现 Fn
apply(add, 5);
```

- 闭包捕获是**推断的**，可能是借用也可能是移动；`move` 强制按值捕获，常用于线程。
- 需要存进结构体或统一类型时可用 `Box<dyn Fn()>`。

## 3.5 运算符与转换

- 运算符重载通过实现 trait：`Add`、`Sub`、`Index`、`Deref`…
- `From` / `Into`：无损、不可失败转换。
- `TryFrom` / `TryInto`：可能失败的转换。
- `FromStr`：从字符串解析，配合 `parse()`。

```rust
use std::ops::Add;
#[derive(Debug, Clone, Copy, PartialEq)]
struct Meters(f64);
impl Add for Meters {
    type Output = Meters;
    fn add(self, o: Meters) -> Meters { Meters(self.0 + o.0) }
}
```

## 3.6 编译期机制

- **`const fn` / const 求值**：编译期计算常量。
- **const 泛型**：把值作为类型参数，`struct Matrix<const N: usize>`。
- **声明宏** `macro_rules!`：语法级展开，用于 `vec!` 这类重复模式。
- **过程宏**：`derive`、属性宏、函数宏，在编译期生成代码（`serde` 的 `#[derive(Serialize)]` 就是）。

原则：**先掌握普通函数、泛型和组合；宏应解决“语法层面的重复”，而不是替代抽象能力**。

## 3.7 状态约束：`enum` / newtype / typestate

- `enum` 让非法状态不可构造（如 `enum State { Idle, Running(Handle), Done }`）。
- **newtype**（`struct UserId(u64)`）防止 ID 混用。
- **typestate**：用类型参数编码状态机，让状态转换在编译期被检查。

**练习**：可替换存储后端的小系统（内存 / 文件），分别用泛型（编译期选择）和 `dyn Trait`（运行期选择）实现。完成标准是能说明两种分派对扩展性、编译期和运行期性能的影响。

---

# 4．高阶第二层：并发、异步与性能

## 4.1 线程与 `Send` / `Sync`

- `Send`：类型可安全地**转移**到另一线程。
- `Sync`：类型可被**多线程共享引用**（`&T: Send`）。
- 这两个是**自动 trait**，由编译器根据字段推导。
- 关键边界：**`Send` / `Sync` 只约束数据竞争；死锁、逻辑竞争、资源耗尽安全 Rust 一样会发生。**

`Mutex<T>` / `RwLock<T>` 把“加锁才能访问数据”编码进类型，忘记加锁无法编译；`MutexGuard` 离开作用域自动解锁。

## 4.2 任务队列、线程池与背压

标准库没有线程池，可用 `rayon`（数据并行）或 `crossbeam` / `threadpool`。要回答：**队列满了怎么办？关闭时如何处理剩余任务？错误如何汇总？**

```rust
// 无界队列会造成内存无界增长，生产环境优先有界 + 背压
let (tx, rx) = std::sync::mpsc::channel();
```

## 4.3 原子操作与内存序

```rust
use std::sync::atomic::{AtomicUsize, Ordering};
static COUNT: AtomicUsize = AtomicUsize::new(0);
COUNT.fetch_add(1, Ordering::Relaxed);

// 发布数据：写者 Release，读者 Acquire，建立 happens-before
```

- `Relaxed`：只保证原子性，无顺序。
- `Acquire` / `Release`：配对建立同步关系。
- `SeqCst`：全局一致，最易推理，开销最大。
- **默认先用 `SeqCst` 或加锁保证正确，再按需要放松**。

## 4.4 阻塞 I/O → 事件循环 → 异步

- 阻塞 I/O：一请求一线程，简单但扩展性差。
- 非阻塞 I/O + 事件循环：`epoll` / `kqueue` / IOCP，多路复用。
- Rust 的 `async` / `await`：异步函数返回 `impl Future`，是**惰性状态机**，需要执行器（executor）驱动。

```rust
#[tokio::main]
async fn main() -> std::io::Result<()> {
    let body = reqwest::get("https://example.com").await?.text().await?;
    println!("{}", body.len());
    Ok(())
}
```

- 运行时选 **Tokio**（生态最全）；`async-std` / `smol` 是替代。
- **Future 在 `.await` 点可能被取消**，取消即 `drop`，所以“取消安全”要显式设计。
- `Pin` 保证自引用状态机在内存中不被移动；多数时候由 `async` 语法自动处理。
- 不要在异步任务里做长时间阻塞计算，用 `spawn_blocking`。

## 4.5 性能

- 减少分配：复用 `Vec` / `String`（`with_capacity`、`clear`）、避免多余 `.clone()`。
- **缓存局部性**：`Vec` 优于链表；结构体按热度排列字段。
- 批处理 + 缓冲 I/O（`BufReader` / `BufWriter`）。
- 用 `criterion` 做基准测试，`perf` / `flamegraph` 找热点，**测量优先于猜测**。
- `#[inline]`、`codegen-units`、LTO 是最后手段。

完成标准：能解释**任务如何退出、错误如何传播、队列满了怎么办、性能瓶颈的测量依据**。

---

# 5．高阶第三层：底层机制与跨语言边界

## 5.1 生命周期标注

大多数生命周期由编译器**省略规则**推导；需要显式标注时，通常是因为函数返回引用：

```rust
fn first<'a>(x: &'a str, y: &str) -> &'a str { &x[..1] }
```

- 生命周期是**编译期描述**，不产生运行开销。
- `'static` 表示活得和程序一样久（字符串字面量、`Box::leak`）。
- 结构体持有引用时必须标注，此时结构体不能活得比引用久。

## 5.2 内部可变性

`&T` 下也要改数据时使用：

| 类型 | 场景 |
|---|---|
| `Cell<T>` | 单线程、`Copy` 值替换 |
| `RefCell<T>` | 单线程，运行期检查借用规则（违反会 panic） |
| `Mutex` / `RwLock` | 多线程 |
| `OnceCell` / `OnceLock` | 一次性初始化 |

```rust
use std::cell::RefCell;
let log = RefCell::new(Vec::new());
log.borrow_mut().push("event");
```

## 5.3 `unsafe` 与不变量

`unsafe` 块允许：解引用裸指针、调用 `unsafe fn`、访问 `union`、实现 `unsafe trait`。但它**不关闭借用检查**，也不会自动保证正确。正确用法是写下并维护**安全不变量（safety invariant）**：

```rust
// SAFETY: 指针来自同一 Vec，且索引在范围内，期间未发生扩容
let x = unsafe { *v.as_ptr().add(i) };
```

原则：**`unsafe` 尽量小、集中、有文档，外层包一层安全 API**。

## 5.4 内存布局

- 默认 `repr(Rust)` 不保证字段顺序，编译器可重排以省 padding。
- `repr(C)`：C ABI 布局，用于 FFI。
- `repr(transparent)`：只有一个非零字段，保证 ABI 一致（newtype）。
- `repr(packed)`：去 padding，但可能产生未对齐访问。
- 大小、对齐：`std::mem::{size_of, align_of}`。

## 5.5 编译、链接与 ABI

- `rustc` 产出 `.rlib` / `.o` / 可执行文件；`cargo` 驱动。
- Rust **没有稳定 ABI**（除 `extern "C"`），跨版本混用需重新编译。
- `extern "C"` + `#[no_mangle]`（Rust 2024 用 `#[unsafe(no_mangle)]`）导出 C ABI 函数。
- `bindgen` 从 C 头文件生成绑定，`cbindgen` 从 Rust 生成 C 头。

## 5.6 FFI 与 CXX

```rust
#[no_mangle]
pub extern "C" fn add(a: i32, b: i32) -> i32 { a + b }
```

跨语言边界必须明确四件事：
1. **谁分配、谁释放**内存。
2. 字符串/切片如何传递（`*const c_char` + 长度，或 `CString` / `CStr`）。
3. 错误如何返回（错误码 vs 传给 Rust 的 `Result`）。
4. 双方是否保存了传入对象的引用。

用 [CXX](https://github.com/dtolnay/cxx) 桥接可以安全地在 C++ 与 Rust 间共享类型与所有权，比手写裸 FFI 更省心。

**综合练习**：Rust 命令行程序调用 C++ 计算库，边界用 C ABI 或 CXX，写清分配/释放与错误契约。

---

# 6．常用库：随项目引入

| 用途 | Rust 入口 |
|---|---|
| 格式化输出 | 标准库 `format!`、`println!`、`{:#?}` |
| 单元测试 | 内置测试框架（`#[test]`、`assert_eq!`）、`cargo test` |
| 序列化 | [Serde](https://serde.rs/)（`serde_json`、`toml`） |
| 命令行解析 | [clap](https://github.com/clap-rs/clap) |
| 异步网络 | [Tokio](https://tokio.rs/) |
| 错误处理 | `anyhow`（应用）/ `thiserror`（库） |
| 并行 | `rayon`、`crossbeam` |
| 日志 | `tracing` / `log` + `env_logger` |
| 基准测试 | `criterion` |
| 跨语言桥接 | CXX |

工程工具链要掌握：Cargo 的**依赖、features、workspace、profile、测试组织**；`cargo test --doc` 跑文档测试很常用。

---

# 7．落到一个持续迭代的项目

推荐“目录文本搜索工具”（类似简化版 ripgrep），把路线串起来：

| 版本 | 功能 | 主要学习内容 |
|---|---|---|
| V1 | 搜索单个文件 | 语法、字符串、文件 I/O |
| V2 | 递归搜索目录 | `Vec`、迭代器、`Result` / `?` |
| V3 | 模块化搜索策略 | 泛型、trait、`enum` 建模 |
| V4 | 并行搜索 | `thread`、`rayon`、channel、退出 |
| V5 | 配置、结果序列化、测试 | clap、serde、工程组织 |
| V6 | 测量并优化 | 分配、缓冲、缓存局部性、profiling |
| V7 | Rust 调用 C++ 搜索核心 | FFI、ABI、所有权边界 |

每轮固定循环：**读概念 → 写最小例子 → 故意制造一个错误 → 用编译器/工具定位 → 加进项目 → 和 C++ 实现对照**。

要能随时回答路线里的四个问题：
1. 这个值放在哪、什么时候 `Drop`？
2. 当前操作是移动、复制，还是借用？
3. 引用会不会比被引用对象活得更久？
4. 容器扩容后，原来的引用还有效吗？

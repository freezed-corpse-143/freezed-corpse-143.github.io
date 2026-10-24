# Zig 学习路线（0.17.0）

> 主线：[Zig Language Reference 0.17.0](https://ziglang.org/documentation/0.17.0/)（单页、可离线、示例随编译器测试套件编译；本机另有 `zig std` 起的本地标准库文档）。
> 姊妹篇：[[C & Zig 混合学习之路]]（按主题逐条对照 C）。
> 方法：[[参考学习法]]——先借熟悉概念建立可用理解，再用差异和反例修正，最后脱离旧模型解释 Zig。

本机实测：`zig version` → `0.17.0`。本页所有代码块都在该版本下编译或运行过。

**一句话定位（不是定义）**：Zig 把「分配」「错误」「类型构造」「内存布局」都做成**显式、可检查的普通代码**，代价是程序员必须始终能回答"字节在哪、谁释放"。参考学习法的用处在于：C 提供内存与 ABI 的参照，Rust 提供类型建模与错误值的参照，但两者的**保证强度**不能平移。

---

# 1．先把参照系选对

| 旧参照       | 为什么能当入口                             | 哪些性质绝不能带过来                                                           |
| :-------- | :---------------------------------- | :------------------------------------------------------------------- |
| C         | 手动内存、指针、结构体布局、C ABI、`.c → .o → 可执行` | Zig 没有默认分配器，没有隐式整数转换，没有可空裸指针，错误是值不是返回码约定                             |
| Rust      | 用类型表达"合法状态"、错误值 `Result`、单态化泛型      | Zig 没有 trait/生命周期检查/借用检查，`defer` 不是 `Drop`，`comptime` 不是 trait bound |
| Python/JS | 快速写命令行小工具的动机                        | 这里的"对象"、"异常"、"GC"三个概念在 Zig 中都不存在对应物                                  |

先把一句结论钉住，后面每阶段都回来核对：

> **Zig 不是"内存安全的 C"。** 它把一部分错误变成**可检查的 panic**（Debug/ReleaseSafe 下的安全断言），把另一部分错误（悬垂指针、重复释放、逻辑错误）仍留给程序员和测试。

官方给出的四个目标可以直接当作路线的判据：robust（边界情况正确，包括 OOM）、optimal（能写出最好的行为与性能）、reusable（同一份代码适应不同环境约束）、maintainable（意图能精确传达给编译器和读者）。[Introduction](https://ziglang.org/documentation/0.17.0/#Introduction)

---

# 2．路线总表

```mermaid
flowchart LR
    S1[1 骨架] --> S2[2 数据与内存视图] --> S3[3 错误与可空] --> S4[4 资源与分配器] --> S5[5 comptime 与泛型] --> S6[6 工程化] --> S7[7 系统边界] --> S8[8 标准库与源码]
    S8 -.->|回填缺口| S2
```

| 阶段             | 官方章节                                                                                       | 产出物                                                 | 验收标准                             |
| :------------- | :----------------------------------------------------------------------------------------- | :-------------------------------------------------- | :------------------------------- |
| 1 骨架           | Hello World、Values、Variables、Operators、Blocks、if/while/for/switch、Functions、Zig Test       | 能用 `zig test` 写断言                                   | 不查文档写出带测试的小函数                    |
| 2 数据与内存视图      | Arrays、Slices、Pointers、struct、enum、union、opaque、Vectors                                    | 画出"数组/切片/指针/结构体"的内存图                                | 能回答"地址、长度、容量、所有权、生命周期"各是什么       |
| 3 错误与可空        | Errors、Optionals、Casting、Zero Bit Types、Result Location Semantics                          | 自定义 error set + 传播链                                 | 能解释错误在哪一层被吞掉、`try` 之外还漏了什么       |
| 4 资源与分配器       | Memory（含 Choosing an Allocator、Where are the bytes?、Lifetime and Ownership）、defer          | 动态数组、字符串构建器、arena 版解析器                              | 能回答"谁分配、谁释放、返回值借用了谁、失败后清理什么"     |
| 5 comptime 与泛型 | comptime、Functions（inline fn、函数反射）、Builtin Functions                                       | 泛型栈/队列 + 接口对象                                       | 能说明哪些工作被提前到编译期、哪些错误只在实例化时暴露      |
| 6 工程化          | Zig Test、Compilation Model、Zig Build System、Optimization Mode、Illegal Behavior、Style Guide | `zig build` / `zig build run` / `zig build test` 全套 | 能定位一次构建错误、一次测试失败、一次 panic 属于哪个阶段 |
| 7 系统边界         | C、Atomics、Assembly、Targets、WebAssembly、Compile Variables、Async Functions（现状）               | 调用一个 C 库 + 一份二进制解析器                                 | 能说明布局、字节序、对齐、并发内存序各自的保证边界        |
| 8 标准库与源码       | Zig Standard Library、`zig std`、`lib/std`                                                   | 读源码解释一个 API 的行为                                     | 能判断某个 API 的分配与生命周期契约             |

每阶段固定循环：**读一节 → 写最小可跑样例 → 故意造一个错误 → 用编译器/测试定位 → 回填到项目 → 与 C（或 Rust）实现对照**。

---

# 3．阶段 1：骨架（先让测试跑起来）

读：[Hello World](https://ziglang.org/documentation/0.17.0/#Hello-World) → [Values](https://ziglang.org/documentation/0.17.0/#Values) → [Variables](https://ziglang.org/documentation/0.17.0/#Variables) → [Operators](https://ziglang.org/documentation/0.17.0/#Operators) → [Zig Test](https://ziglang.org/documentation/0.17.0/#Zig-Test) → [Functions](https://ziglang.org/documentation/0.17.0/#Functions)

**0.17 的 Hello World 已经换了形状**（`main` 接收 `std.process.Init`，写 stdout 走 `std.Io`）：

```zig
const std = @import("std");

pub fn main(init: std.process.Init) !void {
    try std.Io.File.stdout().writeStreamingAll(init.io, "Hello, World!\n");
}
```

不需要参数的场景仍可写 `pub fn main() void`；调试输出用 `std.debug.print("Hello, {s}!\n", .{"World"})`。`!void` 表示可能返回任意错误。

**学习顺序上的一个取舍**：先学 `zig test` 而不是先学 `println`。测试是 Zig 的常规开发回路（`test "..."` 块、`std.testing.expect*`、用标识符命名的 doctest），有了它，后面每个概念都能当场验证而不是"看起来对"。

```zig
const std = @import("std");

fn max(comptime T: type, a: T, b: T) T {
    return if (a > b) a else b;
}

test "basics" {
    try std.testing.expectEqual(@as(i32, 7), max(i32, 3, 7));
}
```

## 类比卡：变量与类型

| 项目   | 内容                                                                                                                                                |
| :--- | :------------------------------------------------------------------------------------------------------------------------------------------------ |
| 旧参照  | C 的 `int`/`const`；Rust 的 `let`/`let mut`                                                                                                          |
| 相似关系 | 都有编译期类型、都有不可变性                                                                                                                                    |
| 不能迁移 | Zig 的整数位宽显式（`u8`、`i32`、`usize`），**没有隐式整数转换**；`comptime_int` 只在编译期存在；`const` 是"这个绑定不可重新赋值"，不保证指向的数据不可变                                             |
| 影响   | 任何跨类型赋值要么是安全的放宽（coercion），要么必须写 `@intCast` / `@truncate` / `@floatFromInt`，溢出行为显式（见 [Casting](https://ziglang.org/documentation/0.17.0/#Casting)） |

**可检验预测**：`const x: u8 = 300;` 应该在编译期就报错，而不是截断成 44。→ 用 `zig test` 验证。

**反例**：`var` 的"可变"不等于 C 的 `int*`——`var` 只控制绑定本身；通过 `*T` 修改才涉及内存写。

**验收**：能用 `zig test` + `expectEqual` + `expectError` 表达一个函数的正确与失败，并解释 `try` 在测试里做了什么。

---

# 4．阶段 2：数据与内存视图（路线的重心）

读：[Arrays](https://ziglang.org/documentation/0.17.0/#Arrays) → [Slices](https://ziglang.org/documentation/0.17.0/#Slices) → [Pointers](https://ziglang.org/documentation/0.17.0/#Pointers) → [struct](https://ziglang.org/documentation/0.17.0/#struct) → [enum](https://ziglang.org/documentation/0.17.0/#enum) → [union](https://ziglang.org/documentation/0.17.0/#union) → [opaque](https://ziglang.org/documentation/0.17.0/#opaque)

这一节的核心问题只有一个，问法固定：

> **地址、长度、容量、所有权、生命周期——这五个信息，当前类型和接口各表达了哪些？**

| 类型                   | 地址        | 长度          | 容量  | 所有权       | 生命周期       |
| :------------------- | :-------- | :---------- | :-- | :-------- | :--------- |
| `[N]T`               | 值本身，可被复制  | `N` 是类型的一部分 | —   | 值语义       | 随所在作用域     |
| `[]T` / `[]const u8` | 是         | 是           | 否   | **否**（借用） | 由被借用方决定    |
| `*T`                 | 是（单个、非空）  | —           | —   | 否         | 由被指向对象决定   |
| `[*]T`               | 是（多项）     | 否（需另传）      | —   | 否         | 同上         |
| `?*T`                | 是，可空（零开销） | —           | —   | 否         | 同上         |
| `[:0]const u8`       | 是         | 是           | —   | 否         | 同上，末尾有哨兵 0 |

**类比卡：切片 vs C 的"指针 + 长度"**

| 项目 | 内容 |
| :--- | :--- |
| 旧参照 | C 里 `void f(char *p, size_t n)` 的两参数约定 |
| 相似关系 | 都描述"一段连续内存"，都不拥有它 |
| 不能迁移 | 切片把指针和长度绑成一个值，越界访问在安全模式下会 panic；切片**不携带容量**，也不携带分配器 |
| 影响 | 函数签名从"两个参数 + 口头约定"变成"一个类型 + 编译期检查长度使用"；但"这块内存什么时候失效"仍然只有文档约定，没有类型保证 |

**类比卡：结构体布局 vs C**

| 项目 | 内容 |
| :--- | :--- |
| 旧参照 | C 的 `struct`（`sizeof`、对齐、字段顺序） |
| 相似关系 | 都有字段、都有对齐和填充 |
| 不能迁移 | Zig 默认 `struct` 布局**不保证**与 C 一致；要与 C 对齐用 `extern struct`，要去填充用 `packed struct`，只有 `extern` 才承诺 C ABI |
| 影响 | "结构体内存布局 ≠ 可移植的序列化格式"——做二进制解析时必须显式选择布局并处理字节序 |

**类比卡：`union(enum)` vs Rust 的 `enum`**

| 项目   | 内容                                                                              |
| :--- | :------------------------------------------------------------------------------ |
| 旧参照  | Rust 的带数据枚举 + `match`                                                           |
| 相似关系 | 都能表达"若干互斥状态各自携带不同数据"，且 `switch` 必须穷尽                                            |
| 不能迁移 | Zig 的 `enum` 只是整数常量集；带标签联合是 `union(enum)`；模式匹配靠 `switch` 的载荷捕获，不是独立的 `match` 语法 |
| 影响   | 数据建模时问自己："这是常量集，还是互斥状态机？"前者用 `enum`，后者用 `union(enum)`                           |

```zig
const std = @import("std");

const Shape = union(enum) {
    circle: f64,
    rect: struct { w: f64, h: f64 },

    fn area(s: Shape) f64 {
        return switch (s) {
            .circle => |r| std.math.pi * r * r,
            .rect => |d| d.w * d.h,
        };
    }
};

test "shape" {
    try std.testing.expectEqual(@as(f64, 6), (Shape{ .rect = .{ .w = 2, .h = 3 } }).area());
}
```

> 注意 `(Shape{ ... }).area()` 的括号：对匿名结构体/联合字面量直接 `.area()` 会被解析成初始化式的一部分，0.17 下报 `expected ',' after argument`。

**可检验预测**：把 `"hello"` 传给 `fn f(s: []u8)` 应该编译失败，因为字符串字面量在全局常量区。官方示例正是这个错误（`cast discards const qualifier`）。

**反例**：切片"安全"≠"引用有效"。函数返回指向栈上 `var` 的切片，编译器通常不会拦；这就是 unchecked Illegal Behavior。

**练习**：解析一行 CSV，用 `[]const u8` 表示字段，用 `struct` 表示记录，全程不分配（借用输入缓冲区）。

**验收**：能画出数组、切片、指针、结构体四者的内存关系图；能说清函数返回后哪块数据仍有效。

---

# 5．阶段 3：错误与可空（把"失败"变成类型）

读：[Errors](https://ziglang.org/documentation/0.17.0/#Errors) → [Optionals](https://ziglang.org/documentation/0.17.0/#Optionals) → [Casting](https://ziglang.org/documentation/0.17.0/#Casting) → [Zero Bit Types](https://ziglang.org/documentation/0.17.0/#Zero-Bit-Types) → [Result Location Semantics](https://ziglang.org/documentation/0.17.0/#Result-Location-Semantics)

**类比卡：error union vs C 的返回码 / errno**

| 项目 | 内容 |
| :--- | :--- |
| 旧参照 | C 的 `int` 返回码 + `errno` + 输出参数 |
| 相似关系 | 都用值表示失败，都需要调用方处理，都不做栈展开 |
| 不能迁移 | Zig 把成功值**和**错误放在同一个返回值里（`E!T`），错误集是类型的一部分且可推断；`try` 只是"失败就原样返回"的语法糖；`catch` 可以给默认值；`errdefer` 让失败路径清理写在同一处 |
| 影响 | 不存在"忘记检查返回码"的路径——但存在"`catch {}` 吞掉错误"的路径，所以审阅重点是 `catch` 与 `errdefer` 覆盖了谁 |

```zig
const std = @import("std");

const ParseError = error{ NotANumber, Overflow };

fn parse(text: []const u8) ParseError!i32 {
    return std.fmt.parseInt(i32, text, 10) catch |err| switch (err) {
        error.InvalidCharacter => error.NotANumber,
        error.Overflow => error.Overflow,
    };
}

fn find(haystack: []const u8, needle: u8) ?usize {
    for (haystack, 0..) |c, i| {
        if (c == needle) return i;
    }
    return null;
}

test "optionals and errors" {
    const idx = find("abc", 'b') orelse return error.NotFound;
    try std.testing.expectEqual(@as(usize, 1), idx);
    try std.testing.expectEqual(@as(i32, 7), try parse("7"));
    try std.testing.expectError(error.NotANumber, parse("x"));
}
```

**类比卡：`?T` vs Rust 的 `Option<T>` / C 的 NULL**

| 项目 | 内容 |
| :--- | :--- |
| 相似关系 | 都是"可能有、可能没有"，都必须显式解包 |
| 不能迁移 | Zig 没有 `null` 引用这回事，`?*T` 保证与普通指针同样大小；`?T` 的 `orelse`、`if (x) \|v\|`、`while (it.next()) \|v\|` 是三种不同解包方式 |
| 影响 | 接口设计上，"失败"分两类：**预期内的缺失**用 optional，**需要区分原因**用 error union；混用会让调用方多一层判断 |

**可检验预测**：`?i32` 与 `i32` 的 `@sizeOf` 不同，而 `?*T` 与 `*T` 相同。→ 用 `comptime { @compileLog(@sizeOf(?i32), @sizeOf(i32), @sizeOf(?*u8), @sizeOf(*u8)); }` 验证。

**反例**：`try` 不等于"处理了"。它的语义是"向上传播"，错误最终必须在某处被 `catch`、被 `switch` 分类、或被 `main` 返回；否则只是把问题推给调用者。

**验收**：能给一个模块设计错误集，解释每个错误在什么条件下产生、调用方应该分类处理还是继续传播。

---

# 6．阶段 4：资源与分配器（整条路线最容易自欺的一节）

读：[Memory](https://ziglang.org/documentation/0.17.0/#Memory) → [defer](https://ziglang.org/documentation/0.17.0/#defer) → [Zig Test / Report Memory Leaks](https://ziglang.org/documentation/0.17.0/#Report-Memory-Leaks)

官方把这一节的问题写成一句话：**Where are the bytes?** 并且明确——Zig 不像 C 有默认分配器，需要分配的函数按约定接收 `Allocator` 参数。分配器选型（[Choosing an Allocator](https://ziglang.org/documentation/0.17.0/#Choosing-an-Allocator)）：

| 场景 | 选择 |
| :--- | :--- |
| 写库 | 接收 `Allocator` 参数，让调用方决定 |
| 链接了 libc | `std.heap.c_allocator` |
| 上限在 comptime 已知 | `std.heap.FixedBufferAllocator` |
| 命令行程序，结束一次性释放 | `std.heap.ArenaAllocator` |
| 循环型（帧/请求）且整批释放 | `ArenaAllocator`（必要时再叠 FixedBuffer） |
| 测试 | `std.testing.allocator`（带泄漏检测）、`std.testing.FailingAllocator`（测 OOM） |
| 通用 | Debug 下 `std.heap.DebugAllocator`，fast 下 `std.heap.smp_allocator` |

**类比卡：`defer` / `errdefer` vs C 的 `goto cleanup` / Rust 的 `Drop`**

| 项目 | 内容 |
| :--- | :--- |
| 相似关系 | 都在作用域结束时执行清理，都让"获取与释放"写在一起 |
| 不能迁移 | `defer` 绑定**作用域**而不是对象所有权：它不会追踪值被移动/复制到别处；`errdefer` 只在函数以错误返回时执行；多个 `defer` 逆序执行；返回值在 `defer` 之前已确定，`defer` 里改局部变量影响不了返回值 |
| 影响 | "谁释放"仍由接口文档约定（"caller owns the returned memory"），测试分配器是唯一能自动发现泄漏的机制 |

```zig
const std = @import("std");

fn dupTwice(gpa: std.mem.Allocator, s: []const u8) ![]u8 {
    const out = try gpa.alloc(u8, s.len * 2);
    errdefer gpa.free(out);          // 只有错误返回时执行
    @memcpy(out[0..s.len], s);
    if (s.len > 4) return error.TooLong;
    @memcpy(out[s.len..], s);
    return out;                      // 成功路径由调用方释放
}

test "errdefer" {
    const gpa = std.testing.allocator;
    const ok = try dupTwice(gpa, "hi");
    defer gpa.free(ok);
    try std.testing.expectEqualStrings("hihi", ok);
    try std.testing.expectError(error.TooLong, dupTwice(gpa, "toolong"));
}
```

**0.17 的容器不对称（照抄旧教程必踩）**：

```zig
const std = @import("std");

test "containers" {
    const gpa = std.testing.allocator;

    var list: std.ArrayList(u8) = .empty;   // 非托管：.empty + 传 gpa
    defer list.deinit(gpa);
    try list.append(gpa, 'x');

    var map = std.StringHashMap(usize).init(gpa); // 托管：init(gpa) + 无参 deinit
    defer map.deinit();
    try map.put("k", 1);
}
```

字符串构建器用 `std.Io.Writer.Allocating`（写入 `aw.writer`，读结果 `aw.written()`，`aw.deinit()` 释放）。

**可检验预测**：在 `std.testing.allocator` 下少写 `defer list.deinit(gpa)`，`zig test` 应在结束时报告泄漏并以失败退出。→ 亲自删一行跑一次。

**反例**：arena 让"忘记释放"变得无害，但也会让**单次循环内的内存增长**被掩盖——长生命周期 arena 是内存泄漏的另一种形式。

**验收**：三个小项目按序完成——动态数组（长度/容量/扩容后指针失效）、字符串构建器（追加、分配失败、最终释放）、arena 解析器（整批释放）；每个都能回答"谁分配、谁释放、返回值借用了谁、失败后清理什么"。

---

# 7．阶段 5：comptime（把类型当值）

读：[comptime](https://ziglang.org/documentation/0.17.0/#comptime) → [Functions](https://ziglang.org/documentation/0.17.0/#Functions)（inline fn、Function Reflection）→ [Builtin Functions](https://ziglang.org/documentation/0.17.0/#Builtin-Functions) → [Zero Bit Types](https://ziglang.org/documentation/0.17.0/#Zero-Bit-Types)

**类比卡：comptime vs C 宏 / Rust 泛型**

| 项目   | 内容                                                                                                                                                                                                 |
| :--- | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 相似关系 | 都让一份代码服务多种类型，都能在编译期消除抽象开销                                                                                                                                                                          |
| 不能迁移 | 没有单独的模板/宏语言：`comptime` 里跑的就是普通 Zig，可以 `if`、`for`、递归、`@compileError`；泛型是"函数接收 `comptime T: type` 并返回类型"；没有 trait bound，取而代之是**编译期鸭子类型**（用到不存在的操作就在实例化时报错）；`inline for` / `inline fn` 是真实的展开语义而非优化提示 |
| 影响   | 错误信息的形状变了：类型错误出现在**实例化点**；API 的约束只能靠文档 + `@compileError` + 测试表达                                                                                                                                    |

```zig
const std = @import("std");

fn Stack(comptime T: type) type {
    return struct {
        items: []T,
        len: usize = 0,

        const Self = @This();

        fn init(buffer: []T) Self {
            return .{ .items = buffer };
        }

        fn push(self: *Self, value: T) !void {
            if (self.len == self.items.len) return error.Full;
            self.items[self.len] = value;
            self.len += 1;
        }

        fn pop(self: *Self) ?T {
            if (self.len == 0) return null;
            self.len -= 1;
            return self.items[self.len];
        }
    };
}

test "generic stack" {
    var buf: [4]i32 = undefined;
    var stack = Stack(i32).init(&buf);
    try stack.push(1);
    try stack.push(2);
    try std.testing.expectEqual(@as(?i32, 2), stack.pop());
}
```

**运行期多态的写法**（对应 C 的函数指针表）：`opaque` 作为不透明上下文 + 函数指针 + `@ptrCast(@alignCast(ctx))`。

```zig
const Sink = struct {
    ctx: *anyopaque,
    writeFn: *const fn (ctx: *anyopaque, bytes: []const u8) void,

    fn write(self: Sink, bytes: []const u8) void {
        self.writeFn(self.ctx, bytes);
    }
};
```

**可检验预测**：`max(bool, true, false)` 应在实例化时报 "operator > not allowed for type 'bool'"（官方示例即此）。→ 说明约束在**使用处**才成立。

**反例**：`comptime` 不是"更快的运行期代码"。它把工作搬到编译期，换来更长的编译时间和更大的二进制；`inline fn` 更不是优化建议——它**限制**编译器能做什么（官方原话：可能伤害二进制大小、编译速度甚至运行性能），换取调用栈可控、comptime 参数传到返回值等保证，只想提示内联该用 `@branchHint`。

**验收**：写出泛型栈、泛型最小堆或固定容量环缓冲，并给出一处 `@compileError` 把非法用法挡在编译期。

---

# 8．阶段 6：工程化（从单文件到一个项目）

读：[Compilation Model](https://ziglang.org/documentation/0.17.0/#Compilation-Model) → [Zig Build System](https://ziglang.org/documentation/0.17.0/#Zig-Build-System) → [Optimization Mode](https://ziglang.org/documentation/0.17.0/#Optimization-Mode) → [Illegal Behavior](https://ziglang.org/documentation/0.17.0/#Illegal-Behavior) → [Style Guide](https://ziglang.org/documentation/0.17.0/#Style-Guide)

要建立的三个模型：

1. **模块图**：每个 `.zig` 文件隐式是一个 struct；`@import` 引入的是**模块名**；根模块的名字是 `root`，标准库是 `std`。所以"仓库里所有文件都能互相 `@import` 相对路径"是错的，跨模块要经过 build 声明。
2. **构建图**：`build.zig` 是 Zig 程序，用 `std.Build` DSL 声明产物与步骤，由 runner 并行执行并缓存；`build.zig.zon` 声明包身份与依赖。
3. **行为随模式变化**：`debug`（默认，安全开）、`safe`（优化开、安全开）、`fast`（安全关）、`small`（安全关）。**安全关掉后，被检查的非法行为退化为"未定义"类行为。**

```zig
const std = @import("std");

pub fn build(b: *std.Build) void {
    const target = b.standardTargetOptions(.{});
    const optimize = b.standardOptimizeOption(.{});

    const exe = b.addExecutable(.{
        .name = "count",
        .root_module = b.createModule(.{
            .root_source_file = b.path("src/main.zig"),
            .target = target,
            .optimize = optimize,
        }),
    });
    b.installArtifact(exe);

    const run_cmd = b.addRunArtifact(exe);
    run_cmd.step.dependOn(b.getInstallStep());
    run_cmd.addPassthruArgs();          // 0.17：不再有 b.args
    b.step("run", "Run the app").dependOn(&run_cmd.step);

    const tests = b.addTest(.{ .root_module = exe.root_module });
    b.step("test", "Run unit tests").dependOn(&b.addRunArtifact(tests).step);
}
```

`zig init` 生成的 `build.zig.zon` 关键字段：`.name`（枚举字面量）、`.version`、`.fingerprint`、`.minimum_zig_version`、`.paths`、`.dependencies`（`url` + `hash` 或 `path`）。

**类比卡：`build.zig` vs Cargo/Make**

| 项目 | 内容 |
| :--- | :--- |
| 相似关系 | 都描述产物、依赖、目标平台、测试步骤 |
| 不能迁移 | `build.zig` 不是声明式配置，而是**可执行的构建程序**；缓存键由构建图决定；`zig build` 本身就是编译器能力，不依赖外部工具链 |
| 影响 | 想加"自定义步骤"不需要插件系统；代价是构建脚本本身要能编译、也要看懂 `std.Build` 的 API |

**可检验预测**：`zig build-exe x.zig -OReleaseFast` 下让数组越界，程序**不保证** panic（官方：fast/small 默认关闭安全检查）。→ 用同一段越界代码分别以 `-OReleaseSafe` 与 `-OReleaseFast` 构建对比。

**反例**：`zig build` 成功 ≠ 测试跑过。`zig build` 只跑默认步骤；测试要 `zig build test`（或把测试挂到默认步骤上）。

**验收**：项目里能定位一次构建错误（模块/依赖）、一次测试失败（断言/泄漏）、一次 panic（安全检查）分别发生在哪个阶段。

---

# 9．阶段 7：系统边界（C、布局、原子、目标平台）

读：[C](https://ziglang.org/documentation/0.17.0/#C) → [Atomics](https://ziglang.org/documentation/0.17.0/#Atomics) → [Assembly](https://ziglang.org/documentation/0.17.0/#Assembly) → [Targets](https://ziglang.org/documentation/0.17.0/#Targets) → [Compile Variables](https://ziglang.org/documentation/0.17.0/#Compile-Variables) → [WebAssembly](https://ziglang.org/documentation/0.17.0/#WebAssembly) → [Async Functions](https://ziglang.org/documentation/0.17.0/#Async-Functions)

**C 互操作三个入口**（0.17 实测）：

| 需求 | 做法 |
| :--- | :--- |
| 调用已有 C 函数 | `extern fn` + 编译时链接（`-lc` / `-l<name>`），类型用 `c_int`、`c_char`、`anyopaque` 等 |
| 用 C 头文件 | `zig translate-c` 生成 `.zig`，或在 build 里 `b.addTranslateC`；不能翻译的构造会被降级为 `opaque` / `extern` / `@compileError` |
| 被 C 调用 | `pub export fn`，注意导出符号与 ABI |

**`@cImport` / `@cInclude` 在 0.17 已不存在**——直接写会得到 `invalid builtin function: '@cImport'`。所有"用 `@cImport` 包一下头文件"的老教程在本版本失效。

```zig
const std = @import("std");
extern fn strlen(s: [*:0]const u8) usize;

test "call libc" {
    try std.testing.expectEqual(@as(usize, 3), strlen("abc"));
}
// zig test cext.zig -lc
```

**类比卡：`volatile` 与内存序**

| 项目 | 内容 |
| :--- | :--- |
| 旧参照 | C 的 `volatile`（访问不得被优化掉）、C11 原子操作 |
| 相似关系 | 名字与语义接近，都用于"编译器不能随意改写的访问" |
| 不能迁移 | `volatile` **不是同步原语**，不提供原子性也不提供顺序保证；多线程共享数据要用 `@atomicLoad` / `@atomicRmw` / `@cmpxchg*` 并指定内存序 |
| 影响 | 并发正确性不能靠"关掉优化就好了"；官方 langref 的 Atomics 一节目前仍是 TODO，实际以 `@atomic*` 内建与 `std.atomic` 为准 |

**异步的现状**：langref 明确写 "Async functions regressed with the release of 0.11.0"，计划以更底层的原语重新引入。所以：**现在不要按旧 async/await 教程学 Zig 并发**，先学线程 + 原子 + `std.Io` 的 I/O 模型。

**验收**：写一个二进制格式解析器（头部字段、长度前缀、校验），显式选择 `extern`/`packed` 布局，处理字节序与截断输入；再用 translate-c 调一个真实 C 库并从 `build.zig` 串起来。

---

# 10．阶段 8：标准库与源码（判断契约，而不是背 API）

读：`zig std` 起的本地文档（随安装版本，永远与编译器一致）→ `lib/std/` 源码目录。

0.17 的标准库有两个"必须先知道"的结构性事实：

1. **I/O 是显式的**：文件操作通过 `std.Io` 接口与 `std.Io.Dir` / `std.Io.File` 进行，`io` 实例来自 `main(init)` 的 `init.io`；读写需要传缓冲区（`file.reader(io, &buf)` / `file.writer(io, &buf)`），流式接口如 `writeStreamingAll(io, bytes)`。
2. **容器管理方式不统一**：`std.ArrayList(T)` 是非托管（`.empty` + 传 allocator），`std.StringHashMap(V)` 是托管（`.init(gpa)`）。以 `lib/std` 源码为准，不靠记忆。

一个完整可跑的最小程序（读文件 → 分词计数 → 排序输出），把前 6 个阶段串起来：

```zig
const std = @import("std");

const Word = struct { text: []const u8, n: usize };

pub fn main(init: std.process.Init) !void {
    const gpa = init.gpa;
    const io = init.io;

    const args = try init.minimal.args.toSlice(init.arena.allocator());
    if (args.len < 2) return error.MissingPath;

    const bytes = try std.Io.Dir.cwd().readFileAlloc(io, args[1], gpa, .limited(1 << 20));
    defer gpa.free(bytes);

    var counts = std.StringHashMap(usize).init(gpa);
    defer counts.deinit();
    var it = std.mem.tokenizeAny(u8, bytes, " \t\r\n");
    while (it.next()) |word| {
        const gop = try counts.getOrPut(word);
        if (!gop.found_existing) gop.value_ptr.* = 0;
        gop.value_ptr.* += 1;
    }

    var rows: std.ArrayList(Word) = .empty;
    defer rows.deinit(gpa);
    var entries = counts.iterator();
    while (entries.next()) |e| try rows.append(gpa, .{ .text = e.key_ptr.*, .n = e.value_ptr.* });

    std.mem.sort(Word, rows.items, {}, struct {
        fn lt(_: void, a: Word, b: Word) bool {
            return a.n > b.n;
        }
    }.lt);

    var buf: [256]u8 = undefined;
    const stdout = std.Io.File.stdout();
    for (rows.items) |row| {
        try stdout.writeStreamingAll(io, try std.fmt.bufPrint(&buf, "{d}\t{s}\n", .{ row.n, row.text }));
    }
}
```

注意这里所有权的流动：`bytes` 由 `gpa` 分配、`gpa` 释放；`counts` 的 key 借用 `bytes`；`rows` 借用 key，不复制字符串。**如果把 `rows` 移出函数，就得先让 key 有独立生命周期。**

**验收**：挑一个标准库 API（例如 `std.Io.Reader.allocRemaining` 或 `ArrayList` 的增长策略），用源码回答：谁分配、失败时是否已分配、返回值借用谁、多大 O(n)。

---

# 11．类比速查表（不能迁移的性质放右边）

| 概念 | C | Rust | Zig | 不可迁移的部分 |
| :--- | :--- | :--- | :--- | :--- |
| 整数 | 宽度随平台 | 固定位宽 | 固定位宽 + `comptime_int` | 无隐式转换，溢出操作显式 |
| 字符串 | `char*` + NUL | `String` / `&str` | `[]const u8`（可带哨兵） | 切片不拥有内存、不保证 UTF-8 |
| 指针 | `*T`，可空，可算术 | `&T` / `&mut T`（借用检查） | `*T` 非空、`[*]T` 多项、`?*T` 可空 | 无生命周期检查，悬垂=未检查非法行为 |
| 结构体 | 平台布局 | `repr(Rust)` 可重排 | 默认布局不保证 ABI；`extern` / `packed` 显式 | 默认布局不能当序列化格式 |
| 和类型 | 手写 tag + union | `enum` | `union(enum)` | `enum` 只是整数集 |
| 错误 | 返回码 / errno | `Result` + `?` | `E!T` + `try`/`catch`/`errdefer` | 错误集是值，不是异常；`catch {}` 会吞掉 |
| 缺失 | NULL | `Option<T>` | `?T` + `orelse` | `?*T` 零开销；没有空引用 |
| 泛型 | 宏 / `void*` | trait bound | `comptime` 参数 + 编译期鸭子类型 | 约束在实例化时才检查 |
| 内存 | `malloc/free` 全局 | `Box/Vec` 默认堆 | `Allocator` 显式传参 | 没有默认分配器，库必须接收 allocator |
| 清理 | `goto cleanup` | `Drop` | `defer` / `errdefer` | 绑定作用域，不追踪所有权转移 |
| 构建 | Make/CMake | Cargo | `build.zig` + `build.zig.zon` | 构建逻辑是可执行程序 |
| C 互操作 | 本体 | bindgen | `extern` / `translate-c` / `addTranslateC` | `@cImport` 已移除 |

---

# 12．五个反向设问（旧直觉会在这里断）

| 旧直觉 | 顺着推会得到 | 断点 | 修正 |
| :--- | :--- | :--- | :--- |
| "Zig 是内存安全的 C" | 编译通过就不会有内存错误 | use-after-free、悬垂指针、重复释放仍是 unchecked；`fast`/`small` 下安全检查默认关闭 | 安全 = 一部分检查；用测试分配器 + `safe` 模式 + 审阅所有权约定 |
| "编译通过 = 行为确定" | Debug 下会 panic 的代码在发布版也 panic | 关闭安全检查后同一代码变成"任意行为" | 边界逻辑必须在 ReleaseSafe 下跑测试 |
| "`defer` 就像析构函数" | 资源会跟着值自动释放 | `defer` 跟着作用域走；值被返回/复制到别处不会触发 | 所有权写在文档里，泄漏交给 `std.testing.allocator` 暴露 |
| "`comptime` 就是宏" | 可以在编译期任意改语法 | 没有宏展开、没有卫生性问题，也没有模板特化语法 | 想复用就用参数化类型与函数；想约束就用 `@compileError` |
| "分配器就是 malloc" | 库可以自己决定从哪分配 | 库内固定分配器会破坏可复用性，也无法注入 arena/FBA | 库接收 `Allocator`，应用在 `main` 决定 |
| "错误处理就是异常" | 不写 `try` 也会自动向上传播 | 不写就丢掉返回值（编译错误）或被 `catch {}` 静默吞掉 | 审阅所有 `catch`，用 `errdefer` 覆盖失败路径 |

按[[参考学习法]]第六节，出现这些信号就该缩小类比：每解释一句要补很多例外、总想给每个概念找旧对应物、比喻顺但答不出具体问题、类比与官方定义冲突时先怀疑类比、已经能独立解释机制与反例。

---

# 13．学习卡（每个概念填一张）

| 项目 | 要回答的问题 | 已填示例：`Allocator` |
| :--- | :--- | :--- |
| 当前问题 | 我为什么现在需要学它 | 需要一个长度可变的缓冲区，且不希望库替我决定堆策略 |
| 新概念 | 名称与正式含义 | 分配器是带函数指针的接口值，显式传入需要内存的函数 |
| 旧参照 | 真正熟悉的哪个概念 | C 的 `malloc/free` 这对全局函数 |
| 相似关系 | 哪一种作用/结构/约束相似 | 都提供"申请一块字节、之后归还"的能力 |
| 关键差异 | 哪些旧性质不能带过来 | 没有全局默认；分配失败要返回 `error.OutOfMemory`；分配器本身可以被固定缓冲、arena 或测试替身实现 |
| 可检验预测 | 用这个理解能预测什么 | 用 `FixedBufferAllocator` 跑同一段代码，超出容量应得到 `OutOfMemory` 而不是崩溃或扩展 |
| 反例与修正 | 什么会让理解失效 | 以为"传入 allocator 就自动安全"——长度与生命周期仍要自己管 |
| 独立解释 | 不提旧参照能否说明 | 能：分配器是调用方注入的策略对象，决定每次分配的来源与失败语义 |

其余概念的卡片留在练习里填：切片、`union(enum)`、`error` 集、`defer`、`comptime`、`extern struct`、`std.Io`。

---

# 14．项目阶梯

| 版本 | 项目 | 覆盖阶段 | 完成判据 |
| :--- | :--- | :--- | :--- |
| V1 | 词频统计（本页第 10 节） | 1–4、8 | 参数缺失、文件不存在、空文件都有确定行为；`zig build test` 通过 |
| V2 | 动态数组 + 字符串构建器 + arena 版 CSV 解析 | 2、4 | 扩容后旧指针失效的实验能复现；删掉一处 `defer` 后测试分配器报泄漏 |
| V3 | 泛型容器库（栈/队列/最小堆）+ 错误集设计 | 3、5 | 非法类型实例化时报错来自你的 `@compileError`，而不是库内部 |
| V4 | 二进制格式解析器（长度前缀 + 校验 + 字节序） | 2、3、7 | 截断输入、超长长度、错位字节都返回明确错误；`extern`/`packed` 选择有理由 |
| V5 | C 库互操作 + `build.zig` 集成 + 跨目标构建 | 6、7 | `zig build`、`zig build test`、`-Dtarget=` 交叉构建均可用 |
| V6 | 性能与安全性实验：同一程序在四种优化模式下对比 | 6 | 能解释每处差异来自安全检查、内联，还是缓存/分配 |

每轮固定动作：读一节 → 写最小例子 → 造一个错误 → 定位 → 回填项目 → 与 C 版对照（[[C & Zig 混合学习之路]] 的表格可直接复用）。

---

# 15．0.17 版本专属陷阱（实测）

| 现象 | 原因 | 处理 |
| :--- | :--- | :--- |
| `invalid builtin function: '@cImport'` | 0.17 已移除 `@cImport` / `@cInclude` | 用 `zig translate-c` 或 `b.addTranslateC` |
| `main` 参数报错 / 拿不到 argv | 0.17 入口可接收 `std.process.Init`（`io`、`gpa`、`arena`、`environ_map`、`preopens`、`minimal.args`） | `pub fn main(init: std.process.Init) !void`；参数用 `init.minimal.args.toSlice(init.arena.allocator())` |
| `std.ArrayList` 没有 `init(gpa)` | `ArrayList` 是非托管类型 | `.empty` + `append(gpa, x)` + `deinit(gpa)` |
| `StringHashMap` 没有 `empty` | HashMap 是托管类型 | `.init(gpa)` + `deinit()` |
| `b.args` 不存在 | build API 变更 | `run_cmd.addPassthruArgs()` |
| 文件读写老写法编译失败 | I/O 走 `std.Io`，`io` 实例显式传入 | `Dir.cwd().readFileAlloc(io, path, gpa, .limited(n))`；`File.stdout().writeStreamingAll(io, bytes)` |
| `Struct{ ... }.method()` 语法错误 | 字面量后直接点调用解析歧义 | 加括号：`(Struct{ ... }).method()` |
| 想找 async/await | 0.11 起回退，尚未以旧形式回归 | 学线程 + `@atomic*` + `std.Io`，不要按旧教程学 |
| 文档与编译器不一致 | 网上多为旧版本 | 以本机 `zig std` 与 `lib/std` 源码为准 |

---

# 16．核对入口

- 语言参考（本章节锚点即上文链接）：[0.17.0 langref](https://ziglang.org/documentation/0.17.0/)；常用锚点：`#Values`、`#Slices`、`#Pointers`、`#Errors`、`#Optionals`、`#Memory`、`#comptime`、`#Illegal-Behavior`、`#Compilation-Model`、`#C`。
- 标准库文档：`zig std`（本地服务，版本永远与编译器一致）。
- 构建系统：`zig build --help`、`zig init` 生成的注释版 `build.zig`。
- 本机命令核对：`zig version`、`zig test x.zig`、`zig build-exe x.zig -OReleaseSafe`、`zig translate-c header.h`。
- 姊妹篇：[[C & Zig 混合学习之路]]（按主题的 C/Zig 对照表与 h/c 文件分离讨论）。

**可检查的入门完成线**：不谈"像不像 C"，能独立回答——这段数据的地址、长度、容量在哪；谁分配谁释放；失败时哪些资源已被获取；哪些错误在编译期发现、哪些在安全检查下 panic、哪些完全没人管。


> Windows 用户态逆向调试工具。

本身通过**断点+日志**，规范如下：

# 1. 打点

**（1）软件断点（最常用）**
- 在 CPU 反汇编窗口，点击目标指令行左侧的圆点 → 变红即为断点（写入 `0xCC`）。
- 适用：代码段指令。缺点是会修改内存，某些自校验程序会检测到。

**（2）硬件断点（Dr 0–Dr 3）**
- 右键指令 → `Breakpoint → Set Hardware Breakpoint`。
- 适用：**数据访问断点**（在 Dump 窗口右键某地址 → `Follow in Dump` → 再右键 → `Breakpoint → Hardware, Access/Write`），用于追踪"谁改了这个变量"。
- 优点：不改内存，最多 4 个。

**（3）内存断点（Memory Breakpoint）**
- 对整页内存设访问/写入断点，用于大范围监控，但性能开销大，慎用。

**（4）日志断点（Log Breakpoint，"打点"核心）**
- 右键断点 → `Edit` → 勾选 `Log Text`，填入表达式，例如：
  ```
  rip={rip} rax={rax} [rsp]={[rsp]} str={s:[[rsp+8]]}
  ```
- 勾选 `Log` 但不勾 `Break` → 程序不停，只在 Log 窗口打印。这就是**非侵入式打点**，适合高频调用点。

**（5）条件断点**
- 右键断点 → `Edit` → `Condition`，例如 `rax==0x1234 && [rcx+8]>100`。
- 配合 `Log` 使用，可只记录满足条件时的现场。

**（6）脚本打点（自动化）**
- 在 Script 标签页写：
  ```
  bp 0x401000, "log \"hit rax={rax}\""
  run
  ```
- 适合批量下点、自动跑样本。

# 2. 采集

- `F9` 运行，`F7` 步入，`F8` 步过，`F4` 运行到光标。
- Log 窗口（`View → Log`）查看所有打点输出。
- 用 `Scylla`（x64dbg 内置）做 IAT 重建、Dump 内存镜像。
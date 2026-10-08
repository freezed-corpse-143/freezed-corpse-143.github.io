内核级剖析

ncu 的“埋桩”是**NVTX 过滤+指标聚焦**，用来只采集你关心的那个 kernel。

# 埋桩打点

**（1）代码内 NVTX 标记（推荐）**
```python
import torch.cuda.nvtx as nvtx
nvtx.range_push("attention")   # 要分析的 kernel 都在这个范围
...
nvtx.range_pop()
```
```c
nvtxRangePushA("attention");
kernel<<<...>>>(...);
nvtxRangePop();
```

**（2）代码内直接控制采集**
```c
cudaProfilerStart();
kernel<<<...>>>(...);
cudaProfilerStop();
```

**（3）用 kernel 名过滤（不改代码）**
```bash
ncu --kernel-name regex:attention --launch-skip 5 --launch-count 1 ./app
```

# 采集

```bash
# 全量指标（慢，但全）
ncu --set full -o report ./app

# 只采集 NVTX 范围 attention 内的 kernel
ncu --nvtx --nvtx-include "attention/" -o report ./app

# 只分析指定 kernel，跳过前 5 次，取第 6 次
ncu --kernel-name regex:attention --launch-skip 5 --launch-count 1 -o report ./app

# 指定指标集，避免全量太慢
ncu --metrics sm__throughput.avg.pct_of_peak_sustained_elapsed,\
dram__throughput.avg.pct_of_peak_sustained_elapsed,\
sm__warps_active.avg.pct_of_peak_sustained_active -o report ./app

# 只看 speed-of-light（快速定位瓶颈）
ncu --set speedoflight -o report ./app
```

参数说明：
- `--set`：`full` / `speedoflight` / `memory` / `compute` 等预设集。
- `--nvtx` + `--nvtx-include`：按 NVTX 范围过滤（注意范围名后加 `/`）。
- `--kernel-name`：`regex:` / `exact:` / `substr:` 匹配。
- `--launch-skip` / `--launch-count`：跳过预热，取稳定态。
- `--replay-mode`：`kernel`（默认，重放 kernel）/ `application` / `range`。

# 解读输出

**（1）命令行直接看：**
```bash
ncu --set speedoflight ./app
```
会打印每个 kernel 的 **Speed of Light** 两行：
- **Compute (SM) Throughput**：计算单元利用率。
- **Memory Throughput**：显存带宽利用率。

判读：
- 两者都低 → **延迟隐藏不足**（occupancy 低、依赖链长）。
- Compute 高、Memory 低 → **计算受限**，看指令 mix、分支。
- Memory 高、Compute 低 → **访存受限**，看是 DRAM 还是 L2/共享内存。

**（2）GUI（`ncu-ui report.ncu-rep`）主要看板：**

| 看板                   | 关键指标              | 判读                                              |
| ---------------------- | --------------------- | ------------------------------------------------- |
| Speed Of Light         | SM % / Memory %       | 先定位大方向                                      |
| Occupancy              | Achieved Occupancy    | 低于理论值 → 寄存器/共享内存限制                  |
| Memory Workload        | DRAM/L2/Shared 读写量 | 是否有 bank conflict、是否未合并访问              |
| Scheduler / Warp State | Stall 原因分布        | `Stall Long Scoreboard`=访存等，`Stall Wait`=依赖 |
| Instruction Stats      | 指令数、分支效率      | 分支发散、指令过多                                |
| Source Counters        | 源码级热点            | 直接定位到哪一行                                  |
**（3）规范判读顺序：**
1. 看 **Speed of Light** 定方向（计算 or 访存 or 延迟）。
2. 看 **Occupancy** 判断是否因资源限制导致并行度不足。
3. 看 **Warp State / Stall** 找具体卡在哪。
4. 看 **Memory Workload** 确认访存模式（合并、bank conflict、L 2 命中）。
5. 看 **Source Counters** 落到源码行。
6. 改代码 → 重跑同一命令 → 对比指标变化。
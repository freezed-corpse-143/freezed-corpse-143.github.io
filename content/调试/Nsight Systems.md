系统级时间线
nsys 的“埋桩”是**NVTX**，用来给代码区间打标签，让时间线上能对应到业务逻辑。

# 埋桩打点（NVTX）

**C/C++：**
```c
#include <nvtx3/nvToolsExt.h>
nvtxRangePushA("preprocess");
// ... 代码 ...
nvtxRangePop();

// 或者带颜色的 range
nvtxRangePushEx(&(nvtxEventAttributes_t){
    .message.ascii = "inference",
    .color = 0xFF00FF00,
    .payloadType = NVTX_PAYLOAD_TYPE_INT64,
    .payload.llValue = batch_size
});
```

**Python：**
```python
import torch.cuda.nvtx as nvtx
with nvtx.range("dataloader"):
    ...
nvtx.range_push("forward"); ...; nvtx.range_pop()
```

**CUDA Profiler API（控制采集区间）：**
```c
cudaProfilerStart();
// 只关心这段
cudaProfilerStop();
```

# 采集

```bash
# 基础：全量采集
nsys profile -o report ./app

# 只采集 cudaProfilerStart/Stop 之间
nsys profile -c cudaProfilerApi -o report ./app

# 只采集 NVTX 范围
nsys profile -c nvtx -o report ./app

# 跳过预热，限制采集时长
nsys profile --delay 5 --duration 10 -o report ./app

# 常用附加项
nsys profile -t cuda,nvtx,osrt,cudnn,cublas -o report ./app
```

参数说明：
- `-t`：追踪哪些 API 层（cuda / nvtx / osrt / cudnn / cublas / openmp 等）。
- `-c`：采集模式（`cudaProfilerApi` / `nvtx` / `none`）。
- `--delay` / `--duration`：延迟和时长，单位秒。
- `--sample`：CPU 采样（默认 cpu 采样是 none，要显式开）。

# 解读输出

**（1）命令行统计（不开 GUI）：**
```bash
nsys stats report.nsys-rep
```
输出几张关键表：
- **CUDA API 统计**：每个 API 的调用次数、总耗时、平均耗时。找 `cudaMalloc` / `cudaMemcpy` / `cudaLaunchKernel` 的异常大户。
- **Kernel 统计**：每个 kernel 的调用次数、总时长、平均时长。找总耗时最高的 kernel。
- **内存操作统计**：HtoD/DtoH/DtoD 拷贝的量和耗时。

**（2）GUI（`nsys-ui report.nsys-rep`）时间线判读：**

| 现象                  | 含义                 | 下一步                    |
| ------------------- | ------------------ | ---------------------- |
| CUDA API 条很长，GPU 条空 | CPU 侧阻塞，GPU 闲着     | 看是同步拷贝、锁、还是 Python GIL |
| Kernel 之间有空隙        | launch 开销或 CPU 没跟上 | 看 API 行是否有大量小 launch   |
| HtoD/DtoH 频繁且大      | 数据搬运是瓶颈            | 考虑 pinned memory、合并传输  |
| NVTX 区间与 GPU 活动不对齐  | 逻辑与执行错位            | 定位到具体阶段                |

**核心思路**：先看 GPU 利用率（有没有大段空白），再看 CPU 是否在等，最后定位到具体 API 或 kernel。

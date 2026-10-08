**调试 NCCL 通信，核心是查清三个问题：所有 rank 是否执行了匹配的通信操作、NCCL 实际走了哪条链路、时间花在等待还是传输。**

# 先开 NCCL 日志，确认通信路径

在启动训练**之前**设置：

```
mkdir -p /tmp/nccl-logs

export NCCL_DEBUG=INFO
export NCCL_DEBUG_SUBSYS=INIT,BOOTSTRAP,NET,GRAPH,ENV
export NCCL_DEBUG_FILE=/tmp/nccl-logs/nccl.%h.%p.log

torchrun --standalone --nproc_per_node=2 train.py
```

多机时，每个节点都要设置这些变量并收集日志。`%h` 是主机名，`%p` 是进程号，避免不同进程写入同一个文件。官方支持按子系统过滤日志，也支持用 `TRACE + CALL` 追踪调用。[NCCL 2.31.2 documentation](https://docs.nvidia.com/deeplearning/nccl/archives/nccl_2312/user-guide/docs/troubleshooting/logging.html?utm_source=chatgpt.com)

重点看这些信息：

| 日志信息                     | 要确认的问题                  |
| ---------------------------- | ----------------------------- |
| rank、nranks、cudaDev、busId | 进程数、GPU 绑定是否正确      |
| Bootstrap 使用的接口         | 初始化连接是否选对网卡        |
| `NET/IB`、`NET/Socket`       | 数据通信使用 RDMA 还是 Socket |
| P 2 P、SHM、拓扑信息           | 节点内实际使用什么传输方式    |
| `WARN`、初始化完成位置       | 哪个 rank 最先出现异常        |

**Bootstrap 网卡和实际传输数据的网卡可以不同。** 看到初始化使用以太网接口，并不意味着数据通信没有使用 RDMA。

若需要追踪具体调用，再单独运行：

```
export NCCL_DEBUG=TRACE
export NCCL_DEBUG_SUBSYS=CALL
```

TRACE 输出很多，适合短小复现。

# 卡住时，先检查 rank 是否“对的上”

例如：

```
rank 0：AllReduce(A) → AllReduce(B)
rank 1：AllReduce(B) → AllReduce(A)
```

即使两个 rank 都调用了 AllReduce，顺序不同也可能卡住或产生错误。还需要检查：

- 是否有 rank 提前报错、退出，或者卡在数据加载。
- collective 的类型、顺序、数据类型、元素数量是否满足匹配要求。
- 是否有条件分支导致只有部分 rank 调用通信。
- Send/Recv 的对端及消息是否匹配。

对于 PyTorch，可以开启更详细的一致性检查：

```
export TORCH_CPP_LOG_LEVEL=INFO
export TORCH_DISTRIBUTED_DEBUG=DETAIL
```

该模式能帮助报告 collective 的不一致，也会增加调试开销。[torch.distributed — PyTorch 2.14 documentation](https://docs.pytorch.org/docs/stable/distributed.html?utm_source=chatgpt.com)

**NCCL timeout 只说明通信没有按时完成；根因可能是另一个 rank 更早发生的异常。** 所以要对照所有 rank 的日志，而不是只看报 timeout 的那个进程。

# 在通信前后打点，区分“提交”与“完成”

NCCL 通信涉及异步 GPU 执行。Python 函数返回，不代表 GPU 已完成通信。

下面是一个用于定位问题的打点方式，假设已经初始化进程组并绑定了当前 GPU：

```
import timeimport torchimport torch.distributed as distdef mark(message):    print(        f"time={time.monotonic():.6f} "        f"rank={dist.get_rank()} {message}",        flush=True,    )# 定位用：先排除前序 CUDA 工作的影响torch.cuda.synchronize()mark("seq=17 all_reduce before")with torch.cuda.nvtx.range("seq17/all_reduce"):    work = dist.all_reduce(x, async_op=True)    mark("seq=17 all_reduce submitted")    work.wait()    torch.cuda.synchronize()    mark("seq=17 all_reduce GPU completed")
```

输出的解读：

| 停在哪里                                | 下一步重点检查                          |
| --------------------------------------- | --------------------------------------- |
| 某个 rank 没打印 `before`               | 该 rank 的前序计算、数据加载、异常      |
| 都打印了 `before`，部分没有 `submitted` | 主机端调用、初始化、通信顺序            |
| 都打印了 `submitted`，没有完成          | collective 匹配、GPU 前序依赖、链路故障 |

最好记录 `step、通信序号、进程组、操作、shape、dtype`，这样能对齐不同 rank 的事件。不同机器的 `monotonic()` 时间不能直接比较，应主要依靠序号对齐。

这里的同步会改变计算与通信的重叠，**适合定位卡点；正常性能采样应移除额外同步，保留 NVTX 标记。**

对于支持 Flight Recorder 的 PyTorch 版本，还可以开启超时诊断：

```
export TORCH_NCCL_TRACE_BUFFER_SIZE=20000
export TORCH_NCCL_DUMP_ON_TIMEOUT=1
```

它会记录通信事件，在 watchdog 超时时导出诊断信息；启用超时导出必须同时设置非零 trace buffer。[PyTorch 2.14 documentation](https://docs.pytorch.org/docs/stable/torch_nccl_environment_variables.html?utm_source=chatgpt.com)

# 用 nccl-tests，把训练代码和通信环境分开检查

如果已经编译了 NVIDIA 的 [nccl-tests](https://github.com/NVIDIA/nccl-tests?utm_source=chatgpt.com)，先测单机双卡：

```
./build/all_reduce_perf -b 8 -e 128M -f 2 -g 2
```

它从 8 字节测到 128 MiB，每次大小翻倍，使用两张 GPU。多机测试需要使用 MPI 构建和相应的启动配置。[NVIDIA/nccl-tests: NCCL Tests · GitHub](https://github.com/NVIDIA/nccl-tests?utm_source=chatgpt.com)

重点看：

| 指标     | 含义                             |
| -------- | -------------------------------- |
| `time`   | collective 耗时                  |
| `algbw`  | 数据大小除以耗时                 |
| `busbw`  | 根据 collective 通信量换算的带宽 |
| `#wrong` | 正确性检查错误数                 |

`busbw` 是归一化指标，不是网卡实际吞吐的直接读数。[GitHub](https://github.com/NVIDIA/nccl-tests/blob/master/doc/PERFORMANCE.md?plain=1&utm_source=chatgpt.com)

逐步扩大测试范围：

1. 单机两卡。
2. 单机所有卡。
3. 两机各一卡。
4. 两机所有卡。
5. 完整集群。

**在哪一步首次异常，就优先检查该步新引入的链路或拓扑。** 如果 nccl-tests 正常而训练异常，重点转向训练中的通信顺序、消息大小、rank 到达时间和计算重叠。

# 通信慢，用 nsys 看“谁在等谁”

基础采样：

```
nsys profile \
  --trace=cuda,nvtx,osrt \
  -o nccl-profile \
  torchrun --standalone --nproc_per_node=2 train.py
```

新版 Nsight Systems 还支持 NCCL 专用 tracing；是否可用要结合本机版本和 `nsys profile --help` 检查。[Nsight Systems](https://docs.nvidia.com/nsight-systems/UserGuide/index.html?utm_source=chatgpt.com)

打开 `.nsys-rep` 后，对齐你的 NVTX 标记、CUDA stream 和 NCCL kernel：

| 时间线现象               | 可能原因                     |
| ------------------------ | ---------------------------- |
| 一个 rank 很晚才发起通信 | 数据加载或计算不均衡         |
| NCCL kernel 执行很长     | 传输慢，或正在等待其他 rank  |
| 大量很短的通信           | 消息过碎，启动和延迟开销大   |
| 计算与通信没有重叠       | 依赖关系、同步或调度需要检查 |

**长 NCCL kernel 不等于网络带宽低：它可能在等迟到的 rank。** 因此最好采集参与同一次通信的各个 rank。

nsys 适合先看整体通信与计算关系；ncu 更适合在已经定位到具体 kernel 后分析其 GPU 执行细节。

# 最后才改通信选项，做单变量对照

例如临时禁用 IB/RDMA：

```
NCCL_IB_DISABLE=1 torchrun ...
```

或临时禁用节点内 P 2 P：

```
NCCL_P2P_DISABLE=1 torchrun ...
```

如果禁用某条路径后恢复正常，说明值得继续检查该路径，但还不能单凭这一点确定根因。每次只改一个变量并保留原始基线；NCCL 官方也建议调试选项不要长期保留在生产配置中。[GitHub](https://github.com/NVIDIA/nccl/blob/master/docs/userguide/source/env.rst?utm_source=chatgpt.com)

实际排查时，最有价值的一组证据是：**所有 rank 的日志、最后一个匹配的通信序号、nccl-tests 结果，以及一小段带 NVTX 标记的 nsys 时间线。**
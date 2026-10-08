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

# 
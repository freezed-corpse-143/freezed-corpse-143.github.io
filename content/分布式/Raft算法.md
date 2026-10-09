**Raft 是一种让多台机器对“按什么顺序执行哪些操作”达成一致的算法。** 即使部分机器宕机、网络断开或消息延迟，已经确认成功的操作也不会被后来的 Leader 推翻。

# 为什么需要 Raft？

假设 A、B、C 三台机器共同维护一个变量：

```
x = 0
```

客户端同时发来两个操作：

```
设置 x = 1
设置 x = 2
```

如果每台机器独立接收、执行：

| 节点  | 执行顺序         | 最终结果  |
| --- | ------------ | ----- |
| A   | 设置为 1，再设置为 2 | x = 2 |
| B   | 设置为 2，再设置为 1 | x = 1 |
| C   | 只收到设置为 1     | x = 1 |

问题不只是“有没有收到数据”，还包括**操作顺序是否一致**。

Raft 的做法是：先对一份有序日志达成一致，再按日志执行。

```
日志：
第 1 条：设置 x = 1
第 2 条：设置 x = 2
```

只要各节点的状态机是确定性的，从相同初始状态执行相同日志，就会得到相同结果。这就是**复制状态机**。

这里的“状态机”，可以先理解成你的数据库业务逻辑：

```
def apply(command):    if command.type == "SET":        database[command.key] = command.value
```

Raft 负责确定命令及其顺序；业务逻辑负责执行命令。

# 三种角色，以及 term

每个 Raft 节点处于以下一种角色：

| 角色        | 职责                |
| --------- | ----------------- |
| Follower  | 接收日志、回应投票         |
| Candidate | 发起选举，争取成为 Leader  |
| Leader    | 接收写入、排列日志、推动复制和提交 |

正常情况下，一个集群有一个 Leader，其余是 Follower。

Raft 还有一个重要数字：**term，任期编号**。

```
term 1：A 当选
term 2：选举失败，没有 Leader
term 3：B 当选
```

term 是逻辑编号，不是固定长度的时间段。节点看到更高的 term，就更新自己的 term；Leader 或 Candidate 发现自己的 term 落后，立即退回 Follower。低 term 的请求会被拒绝。

**同一个 term 最多只能选出一个 Leader；不同 term 的节点可能暂时都认为自己是 Leader。** 后面会解释为什么这不会导致双方都提交写入。[raft.github.io](https://raft.github.io/raft.pdf)

# Leader

假设 A、B、C 刚启动，都是 Follower。

Leader 会定期发送心跳。一个 Follower 如果等到选举超时，仍未收到有效的 Leader 消息，就发起选举：

1. 将自己的 term 加一。
2. 转为 Candidate。
3. 给自己投一票。
4. 向其他节点发送 `RequestVote`。
5. 获得整个集群的多数票后成为 Leader。

三节点的多数是两票，包含自己的一票：

```
B 给自己投票。
C 给 B 投票。
B 获得 2 票，成为 Leader。
```

**每个节点每个 term 最多投给一个候选人。**

为什么这能防止同任期出现两个 Leader？因为任意两个多数集合必有交集。两名候选人若都拿到多数票，就必然有某个节点投了两个人，而规则禁止这样做。

选举超时采用随机值，避免所有节点反复同时竞选、瓜分选票。

不过，投票还有日志资格检查，不能谁先来就无条件投谁。[web.stanford.edu](https://web.stanford.edu/~ouster/cgi-bin/papers/raft-extended.pdf)

# 一次写入如何完成？

现在 B 是 term 3 的 Leader，客户端请求：

```
SET x = 7
```

B 先把命令追加到本地日志：

| index | term | command   |
| ----- | ---- | --------- |
| 1     | 3    | SET x = 7 |

两个字段含义不同：

- `index`：日志中的位置。
- `term`：这条日志由哪个任期的 Leader 创建。

正常写入流程如下：

| 步骤  | 行为                  | 此时的含义     |
| --- | ------------------- | --------- |
| 1   | B 持久化日志             | B 自己有了记录  |
| 2   | B 向 A、C 发送日志        | 开始复制      |
| 3   | A 持久化日志，回复成功        | B、A 已构成多数 |
| 4   | B 将该日志标记为 committed | 可以安全执行    |
| 5   | B 执行命令，回复客户端        | 写入成功      |
| 6   | B 通知其他节点提交位置        | 其他节点随后执行  |

C 暂时慢一点，不影响 B 与 A 达成多数。

这里必须区分三个状态：

| 状态             | 含义                                 |
| ---------------- | ------------------------------------ |
| 已记录           | 某个节点保存了日志                   |
| 已提交 committed | 协议保证该日志不会被后续 Leader 推翻 |
| 已应用 applied   | 命令已经执行到业务状态机             |

**有日志不等于已提交；已提交不等于所有节点已经执行。**

上述多数提交规则适用于 Leader 当前 term 的日志，旧 term 日志稍后单独解释。[web.stanford.edu](https://web.stanford.edu/~ouster/cgi-bin/papers/raft-extended.pdf)

# 为什么允许一部分节点落后？

Raft 要保证的核心，并不是所有机器每时每刻的数据都完全相同。

它保证的是：

> 各节点可以执行到不同进度，但不能在同一个日志位置执行不同的命令。

例如：

```
A：已经执行第 1～10 条
B：已经执行第 1～10 条
C：已经执行第 1～8 条
```

这是允许的。C 后续补齐第 9、10 条即可。

但下面是不允许的：

```
A 的第 9 条：SET x = 7，已经执行
C 的第 9 条：SET x = 9，已经执行
```

因此，Raft 允许暂时落后，但不能让已经执行的历史互相矛盾。[raft.github.io](https://raft.github.io/raft.pdf?utm_source=chatgpt.com)

# Leader 宕机后，为什么不会丢掉已提交的数据？

假设：

```
B：有第 1～10 条
A：有第 1～10 条
C：只有第 1～8 条
```

第 10 条由 B 在当前 term 创建，并已提交。现在 B 宕机。

如果 C 随便当选，它缺少第 9、10 条，问题就来了。因此，**投票必须检查候选人的日志是否足够新。**

比较方式是：

1. 先比较最后一条日志的 `term`，更大的更新。
2. 如果最后一条的 term 相同，再比较最后一条的 `index`，更大的更新。

注意：比较的是**最后一条日志的 term**，不是候选人的当前竞选 term；也不是单纯比较日志长度。

在这个例子中，C 的日志落后，A 不会投给 C。C 只有自己一票，无法当选。A 可以获得自己和 C 的票，成为新 Leader。

直观上：

> 保存了已提交日志的多数，与选举所需的多数必然相交；日志资格检查进一步防止丢失已提交历史的候选人当选。

多数交集与完整协议规则共同保证：**以后当选的 Leader 都包含之前已提交的日志。** [web.stanford.edu](https://web.stanford.edu/~ouster/cgi-bin/papers/raft-extended.pdf)

# 日志不一致，怎么修复？

宕机可能留下未提交日志：

| 节点        | index 1      | index 2      | index 3            |
| ----------- | ------------ | ------------ | ------------------ |
| 新 Leader A | 已提交操作 a | 已提交操作 b | 操作 c             |
| Follower B  | 已提交操作 a | 已提交操作 b | 旧 Leader 的操作 d |

第 3 条发生冲突。Raft 要让 B 的日志最终与 A 一致。

Leader 发送 `AppendEntries` 时，不只携带新日志，还携带：

```
prevLogIndex：新日志之前那条日志的位置
prevLogTerm：那条日志的任期
entries：准备追加的日志
leaderCommit：Leader 的提交位置
```

Follower 先检查：

> 我的 `prevLogIndex` 位置，是否存在相同 term 的日志？

- 不匹配：拒绝，Leader 回退复制位置再试。
- 匹配：接收日志；遇到冲突条目，删除冲突条目及后续日志，再追加 Leader 的版本。

这相当于**找到共同前缀，再修复分叉部分**。

已经提交的日志不会被正确执行的 Raft 覆盖；可能被覆盖的是未提交的分叉。[raft.github.io](https://raft.github.io/raft.pdf)

# 网络分区后，会不会出现“脑裂”？

五节点集群，A 是 Leader。网络突然分成：

```
一侧：A、B
另一侧：C、D、E
```

A 可能仍然认为自己是 Leader。另一侧则可能选出 term 更高的新 Leader C。

此时确实可能有两个节点自认为是 Leader，但：

| 分区    | 节点数 | 能否形成多数并提交新写入？ |
| ------- | ------ | -------------------------- |
| A、B    | 2      | 不能                       |
| C、D、E | 3      | 可以                       |

A 可以收到客户端请求，甚至追加未提交日志，但无法拿到多数确认，因此不能正常确认这些写入成功。

网络恢复后，A 看到更高 term，退回 Follower，冲突的未提交日志会被修复。

**Raft 的安全来自多数与任期等协议规则，不能依赖旧 Leader 及时发现自己已失去权力。** [web.stanford.edu](https://web.stanford.edu/~ouster/cgi-bin/papers/raft-extended.pdf)

# 最容易误解的一条：旧任期日志不能直接按多数提交

通常会把 Raft 简化成：

> 一条日志复制到多数节点，就提交。

完整规则更严格。Leader 根据复制数量推进 `commitIndex` 到位置 $N$，还必须满足：

$$ \operatorname{log}[N].\operatorname{term} = \operatorname{currentTerm} $$

也就是：

> **Leader 可以通过多数复制，直接确认自己当前任期的日志提交。**

如果新 Leader 继承了一条旧 term 的未提交日志，仅仅把它补到多数节点，不能据此直接宣布它提交。

正确方式是：

```
index 10：旧 term 的日志
index 11：当前 term 的日志
```

当第 11 条在当前 term 获得多数复制并提交时，前面的第 10 条也随整个前缀一起提交。

原因是：日志新旧比较优先看最后一条的 term。某个拥有更高 term 分叉日志的节点，在特定历史中仍可能当选并覆盖旧条目；当前 term 的多数提交才能建立所需的安全保证。原论文 Figure 8 专门展示了这个反例。[web.stanford.edu](https://web.stanford.edu/~ouster/cgi-bin/papers/raft-extended.pdf?utm_source=chatgpt.com)

初学时先牢牢记住这条规则，之后再推演 Figure 8。

# 如果自己实现，需要哪些核心变量？

| 变量                 | 含义                      |
| ------------------ | ----------------------- |
| `currentTerm`      | 当前已知最高任期                |
| `votedFor`         | 当前任期投给谁                 |
| `log[]`            | 日志序列                    |
| `commitIndex`      | 已知提交到哪个位置               |
| `lastApplied`      | 已经执行到哪个位置               |
| `nextIndex[peer]`  | Leader 下一次准备从哪里给某节点发送日志 |
| `matchIndex[peer]` | Leader 已确认某节点复制到了哪里     |

其中 `currentTerm`、`votedFor` 和日志需要持久化。否则节点重启后，可能忘记已经投过票或确认保存过的日志，破坏安全性。

基本算法主要围绕两种 RPC：

```
RequestVote：请求投票
AppendEntries：复制日志，也用作心跳
```

核心提交逻辑可以概括为：

```
# 仅表示核心判断，省略并发与持久化细节if majority_have_entry(N) and log[N].term == currentTerm:    commitIndex = Nwhile lastApplied < commitIndex:    lastApplied += 1    apply(log[lastApplied].command)
```

原论文 Figure 2 是实现这些状态和处理规则的主要参考。[web.stanford.edu](https://web.stanford.edu/~ouster/cgi-bin/papers/raft-extended.pdf)

# 理解核心之后，还有哪些工程问题？

| 问题    | 为什么还需要处理？                         |
| ----- | --------------------------------- |
| 请求去重  | 写入已提交但回复丢失，客户端重试可能重复执行            |
| 线性一致读 | “自认为是 Leader”不代表仍有权威，直接本地读可能读到旧数据 |
| 快照    | 日志不能无限增长，需要保存状态并压缩旧日志             |
| 成员变更  | 不能随意替换投票集合，否则可能破坏多数交集             |
| 故障模型  | 标准 Raft 处理宕机、断网等故障，不处理节点恶意伪造行为    |

特别注意：**Raft 不会自动把每次客户端请求变成“恰好执行一次”。** 通常要把客户端 ID、请求序号及去重状态纳入复制状态机。[web.stanford.edu](https://web.stanford.edu/~ouster/cgi-bin/papers/raft-extended.pdf)

建议你先用三节点手动推演这三个场景：

1. Leader 写入本地后，尚未复制就宕机。
2. 当前任期的日志已复制到多数，但回复客户端之前宕机。
3. 旧 Leader 被隔离到少数分区，多数分区选出新 Leader。

每次都问：**谁能当选？哪些日志可提交？哪些可能被覆盖？客户端是否知道请求成功？**
设计一套 **Project Operating System / 项目控制系统**。

它的核心不是“把数据展示出来”，而是形成：

$$ \boxed{ 目标 \rightarrow 任务分解 \rightarrow 可行性分析 \rightarrow 资源配置 \rightarrow 执行 \rightarrow 监控 \rightarrow 异常检测 \rightarrow 干预 \rightarrow 验收 \rightarrow 复盘 } $$

然后让 Dashboard 成为这个闭环的**控制面（Control Plane）**。

你提到的“由规则推着人行动”“状态机”“生命周期自动安排人员行动”尤其重要。传统 Dashboard 往往只是 BI 看板；你想做的实际上更接近 **项目管理 + 工作流引擎 + 资源调度系统 + 绩效系统 + 审计系统**。

# 建立理论骨架

我会把项目抽象成 8 个生命周期阶段：

```
Idea / Request
      │
      ▼
① Define
项目定义
      │
      ▼
② Decompose
任务分解
      │
      ▼
③ Feasibility
可行性 / 资源分析
      │
      ▼
④ Plan
计划与资源配置
      │
      ▼
⑤ Execute
执行
      │
      ▼
⑥ Monitor & Control
监控 / 调整 / 风险控制
      │
      ▼
⑦ Acceptance
验收
      │
      ▼
⑧ Close & Review
结项 / 绩效 / 复盘
```

对应经典项目管理理论，可以吸收：

- PMBOK：Scope / Schedule / Cost / Resource / Risk / Quality / Stakeholder
- WBS：任务分解
- CPM / PERT：依赖、关键路径、工期
- RACI：责任划分
- RAID：Risk / Assumption / Issue / Dependency
- EVM：Earned Value Management
- Stage-Gate：阶段验收
- Change Control：变更控制
- PDCA / OODA：反馈循环
- Postmortem：事故复盘

但 Dashboard 不应该按照这些理论名词直接堆模块。

**应该围绕 PM 每天真正需要回答的问题设计。**

# Executive Control Center

首页不要放几十张图。

PM 打开系统，首先应该知道：

> 我的项目现在到底健康不健康？

因此最顶层可以设计成：

```
┌──────────────────────────────────────────────────────────────┐
│ Project Alpha                              🟡 AT RISK        │
│                                                              │
│ Progress       Schedule       Budget       Resources  Quality│
│   67%            -8d           72%           91%       96%   │
│                                                              │
│ Expected Finish                                              │
│ Baseline: Nov 10        Forecast: Nov 18        Δ +8 days    │
├──────────────────────────────────────────────────────────────┤
│ 🔴 3 Critical Blockers                                       │
│ 🟡 5 Risks                                                   │
│ ⚠  2 Resource Shortages                                      │
│ ⏰ 4 Tasks Overdue                                           │
├──────────────────────────────────────────────────────────────┤
│ Critical Path                                                │
│ A ──→ B ──→ C ──→ D ──→ Release                              │
│          🔴                                                  │
├──────────────────────────────────────────────────────────────┤
│ Actions Required                                             │
│ [Approve GPU quota]                                          │
│ [Assign backend engineer]                                    │
│ [Review milestone M3]                                        │
└──────────────────────────────────────────────────────────────┘
```

首页实际上回答六件事情：

$$ \boxed{ Where\ are\ we? } $$$$ \boxed{ Are\ we\ on\ track? } $$$$ \boxed{ What\ is\ blocking\ us? } $$$$ \boxed{ What\ will\ happen? } $$$$ \boxed{ Why? } $$$$ \boxed{ What\ should\ someone\ do\ next? } $$

最后一个尤其重要。

**好的 Dashboard 不只是告诉 PM“发生了什么”，还应该驱动下一步行动。**

# 任务很抽象：Scope & WBS / 项目分解器

比如老板给你一句：

> 做一个企业知识库系统。

这是不能直接执行的。

系统首先建立：

```
Objective
↓
Outcome
↓
Deliverable
↓
Milestone
↓
Work Package
↓
Task
↓
Subtask
```

例如：

```
企业知识库
│
├── 数据接入
│   ├── PDF
│   ├── Word
│   └── Web
│
├── 数据处理
│   ├── Parser
│   ├── Chunking
│   └── Embedding
│
├── Retrieval
│   ├── Vector DB
│   ├── Reranker
│   └── Query Rewrite
│
└── Product
    ├── API
    ├── Web UI
    └── Auth
```

但 WBS 不能只是一棵树。

每个叶节点必须满足：

```
Task
├─ Owner
├─ Input
├─ Output
├─ Acceptance Criteria
├─ Dependency
├─ Required Skill
├─ Required Resource
├─ Estimated Effort
├─ Estimated Duration
├─ Risk
└─ Evidence
```

于是系统可以检测：

> 这个任务到底是不是“可执行任务”。

比如：

❌ 优化模型性能

不是合格 Task。

应该拆成：

> 在 MMLU-Pro 上将模型准确率从 71% 提升到 ≥74%，GPU Budget ≤ 200 A 100-hours，11 月 10 日前提交实验报告。

这才进入 READY 状态。

# 可行性分析：Feasibility & Capacity Planning

系统应该回答：

> 要完成这些任务，我到底需要什么？

可以从 WBS 自动向上汇总：

```
Task
 ↓
Required Skills
 ↓
Required People
 ↓
Required Equipment
 ↓
Required Compute
 ↓
Required Budget
 ↓
Required Time
```

例如：

| Resource         | Need  | Available | Gap    |
| ---------------- | ----- | --------- | ------ |
| Backend Engineer | 3     | 2         | 🔴 -1   |
| ML Engineer      | 2     | 2         | 0      |
| Designer         | 1     | 0.5       | 🟡 -0.5 |
| A 100 GPU         | 16    | 8         | 🔴 -8   |
| Budget           | $120 K | $150 K     | 🟢      |

于是 Dashboard 有一个非常重要的指标：

$$ Resource\ Gap = Demand - Capacity $$

进一步还应该计算：

$$ Utilization = \frac{Allocated\ Capacity} {Available\ Capacity} $$

例如：

```
Alice      ████████████ 120% 🔴
Bob        ██████████    95% 🟡
Charlie    ██████        62% 🟢
David      ███           31% ⚪
```

这样不仅发现“缺人”，还能发现：

> 人其实有，但分配错了。

# Resource Allocation / Assignment

系统核心对象应该变成：

$$ Task \leftrightarrow Person \leftrightarrow Resource $$

而不是简单的：

```
Task → Alice
```

真正的 Assignment 应该是：

```
Assignment
├─ Task
├─ Person
├─ Role
├─ Responsibility
├─ Start
├─ Deadline
├─ Allocation %
├─ Budget
├─ Compute Resource
├─ Dependencies
└─ Expected Output
```

这里可以直接引入 RACI：

| Task  | Responsible | Accountable | Consulted | Informed |
| ----- | ----------- | ----------- | --------- | -------- |
| API   | Alice       | Bob         | Charlie   | PM       |
| Model | David       | Bob         | Alice     | PM       |

这样以后出了问题就不需要靠聊天记录寻找：

> “当时到底是谁负责？”

系统本身已经定义责任边界。

# 状态机

你提到：

> 通过状态机和生命周期自动安排人员行动。

我认为这是整个产品的核心。

Task 不应该只有：

```
Todo
Doing
Done
```

而应该有完整生命周期：

```
Draft
  ↓
Defined
  ↓
Feasibility Check
  ↓
Ready
  ↓
Assigned
  ↓
In Progress
  ↓
Review
  ↓
Validation
  ↓
Accepted
  ↓
Closed
```

异常分支：

```
              ┌→ Blocked
              │
In Progress ──┼→ At Risk
              │
              ├→ Rework
              │
              └→ Cancelled
```

每个状态转换都有 **Guard Condition**。

比如：

```
Draft → Ready
```

必须满足：

```
✓ Owner assigned
✓ Requirement defined
✓ Acceptance criteria defined
✓ Dependency ready
✓ Required resources available
✓ Estimate exists
```

否则：

```
Transition rejected
```

这非常关键。

从这里开始，**制度开始由软件执行，而不是靠 PM 天天催。**

# 规则引擎：让系统推着人走

例如定义规则：

```
IF
    task.status = BLOCKED
AND
    blocked_time > 24h
THEN
    notify(owner)
```

超过 48 小时：

```
→ notify(Project Manager)
```

超过 72 小时：

```
→ escalate(Department Lead)
```

类似地：

```
Deadline - 3 days
AND progress < 50%
        ↓
AT_RISK
        ↓
Request Recovery Plan
```

或者：

```
Task completed
        ↓
Automatically assign reviewer
        ↓
Review passed
        ↓
Automatically trigger downstream tasks
```

于是整个项目变成一个巨大的状态机：

```
Event
  ↓
State Change
  ↓
Rule
  ↓
Action
  ↓
New Event
  ↓
New State
```

形成：

$$ \boxed{ Event \rightarrow State \rightarrow Rule \rightarrow Action } $$

这就是你说的：

> **规则推着人行动。**

# Schedule / Dependency / Critical Path

任务应该形成 DAG：

```
A ──→ B ──→ D ──→ F
      │
      └──→ E ──→ F

C ─────────────→ F
```

计算 Critical Path。

Dashboard 应该直接告诉 PM：

```
Critical Path

Data Pipeline
     ↓
Model Training      🔴 +4d
     ↓
Evaluation          🔴 +2d
     ↓
Integration
     ↓
Release

Forecast delay: +6 days
```

PM 真正关心的不是：

> 哪些任务晚了？

而是：

> **哪些任务晚了会导致整个项目晚？**

# Blocked：一等公民

这是很多 Jira 类工具设计不足的地方。

Blocked 应该是一等公民：

```
Blocker
├─ Blocked Task
├─ Blocking Object
├─ Blocking Owner
├─ Reason
├─ Start Time
├─ Duration
├─ Impact
├─ Critical Path Impact
├─ Escalation Level
└─ Resolution
```

于是 Dashboard 可以显示：

```
Top Blockers

GPU quota
├─ Blocking: Model Training
├─ Duration: 4d
├─ Owner: Infra Team
└─ Project impact: +3d

API specification
├─ Blocking: Frontend
├─ Duration: 2d
└─ Project impact: +1d
```

这样 PM 一眼知道：

> 今天最应该解决哪个问题。

# EVM

项目管理里面非常有价值的一套方法是 **Earned Value Management**。

三个基本量：

$$ PV = Planned\ Value $$

计划现在应该完成多少钱的工作。

$$ EV = Earned\ Value $$

实际上完成了多少钱的工作。

$$ AC = Actual\ Cost $$

实际上花了多少钱。

得到：

$$ SPI=\frac{EV}{PV} $$

Schedule Performance Index。

以及：

$$ CPI=\frac{EV}{AC} $$

Cost Performance Index。

例如：

```
SPI = 0.82 🔴
```

意味着：

> 项目进度只有计划的 82%。

而：

```
CPI = 1.13 🟢
```

意味着成本效率不错。

这比：

> 完成 57 个 Issue

有意义得多。

# 风险管理

建议建立 RAID：

```
R = Risk
A = Assumption
I = Issue
D = Dependency
```

例如：

```
Risk
GPU 可能无法按期到货

Probability: 60%
Impact: HIGH

↓ 真的发生

Issue
GPU 未按期到货

↓ 导致

Blocker
Training Blocked

↓ 导致

Schedule Impact
+7 days
```

于是形成完整因果链：

$$ Risk \rightarrow Issue \rightarrow Blocker \rightarrow Task \rightarrow Milestone \rightarrow Project $$

Dashboard 可以把这个关系可视化。

# 项目变更

现实中还有一个特别重要的问题：

> 项目为什么延期？

很多时候不是执行差，而是需求一直变化。

所以任何 Baseline 建立以后：

```
Scope Baseline
Schedule Baseline
Cost Baseline
Resource Baseline
```

都不能偷偷修改。

必须：

```
Change Request
      ↓
Impact Analysis
      ↓
Approve / Reject
      ↓
Update Baseline
```

例如：

```
CR-017

Add mobile support

Impact:
+ 3 engineer-weeks
+ $18K
+ 12 days

Approved by: Product Director
```

这样以后就能区分：

```
Original deadline: Nov 1
Approved scope change: +12d
Execution delay: +3d

Current forecast: Nov 16
```

否则所有延期最终都会错误归因给执行人员。

# Acceptance & Quality

Milestone 完成条件必须提前定义：

```
Deliverable
      ↓
Acceptance Criteria
      ↓
Evidence
      ↓
Reviewer
      ↓
Validation
      ↓
Accepted
```

例如：

```
Model Release

Acceptance Criteria

Accuracy ≥ 75%       ✓ 76.4%
Latency < 500ms      ✓ 412ms
GPU Memory < 24GB    ✓ 21.3GB
Regression Tests     ✓ 284/284
Security Review      ✓ Passed
Documentation        ✓ Completed
```

全部通过：

```
VALIDATED
    ↓
ACCEPTED
```

而不是员工自己点击：

> Done

就算完成。

# Documentation / Handover 应该成为生命周期

项目结束后自动生成：

```
Project Closure Package
│
├── Requirements
├── Architecture
├── Decision Log
├── Change Log
├── Deliverables
├── Test Report
├── Deployment Guide
├── Operation Manual
├── Known Issues
├── Risk Register
├── Ownership Transfer
└── Postmortem
```

交接也应该有状态：

```
Preparing
↓
Documentation Complete
↓
Knowledge Transfer
↓
Receiver Confirmed
↓
Ownership Transferred
↓
Closed
```

因此不会出现：

> 项目做完了，但是只有原作者知道怎么维护。

# 绩效评估

如果直接：

$$ Performance = \#CompletedTasks $$

员工马上就会 Goodhart：

> 疯狂拆简单任务刷 KPI。

因此至少要拆成四个维度：

$$ Performance = f(Output, Quality, Efficiency, Reliability) $$

例如：

```
Employee: Alice

Delivery
────────────
Committed work      120 pts
Accepted work       112 pts
Completion          93%

Timeliness
────────────
On-time             88%
Avg delay           0.7 days

Quality
────────────
First-pass accept   91%
Rework              7%
Defect escape       2%

Efficiency
────────────
Estimated effort    420h
Actual effort       390h

Impact
────────────
Critical-path work  38%
Project contribution HIGH
```

投入产出可以进一步建立：

$$ ROI = \frac{Value\ Delivered} {Cost} $$

但这里一定不要只使用“工时”。

因为：

> 高能力员工解决困难问题，可能任务数量反而少。

所以需要引入：

```
Task Value
Task Complexity
Criticality
Quality
Timeliness
Resource Consumption
```

才能形成比较合理的绩效指标。

# Accountability & Audit

目标不应该是：

> 找一个人背锅。

而应该是：

> **重建事实链，区分责任、系统性原因和合理风险。**

否则员工很快会学会：

```
少做事
↓
少承担责任
↓
少出事故
↓
绩效反而更好
```

最终组织会产生严重的风险规避。

正确设计是建立 **Event Sourcing / Audit Trail**。

每一个动作：

```
09:13 Alice
Task A → In Progress

10:42 Bob
Changed API specification

11:03 Alice
Raised dependency warning

11:20 PM
Risk accepted

Oct 8
Deadline reached

Oct 9
Task delayed
```

任何重要决策也建立 Decision Log：

```
Decision #D-284

Decision:
Continue deployment despite test coverage 72%

Recommended:
≥ 90%

Decision maker:
Bob

Risk raised by:
Alice

Timestamp:
2026-10-05 14:32

Reason:
Customer deadline

Result:
Production incident
```

于是事故调查不再依赖：

> “我记得当时 Alice 好像说……”

而是可以重建完整 causal chain：

```
Requirement
     ↓
Decision
     ↓
Assignment
     ↓
Execution
     ↓
Warning
     ↓
Decision
     ↓
Failure
```

最终区分：

```
Execution failure
Planning failure
Requirement failure
Resource failure
Management decision
External dependency
Unavoidable risk
```

这比“甩锅系统”高级很多，也更适合真正的组织治理。

# Decision Log

很多项目失败以后最大的问题其实不是不知道：

> 谁做了什么。

而是不知道：

> **为什么当时这么做。**

所以 Dashboard 应该存在：

```
Decision

Context
↓
Options
↓
Trade-offs
↓
Decision
↓
Owner
↓
Evidence
↓
Expected Result
↓
Actual Result
```

半年以后可以知道：

> 为什么不用方案 B？

这对长期项目极其重要。

# 总结

拆分为 9 个控制中心：

```
PROJECT CONTROL SYSTEM
│
├── ① Overview
│      Health / Forecast / Alerts / Actions
│
├── ② Scope
│      Goal / Deliverable / WBS
│
├── ③ Plan
│      Milestone / Timeline / Dependency / Critical Path
│
├── ④ Resources
│      People / Skill / Capacity / Budget / Equipment
│
├── ⑤ Execution
│      Task / Assignment / Workflow / State Machine
│
├── ⑥ Control
│      Progress / EVM / Forecast / Blocker / RAID
│
├── ⑦ Quality
│      Acceptance / Test / Evidence / Stage Gate
│
├── ⑧ Governance
│      Change / Decision / Approval / Audit Trail
│
└── ⑨ Organization
       Performance / ROI / Workload / Contribution
```

# 以对项目模型为核心

而不是以页面为核心

这是这个系统能不能真正做好最关键的一点。

底层实际上只需要十几种核心 Entity：

```
Project
│
├── Objective
├── Deliverable
├── Milestone
├── Task
├── Dependency
├── Person
├── Resource
├── Assignment
├── Risk
├── Issue
├── Change
├── Decision
├── Evidence
└── Event
```

它们形成一张 **Project Graph**：

```
                  Objective
                      │
                  Deliverable
                      │
                  Milestone
                      │
                     Task
                ┌─────┼─────┐
             Person Resource Dependency
                │             │
           Assignment       Task
                │
             Evidence
```

然后状态变化全部进入 Event Log：

```
Event Store
     ↓
Project State
     ↓
Metrics
     ↓
Rules Engine
     ↓
Alerts / Actions
     ↓
Human
     ↓
Event Store
```

于是你想要的**负反馈控制循环**真正形成：

$$ \boxed{ Plan \rightarrow Execute \rightarrow Observe \rightarrow Compare \rightarrow Detect\ Deviation \rightarrow Correct \rightarrow Execute } $$

从控制论角度甚至可以写成：

$$ e(t)=Target(t)-Actual(t) $$

Dashboard 的核心任务就是持续测量这个 **error signal**。

当：

$$ |e(t)|>\epsilon $$

规则引擎自动产生 corrective action。

所以你真正要设计的不是一个 Dashboard，而是：

> **一个以项目状态机为核心、Project Graph 为数据模型、Event Log 为事实来源、Rule Engine 为控制器、Dashboard 为人机控制面的 Project Operating System。**

这会比“项目管理 Dashboard”这个定位强很多。

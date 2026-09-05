# Feature Issue 提交指南

## 提交前必做

1. **查重**。搜索仓库全部 issue/PR/Discussions（含已关闭）中的相关关键词。
   - 反例：oh-my-pi #10911 因与 #1734 重复被机器人秒级折叠。
   - 已验证：edamame 全库无 LaTeX/math 相关 issue → 需自开，安全。
2. **读 CONTRIBUTING.md**，确认是否要求"先开 issue 再写码"。
   - edamame：**非平凡改动必须先开 issue**，scope 窄，直接 PR 会被拒。
3. **读维护者的已知表态**，把它作为 issue 锚点。
   - edamame #37：owner 亲述 `ENABLE_MATH needs a rendering or resolution designof their own ` → 我们的 issue 应定位为"认领该待设计课题"，而非重复造轮子。

## issue 正文结构

### 模板五段

| 段 | 内容 | 要求 |
|---|---|---|
| Description | 要什么 | 建议 + 具体配置/API 语法示例（代码块），30 秒可懂 |
| Use Case | 为什么 | 真实场景、版本号、量化数据 |
| Area | 涉及模块 | 下拉选择 |
| Proposed Solution | 怎么实现 | 方案 + 链接相关文档/API |
| Alternatives Considered | 备选与 workaround | 承认有备选并说明代价 |

### 标杆加分项

1. **标题**：陈述性短句，直接说需求，不带情绪、不加前缀噪音。
   - 例：`Allow a separate model for automatic auto-learn capture`
2. **Use Case 附诚实边界**：给出量化数据（版本、token 增长），同时主动划清
   因果边界（"非断言 X 导致全部问题"）——坦诚比夸大更可信。
3. **Current implementation 段**：先验证源码再说话——贴 commit hash 锚定的
   源码行号链接，证明不是空想。这是与泛泛需求的分水岭。
4. **Requested behavior 段**：编号验收清单（1–5 条），每条可测、可写测试。
5. **Scope 声明**：明确"本请求不做什么"——直接消解维护者最怕的 scope 蔓延。
6. **Related work 段**：列相邻 issue/PR，逐一说明与本次的**区别**。
7. **Alternative 段**：承认有 workaround 但说明其代价（为何不可接受）。
8. **收尾姿态**：声明不抢 PR、不扩 scope、等待维护者批准。
   - 例：`I am not preparing a competing PR. If maintainer approval is required,please flag that rather than expanding the scope. `

## 标题命名

- 无强制前缀（oh-my-pi 模板不要求 conventional 前缀；PR 提交信息才用）。
- 写法：`动词短语，说清对象`。
- 例：`Add g/c flags to vim substitution`（edamame #25 同类）、
  `Allow a separate model for automatic auto-learn capture`（#10889）。
## 提交后预期

- roboomp（自动化分类机器人）会：打 label、验证前提（"premise checks out against
  the current tree"）、评估可行性、指认源码落点、**查重并折叠重复项**。
- 所以：贴源码行号且说清与既有 issue 区别的 issue 会被快速确认；
  重复或泛泛的会被折叠或冷落。

## 模板速查

```markdown
## Description

<要什么。附具体配置/API 语法示例：>

\```yaml / toml / 代码
<示例>
\```

## Use case

<真实场景、版本号、量化数据。诚实划清因果边界。>

## Current implementation

<验证过的源码位置，贴 commit 锚定行号链接。>

## Requested behavior

1. <可测验收点>
2. …

本请求不：<scope 边界声明>。

## Related work

- #NNN：<相邻 issue>，与本请求的区别：…
- #NNN：<相邻 issue>，与本请求的区别：…

## Alternative

<workaround 及其代价>

<收尾姿态：不抢 PR、待批准。>
```
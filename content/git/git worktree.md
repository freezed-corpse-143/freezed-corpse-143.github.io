`git worktree` 是 Git 提供的一个非常实用的功能，它允许你**在同一个仓库中同时检出多个分支到不同的目录**，而无需克隆多个仓库副本。

## 核心概念

通常，一个 Git 仓库只有一个工作目录（working directory），你切换到某个分支时，文件会被替换成该分支的内容。而 `git worktree` 让你可以：

- 让同一个仓库拥有**多个工作目录**
- 每个工作目录可以检出**不同的分支**
- 它们**共享同一个 `.git` 仓库数据**（对象、引用等）

简单说：**一个仓库，多个工作区，各自在不同分支上并行工作。**

---

## 为什么需要它？

### 常见痛点
1. **临时切换分支很麻烦**：正在写功能 A，突然要修 bug，得 `git stash` → 切分支 → 修完 → 切回来 → `stash pop`，容易出错。
2. **想同时对比两个分支的代码**：只能开两个 clone，占双倍磁盘。
3. **CI/CD 或测试**：需要在不同分支上并行跑构建。

### worktree 的解决方案
为每个任务开一个独立目录，互不干扰，但底层共享同一个 Git 数据库。

---

## 基本用法

### 1. 创建新的 worktree
```bash
# 在 ../hotfix 目录创建一个新工作区，检出 hotfix 分支
git worktree add ../hotfix hotfix

# 基于新分支创建
git worktree add -b new-feature ../feature-dir main

# 检出某个提交（detached HEAD）
git worktree add ../test-dir abc1234
```

### 2. 查看所有 worktree
```bash
git worktree list
```
输出示例：
```
/home/user/project        abc1234 [main]
/home/user/hotfix         def5678 [hotfix]
/home/user/feature-dir    ghi9012 [new-feature]
```

### 3. 删除 worktree
```bash
# 先删除目录，再清理记录
git worktree remove ../hotfix

# 或强制删除（有未提交改动时）
git worktree remove --force ../hotfix

# 手动删了目录后清理元数据
git worktree prune
```

---

## 关键特性与限制

| 特性       | 说明                                                 |
| ---------- | ---------------------------------------------------- |
| 共享对象库 | 所有 worktree 共用一个 `.git`，节省磁盘              |
| 分支唯一性 | **同一分支不能同时在两个 worktree 检出**（否则报错） |
| 独立工作区 | 每个 worktree 有独立的暂存区、HEAD、未提交改动       |
| 独立索引   | 各 worktree 的 `git status`、`git add` 互不影响      |

> ⚠️ 注意：不能两个 worktree 同时检出同一个分支。如果需要，可以用 `--detach` 检出提交，或创建新分支。

---

## 典型使用场景

### 场景 1：紧急修复 bug
```bash
# 主目录正在开发 feature
cd ~/project

# 另开目录修 bug，不影响当前工作
git worktree add ../project-hotfix hotfix
cd ../project-hotfix
# 修复、提交、推送
cd ~/project
git worktree remove ../project-hotfix
```

### 场景 2：代码审查
```bash
# 为 PR 创建一个临时 worktree
git worktree add ../review-pr pr-branch
cd ../review-pr
# 运行测试、查看代码
```

### 场景 3：并行运行测试
```bash
git worktree add ../test-main main
git worktree add ../test-dev dev
# 两个目录同时跑不同分支的测试
```

---

## 与 `git clone` 的对比

| 维度     | `git worktree`     | 多次 `git clone`   |
| -------- | ------------------ | ------------------ |
| 磁盘占用 | 共享对象库，省空间 | 每个副本完整独立   |
| 同步     | 自动共享提交/引用  | 需手动 fetch/push  |
| 分支管理 | 天然隔离，不能重复 | 完全独立           |
| 适用场景 | 同一仓库多分支并行 | 完全独立的仓库副本 |

---

# 目录结构示例

```text
project/                    ← 主工作区
├── .git/                   ← 主仓库的 Git 目录
│   ├── HEAD                ← 主 worktree 的 HEAD
│   ├── index               ← 主 worktree 的索引
│   ├── objects/            ← 所有 worktree 共享的对象库
│   ├── refs/               ← 所有 worktree 共享的引用
│   ├── config
│   └── worktrees/          ← 新增！每个额外 worktree 一个子目录
│       ├── hotfix/
│       │   ├── HEAD
│       │   ├── index
│       │   ├── gitdir
│       │   ├── commondir
│       │   └── locked (可选)
│       └── review-pr/
│           ├── HEAD
│           ├── index
│           └── ...
└── src/...

project-hotfix/             ← 额外 worktree 的工作目录
├── .git                    ← 这是一个「文件」，不是目录！
└── src/...
```
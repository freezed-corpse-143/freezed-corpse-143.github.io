# 一级目录结构


- package.json / package-lock.json: workspace 根； scriptions 串联 build → check → test → release；lockfile 是依赖“ground truth”，提交受 pre-commit 保护。
- tsconfig.json：全仓库类型检查入口：extends base，用 paths 把各包映射到 src/ （源码直连、无 dist 依赖），include 所有包 src/test。
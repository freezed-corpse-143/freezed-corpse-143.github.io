# 一级目录结构


- package.json / package-lock.json: workspace 根； scriptions 串联 build → check → test → release；lockfile 是依赖“ground truth”，提交受 pre-commit 保护。
- tsconfig.json：全仓库类型检查入口：extends base，用 paths 把各包映射到 src/ （源码直连、无 dist 依赖），include 所有包 src/test。
- tsconfig.base.jon：各包共享的编译选项基座。
- biome.json：lint + format（biome）配置，npm run check 用它
- vitest.base.ts：各包 vitest 配置共享基座
- README.md：项目说明
- CONTRIBUTING.md：贡献守则（含 contributor gate）
- SECURITY.md：安全
- LICENSE：许可
- AGENTS.md：给人和 agent 的仓库规则
- test.sh： 跑全部测试：隔离 HOME/env（临时目录、禁 git 交互、无 API key 环境），env -i npm test
- mini-test.sh：单独跑 coding-agent/src/experimental/mini/ 的 mini 实验版（tsx 直跑源码，--dist/--fresh/--stop 控制 session server）
- pi-test.sh / pi-test.ps 1 / pi-test.bat：直接从源码启动完整 pi（可任意目录运行）
- tui-plan.md：TUI 开发计划文档
- .npmrc：save-exact=true、min-release-age=2（npm 解析防当日依赖）
- .gitattributes：忽略规则与属性
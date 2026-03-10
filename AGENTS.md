# AGENTS.md

> 面向 AI 辅助敏捷开发的协作约定。适用于本仓库中所有人类开发者与 AI Agent。

## 1. AI 敏捷协作原则

- 小步快跑：每次改动聚焦一个明确目标，避免“大而全”提交。
- 测试先行：默认采用 TDD（Red -> Green -> Refactor）闭环。
- 快速反馈：优先运行最小测试集，再逐步扩大到全量检查。
- 可追踪：需求、测试、代码、提交信息、PR 描述保持一一对应。
- 可回滚：每次提交应可独立回退，不依赖隐式上下文。

## 2. Git 提交规范

本仓库采用 Conventional Commits（`@commitlint/config-conventional`）。

### 2.1 提交格式

```text
<type>(<scope>): <subject>

[optional body]

[optional footer]
```

- `type` 允许：`feat`、`fix`、`refactor`、`test`、`docs`、`chore`、`ci`、`build`、`perf`、`revert`
- `scope` 建议填写模块名，如 `api`、`auth`、`tenant`、`llm`、`tests`
- `subject` 使用祈使句、现在时，简洁描述变更意图
- 破坏性变更使用 `!` 或 `BREAKING CHANGE:`

示例：

```text
feat(api): add tenant-aware prompt list endpoint
fix(auth): handle expired refresh token validation
test(repositories): cover tenant filter isolation behavior
refactor(services): split llm routing policy evaluator
```

### 2.2 提交粒度

- 一个提交只做一件逻辑上完整的事。
- 代码重构与功能改动尽量分开提交。
- 大批量格式化不要混入业务逻辑修改。
- 不提交无关文件（临时文件、日志、IDE 垃圾文件）。

### 2.3 提交前检查

至少保证本地通过以下检查（按需增减）：

```bash
uv run ruff check src tests
uv run pyright src
uv run mypy src
uv run pytest
```

### 2.4 禁止事项

- 禁止直接向 `main` 提交。
- 禁止使用 `--no-verify` 跳过钩子（除非团队明确批准）。
- 禁止对受保护分支执行 `push --force`。

## 3. Git Worktree 使用规范

适用场景：并行开发多个需求、多人机协作、多个 AI Agent 同时工作。

### 3.1 分支命名建议

- `feat/<ticket>-<short-desc>`
- `fix/<ticket>-<short-desc>`
- `chore/<ticket>-<short-desc>`

例如：`feat/123-prompt-versioning`

### 3.2 创建 Worktree

```bash
git fetch origin
git worktree add ../wt-123-prompt-versioning -b feat/123-prompt-versioning origin/main
```

说明：

- 一个 worktree 对应一个需求/缺陷。
- 一个 AI Agent 只在自己的 worktree 内改动代码。
- 避免多个 Agent 在同一目录并发修改。

### 3.3 日常操作

```bash
git worktree list
git fetch origin
git rebase origin/main
```

- 开工前先同步 `origin/main`。
- 每次开始新任务先确认当前路径和分支，避免误提交。

### 3.4 清理 Worktree

在分支合并后执行：

```bash
git worktree remove ../wt-123-prompt-versioning
git branch -d feat/123-prompt-versioning
git worktree prune
```

## 4. TDD 开发模式（AI 协作版）

### 4.1 标准循环

1. 定义场景：把需求写成可验证的验收条件（建议 Given/When/Then）。
2. Red：先写失败测试，只描述期望行为，不提前实现。
3. Green：写最少代码让测试通过，避免过度设计。
4. Refactor：在测试保持绿色时优化结构与命名。
5. Commit：通过质量门禁后提交。

### 4.2 测试分层策略

- 单元测试：优先覆盖纯逻辑、服务层、仓储层边界。
- 集成测试：覆盖数据库交互、多租户隔离、外部依赖适配。
- E2E 测试：覆盖关键 API 主流程（登录、租户切换、核心资源 CRUD）。

目录约定：

- `tests/unit/`
- `tests/integration/`
- `tests/e2e/`

### 4.3 AI 执行建议

- 先让 AI 生成测试用例，再让 AI 生成最小实现。
- 每轮仅允许 AI 修改与当前测试失败直接相关的代码。
- 每次迭代先跑最小范围：

```bash
uv run pytest tests/unit/path/to/test_file.py -q
```

- 功能稳定后再跑全量：

```bash
uv run pytest
uv run ruff check src tests
uv run pyright src
uv run mypy src
```

### 4.4 完成定义（DoD）

- 验收条件全部满足。
- 新增/修改行为有对应测试。
- 全量测试、Lint、Type Check 通过。
- 提交信息符合 Conventional Commits。
- PR 描述包含变更动机、影响范围、风险与回滚方案。

## 5. 推荐工作流（端到端）

1. 从 `origin/main` 创建独立 worktree 与分支。
2. 编写验收条件，进入 TDD Red 阶段。
3. Green + Refactor，通过本地质量门禁。
4. 按规范提交（必要时拆分为 `test` + `feat/fix`）。
5. 发起 PR，完成 Review 后合并并清理 worktree。

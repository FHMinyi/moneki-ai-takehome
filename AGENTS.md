## 提交格式

涉及提交操作时，如果项目没有规则特别说明提交格式，则按下面这个格式来提交：

```text
<type>(<scope>): <summary>

<正文：描述本次变更的背景与动机>

Agent-Task: <原始任务描述或任务 ID>
Agent-Model: <实际使用的模型>
Agent-Decision: <关键设计决策及理由>
Agent-Limitation: <已知局限或后续 TODO；无则写“无”>
```

## Agent skills

### Issue tracker

本仓库的任务和规格记录在 GitHub Issues；使用前阅读 `docs/agents/issue-tracker.md`。

### Triage labels

处理任务分流时，使用五个默认标签；标签映射见 `docs/agents/triage-labels.md`。

### Domain docs

探索领域概念或架构决策时，按 single-context 布局阅读 `docs/agents/domain.md`。

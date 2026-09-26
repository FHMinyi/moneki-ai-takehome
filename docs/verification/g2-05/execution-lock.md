# G2-05 execution lock

Executing: 无 Key 第二关整体验收、独立知识库替换与可复现报告。
Source: GitHub Issue #17（完整正文、零评论）及主会话 01a0dc94-4947-7a93-84b9-46b5c7249dfa 的本轮执行授权。
Fixed point: 358859a5be641b04395f314029e4b9325631dd8a，初始 main；新分支 codex/g2-05-acceptance。
In scope: Issue九项验收、干净安装、55题、历史/替换/真实RAG、看板、报告与必要复现脚本。
Out of scope: 第三关实现、live/付费模型、部署、合并/最终关闭Issue、其他worktree。
Validation: git archive固定源码 + 全新安装环境 + 公开make setup/rebuild/run + 真实HTTP及浏览器。
External authority: 分阶段commit/push、PR、Issue进度评论、向主会话回报；清理分支/剩余临时源码等待具体指令。

原有未跟踪 docs/baseline/2026-09-26-followup-draft.md 与 docs/research/ 保护不动。
protected-before.json包含原数据/KB/评测/计划/基线/诊断/前序证据和未提交材料的SHA-256。
G2-04以README顶部R1 c713077为当前业务证据；中间失败保留。
执行模型 GPT-6 Astra/medium；不派生子agent。

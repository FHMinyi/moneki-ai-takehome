Executing: 运营用自然问法检索到相关且适用的资料。
Source: https://github.com/FHMinyi/moneki-ai-takehome/issues/15 (完整正文，无评论)；主会话 01a0dc94-4947-7a93-84b9-46b5c7249dfa 启动授权。
Fixed point: 4a07686449337322c87520ebca52ac838ede86db = origin/main。
In scope: 中文/别名BM25、时间和门店适用性、top-k及补位证据隔离、retrieve/chat同源诊断、重建跟随材料。
Out of scope: 完整单轮回答路由/事实选择、混合多轮/UI、付费模型、部署、合并及自行关闭Issue。
Validation: 真实隔离源码/缓存/VAR_DIR重建+HTTP；R01-R15正分相关来源、确定性变体、版本边界、门店过滤、补位隔离、未知信号；G2-01/02、原后端、全量公开无模型评测。
External authority: 分阶段提交推送、PR、Issue进度评论及向主会话回报已授权；清理等主会话具体指令。
Resources: 复用共享checkout，分支codex/g2-03-retrieval，不新增worktree。不修改另三个受管理checkout。
Preserve: 原始输入/公开题库评分器/旧基线证据；未跟踪docs/baseline/2026-09-26-followup-draft.md和docs/research/。
Model: GPT-6 Astra / high。

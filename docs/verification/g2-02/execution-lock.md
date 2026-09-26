Executing: G2-02 complete evidence and consistent source identity.
Source: https://github.com/FHMinyi/moneki-ai-takehome/issues/14 and authorized execution prompt.
Review fixed point: 8b72f47f712eab309bcc5e65841acfce45f0e17e
In scope: full body coverage, paragraph/table context, contiguous source offsets, retrieval identity, deterministic layout/cache invalidation.
Out of scope: Chinese ranking, version/top-k filtering, QA routing, UI, hybrid/multi-turn, deployment or paid models.
Validation: isolated source/cache/VAR_DIR public rebuild and real HTTP; actual KB audit; G2-01 regressions; backend/public no-model evaluation.
External authority: red/green commits and push, PR, Issue progress, coordinator messaging. No merge, main push, force push or .env.live.
Workspace: reuse shared checkout on codex/g2-02-evidence; preserve untracked draft/research and all other managed worktrees.

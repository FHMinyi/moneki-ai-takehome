# 任务跟踪平台：GitHub

本仓库的任务和规格记录在 GitHub Issues 中。操作时使用 `gh` CLI。

## 操作约定

- 创建任务：`gh issue create --title "..." --body-file <file>`
- 阅读任务：`gh issue view <number> --comments`；按需获取标签。
- 列出任务：`gh issue list --state open --json number,title,body,labels,comments`
- 添加评论：`gh issue comment <number> --body-file <file>`
- 添加或移除标签：`gh issue edit <number> --add-label "..."` 或 `--remove-label "..."`
- 关闭任务：`gh issue close <number> --comment "..."`

从 `git remote -v` 确认仓库；在本仓库目录内运行时，`gh` 会自动识别仓库。

## 是否分流 Pull Request

**PRs as a request surface: no.** 如果以后要把外部 PR 当作需求处理，可将 `no` 改为 `yes`。

启用后，用 `gh pr view <number> --comments` 和 `gh pr diff <number>` 阅读 PR；列出开放 PR 时获取作者关联身份，只将外部作者的 PR 纳入分流。后续操作使用 `gh pr comment`、`gh pr edit` 和 `gh pr close`。遇到含糊的 `#<number>` 引用时，确认它指 PR 还是 Issue。

## skill 要求“发布到任务跟踪平台”时

创建 GitHub Issue。

## skill 要求“获取相关任务”时

运行 `gh issue view <number> --comments`。

## Wayfinder 操作

供 `/wayfinder` 使用。地图是带 `wayfinder:map` 标签的 Issue；子任务使用 sub-issue，若不可用则列在地图的任务清单中。子任务标签为 `wayfinder:research`、`wayfinder:prototype`、`wayfinder:grilling` 或 `wayfinder:task`。用 GitHub Issue 依赖关系记录阻塞；不可用时，在任务中写入 `Blocked by: #<n>`。按地图顺序，选取第一个开放、无阻塞且未分配的子任务。运行 `gh issue edit <n> --add-assignee @me` 领取任务。完成时，评论写入答案、关闭任务，并在地图中添加上下文链接。

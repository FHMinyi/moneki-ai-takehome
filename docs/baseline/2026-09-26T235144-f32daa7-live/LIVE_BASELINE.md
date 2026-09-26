# 原始 starter 接入预检与真实模型基线

执行时间：2026-09-26 23:51 至 2026-09-27 00:04（北京时间）。当前仓库 `main` 的 HEAD 为 `b5703aa596670674ec811a028de9bd5167139564`；它只比原始业务固定点 `f32daa70b8236429a0daad2090c6e91dc309deb6` 多了无 Key 基线证据。运行前核对两个提交间的 `starter/`、`eval/`、`data/`、`knowledge_base/` 无差异。本次原始业务代码、输入数据和题库未修改。

## 运行边界与配置

- 将原始 `starter/` 复制到新的系统临时目录，在副本中运行。复用前一轮 Python 3.12.14 虚拟环境，已确认 FastAPI 0.141.1、httpx 0.28.1 可导入；完整版本见 `dependencies.txt`。清洗库和索引只写在该临时副本内。
- `.env.live` 是被 Git 忽略、未被跟踪的本地文件。只以 Python 按 dotenv 数据格式读取 `LLM_BASE_URL`、`LLM_API_KEY`、`LLM_MODEL`，没有 shell `source`。三项非空；URL 为 HTTPS，且没有 URL userinfo、查询串或 fragment。真实 Key 未写入本目录。
- 非秘密配置：上游主机 `api.deepseek.com`，模型 `deepseek-flash`，OpenAI 兼容 Chat Completions。真实流量经过仓库自带 `llm_gateway.py` 本地代理，代理没有注入 `thinking` 或改动请求体；实际请求均为 `POST /ds-gw/chat/completions`，`model` 均为 `deepseek-flash`。这是评审约定的服务与模型，但仍只证明本次配置和本次请求。
- 使用一次完整公开题库。没有重跑刷分、修改模型参数或进行额外供应商比较。代理记录请求和响应正文、状态及 `usage`；`Authorization` 仅记录长度，不记录值。保留在本目录的代理日志还移除了 `upstream_url`，并经过真实 Key 字节匹配检查；原始临时代理日志已删除。

## 复现路径与实际命令

本次副本构建方式：`cp -R starter "$RUNTIME/starter"`，其中 `RUNTIME` 是新的 `mktemp -d /tmp/moneki-live.XXXXXX`；以 `VAR_DIR="$RUNTIME/starter/var"`、`DATA_DIR="$ROOT/data"`、`KB_DIR="$ROOT/knowledge_base"` 运行服务。`ROOT` 为仓库根目录。若要重新创建环境，可用 Python 3.12 虚拟环境安装 `starter/requirements.txt`，并加 `-c` 指向上一轮无 Key 基线的 `dependencies.txt` 固定本次依赖版本。该步骤会访问包源；本轮实际复用了前一轮环境。

本地假上游预检：在副本服务中只注入工具默认的 `preflight-key-3b9c1f`、`preflight-model-7f3a` 与动态假上游 `http://127.0.0.1:<假模型端口>/ds-gw`。使用下列命令完整运行默认 16 个场景与两道中性问题；假 Key 不是 `.env.live` 中的真实 Key。

```bash
python3.12 eval/llm_gateway.py preflight \
  --service-url http://127.0.0.1:<预检服务端口> \
  --port <假模型端口> --no-wait \
  --out docs/baseline/<新建的独立目录>
```

真实阶段：先用 Python 按数据格式解析 `.env.live`，将真实 `LLM_BASE_URL` 交给 `llm_gateway.start_proxy_server`；用代理返回的本地 URL 作为副本服务的 `LLM_BASE_URL`，其余两个值由内存中的解析结果传给服务子进程。没有把 Key 写进 shell 命令、配置副本或代理命令行。健康接口确认为 `live` 后，顺序发出 4 个本地冒烟请求（纯数据、纯文档、混合、同会话追问），再从仓库根目录执行一次：

```bash
env -i PATH='/opt/homebrew/bin:/usr/bin:/bin' HOME="$HOME" \
  python3.12 eval/run_eval.py \
  --base-url http://127.0.0.1:<真实服务端口> \
  --questions eval/public_questions.jsonl \
  --out docs/baseline/<新建的独立目录>
```

`--out` 必须选新目录，避免覆盖本次原始证据。评测器到本地服务的命令不含 Key；Key 只在服务子进程环境中，服务请求经代理转发。复现真实阶段会产生模型费用，应由操作者主动决定是否运行。

## 原始结果

| 项目 | 结果 | 证据 |
| --- | --- | --- |
| 本地接入预检 | 退出码 0，P1–P14 **14/14 PASS**，0 FAIL、0 SKIP；32 次 `/api/chat` 均 HTTP 200；假上游观察到 60 次 POST、44 次工具调用；两次 `hang` 各约 120 秒，均低于 180 秒 | `preflight_report.json`、`preflight_report.md`、`preflight.output.txt`、`preflight.exit` |
| 真实服务健康检查 | `llm_mode: live`；数据健康字段仍与无 Key 基线相同 | `live-health.json` |
| 真实接入冒烟 | 4 次本地问答均 HTTP 200；真实上游 14 次请求均 HTTP 200 且有 usage。纯数据返回 data 和 1 条数据证据；文档题返回 refusal；混合题返回 doc、2 条引用但 0 条数据证据；追问返回 clarify | `smoke-*.json`、`smoke-proxy-sanitized.jsonl`、`smoke-proxy-summary.json` |
| 完整公开评测 | 退出码 0；**25.5/100**，55 题中 14 题全绿、41 题未全绿；真实上游 119 次请求均 HTTP 200 且有 usage | `report.json`、`report.md`、`eval.output.txt`、`eval.exit`、`eval-proxy-sanitized.jsonl`、`eval-proxy-summary.json`、`failed-questions.tsv` |

真实评测分类：metrics 1/6，retrieval 6/15，data 0/12，doc 2/16，version 0/6，hybrid 0/18，multi_turn 2.5/9，refusal 8/8，safety 6/9，health 0/1。44 道无 Key 失败题中本次仍有 41 道未全绿。逐题响应和判分理由以原始 `report.json` / `report.md` 为准。

## 与无 Key 原始基线比较

无 Key 基线同一原始代码为 **17/100，11/55 题全绿**；本次为 **25.5/100，14/55 题全绿**，总分增加 8.5。逐题得分上升仅 C02（+2）、T03（+1.5）、F01（+2）、S02（+3），其余 51 题分数相同；本次没有降分题。详细机器对比见 `mock-vs-live.json`。这是一轮公开题库的观察，不证明模型输出稳定或所有提高都可泛化。

指标与检索两个类别完全同分，且它们由确定性本地接口给出。`clean_rows` 未按 KB-001 清洗、指标排除退款并按明细行计订单、加载器漏读 `.txt`/`.html` 与中文按空白分词等已确认行为，不会因接入模型而修复。纯数据与混合问答仍为 0 分，说明真实模型连接成功并不足以交付可信经营答案。具体单题根因仍须在后续任务中用红测试逐层验证，不把单次模型输出当成修复证据。

## 用量、未验证项与保护检查

真实上游 `usage` 共 133 条：冒烟 77,101 tokens（prompt 70,993、completion 6,108），公开评测 791,524 tokens（prompt 749,463、completion 42,061），合计 **868,625 tokens**。其中 prompt cache hit 合计 569,856 tokens，reasoning tokens 合计 29,687；这些是代理记录的供应商响应字段。未读取供应商账单，也未核实价格，因此**无法给出实际费用**。没有再发额外模型请求。

没有验证隐藏题库、替换数据/知识库、浏览器 UI、真实服务的长期稳定性，也没有完成 `LLM_SETUP.md` 或后续业务修复。原始输入与代码的 `input-sha256-before.txt` / `input-sha256-after.txt` 一致；本目录经过真实 Key 字节匹配检查，匹配数为 0。本轮启动的预检服务、真实服务与代理均已停止。未 Git 提交、推送、建 PR、改 Issue 或部署。

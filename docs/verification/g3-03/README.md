# G3-03 mixed answer verification

> Latest integration: normal merge623b38c of accepted main bb7883c; P1 monetary-format repair20fe53a; final business d9a69ab. 217 affected checks,14 actual HTTP cross cases,53 separate original backend and7 visible-mouse browser cases passed; no-key94/100,53/55. No additional paid calls. See [integration and review repair evidence](integration-g304/README.md). The original delivery below retains its historical SHAs/results.

Source: Issue #26 (body and all comments), inherited continuous-delivery authorization. Only this reused worktree was modified. Review baseline `eb064fb1954b8d4d241c974a65f83be3420cefaf`; branch `codex/g3-03-mixed-answer`. Final business implementation: `603c611`; the later evidence commit does not change product code. `fixed-source-delivery.json` records exact final hashes; `fixed-source-final.json` preserves the preceding aa72140 snapshot.

Implementation and controlled self-verification are complete; independent coordinator acceptance is pending. **Real-model semantics are only partially verified:** H02 and H04 succeeded at their recorded commits; H01 and H05 failed at theirs. Their saved choices pass free replay after filtering repairs; that is not a new provider run. H03/H06 have not been called live. No merge, Issue closure, deployment, new model judge, or full paid 55-case evaluation was performed.

## Actual starting point and red/green provenance

- `d0f1faa` preserves the tests written before implementation. Original backend: 53 passed in a separate process (`before-original.txt`). The first attempt had a JSONL header collection error (`before.txt`), corrected before the business red run.
- **Actual pre-implementation red run:** `before-corrected.txt`, six failures comprising **four** `data_binding` failures plus **two** controlled selectors that did not find their expected first-retrieval spans (H03/H05). Earlier conversational shorthand saying all six were product-protocol failures was wrong and was corrected in both execution and coordinator chats.
- The selectors were repaired by using a targeted goal search and an actually returned payment-event clause. `before-replayed-corrected-selectors.txt` is a **later replay against separately exported eb064fb source**, six `data_binding` failures; it is not an implementation-before measurement. This version of the test is in `cc4bcdd` before later additional tests.
- First implementation: `cc4bcdd`. Real H01 exposed a mixed evidence filtering boundary, repaired in `1c65ef1`; real H05 exposed the same all-or-nothing boundary for attribute rather than date. `bb03e5a` independently filters each candidate, preserves verified data if every reason fails, and recognizes explicit ISO date intervals. It does not conclude that an excluded background has no causal connection.
- `aa72140` adds final explicit metric conflict checks (another valid target metric or denominator cannot replace the one asked for) and isolates offline validation outputs. No additional paid run after the four authorized chats.

- Final bounded review correction `603c611`: an unrecognized colloquial payment label must not create a synthetic zero for that label when the actual database uses another category. Zero fill is limited to canonical categories; unknown aliases show actual returned categories. Independent bank-card 100% counterexample and delivery 57-check run passed. No paid calls. `payment-alias-old-source-replay.txt` is a later replay against aa72140 (1 failed), not a pre-edit measurement; `http-complete/payment-classification-*.json` independently proves unknown colloquial labeling cannot invent zero, bank-card 100% and genuine canonical cash 0% preserve the denominator. All 18 browser/139 predecessor/53 original/199 RAG results remain explicitly tied to aa72140; these paths are unchanged except the new mixed payment category selection.

## Acceptance mapping

| Issue criterion | Evidence and result |
|---|---|
| H01–H06 through model tool selection, SQLite/BM25, API and UI | `test_mixed.py`, `http-final-metric/H01..H06.json`, `browser-aa72140/`: controlled transport, real tools, all six behaviors. 18 browser cases cover six questions at 1280/1440/390. These are not live semantic results. |
| Code-generated actuals, goals, differences, shares, comparisons | Typed `mode/results/facts`; only executed call IDs and request-local document IDs. Code derives unit/metric and actual-minus-target, B-minus-A, share numerator/denominator and notice-minus-table-price. `calculations` accompanies actual data evidence and is visible in the browser. Wrong metric, inverted dates/direction, invalid tool or forged ID are rejected. |
| DB/KB conflicts and independent replacements | `independent_expectations.py` uses direct read-only SQLite, not DataTools. Replacement DB: sale 7 minus refund 2 gives 5, sale 17 minus refund 2 gives 15. Target 10/21 crosses fail/pass independently, including equality. Zero amount contributes neither sale qty nor order count. Price notice 47 vs actual 30 remains a conflict; table 42 does not overwrite actual. |
| Real zero, unknown reason, matching event | H06 preserves actual 0 and data_evidence with no citation. Wrong store/product/date/non-event and payment-unrelated background are filtered independently; no surviving reason yields verified data + cause unknown. Explicit ongoing interval 6/15–6/20 can support 6/18. Paid H01/H05 original choices replay through this path; discarded text does not remain in answer/citations/calculations. |
| Shared identity, applicability and timing | Reuses DocumentEvidence IDs, original spans, source metadata, scope and BM25 eligibility; model cannot create references. Mixed numeric roles use a closed source grammar; pure-doc subject/attribute/value binding is unchanged. Goal date must equal actual period; price policy date remains current while transactions end at data coverage; events use their explicit interval/date, otherwise dated notice effectivity. |
| Browser/API contract | Eighteen real browser submissions under a controlled HTTP provider compare answer, actual query params/result, calculations and citations against the received payload. 390 screenshot inspected. Long real price distributions safely refuse at result byte/number limits; no JSON truncation. All selected quotes are checked against source IDs and normalized 400-character limit. |
| Order changes/repeated searches and original guarantees | Reverse tool order and unrelated second search preserve source bindings. Fixed final checks below; no-key stays 88.5/100 and 49/55. Real results and their gaps listed separately. |

## Final fixed-point checks

Run from this repository root with a fresh output directory; **never reuse a committed evidence path**. The broad frozen checkpoint is `aa72140`. The mixed/HTTP/replay command below was rerun after the final narrow payment-label correction at `603c611` (57 passed); other listed broad results are aa72140, with unchanged tested predecessor code.

```bash
# 46 mixed checks + 9 HTTP checks + 2 free replays = 57 passed at 603c611
mkdir -p /tmp/g303-review-replay
G303_HTTP_OUT=/tmp/g303-review-http G303_REPLAY_OUT=/tmp/g303-review-replay \
  starter/.venv/bin/python -m pytest docs/verification/g3-03/test_mixed.py \
  docs/verification/g3-03/test_http.py docs/verification/g3-03/test_live_replay.py -q
# delivery-complete.txt; preceding aa72140 final-checks.txt retains its 53 passed

# Original fixture globally replaces Retriever.search; MUST run separately: 53 passed
starter/.venv/bin/python -m pytest starter/tests -q
# original-final.txt

# Existing G301/G302/G306 guarantees: 139 passed
G3_CREDENTIAL_EVIDENCE=/tmp/g303-review-credentials starter/.venv/bin/python -m pytest \
 docs/verification/g3-01/test_data_chat.py docs/verification/g3-01/test_credentials.py \
 docs/verification/g3-02/test_document_binding.py \
 docs/verification/g3-02/review-r1-r2/test_anchored_selection.py \
 docs/verification/g3-02/review-roles/test_roles.py \
 docs/verification/g3-06/test_trend_context.py \
 docs/verification/g3-06/test_early_plan_context.py docs/verification/g3-06/test_route_regression.py -q
# regression-final.txt

# Pure budget rules + local fake upstream transport: 10 passed, no credential needed
starter/.venv/bin/python -m pytest docs/verification/g3-03/test_budget.py \
 docs/verification/g3-03/test_budget_transport.py -q
# budget-final.txt

# Real RAG predecessor suite: 199 passed
G2_EVIDENCE=/tmp/g303-review-rag starter/.venv/bin/python -m pytest \
 docs/verification/g2-01/test_ingestion.py docs/verification/g2-02/test_evidence.py \
 docs/verification/g2-03/test_retrieval.py docs/verification/g2-04/test_doc_qa.py \
 docs/verification/g2-04-heading-fix/test_heading.py -q
# rag-final.txt; initial precommit run separately retained as rag.txt

# Fresh var, no Key, unmodified public suite: 88.5/100, 49/55
G303_NOKEY_OUT=/tmp/g303-review-nokey starter/.venv/bin/python docs/verification/g3-03/verify_no_key.py
# no-key-final/ includes actual command, SHA, health and reports

# Existing production frontend built successfully; build.txt
# Start controlled harness (prints its URL/PIDs); Ctrl-C only when no review needs it:
starter/.venv/bin/python docs/verification/g3-03/http_harness.py /tmp/g303-review-browser
# In frontend/, use printed URL:
BROWSER_BASE_URL=http://127.0.0.1:PORT G303_BROWSER_OUT=/tmp/g303-review-screens \
 npx playwright test tests/g3-mixed.spec.ts --workers=1 --output=/tmp/g303-review-playwright
# browser-aa72140.txt: 18 passed
```

`browser-first.txt` records an initial wrong-relative-path/no-test invocation, not browser acceptance. `first-green-attempt.txt`/`six-green.txt` are failed development attempts; only the named final outputs establish final checks.

## Live attempts and expenditure — stopped at four chats

All use official DeepSeek `deepseek-flash`, `max_tokens=4096`, six tool rounds plus final `tool_choice=none` opportunity, existing overall time cap. The runner reads the shared `.env.live` only when explicitly invoked; no balance/model-list requests. **Do not rerun the paid script: its authorized four-chat count is exhausted.**

| Chat | Business SHA | Question | Actual result | API attempts | Free replay at aa72140 |
|---|---|---|---|---:|---|
| 1 | cc4bcdd | H02 actual vs goal | PASS: qty125, goal120, exceeds5, genuine query and KB023 | 2 | Not needed; final controlled path retested |
| 2 | cc4bcdd | H01 low revenue | FAIL: valid 6/8–11 closure plus 6/5 background made all-or-nothing date check refuse | 4 | PASS: retains closure, 3630 and B−A=-2487; discarded background absent. Not a live rerun. |
| 3 | 1c65ef1 | H05 cash share | FAIL: model also chose network-upgrade background without direct payment attribute | 2 | PASS: 27/27=100%, direct terminal/cash facts retained, unsupported background absent. Not a live rerun. |
| 4 | bb03e5a | H04 notice vs actual/table | PASS: notice45, latest actual45, table42, computed difference3, three genuine clauses | 3 | Final explicit-metric guard does not affect this path; no new provider run |

H03 and H06 were not called live. None of the final free replay, browser, fake-provider or no-key results proves final-model general semantics. Final aa72140 is **not** described as four live passes.

`live/chat-*.json` preserves full request/response/trace and actual Git SHA; `live/api-*.json` preserves all eleven outbound bodies and upstream results, including calls whose eventual business answer failed. `live/ledger.json` retains each attempt and final usage/accounting; reservation is persisted before send by `live_budget.reserve` and settled only on complete usage. Offline transport tests assert this ordering, reject insufficient funds/oversize/attempt exhaustion, and retain 2.20 CNY for unknown usage. The byte limit is only a local size guard, not a token upper bound.

Accounting verified in `audit-delivery.json`: **98,879 input + 3,178 output tokens, 11 actual API calls, 0.223182 CNY estimated**, at peak input 2/output8 CNY per million with all input treated as cache misses. The 2.20 CNY pre-send reserve covers 1,048,576 input and 4096 output tokens (2.12992 CNY maximum under those configured provider limits). All usage complete; zero unknown usage or pending reserves. This is not a provider bill. This ticket's 12 CNY balance is 11.776818; coordinator's latest other-ticket total 1.217374 + this ticket = **1.440556 CNY**. Directed pool, corrected by the coordinator after accounting for concurrent G3-04 runs: **16/18 = G3-02 7 + G3-06 2 + G3-04 3 + G3-03 4**. G3-01 initial 3 chats are counted separately. The earlier 13/18 statement omitted the concurrent G3-04 chats; historical `audit-final.json` and the runner ledger retain their original snapshots, while `audit-delivery.json` and the audit summary now record this correction. No API attempt, usage, cost or reservation was changed.

## Metric consistency and bounded limitations

KB-001 §4 defines sales as amount>0, refunds as amount<0, effective orders as distinct sale order IDs, and net revenue/qty including refund effects on their own dates. §5.3 distinguishes actual receipts, notice price and stale products.unit_price. `payment_mix` previously counted amount=0 as a sale because is_refund=0; `unit_price_check` could present a zero-amount row as its latest transaction price. Both now require positive sales. The replacement fixture records sale210, refund-60, zero0, optional card50: net150 (or200), valid orders1 (or2), cash order share50% vs revenue share75% with the extra card row. Zero rows remain in the cleaned source; they simply are not sales. No other metric SQL, raw input or database is rewritten. Original API/dashboard tests and no-key suite remain green.

Mixed operations are intentionally bounded: goals need one explicit numeric target/unit/date and a matching subject, price roles need a recognizable price clause, and events need a verifiable subject/date/operating attribute. Complex unstated continuing periods, arbitrary semantic causality and natural-language entailment are not proven. Extracted events are labelled as material records and do not estimate causal impact. A filtered network background is **not** claimed to be causally unrelated. First-month targets require the stated first month to match notice effectivity; uncertain cases fail honestly. No language-specific endless mock expansion or second model judge was added.

## Preservation and retained resources

4209 baseline tracked input/evaluation/historical verification files have identical hashes (`protected-before.json`, `audit-delivery.json`). Protected shared research files were never edited; only the authorized shared credential file was read without output. The first explicit hash comparison was performed while chat1 was in progress, not before it; `protected-prelive.json` states that timing. Later audits still report zero changes and zero credential leaks.

`retained-resources.json` lists all still-running controlled model/API pairs. Latest review URL **http://127.0.0.1:53503**, business603c611, harness79223/API79232, model53502/API53503, var `/tmp/g303-603c611-review-runtime/var`. Broad browser acceptance URL **http://127.0.0.1:50959**, business aa72140: harness76098/API76104, ports50958/50959, var `/tmp/g303-aa72140-browser-runtime/var`. Earlier pairs69615/69621 ports63627/63628 and75025/75031 ports50486/50487 are also retained pending coordinator cleanup instruction. Paid API/guard processes and transient test runtimes were scoped processes stopped by their harnesses on completion; no paid service remains. `/tmp/moneki-g303-paid-var`, earlier/final controlled var DBs, temp replacement runtimes and all evidence remain. Worktree stays at its task branch; no archive or branch deletion was performed.

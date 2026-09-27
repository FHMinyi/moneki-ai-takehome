# G3-02 live binding repair — evidence receipt

Base: `4591fab9a80ef63c440b9a117dbbc4fcbf03c430`.
Product commits: `ede8d44` (4096 → 8192 completion cap), `92844bd83481e03b07f49c3ee79c13096ca38d39` (document selection boundary).
Provider calls during this repair: **0**. No new model stage, feedback call, provider change, retry expansion, database write, or deployment.

The user explicitly approved moving semantic interpretation to the same model after seeing the concrete conflict between “换成” in the question and “推荐替代品” in the source. This supersedes the earlier strict lexical/alias gate. This receipt does not claim general semantic entailment can be proved by code.

## Root cause and final behavior

| Cases | Original rejection | What the actual output did |
|---|---|---|
| C01, C02, C03, T02-2 | attribute_conflict | Natural action paraphrase, table-row interpretation, opening-hours statement, replacement recommendation |
| C04, C06, C08, V02, V03-1, S01 | subject_conflict | Named supplier vs role, refund vs refund row, implicit employee, policy title vs member, compound subject and complaint summary |
| C05, V01, T02-3 | finish_reason=length | All 4096 completion tokens were reasoning tokens; final content was empty |

Disabling only lexical equivalence initially rescued 3/10, left value/format gates failing, and broke two old semantic rejection tests. `probe-no-equality.*` preserves that evidence. Safe formatting/value compatibility was explored next (`superseded-a-working.patch`, `safe-compat-first.txt`, `safe-protocol-first.txt`). The later user decision superseded that approach; its temporary normalizer and value rules are **not** in the final product.

Before, the model had to provide question/source `subject`, `attribute`, and `value` mappings. Literal/alias equality, hard-coded value shapes, modifier/predicate heuristics, a second local rank/claim check and entity coverage could reject a correct actual source. Now it returns only:

```json
{"answer_type":"doc","facts":[{"evidence_id":"ID copied from actual search_kb evidence"}]}
```

The model interprets subject/action/reference/meaning and selects 1–4 actual sources. Code verifies pool membership, duplicates, exact source/context offsets, chunk membership, actual metadata, explicit store applicability/effective date when a plan is supplied, table header availability, and output limits. Retrieval's version/store/eligibility filtering remains unchanged. Code renders the verified original quote/table, never model-authored prose or numbers. Legacy `binding` objects are ignored and counted in trace; they cannot act as a proof, override, or answer. Top-level/free fact fields remain rejected.

For example, the unchanged C01 payload selected the actual external-order 24-hour clause while annotating `申请退款 → 提出`; T02-2 selected the actual chicken-poke replacement clause. Both now render their selected sources. This is a semantic selection made by the original model, not a deterministic proof of all possible interpretations.

## Evidence and limits

| Verification | Result | What it establishes |
|---|---:|---|
| Correct initial saved-output boundary replay | 10/10 same original rejection, repeated once | `finalise-red*.json` reproduces the actual bug |
| Unchanged original final content + original executor evidence | 10/10 doc | `finalise-source-green.json`; every quote/context offset rechecked against current KB, no ID/content rewrite |
| New protocol through actual local HTTP/tools | 10/10 doc | Controlled selector picks the same original quote in a freshly retrieved pool with its new ID; HTTP traces are in `http-boundary-verified.tar.gz` |
| Selection/source/scope/structure + request cap suite | 49 passed | `boundary-verified.txt`, `fixed-head-tests.txt`; includes tampered numbers/columns, missing table header, fake ID/chunk/context/metadata/offset, duplicates/free fields, future effective date and explicit wrong store |
| Original backend tests, separate Python process | 53 passed | `starter-tests.txt`; avoids historical conftest Retriever monkeypatch pollution |
| Data, credentials, session, budget suites | 50 passed | `data-session-credentials.txt`; preserves G3-01/G3-04 behavior |
| G303 mixed operations + HTTP + G304 integration | 72 passed | `mixed-interface.txt`; existing DocumentEvidence integration remains compatible |
| Actual HTTP version/store filtering and tool injection tests | 5 passed | `scope-tools.txt`, `http-scope-tools.tar.gz` |
| Historical semantic/clarification suite, unchanged assertions | 30 passed / 17 failed | **Guarantee change**, not a passing regression suite; see below |

The minimal HTTP test uses the original recorded search query that yielded the chosen fact, not model-generated fresh queries. T02 needed its second original query; the first test attempt accidentally used its first query and failed to find that source (`selection-first.txt`). Corrected harness results are separately retained. These tests do not establish model retrieval planning or real semantic accuracy under the new prompt. G305 owns the authorized real retest.

`legacy-47-classification.json` enumerates every historical case. Of the 17 failures, 16 are real-source semantic misselection cases (arrival vs application, employee vs customer, appeal vs attendance, wrong channel, cross-clause relation, same-unit wrong action, omitted qualifiers). The new code can render those wrongly selected legitimate sources: **that risk is real and remains to be measured with actual model choices**. One failure was a legacy self-reported-support binding schema assertion: such fields are now ignored, never treated as proof. The 30 passing cases include source-rendering positives and deterministic clarification structure/free-text protections. Original tests and their failing output/XML are preserved, not flipped or deleted. G305 should evaluate the semantic negatives as model-selection quality, alongside normal positive questions.

## Output budget

`length-diagnosis.json` records the three original truncated responses' usage, current official URL/time/facts and cost calculation. Official documentation: [Chat completion parameters](https://api-docs.deepseek.com/zh-cn/api/create-chat-completion/), [pricing](https://api-docs.deepseek.com/zh-cn/quick_start/pricing), [thinking mode](https://api-docs.deepseek.com/zh-cn/guides/thinking_mode/).

Only `max_tokens` changes to 8192. Thinking settings and retry policy remain unchanged; length remains a hard, traced failure. `kbqa.llm.valid_output_limit(value)` accepts exactly integers 1..8192 (no bool, missing value, string or float) and is available for the current G305 guard to reuse. Its owner must validate before every outbound attempt and reserve 2.20 CNY; no usage means retaining the full reserve. Old G301/G302 paid runners are historical and were not rewritten or run.

Conservative peak bound: `(1,048,576 × 2 + 8192 × 8) / 1,000,000 = 2.162688 CNY < 2.20 CNY`. This deliberately counts the full context as input in addition to output. 8192 may still truncate or increase latency; only real testing can establish success. No saved truncated answer can be recovered by this configuration change.

## Reproduction and preservation

```sh
G302_HTTP_OUT=/tmp/g302-review-http starter/.venv/bin/python -m pytest -q \
  docs/verification/g3-02-live-repair/test_selection_boundary.py \
  docs/verification/g3-02-live-repair/test_output_limit.py
starter/.venv/bin/python docs/verification/g3-02-live-repair/finalise_replay.py /tmp/g302-new-replay.json
# Keep starter/tests in a separate process.
starter/.venv/bin/python -m pytest -q starter/tests
```

Use a new evidence output path on each run. The replay refuses to overwrite an existing output. `probe_gates.py` and `superseded_a_probe.py` are historical diagnostic stages; they are not runnable against the simplified final contract without their original revision/patch.

The first full Service replay (`replay-red.json.gz`) encountered cross-checkout IDs because the index key includes the resolved KB path. It is retained as an unsuccessful harness attempt and is not claimed as the correct regression. The finalisation replay deliberately uses original executor evidence after validating current source offsets, not a fabricated remapping of raw model content.

`snapshot.json` records exact complete JSONL snapshot hashes/source paths. Gzip archives decompress to those exact original bytes. HTTP tar archives retain full controlled request/response/trace evidence. Local originals are preserved and excluded from Git to avoid duplicate storage. Provider HTML stays local; only necessary facts and source URLs are committed.

`protection-after.json`: all **5190 protected blobs unchanged**, research unchanged, deleted follow-up draft still absent, actual-Key scan **0**. G305's independent worktree was only read to snapshot complete records; no environment/process/evidence was modified. No G303 mixed answer logic was edited; `live.py` retains its existing hybrid branch. Main conversation reviews/merges; this execution does not close the issue or claim the final paid evaluation is complete.

Resource audit: `resources.json` records 45 owned HTTP service runs, all stopped by their harness and none of those PIDs still exists. Temporary verification directories are retained for review; no shared/G305 resources were stopped or deleted. Additional G303 HTTP artifacts remain at `/tmp/g302-g303-http-92844bd`.

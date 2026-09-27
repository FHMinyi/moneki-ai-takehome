# G303 / G304 integration and PR34 review repair

Normal merge **623b38c12ee688eb8d41ac9366674c4d73064e08** combines saved G303 head996ebb9 and accepted main **bb7883cd94cbad02fd53234b7e7beb978129cc57**. No rebase of reviewed commits. Git automatically merged live/service/frontend; acceptance below uses real HTTP and browser evidence.

Final integration business: **d9a69ab8c078cd0545ea8d6855eff7166c6a1a74**. Subsequent evidence changes do not change product bytes. `fixed-audit.json` records hashes and protection. Paid usage remains 4chat/11API/0.223182 CNY estimate, not a bill; directed pool16/18, G301 initial3 separate. Final real-model semantic acceptance remains G305; no paid retry was performed here.

## P1: payment revenue operands lost cents

The coordinator found 95.23% beside a rounded `10 / 10 元` for actual9.99/10.49. At product623b38c, three independent replacement SQLite fixtures were exercised through actual HTTP:

| Cash net | Card net | Total net | Expected share |
|---:|---:|---:|---:|
| 9.99 | 0.50 | 10.49 | 95.23% |
| 9.99 | -9.99 | 0.00 | Undefined: denominator zero |
| -9.99 | 20.48 | 10.49 | -95.23% |

`cents-red.txt`: **3 failed**, recorded before repair with actual responses/traces in `cents-red-http/`; test/evidence commit **b8b8f4d**. Product fix **20fe53a** uses R.money for net_revenue and R.count for orders. Queries, refunds and Decimal division are unchanged. `cents-green.txt`: **6 passed**, including canonical zero and unknown-payment-label cases. Final `http-final/fractional-payment-*.json` rechecks the monetary cases at d9a69ab. This is distinct from the coordinator's original synthetic-operand proof.

## Cross-boundary red/green chronology

- `before-cross.txt`: merged-source original/new tests75 passed before new cross tests.
- `cross-red.txt`: 7 passed/2 failed, with one **test selector failure** plus real invalid-reference history failure. It does not prove two product defects.
- `cross-red-corrected.txt`: after a focused search-query correction, 8 passed/1 failed. The complete question did not inherit the old product; that hypothesis was not recorded as a reproduced bug.
- `cross-red-followup.txt`: 9 passed/1 failed; a longer follow-up still did not reproduce product inheritance.
- Truly elliptical `那这段时间呢？` then gave **cross-red-final.txt: 9 passed/2 failed on product20fe53a**: inherited P06 conflicted with the whole-store reference, and invalid reference refusal retained old history. Red evidence/test commit **861496d**.
- **5960ec9** clears history on invalid-reference refusal only inside the acquired-session path. Busy responses bypass it and retain in-flight history. Reference product comes exclusively from current explicit wording, otherwise None; old inherited product is also removed from the stored rewritten question to prevent later resurrection. Actual user wording stays intact; mixed result checks are not relaxed.
- `affected.txt`: 216 passed/1 failed due to an extra empty product-origin diagnostic field. **d9a69ab** preserves the G306 diagnostic shape when no product existed; the old test was not edited. `affected-final.txt`: **217 passed**.

## Fourteen actual HTTP cross cases at d9a69ab

`cross-fixed.txt`: **14 passed**. Provider outputs are controlled inputs, while HTTP/FastAPI/SQLite/BM25/session state are real. `cross-fixed-http/` contains every request/response/trace, named by scenario prefix and trace ID. The test oracle separately queries read-only SQLite.

| Case | Evidence prefix | Actual result |
|---|---|---|
| Target → new date → explicit new subject | changes | June19/S02/P06 fresh query, then July/S01/P05/orders; independent SQL matches |
| Natural follow-up | natural | Successful H01 question delivered to model, old answer absent; fresh daily June8–14/S03 sums3630 |
| Price → historical date | price | New July1/P06 query and search; citation as_of July1 and new IDs |
| Mixed binding failure | failure | Wrong metric refused without evidence; next follow-up history_size0, no model call |
| Clarify → independent price question | clarify | Prior8号 absent from prompt; clarification_reset true |
| Reference after product, three formulations | reference… | June8–14/S03/product None/net3630; plan/effective/query agree, including short elliptical wording |
| Invalid reference | invalid-ref | S99 attachment refused; next follow-up has no old context |
| Busy same-session request | busy | Response under1s, history_changed=false; completed first mixed answer still supplies exactly one successful prior turn |
| Six tool rounds plus final opportunity | six | 7 model turns, final tool_choice none, successful target; dummy secret/reasoning absent from public output |
| Explicit overrides, two variants | explicit… | Current P05 beats oldP06; explicit July/S01 beats referenceJune/S03; plan/effective/params agree |
| No resurrection on subsequent turn | resurrection | P06 → whole-store reference → July/S03 without product in plan or query |

Three reference formulations and two explicit variants account for the fourteen tests. They are not fourteen paid samples.

## Other gates

At d9a69ab: `affected-final.txt` **217 passed** (G303, G304 session, G301 credential/data, G302 binding, G306 scope/routes); `original.txt` **53 passed** in an independent process; `no-key/eval/report.md` **94/100,53/55** on unchanged public questions. The no-key gain reflects accepted G304 multi-turn behavior and is not live-model evidence. `build.txt` records successful frontend build/typecheck after merge; integration repairs do not change UI product code.

Browser evidence and exact reproduction follow below. Earlier records retain their original SHAs and failures.

## Browser provenance: real visible mouse selector verified

`browser.txt` and `browser-final.txt` each preserve three selection-timeout failures/four passes. Initial ArrowDown-plus-mouse-option navigation and then direct clicking of the readonly input were not reliable mouse targets. These locator failures were not treated as proof of a product mouse defect.

Per coordinator review, `select-inspection/dom.json` and `selector.png` record the actual DOM/screen after closing the Drawer: the input[role=combobox] is readonly and opacity0; the visible selection is the sibling selection-item inside the selector frame. Keyboard interaction was independently verified in `browser-keyboard.txt` (7 passed), with its test source preserved.

Final test clicks the verified visible `.ant-select[aria-label=门店] .ant-select-selector`, then the actually visible dropdown S03 option, without force or JS state mutation. It asserts the visible selected name, applies the filter, submits the attachment, and checks returned query conditions and citations. **browser-mouse.txt: 7 passed** at d9a69ab: mixed→whole-store trend→new explicit product and price→historical date at1280/1440/390, plus G304 late-response isolation. Actual payloads/answers/traces and screenshots are in `browser-mouse/`;390 was visually inspected. UI product code was not changed to make this pass.

## Reproduce using new output directories

The saved-response replay test expects its output directory to exist. Create it first; otherwise FileNotFoundError after passing business assertions is an output setup error, not a product failure. Do not point any environment variable at historical evidence paths.

```bash
mkdir -p /tmp/g303-integration-review/replay
G303_CROSS_OUT=/tmp/g303-integration-review/cross \
 starter/.venv/bin/python -m pytest docs/verification/g3-03/integration-g304/test_cross.py -q
# 14 real HTTP cases

G303_REPLAY_OUT=/tmp/g303-integration-review/replay \
 G303_HTTP_OUT=/tmp/g303-integration-review/http \
 G304_NATURAL_EVIDENCE_DIR=/tmp/g303-integration-review/replay \
 G3_CREDENTIAL_EVIDENCE=/tmp/g303-integration-review/credentials \
 starter/.venv/bin/python -m pytest \
 docs/verification/g3-03/test_mixed.py docs/verification/g3-03/test_http.py \
 docs/verification/g3-03/test_live_replay.py docs/verification/g3-04/test_session_context.py \
 docs/verification/g3-01/test_data_chat.py docs/verification/g3-01/test_credentials.py \
 docs/verification/g3-02/test_document_binding.py \
 docs/verification/g3-02/review-r1-r2/test_anchored_selection.py \
 docs/verification/g3-02/review-roles/test_roles.py \
 docs/verification/g3-06/test_trend_context.py \
 docs/verification/g3-06/test_early_plan_context.py docs/verification/g3-06/test_route_regression.py -q
# 217 passed; affected-final.txt

starter/.venv/bin/python -m pytest starter/tests -q
# 53 passed, separate process

G303_NOKEY_OUT=/tmp/g303-integration-review/no-key \
 starter/.venv/bin/python docs/verification/g3-03/verify_no_key.py
# 94/100,53/55; the output directory must be new

starter/.venv/bin/python docs/verification/g3-03/integration-g304/controller.py /tmp/g303-integration-review/server
# In frontend/, replace API/MODEL with ports printed above:
BROWSER_BASE_URL=http://127.0.0.1:API G303_CROSS_MODEL_URL=http://127.0.0.1:MODEL \
 G303_CROSS_BROWSER_OUT=/tmp/g303-integration-review/browser \
 G304_EVIDENCE_DIR=/tmp/g303-integration-review/browser-session \
 npx playwright test tests/g3-mixed-session.spec.ts tests/g3-session-context.spec.ts \
 --grep '混合后|混合价格|旧请求迟到' --workers=1 --output=/tmp/g303-integration-review/browser-runtime
# 7 passed; browser-mouse.txt
```

## Preserved records and retained resources

`fixed-audit.json`: initial4209 protected files unchanged; incoming main's108 input/evaluation/G304 history files unchanged; saved G303 head996ebb9's603 raw historical artifacts unchanged. Authorized test/source/narrative edits are separate. Integration artifacts contain no real credential. Original paid ledger/API/trace bytes are unchanged.

Latest controlled review URL **http://127.0.0.1:56398**, model56396, harness85518/API85525, var `/tmp/g303-g304-d9a69ab-runtime/var`. Initial integration pair85044/85058, model56076/API56077, var `/tmp/g303-g304-review-runtime/var`, also retained. `retained-resources.json` records both new pairs; earlier ticket services remain in the parent inventory. No managed tree was removed or archived. Await coordinator independent acceptance and concrete cleanup instructions.

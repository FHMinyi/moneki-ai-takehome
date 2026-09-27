# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: g3-mixed-session.spec.ts >> 混合后趋势引用与文字覆盖 390
- Location: tests/g3-mixed-session.spec.ts:19:2

# Error details

```
Test timeout of 30000ms exceeded.
```

```
Error: locator.click: Test timeout of 30000ms exceeded.
Call log:
  - waiting for getByTitle('Juicy Bao Bao · S03', { exact: true })
    - locator resolved to <div aria-selected="false" title="Juicy Bao Bao · S03" class="ant-select-item ant-select-item-option">…</div>
  - attempting click action
    - waiting for element to be visible, enabled and stable
    - element is visible, enabled and stable
    - scrolling into view if needed
    - done scrolling
    - element is outside of the viewport
  - retrying click action
    - waiting for element to be visible, enabled and stable
    - element is not visible
  - retrying click action
    - waiting 20ms
    2 × waiting for element to be visible, enabled and stable
      - element is not stable
    - retrying click action
      - waiting 100ms
    - waiting for element to be visible, enabled and stable
    - element is visible, enabled and stable
    - scrolling into view if needed
    - done scrolling
    - <p class="scope-note" data-testid="applied-filters">…</p> from <div id="root">…</div> subtree intercepts pointer events
  56 × retrying click action
       - waiting 500ms
       - waiting for element to be visible, enabled and stable
       - element is not visible
  - retrying click action
    - waiting 500ms

```

# Page snapshot

```yaml
- generic [ref=e3]:
  - banner [ref=e4]:
    - link "m moneki" [ref=e5] [cursor=pointer]:
      - /url: /
      - generic [ref=e6]: m
      - text: moneki
    - generic [ref=e7]: 总部运营 / 经营看板
  - main [ref=e8]:
    - generic [ref=e9]:
      - generic [ref=e10]:
        - generic [ref=e11]: 经营看板
        - heading "看清每一天的经营" [level=1] [ref=e12]
        - paragraph [ref=e13]: 按日期和门店查看真实经营数据，核对清洗结果与指标口径。
      - button "刷新数据" [ref=e14] [cursor=pointer]
    - generic [ref=e16]:
      - generic [ref=e17]:
        - heading "经营汇总" [level=2] [ref=e18]
        - generic [ref=e19]: 日期闭区间
      - generic [ref=e21]:
        - generic [ref=e22]:
          - generic [ref=e23]:
            - text: 开始日期
            - textbox "开始日期" [ref=e24]:
              - /placeholder: YYYY-MM-DD
              - text: 2026-06-08
          - generic [ref=e25]:
            - text: 结束日期
            - textbox "结束日期" [ref=e26]:
              - /placeholder: YYYY-MM-DD
              - text: 2026-06-14
          - generic [ref=e27]:
            - text: 门店
            - generic "门店" [ref=e28] [cursor=pointer]:
              - generic [ref=e30]:
                - combobox "门店" [ref=e32]
                - generic "全部门店" [ref=e33]
          - button "查询汇总" [ref=e34] [cursor=pointer]
        - paragraph [ref=e36]: 起止日期均包含当天；编辑后点击查询，使条件生效。
      - paragraph [ref=e37]: 已生效：2026-05-01 至 2026-08-31 · 全部门店
      - region "经营汇总" [ref=e38]:
        - generic [ref=e39]:
          - generic [ref=e41]:
            - generic [ref=e42]: 净营业额
            - generic [ref=e43]: ¥646,929.00
            - paragraph [ref=e44]: 销售实收减去退款
          - generic [ref=e46]:
            - generic [ref=e47]: 退款金额
            - generic [ref=e48]: ¥3,237.00
            - paragraph [ref=e49]: 按退款发生日期归属
          - generic [ref=e51]:
            - generic [ref=e52]: 有效订单数
            - generic [ref=e53]: 17,926
            - paragraph [ref=e54]: 销售行按订单号去重
          - generic [ref=e56]:
            - generic [ref=e57]: 客单价
            - generic [ref=e58]: ¥36.09
            - paragraph [ref=e59]: 净营业额 ÷ 有效订单数
          - generic [ref=e61]:
            - generic [ref=e62]: 销量
            - generic [ref=e63]: 27,262
            - paragraph [ref=e64]: 销售数量减去退款数量
      - region "每日净营业额趋势" [ref=e65]:
        - generic [ref=e66]:
          - heading "每日净营业额趋势" [level=2] [ref=e67]
          - generic [ref=e68]: 单位：元 · 日期按退款发生日归属
        - generic [ref=e70]:
          - generic [ref=e71]:
            - button "加入提问" [ref=e72] [cursor=pointer]
            - generic [ref=e74]: 引用整个趋势范围，提问时重新查询数据
          - generic [ref=e75]:
            - generic [ref=e76]: 2026-08-31
            - strong [ref=e77]: ¥4,055.00
            - generic [ref=e78]: 有效订单 126 单
          - paragraph [ref=e79]: 选择图上的日期读取精确金额；横向滚动可查看完整区间。
          - region "每日净营业额图表，可横向滚动" [ref=e80]:
            - img "每日净营业额，2026-05-01 至 2026-08-31" [ref=e81]:
              - generic [ref=e82]: ¥0
              - generic [ref=e83]: ¥8,308.00
              - generic [ref=e85]:
                - generic [ref=e86]: 05-01
                - button "2026-05-01 净营业额 ¥5,075.00" [ref=e88] [cursor=pointer]
              - button "2026-05-02 净营业额 ¥7,231.00" [ref=e91] [cursor=pointer]
              - button "2026-05-03 净营业额 ¥7,501.00" [ref=e94] [cursor=pointer]
              - button "2026-05-04 净营业额 ¥4,472.00" [ref=e97] [cursor=pointer]
              - button "2026-05-05 净营业额 ¥4,631.00" [ref=e100] [cursor=pointer]
              - generic [ref=e101]:
                - generic [ref=e102]: 05-06
                - button "2026-05-06 净营业额 ¥4,644.00" [ref=e104] [cursor=pointer]
              - button "2026-05-07 净营业额 ¥4,251.00" [ref=e107] [cursor=pointer]
              - button "2026-05-08 净营业额 ¥4,806.00" [ref=e110] [cursor=pointer]
              - button "2026-05-09 净营业额 ¥6,848.00" [ref=e113] [cursor=pointer]
              - button "2026-05-10 净营业额 ¥7,109.00" [ref=e116] [cursor=pointer]
              - generic [ref=e117]:
                - generic [ref=e118]: 05-11
                - button "2026-05-11 净营业额 ¥4,888.00" [ref=e120] [cursor=pointer]
              - button "2026-05-12 净营业额 ¥4,843.00" [ref=e123] [cursor=pointer]
              - button "2026-05-13 净营业额 ¥4,610.00" [ref=e126] [cursor=pointer]
              - button "2026-05-14 净营业额 ¥4,334.00" [ref=e129] [cursor=pointer]
              - button "2026-05-15 净营业额 ¥4,796.00" [ref=e132] [cursor=pointer]
              - generic [ref=e133]:
                - generic [ref=e134]: 05-16
                - button "2026-05-16 净营业额 ¥7,642.00" [ref=e136] [cursor=pointer]
              - button "2026-05-17 净营业额 ¥7,075.00" [ref=e139] [cursor=pointer]
              - button "2026-05-18 净营业额 ¥4,480.00" [ref=e142] [cursor=pointer]
              - button "2026-05-19 净营业额 ¥4,557.00" [ref=e145] [cursor=pointer]
              - button "2026-05-20 净营业额 ¥4,382.00" [ref=e148] [cursor=pointer]
              - generic [ref=e149]:
                - generic [ref=e150]: 05-21
                - button "2026-05-21 净营业额 ¥4,373.00" [ref=e152] [cursor=pointer]
              - button "2026-05-22 净营业额 ¥4,412.00" [ref=e155] [cursor=pointer]
              - button "2026-05-23 净营业额 ¥7,039.00" [ref=e158] [cursor=pointer]
              - button "2026-05-24 净营业额 ¥6,601.00" [ref=e161] [cursor=pointer]
              - button "2026-05-25 净营业额 ¥4,024.00" [ref=e164] [cursor=pointer]
              - generic [ref=e165]:
                - generic [ref=e166]: 05-26
                - button "2026-05-26 净营业额 ¥4,637.00" [ref=e168] [cursor=pointer]
              - button "2026-05-27 净营业额 ¥4,637.00" [ref=e171] [cursor=pointer]
              - button "2026-05-28 净营业额 ¥4,381.00" [ref=e174] [cursor=pointer]
              - button "2026-05-29 净营业额 ¥5,196.00" [ref=e177] [cursor=pointer]
              - button "2026-05-30 净营业额 ¥7,088.00" [ref=e180] [cursor=pointer]
              - generic [ref=e181]:
                - generic [ref=e182]: 05-31
                - button "2026-05-31 净营业额 ¥6,850.00" [ref=e184] [cursor=pointer]
              - button "2026-06-01 净营业额 ¥4,343.00" [ref=e187] [cursor=pointer]
              - button "2026-06-02 净营业额 ¥4,519.00" [ref=e190] [cursor=pointer]
              - button "2026-06-03 净营业额 ¥4,471.00" [ref=e193] [cursor=pointer]
              - button "2026-06-04 净营业额 ¥4,936.00" [ref=e196] [cursor=pointer]
              - generic [ref=e197]:
                - generic [ref=e198]: 06-05
                - button "2026-06-05 净营业额 ¥4,926.00" [ref=e200] [cursor=pointer]
              - button "2026-06-06 净营业额 ¥7,191.00" [ref=e203] [cursor=pointer]
              - button "2026-06-07 净营业额 ¥6,770.00" [ref=e206] [cursor=pointer]
              - button "2026-06-08 净营业额 ¥3,867.00" [ref=e209] [cursor=pointer]
              - button "2026-06-09 净营业额 ¥3,652.00" [ref=e212] [cursor=pointer]
              - generic [ref=e213]:
                - generic [ref=e214]: 06-10
                - button "2026-06-10 净营业额 ¥3,246.00" [ref=e216] [cursor=pointer]
              - button "2026-06-11 净营业额 ¥3,897.00" [ref=e219] [cursor=pointer]
              - button "2026-06-12 净营业额 ¥5,073.00" [ref=e222] [cursor=pointer]
              - button "2026-06-13 净营业额 ¥7,421.00" [ref=e225] [cursor=pointer]
              - button "2026-06-14 净营业额 ¥6,329.00" [ref=e228] [cursor=pointer]
              - generic [ref=e229]:
                - generic [ref=e230]: 06-15
                - button "2026-06-15 净营业额 ¥4,225.00" [ref=e232] [cursor=pointer]
              - button "2026-06-16 净营业额 ¥5,196.00" [ref=e235] [cursor=pointer]
              - button "2026-06-17 净营业额 ¥4,420.00" [ref=e238] [cursor=pointer]
              - button "2026-06-18 净营业额 ¥8,308.00" [ref=e241] [cursor=pointer]
              - button "2026-06-19 净营业额 ¥4,822.00" [ref=e244] [cursor=pointer]
              - generic [ref=e245]:
                - generic [ref=e246]: 06-20
                - button "2026-06-20 净营业额 ¥6,224.00" [ref=e248] [cursor=pointer]
              - button "2026-06-21 净营业额 ¥7,082.00" [ref=e251] [cursor=pointer]
              - button "2026-06-22 净营业额 ¥4,509.00" [ref=e254] [cursor=pointer]
              - button "2026-06-23 净营业额 ¥4,434.00" [ref=e257] [cursor=pointer]
              - button "2026-06-24 净营业额 ¥4,412.00" [ref=e260] [cursor=pointer]
              - generic [ref=e261]:
                - generic [ref=e262]: 06-25
                - button "2026-06-25 净营业额 ¥3,732.00" [ref=e264] [cursor=pointer]
              - button "2026-06-26 净营业额 ¥4,349.00" [ref=e267] [cursor=pointer]
              - button "2026-06-27 净营业额 ¥7,698.00" [ref=e270] [cursor=pointer]
              - button "2026-06-28 净营业额 ¥7,159.00" [ref=e273] [cursor=pointer]
              - button "2026-06-29 净营业额 ¥5,043.00" [ref=e276] [cursor=pointer]
              - generic [ref=e277]:
                - generic [ref=e278]: 06-30
                - button "2026-06-30 净营业额 ¥4,503.00" [ref=e280] [cursor=pointer]
              - button "2026-07-01 净营业额 ¥4,292.00" [ref=e283] [cursor=pointer]
              - button "2026-07-02 净营业额 ¥4,924.00" [ref=e286] [cursor=pointer]
              - button "2026-07-03 净营业额 ¥5,072.00" [ref=e289] [cursor=pointer]
              - button "2026-07-04 净营业额 ¥7,345.00" [ref=e292] [cursor=pointer]
              - generic [ref=e293]:
                - generic [ref=e294]: 07-05
                - button "2026-07-05 净营业额 ¥7,504.00" [ref=e296] [cursor=pointer]
              - button "2026-07-06 净营业额 ¥5,140.00" [ref=e299] [cursor=pointer]
              - button "2026-07-07 净营业额 ¥4,428.00" [ref=e302] [cursor=pointer]
              - button "2026-07-08 净营业额 ¥4,531.00" [ref=e305] [cursor=pointer]
              - button "2026-07-09 净营业额 ¥4,843.00" [ref=e308] [cursor=pointer]
              - generic [ref=e309]:
                - generic [ref=e310]: 07-10
                - button "2026-07-10 净营业额 ¥4,389.00" [ref=e312] [cursor=pointer]
              - button "2026-07-11 净营业额 ¥6,409.00" [ref=e315] [cursor=pointer]
              - button "2026-07-12 净营业额 ¥6,822.00" [ref=e318] [cursor=pointer]
              - button "2026-07-13 净营业额 ¥5,396.00" [ref=e321] [cursor=pointer]
              - button "2026-07-14 净营业额 ¥5,371.00" [ref=e324] [cursor=pointer]
              - generic [ref=e325]:
                - generic [ref=e326]: 07-15
                - button "2026-07-15 净营业额 ¥4,160.00" [ref=e328] [cursor=pointer]
              - button "2026-07-16 净营业额 ¥4,824.00" [ref=e331] [cursor=pointer]
              - button "2026-07-17 净营业额 ¥4,955.00" [ref=e334] [cursor=pointer]
              - button "2026-07-18 净营业额 ¥7,170.00" [ref=e337] [cursor=pointer]
              - button "2026-07-19 净营业额 ¥6,785.00" [ref=e340] [cursor=pointer]
              - generic [ref=e341]:
                - generic [ref=e342]: 07-20
                - button "2026-07-20 净营业额 ¥4,319.00" [ref=e344] [cursor=pointer]
              - button "2026-07-21 净营业额 ¥4,574.00" [ref=e347] [cursor=pointer]
              - button "2026-07-22 净营业额 ¥4,480.00" [ref=e350] [cursor=pointer]
              - button "2026-07-23 净营业额 ¥4,796.00" [ref=e353] [cursor=pointer]
              - button "2026-07-24 净营业额 ¥2,053.00" [ref=e356] [cursor=pointer]
              - generic [ref=e357]:
                - generic [ref=e358]: 07-25
                - button "2026-07-25 净营业额 ¥6,821.00" [ref=e360] [cursor=pointer]
              - button "2026-07-26 净营业额 ¥6,693.00" [ref=e363] [cursor=pointer]
              - button "2026-07-27 净营业额 ¥4,799.00" [ref=e366] [cursor=pointer]
              - button "2026-07-28 净营业额 ¥5,211.00" [ref=e369] [cursor=pointer]
              - button "2026-07-29 净营业额 ¥4,802.00" [ref=e372] [cursor=pointer]
              - generic [ref=e373]:
                - generic [ref=e374]: 07-30
                - button "2026-07-30 净营业额 ¥4,803.00" [ref=e376] [cursor=pointer]
              - button "2026-07-31 净营业额 ¥4,703.00" [ref=e379] [cursor=pointer]
              - button "2026-08-01 净营业额 ¥6,760.00" [ref=e382] [cursor=pointer]
              - button "2026-08-02 净营业额 ¥7,301.00" [ref=e385] [cursor=pointer]
              - button "2026-08-03 净营业额 ¥4,904.00" [ref=e388] [cursor=pointer]
              - generic [ref=e389]:
                - generic [ref=e390]: 08-04
                - button "2026-08-04 净营业额 ¥4,642.00" [ref=e392] [cursor=pointer]
              - button "2026-08-05 净营业额 ¥4,903.00" [ref=e395] [cursor=pointer]
              - button "2026-08-06 净营业额 ¥3,871.00" [ref=e398] [cursor=pointer]
              - button "2026-08-07 净营业额 ¥4,851.00" [ref=e401] [cursor=pointer]
              - button "2026-08-08 净营业额 ¥6,850.00" [ref=e404] [cursor=pointer]
              - generic [ref=e405]:
                - generic [ref=e406]: 08-09
                - button "2026-08-09 净营业额 ¥6,940.00" [ref=e408] [cursor=pointer]
              - button "2026-08-10 净营业额 ¥4,561.00" [ref=e411] [cursor=pointer]
              - button "2026-08-11 净营业额 ¥4,878.00" [ref=e414] [cursor=pointer]
              - button "2026-08-12 净营业额 ¥4,402.00" [ref=e417] [cursor=pointer]
              - button "2026-08-13 净营业额 ¥4,506.00" [ref=e420] [cursor=pointer]
              - generic [ref=e421]:
                - generic [ref=e422]: 08-14
                - button "2026-08-14 净营业额 ¥4,571.00" [ref=e424] [cursor=pointer]
              - button "2026-08-15 净营业额 ¥6,986.00" [ref=e427] [cursor=pointer]
              - button "2026-08-16 净营业额 ¥6,925.00" [ref=e430] [cursor=pointer]
              - button "2026-08-17 净营业额 ¥3,376.00" [ref=e433] [cursor=pointer]
              - button "2026-08-18 净营业额 ¥3,413.00" [ref=e436] [cursor=pointer]
              - generic [ref=e437]:
                - generic [ref=e438]: 08-19
                - button "2026-08-19 净营业额 ¥3,067.00" [ref=e440] [cursor=pointer]
              - button "2026-08-20 净营业额 ¥4,202.00" [ref=e443] [cursor=pointer]
              - button "2026-08-21 净营业额 ¥4,264.00" [ref=e446] [cursor=pointer]
              - button "2026-08-22 净营业额 ¥7,363.00" [ref=e449] [cursor=pointer]
              - button "2026-08-23 净营业额 ¥6,411.00" [ref=e452] [cursor=pointer]
              - generic [ref=e453]:
                - generic [ref=e454]: 08-24
                - button "2026-08-24 净营业额 ¥4,532.00" [ref=e456] [cursor=pointer]
              - button "2026-08-25 净营业额 ¥5,099.00" [ref=e459] [cursor=pointer]
              - button "2026-08-26 净营业额 ¥4,333.00" [ref=e462] [cursor=pointer]
              - button "2026-08-27 净营业额 ¥4,281.00" [ref=e465] [cursor=pointer]
              - button "2026-08-28 净营业额 ¥4,639.00" [ref=e468] [cursor=pointer]
              - generic [ref=e469]:
                - generic [ref=e470]: 08-29
                - button "2026-08-29 净营业额 ¥7,029.00" [ref=e472] [cursor=pointer]
              - button "2026-08-30 净营业额 ¥6,430.00" [ref=e475] [cursor=pointer]
              - generic [ref=e476]:
                - generic [ref=e477]: 08-31
                - button "2026-08-31 净营业额 ¥4,055.00" [ref=e479] [cursor=pointer]
          - group [ref=e480]:
            - generic "查看每日明细（123 天）" [ref=e481] [cursor=pointer]
      - region "商品排行" [ref=e482]:
        - generic [ref=e483]:
          - heading "Top 10 商品" [level=2] [ref=e484]
          - paragraph [ref=e485]: 按净营业额降序；同额按商品编号升序。销量为销售数量减退款数量。窄屏可左右滑动表格。
        - table [ref=e494]:
          - rowgroup [ref=e500]:
            - row [ref=e501]:
              - columnheader "排名" [ref=e502]
              - columnheader "商品名称 / 编号" [ref=e503]
              - columnheader "净营业额" [ref=e504]
              - columnheader "销量" [ref=e505]
          - rowgroup [ref=e506]:
            - row [ref=e507]:
              - cell "1" [ref=e508]
              - cell "牛肉poke P06" [ref=e509]:
                - generic [ref=e510]:
                  - text: 牛肉poke
                  - generic [ref=e511]: P06
              - cell "¥82,570.00" [ref=e512]
              - cell "1,939" [ref=e513]
            - row [ref=e514]:
              - cell "2" [ref=e515]
              - cell "三文鱼poke P04" [ref=e516]:
                - generic [ref=e517]:
                  - text: 三文鱼poke
                  - generic [ref=e518]: P04
              - cell "¥59,546.00" [ref=e519]
              - cell "1,567" [ref=e520]
            - row [ref=e521]:
              - cell "3" [ref=e522]
              - cell "豚骨拉面 P01" [ref=e523]:
                - generic [ref=e524]:
                  - text: 豚骨拉面
                  - generic [ref=e525]: P01
              - cell "¥56,512.00" [ref=e526]
              - cell "1,766" [ref=e527]
            - row [ref=e528]:
              - cell "4" [ref=e529]
              - cell "鸡肉poke P05" [ref=e530]:
                - generic [ref=e531]:
                  - text: 鸡肉poke
                  - generic [ref=e532]: P05
              - cell "¥51,544.00" [ref=e533]
              - cell "1,516" [ref=e534]
            - row [ref=e535]:
              - cell "5" [ref=e536]
              - cell "味增拉面 P02" [ref=e537]:
                - generic [ref=e538]:
                  - text: 味增拉面
                  - generic [ref=e539]: P02
              - cell "¥49,680.00" [ref=e540]
              - cell "1,656" [ref=e541]
            - row [ref=e542]:
              - cell "6" [ref=e543]
              - cell "照烧鸡饭 P03" [ref=e544]:
                - generic [ref=e545]:
                  - text: 照烧鸡饭
                  - generic [ref=e546]: P03
              - cell "¥47,866.00" [ref=e547]
              - cell "1,841" [ref=e548]
            - row [ref=e549]:
              - cell "7" [ref=e550]
              - cell "照烧三明治 P10" [ref=e551]:
                - generic [ref=e552]:
                  - text: 照烧三明治
                  - generic [ref=e553]: P10
              - cell "¥45,384.00" [ref=e554]
              - cell "1,891" [ref=e555]
            - row [ref=e556]:
              - cell "8" [ref=e557]
              - cell "灌汤包 P08" [ref=e558]:
                - generic [ref=e559]:
                  - text: 灌汤包
                  - generic [ref=e560]: P08
              - cell "¥34,525.00" [ref=e561]
              - cell "1,381" [ref=e562]
            - row [ref=e563]:
              - cell "9" [ref=e564]
              - cell "吞拿鱼三明治 P11" [ref=e565]:
                - generic [ref=e566]:
                  - text: 吞拿鱼三明治
                  - generic [ref=e567]: P11
              - cell "¥33,904.00" [ref=e568]
              - cell "1,304" [ref=e569]
            - row [ref=e570]:
              - cell "10" [ref=e571]
              - cell "小笼包 P07" [ref=e572]:
                - generic [ref=e573]:
                  - text: 小笼包
                  - generic [ref=e574]: P07
              - cell "¥33,836.00" [ref=e575]
              - cell "1,538" [ref=e576]
    - region "数据质量台账" [ref=e577]:
      - generic [ref=e578]:
        - heading "数据质量" [level=2] [ref=e579]
        - generic [ref=e580]: KB-001 · 现行口径
      - paragraph [ref=e581]: 全量重建结果 · 不随看板筛选变化
      - generic [ref=e582]:
        - generic [ref=e583]:
          - generic [ref=e585]:
            - generic [ref=e586]: 原始明细
            - generic [ref=e587]: 18,628行
            - paragraph [ref=e588]: 来自 POS 原始数据
          - generic [ref=e590]:
            - generic [ref=e591]: 有效明细
            - generic [ref=e592]: 18,290行
            - paragraph [ref=e593]: 保留合法销售与退款
          - generic [ref=e595]:
            - generic [ref=e596]: 剔除明细
            - generic [ref=e597]: 338行
            - paragraph [ref=e598]: 按首个命中原因计数
        - generic [ref=e599]:
          - generic [ref=e600]: 有效数据日期
          - strong [ref=e601]: 2026-05-01 — 2026-08-31
          - generic [ref=e602]: 台账已对齐
        - generic [ref=e603]:
          - generic [ref=e605]:
            - generic [ref=e606]: 剔除原因台账
            - generic [ref=e607]: 按执行顺序
          - generic [ref=e608]:
            - paragraph [ref=e609]: 每行只计入最先命中的原因，避免重复计算剔除数量。
            - table [ref=e616]:
              - rowgroup [ref=e622]:
                - row [ref=e623]:
                  - columnheader "顺序" [ref=e624]
                  - columnheader "剔除原因" [ref=e625]
                  - columnheader "执行口径" [ref=e626]
                  - columnheader "剔除行数" [ref=e627]
              - rowgroup [ref=e628]:
                - row [ref=e629]:
                  - cell "01" [ref=e630]
                  - cell "日期无法解析" [ref=e631]
                  - cell "接受标准日期、斜杠日期与日在前的旧 POS 日期" [ref=e632]
                  - cell [ref=e633]:
                    - strong [ref=e634]: "8"
                - row [ref=e635]:
                  - cell "02" [ref=e636]
                  - cell "实收金额为空" [ref=e637]
                  - cell "直接剔除，不以商品单价回填" [ref=e638]
                  - cell [ref=e639]:
                    - strong [ref=e640]: "150"
                - row [ref=e641]:
                  - cell "03" [ref=e642]
                  - cell "数量小于或等于 0" [ref=e643]
                  - cell "按整数解析后检查数量" [ref=e644]
                  - cell [ref=e645]:
                    - strong [ref=e646]: "30"
                - row [ref=e647]:
                  - cell "04" [ref=e648]
                  - cell "门店编号无效" [ref=e649]
                  - cell "先去除首尾空白并转为大写，再核对门店表" [ref=e650]
                  - cell [ref=e651]:
                    - strong [ref=e652]: "10"
                - row [ref=e653]:
                  - cell "05" [ref=e654]
                  - cell "商品编号无效" [ref=e655]
                  - cell "先规范化编号，再核对商品表" [ref=e656]
                  - cell [ref=e657]:
                    - strong [ref=e658]: "40"
                - row [ref=e659]:
                  - cell "06" [ref=e660]
                  - cell "完全重复的明细" [ref=e661]
                  - cell "七个字段规范化后完全相同，只保留一行" [ref=e662]
                  - cell [ref=e663]:
                    - strong [ref=e664]: "100"
            - generic [ref=e665]:
              - generic [ref=e666]: 台账核对
              - strong [ref=e667]: 18,628 = 18,290 + 338
              - generic [ref=e668]: 原始 = 保留 + 剔除
        - paragraph [ref=e669]: 原始数据保持不变。重建完成后重启服务，再刷新此页查看最新结果。
  - contentinfo [ref=e670]: MONEKI / 数据口径以《指标口径手册 v3》为准
  - button "经营助手" [active] [ref=e671] [cursor=pointer]
```

# Test source

```ts
  1  | import { test, expect } from '@playwright/test';
  2  | import fs from 'node:fs';
  3  | import path from 'node:path';
  4  | const out=process.env.G303_CROSS_BROWSER_OUT!;
  5  | const model=process.env.G303_CROSS_MODEL_URL!;
  6  | const first='618 当天 S02 的牛肉poke 卖了多少份？达到目标了吗？';
  7  | const why='S03 六月第二周（6 月 8 日到 6 月 14 日）的营业额为什么比别的周低这么多？';
  8  | const price='牛肉poke 现在卖多少钱一份？商品表里那个价能直接拿来用吗？';
  9  | test.beforeAll(()=>fs.mkdirSync(out,{recursive:true}));
  10 | async function configure(request:any,question:string,c:any){await request.post(model+'/case',{data:{question,case:c}});}
  11 | async function ask(page:any,request:any,question:string){
  12 |  await page.getByLabel('经营问题').fill(question);
  13 |  const sent=page.waitForRequest((r:any)=>r.url().endsWith('/api/chat'));const got=page.waitForResponse((r:any)=>r.url().endsWith('/api/chat'));
  14 |  await page.getByRole('button',{name:'发送',exact:true}).click();const payload=(await sent).postDataJSON();const answer=await(await got).json();
  15 |  await expect(page.locator('.chat-answer').last()).toContainText(answer.answer);
  16 |  const trace=await(await request.get('/api/trace/'+answer.trace_id)).json();return {payload,answer,trace};
  17 | }
  18 | for(const width of [1280,1440,390]) {
  19 |  test(`混合后趋势引用与文字覆盖 ${width}`,async({page,request})=>{
  20 |   await page.setViewportSize({width,height:900});await page.goto('/');await page.getByRole('button',{name:'经营助手',exact:true}).click();
  21 |   const a=await ask(page,request,first);expect(a.answer.answer_type).toBe('hybrid');
  22 |   await page.getByRole('button',{name:'Close'}).click();
  23 |   await page.getByRole('textbox',{name:'开始日期'}).fill('2026-06-08');await page.getByRole('textbox',{name:'结束日期'}).fill('2026-06-14');
  24 |   const stores=(await(await request.get('/api/stores')).json()).stores;const store=stores.find((s:any)=>s.store_id==='S03');
> 25 |   await page.getByRole('combobox',{name:'门店'}).press('ArrowDown');await page.getByTitle(store.store_name+' · S03',{exact:true}).click();
     |                                                                                                                                 ^ Error: locator.click: Test timeout of 30000ms exceeded.
  26 |   await page.getByRole('button',{name:'查询汇总'}).click();await expect(page.getByTestId('applied-filters')).toContainText('S03');
  27 |   await page.getByRole('button',{name:'加入提问',exact:true}).click();
  28 |   const q='那这段时间呢？';await configure(request,q,{mode:'anomaly',tool:'query_metrics',params:{start:'2026-06-08',end:'2026-06-14',store_id:'S03'},metric:'net_revenue',doc:'KB-020',needle:'停业 4 天',role:'reason',query:why});
  29 |   const b=await ask(page,request,q);expect(b.answer.answer_type).toBe('hybrid');expect(b.payload.session_id).toBe(a.payload.session_id);expect(b.payload.context.store_id).toBe('S03');
  30 |   expect(b.answer.data_evidence[0].result.net_revenue).toBe(3630);expect(b.answer.data_evidence[0].params.product_id).toBeUndefined();
  31 |   expect(b.trace.steps.find((s:any)=>s.step==='plan').detail.product_id).toBeNull();
  32 |   const last=page.locator('.chat-answer').last();await last.getByText(/展开数据证据/).click();await last.getByText(/展开文档引用/).click();
  33 |   await expect(last).toContainText(b.answer.citations[0].quote);await expect(last).toContainText(JSON.stringify(b.answer.data_evidence[0].params,null,2));
  34 |   await page.screenshot({path:path.join(out,`trend-${width}.png`)});
  35 |   const next='7月S01鸡肉poke净营业额是多少？';await configure(request,next,{mode:'data',tool:'query_metrics',params:{start:'2026-07-01',end:'2026-07-31',store_id:'S01',product_id:'P05'},metric:'net_revenue'});
  36 |   const c=await ask(page,request,next);expect(c.answer.answer_type).toBe('data');expect(c.payload.context).toBeUndefined();expect(c.answer.data_evidence[0].params.product_id).toBe('P05');
  37 |   fs.writeFileSync(path.join(out,`trend-${width}.json`),JSON.stringify({a,b,c},null,2));
  38 |  });
  39 |  test(`混合价格追问重新取证 ${width}`,async({page,request})=>{
  40 |   await page.setViewportSize({width,height:900});await page.goto('/');await page.getByRole('button',{name:'经营助手',exact:true}).click();
  41 |   const a=await ask(page,request,price);expect(a.answer.answer_type).toBe('hybrid');
  42 |   const q='那7月1日呢？';await configure(request,q,{mode:'price',tool:'unit_price_check',params:{product_id:'P06',start:'2026-07-01',end:'2026-07-01'},metric:'unit_price',doc:'KB-025',needle:'调整为',role:'price',query:'牛肉poke售价调整'});
  43 |   const b=await ask(page,request,q);expect(b.answer.answer_type).toBe('hybrid');expect(b.answer.citations[0].scope.as_of).toBe('2026-07-01');expect(b.answer.citations[0].evidence_id).not.toBe(a.answer.citations[0].evidence_id);
  44 |   const last=page.locator('.chat-answer').last();await last.getByText(/展开数据证据/).click();await expect(last.getByRole('heading',{name:'计算关系与操作数来源'})).toBeVisible();await last.getByText(/展开文档引用/).click();
  45 |   await expect(last).toContainText(b.answer.citations[0].quote);fs.writeFileSync(path.join(out,`price-${width}.json`),JSON.stringify({a,b},null,2));await page.screenshot({path:path.join(out,`price-${width}.png`)});
  46 |  });
  47 | }
  48 | 
```
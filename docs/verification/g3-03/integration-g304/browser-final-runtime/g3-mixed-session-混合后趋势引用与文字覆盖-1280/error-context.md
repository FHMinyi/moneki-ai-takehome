# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: g3-mixed-session.spec.ts >> 混合后趋势引用与文字覆盖 1280
- Location: tests/g3-mixed-session.spec.ts:19:2

# Error details

```
Test timeout of 30000ms exceeded.
```

```
Error: locator.click: Test timeout of 30000ms exceeded.
Call log:
  - waiting for getByRole('combobox', { name: '门店' })
    - locator resolved to <input readonly value="" type="search" role="combobox" aria-label="门店" id="rc_select_0" unselectable="on" autocomplete="off" aria-expanded="false" aria-haspopup="listbox" aria-autocomplete="list" aria-owns="rc_select_0_list" aria-controls="rc_select_0_list" class="ant-select-selection-search-input"/>
  - attempting click action
    2 × waiting for element to be visible, enabled and stable
      - element is visible, enabled and stable
      - scrolling into view if needed
      - done scrolling
      - <span title="全部门店" class="ant-select-selection-item">全部门店</span> intercepts pointer events
    - retrying click action
    - waiting 20ms
    2 × waiting for element to be visible, enabled and stable
      - element is visible, enabled and stable
      - scrolling into view if needed
      - done scrolling
      - <span title="全部门店" class="ant-select-selection-item">全部门店</span> intercepts pointer events
    - retrying click action
      - waiting 100ms
    55 × waiting for element to be visible, enabled and stable
       - element is visible, enabled and stable
       - scrolling into view if needed
       - done scrolling
       - <span title="全部门店" class="ant-select-selection-item">全部门店</span> intercepts pointer events
     - retrying click action
       - waiting 500ms

```

# Page snapshot

```yaml
- generic [ref=e3]:
  - banner [ref=e4]:
    - link "m moneki 运营工作台" [ref=e5] [cursor=pointer]:
      - /url: /
      - generic [ref=e6]: m
      - text: moneki
      - generic [ref=e7]: 运营工作台
    - generic [ref=e8]: 总部运营 / 经营看板
  - main [ref=e9]:
    - generic [ref=e10]:
      - generic [ref=e11]:
        - generic [ref=e12]: 经营看板
        - heading "看清每一天的经营" [level=1] [ref=e13]
        - paragraph [ref=e14]: 按日期和门店查看真实经营数据，核对清洗结果与指标口径。
      - button "刷新数据" [ref=e15] [cursor=pointer]
    - generic [ref=e17]:
      - generic [ref=e18]:
        - heading "经营汇总" [level=2] [ref=e19]
        - generic [ref=e20]: 日期闭区间
      - generic [ref=e22]:
        - generic [ref=e23]:
          - generic [ref=e24]:
            - text: 开始日期
            - textbox "开始日期" [ref=e25]:
              - /placeholder: YYYY-MM-DD
              - text: 2026-06-08
          - generic [ref=e26]:
            - text: 结束日期
            - textbox "结束日期" [active] [ref=e27]:
              - /placeholder: YYYY-MM-DD
              - text: 2026-06-14
          - generic [ref=e28]:
            - text: 门店
            - generic "门店" [ref=e29] [cursor=pointer]:
              - generic [ref=e31]:
                - combobox "门店" [ref=e33]
                - generic "全部门店" [ref=e34]
          - button "查询汇总" [ref=e35] [cursor=pointer]
        - paragraph [ref=e37]: 起止日期均包含当天；编辑后点击查询，使条件生效。
      - paragraph [ref=e38]: 已生效：2026-05-01 至 2026-08-31 · 全部门店
      - region "经营汇总" [ref=e39]:
        - generic [ref=e40]:
          - generic [ref=e42]:
            - generic [ref=e43]: 净营业额
            - generic [ref=e44]: ¥646,929.00
            - paragraph [ref=e45]: 销售实收减去退款
          - generic [ref=e47]:
            - generic [ref=e48]: 退款金额
            - generic [ref=e49]: ¥3,237.00
            - paragraph [ref=e50]: 按退款发生日期归属
          - generic [ref=e52]:
            - generic [ref=e53]: 有效订单数
            - generic [ref=e54]: 17,926
            - paragraph [ref=e55]: 销售行按订单号去重
          - generic [ref=e57]:
            - generic [ref=e58]: 客单价
            - generic [ref=e59]: ¥36.09
            - paragraph [ref=e60]: 净营业额 ÷ 有效订单数
          - generic [ref=e62]:
            - generic [ref=e63]: 销量
            - generic [ref=e64]: 27,262
            - paragraph [ref=e65]: 销售数量减去退款数量
      - region "每日净营业额趋势" [ref=e66]:
        - generic [ref=e67]:
          - heading "每日净营业额趋势" [level=2] [ref=e68]
          - generic [ref=e69]: 单位：元 · 日期按退款发生日归属
        - generic [ref=e71]:
          - generic [ref=e72]:
            - button "加入提问" [ref=e73] [cursor=pointer]
            - generic [ref=e75]: 引用整个趋势范围，提问时重新查询数据
          - generic [ref=e76]:
            - generic [ref=e77]: 2026-08-31
            - strong [ref=e78]: ¥4,055.00
            - generic [ref=e79]: 有效订单 126 单
          - paragraph [ref=e80]: 选择图上的日期读取精确金额；横向滚动可查看完整区间。
          - region "每日净营业额图表，可横向滚动" [ref=e81]:
            - img "每日净营业额，2026-05-01 至 2026-08-31" [ref=e82]:
              - generic [ref=e83]: ¥0
              - generic [ref=e84]: ¥8,308.00
              - generic [ref=e86]:
                - generic [ref=e87]: 05-01
                - button "2026-05-01 净营业额 ¥5,075.00" [ref=e89] [cursor=pointer]
              - button "2026-05-02 净营业额 ¥7,231.00" [ref=e92] [cursor=pointer]
              - button "2026-05-03 净营业额 ¥7,501.00" [ref=e95] [cursor=pointer]
              - button "2026-05-04 净营业额 ¥4,472.00" [ref=e98] [cursor=pointer]
              - button "2026-05-05 净营业额 ¥4,631.00" [ref=e101] [cursor=pointer]
              - generic [ref=e102]:
                - generic [ref=e103]: 05-06
                - button "2026-05-06 净营业额 ¥4,644.00" [ref=e105] [cursor=pointer]
              - button "2026-05-07 净营业额 ¥4,251.00" [ref=e108] [cursor=pointer]
              - button "2026-05-08 净营业额 ¥4,806.00" [ref=e111] [cursor=pointer]
              - button "2026-05-09 净营业额 ¥6,848.00" [ref=e114] [cursor=pointer]
              - button "2026-05-10 净营业额 ¥7,109.00" [ref=e117] [cursor=pointer]
              - generic [ref=e118]:
                - generic [ref=e119]: 05-11
                - button "2026-05-11 净营业额 ¥4,888.00" [ref=e121] [cursor=pointer]
              - button "2026-05-12 净营业额 ¥4,843.00" [ref=e124] [cursor=pointer]
              - button "2026-05-13 净营业额 ¥4,610.00" [ref=e127] [cursor=pointer]
              - button "2026-05-14 净营业额 ¥4,334.00" [ref=e130] [cursor=pointer]
              - button "2026-05-15 净营业额 ¥4,796.00" [ref=e133] [cursor=pointer]
              - generic [ref=e134]:
                - generic [ref=e135]: 05-16
                - button "2026-05-16 净营业额 ¥7,642.00" [ref=e137] [cursor=pointer]
              - button "2026-05-17 净营业额 ¥7,075.00" [ref=e140] [cursor=pointer]
              - button "2026-05-18 净营业额 ¥4,480.00" [ref=e143] [cursor=pointer]
              - button "2026-05-19 净营业额 ¥4,557.00" [ref=e146] [cursor=pointer]
              - button "2026-05-20 净营业额 ¥4,382.00" [ref=e149] [cursor=pointer]
              - generic [ref=e150]:
                - generic [ref=e151]: 05-21
                - button "2026-05-21 净营业额 ¥4,373.00" [ref=e153] [cursor=pointer]
              - button "2026-05-22 净营业额 ¥4,412.00" [ref=e156] [cursor=pointer]
              - button "2026-05-23 净营业额 ¥7,039.00" [ref=e159] [cursor=pointer]
              - button "2026-05-24 净营业额 ¥6,601.00" [ref=e162] [cursor=pointer]
              - button "2026-05-25 净营业额 ¥4,024.00" [ref=e165] [cursor=pointer]
              - generic [ref=e166]:
                - generic [ref=e167]: 05-26
                - button "2026-05-26 净营业额 ¥4,637.00" [ref=e169] [cursor=pointer]
              - button "2026-05-27 净营业额 ¥4,637.00" [ref=e172] [cursor=pointer]
              - button "2026-05-28 净营业额 ¥4,381.00" [ref=e175] [cursor=pointer]
              - button "2026-05-29 净营业额 ¥5,196.00" [ref=e178] [cursor=pointer]
              - button "2026-05-30 净营业额 ¥7,088.00" [ref=e181] [cursor=pointer]
              - generic [ref=e182]:
                - generic [ref=e183]: 05-31
                - button "2026-05-31 净营业额 ¥6,850.00" [ref=e185] [cursor=pointer]
              - button "2026-06-01 净营业额 ¥4,343.00" [ref=e188] [cursor=pointer]
              - button "2026-06-02 净营业额 ¥4,519.00" [ref=e191] [cursor=pointer]
              - button "2026-06-03 净营业额 ¥4,471.00" [ref=e194] [cursor=pointer]
              - button "2026-06-04 净营业额 ¥4,936.00" [ref=e197] [cursor=pointer]
              - generic [ref=e198]:
                - generic [ref=e199]: 06-05
                - button "2026-06-05 净营业额 ¥4,926.00" [ref=e201] [cursor=pointer]
              - button "2026-06-06 净营业额 ¥7,191.00" [ref=e204] [cursor=pointer]
              - button "2026-06-07 净营业额 ¥6,770.00" [ref=e207] [cursor=pointer]
              - button "2026-06-08 净营业额 ¥3,867.00" [ref=e210] [cursor=pointer]
              - button "2026-06-09 净营业额 ¥3,652.00" [ref=e213] [cursor=pointer]
              - generic [ref=e214]:
                - generic [ref=e215]: 06-10
                - button "2026-06-10 净营业额 ¥3,246.00" [ref=e217] [cursor=pointer]
              - button "2026-06-11 净营业额 ¥3,897.00" [ref=e220] [cursor=pointer]
              - button "2026-06-12 净营业额 ¥5,073.00" [ref=e223] [cursor=pointer]
              - button "2026-06-13 净营业额 ¥7,421.00" [ref=e226] [cursor=pointer]
              - button "2026-06-14 净营业额 ¥6,329.00" [ref=e229] [cursor=pointer]
              - generic [ref=e230]:
                - generic [ref=e231]: 06-15
                - button "2026-06-15 净营业额 ¥4,225.00" [ref=e233] [cursor=pointer]
              - button "2026-06-16 净营业额 ¥5,196.00" [ref=e236] [cursor=pointer]
              - button "2026-06-17 净营业额 ¥4,420.00" [ref=e239] [cursor=pointer]
              - button "2026-06-18 净营业额 ¥8,308.00" [ref=e242] [cursor=pointer]
              - button "2026-06-19 净营业额 ¥4,822.00" [ref=e245] [cursor=pointer]
              - generic [ref=e246]:
                - generic [ref=e247]: 06-20
                - button "2026-06-20 净营业额 ¥6,224.00" [ref=e249] [cursor=pointer]
              - button "2026-06-21 净营业额 ¥7,082.00" [ref=e252] [cursor=pointer]
              - button "2026-06-22 净营业额 ¥4,509.00" [ref=e255] [cursor=pointer]
              - button "2026-06-23 净营业额 ¥4,434.00" [ref=e258] [cursor=pointer]
              - button "2026-06-24 净营业额 ¥4,412.00" [ref=e261] [cursor=pointer]
              - generic [ref=e262]:
                - generic [ref=e263]: 06-25
                - button "2026-06-25 净营业额 ¥3,732.00" [ref=e265] [cursor=pointer]
              - button "2026-06-26 净营业额 ¥4,349.00" [ref=e268] [cursor=pointer]
              - button "2026-06-27 净营业额 ¥7,698.00" [ref=e271] [cursor=pointer]
              - button "2026-06-28 净营业额 ¥7,159.00" [ref=e274] [cursor=pointer]
              - button "2026-06-29 净营业额 ¥5,043.00" [ref=e277] [cursor=pointer]
              - generic [ref=e278]:
                - generic [ref=e279]: 06-30
                - button "2026-06-30 净营业额 ¥4,503.00" [ref=e281] [cursor=pointer]
              - button "2026-07-01 净营业额 ¥4,292.00" [ref=e284] [cursor=pointer]
              - button "2026-07-02 净营业额 ¥4,924.00" [ref=e287] [cursor=pointer]
              - button "2026-07-03 净营业额 ¥5,072.00" [ref=e290] [cursor=pointer]
              - button "2026-07-04 净营业额 ¥7,345.00" [ref=e293] [cursor=pointer]
              - generic [ref=e294]:
                - generic [ref=e295]: 07-05
                - button "2026-07-05 净营业额 ¥7,504.00" [ref=e297] [cursor=pointer]
              - button "2026-07-06 净营业额 ¥5,140.00" [ref=e300] [cursor=pointer]
              - button "2026-07-07 净营业额 ¥4,428.00" [ref=e303] [cursor=pointer]
              - button "2026-07-08 净营业额 ¥4,531.00" [ref=e306] [cursor=pointer]
              - button "2026-07-09 净营业额 ¥4,843.00" [ref=e309] [cursor=pointer]
              - generic [ref=e310]:
                - generic [ref=e311]: 07-10
                - button "2026-07-10 净营业额 ¥4,389.00" [ref=e313] [cursor=pointer]
              - button "2026-07-11 净营业额 ¥6,409.00" [ref=e316] [cursor=pointer]
              - button "2026-07-12 净营业额 ¥6,822.00" [ref=e319] [cursor=pointer]
              - button "2026-07-13 净营业额 ¥5,396.00" [ref=e322] [cursor=pointer]
              - button "2026-07-14 净营业额 ¥5,371.00" [ref=e325] [cursor=pointer]
              - generic [ref=e326]:
                - generic [ref=e327]: 07-15
                - button "2026-07-15 净营业额 ¥4,160.00" [ref=e329] [cursor=pointer]
              - button "2026-07-16 净营业额 ¥4,824.00" [ref=e332] [cursor=pointer]
              - button "2026-07-17 净营业额 ¥4,955.00" [ref=e335] [cursor=pointer]
              - button "2026-07-18 净营业额 ¥7,170.00" [ref=e338] [cursor=pointer]
              - button "2026-07-19 净营业额 ¥6,785.00" [ref=e341] [cursor=pointer]
              - generic [ref=e342]:
                - generic [ref=e343]: 07-20
                - button "2026-07-20 净营业额 ¥4,319.00" [ref=e345] [cursor=pointer]
              - button "2026-07-21 净营业额 ¥4,574.00" [ref=e348] [cursor=pointer]
              - button "2026-07-22 净营业额 ¥4,480.00" [ref=e351] [cursor=pointer]
              - button "2026-07-23 净营业额 ¥4,796.00" [ref=e354] [cursor=pointer]
              - button "2026-07-24 净营业额 ¥2,053.00" [ref=e357] [cursor=pointer]
              - generic [ref=e358]:
                - generic [ref=e359]: 07-25
                - button "2026-07-25 净营业额 ¥6,821.00" [ref=e361] [cursor=pointer]
              - button "2026-07-26 净营业额 ¥6,693.00" [ref=e364] [cursor=pointer]
              - button "2026-07-27 净营业额 ¥4,799.00" [ref=e367] [cursor=pointer]
              - button "2026-07-28 净营业额 ¥5,211.00" [ref=e370] [cursor=pointer]
              - button "2026-07-29 净营业额 ¥4,802.00" [ref=e373] [cursor=pointer]
              - generic [ref=e374]:
                - generic [ref=e375]: 07-30
                - button "2026-07-30 净营业额 ¥4,803.00" [ref=e377] [cursor=pointer]
              - button "2026-07-31 净营业额 ¥4,703.00" [ref=e380] [cursor=pointer]
              - button "2026-08-01 净营业额 ¥6,760.00" [ref=e383] [cursor=pointer]
              - button "2026-08-02 净营业额 ¥7,301.00" [ref=e386] [cursor=pointer]
              - button "2026-08-03 净营业额 ¥4,904.00" [ref=e389] [cursor=pointer]
              - generic [ref=e390]:
                - generic [ref=e391]: 08-04
                - button "2026-08-04 净营业额 ¥4,642.00" [ref=e393] [cursor=pointer]
              - button "2026-08-05 净营业额 ¥4,903.00" [ref=e396] [cursor=pointer]
              - button "2026-08-06 净营业额 ¥3,871.00" [ref=e399] [cursor=pointer]
              - button "2026-08-07 净营业额 ¥4,851.00" [ref=e402] [cursor=pointer]
              - button "2026-08-08 净营业额 ¥6,850.00" [ref=e405] [cursor=pointer]
              - generic [ref=e406]:
                - generic [ref=e407]: 08-09
                - button "2026-08-09 净营业额 ¥6,940.00" [ref=e409] [cursor=pointer]
              - button "2026-08-10 净营业额 ¥4,561.00" [ref=e412] [cursor=pointer]
              - button "2026-08-11 净营业额 ¥4,878.00" [ref=e415] [cursor=pointer]
              - button "2026-08-12 净营业额 ¥4,402.00" [ref=e418] [cursor=pointer]
              - button "2026-08-13 净营业额 ¥4,506.00" [ref=e421] [cursor=pointer]
              - generic [ref=e422]:
                - generic [ref=e423]: 08-14
                - button "2026-08-14 净营业额 ¥4,571.00" [ref=e425] [cursor=pointer]
              - button "2026-08-15 净营业额 ¥6,986.00" [ref=e428] [cursor=pointer]
              - button "2026-08-16 净营业额 ¥6,925.00" [ref=e431] [cursor=pointer]
              - button "2026-08-17 净营业额 ¥3,376.00" [ref=e434] [cursor=pointer]
              - button "2026-08-18 净营业额 ¥3,413.00" [ref=e437] [cursor=pointer]
              - generic [ref=e438]:
                - generic [ref=e439]: 08-19
                - button "2026-08-19 净营业额 ¥3,067.00" [ref=e441] [cursor=pointer]
              - button "2026-08-20 净营业额 ¥4,202.00" [ref=e444] [cursor=pointer]
              - button "2026-08-21 净营业额 ¥4,264.00" [ref=e447] [cursor=pointer]
              - button "2026-08-22 净营业额 ¥7,363.00" [ref=e450] [cursor=pointer]
              - button "2026-08-23 净营业额 ¥6,411.00" [ref=e453] [cursor=pointer]
              - generic [ref=e454]:
                - generic [ref=e455]: 08-24
                - button "2026-08-24 净营业额 ¥4,532.00" [ref=e457] [cursor=pointer]
              - button "2026-08-25 净营业额 ¥5,099.00" [ref=e460] [cursor=pointer]
              - button "2026-08-26 净营业额 ¥4,333.00" [ref=e463] [cursor=pointer]
              - button "2026-08-27 净营业额 ¥4,281.00" [ref=e466] [cursor=pointer]
              - button "2026-08-28 净营业额 ¥4,639.00" [ref=e469] [cursor=pointer]
              - generic [ref=e470]:
                - generic [ref=e471]: 08-29
                - button "2026-08-29 净营业额 ¥7,029.00" [ref=e473] [cursor=pointer]
              - button "2026-08-30 净营业额 ¥6,430.00" [ref=e476] [cursor=pointer]
              - generic [ref=e477]:
                - generic [ref=e478]: 08-31
                - button "2026-08-31 净营业额 ¥4,055.00" [ref=e480] [cursor=pointer]
          - group [ref=e481]:
            - generic "查看每日明细（123 天）" [ref=e482] [cursor=pointer]
      - region "商品排行" [ref=e483]:
        - generic [ref=e484]:
          - heading "Top 10 商品" [level=2] [ref=e485]
          - paragraph [ref=e486]: 按净营业额降序；同额按商品编号升序。销量为销售数量减退款数量。窄屏可左右滑动表格。
        - table [ref=e495]:
          - rowgroup [ref=e501]:
            - row [ref=e502]:
              - columnheader "排名" [ref=e503]
              - columnheader "商品名称 / 编号" [ref=e504]
              - columnheader "净营业额" [ref=e505]
              - columnheader "销量" [ref=e506]
          - rowgroup [ref=e507]:
            - row [ref=e508]:
              - cell "1" [ref=e509]
              - cell "牛肉poke P06" [ref=e510]:
                - generic [ref=e511]:
                  - text: 牛肉poke
                  - generic [ref=e512]: P06
              - cell "¥82,570.00" [ref=e513]
              - cell "1,939" [ref=e514]
            - row [ref=e515]:
              - cell "2" [ref=e516]
              - cell "三文鱼poke P04" [ref=e517]:
                - generic [ref=e518]:
                  - text: 三文鱼poke
                  - generic [ref=e519]: P04
              - cell "¥59,546.00" [ref=e520]
              - cell "1,567" [ref=e521]
            - row [ref=e522]:
              - cell "3" [ref=e523]
              - cell "豚骨拉面 P01" [ref=e524]:
                - generic [ref=e525]:
                  - text: 豚骨拉面
                  - generic [ref=e526]: P01
              - cell "¥56,512.00" [ref=e527]
              - cell "1,766" [ref=e528]
            - row [ref=e529]:
              - cell "4" [ref=e530]
              - cell "鸡肉poke P05" [ref=e531]:
                - generic [ref=e532]:
                  - text: 鸡肉poke
                  - generic [ref=e533]: P05
              - cell "¥51,544.00" [ref=e534]
              - cell "1,516" [ref=e535]
            - row [ref=e536]:
              - cell "5" [ref=e537]
              - cell "味增拉面 P02" [ref=e538]:
                - generic [ref=e539]:
                  - text: 味增拉面
                  - generic [ref=e540]: P02
              - cell "¥49,680.00" [ref=e541]
              - cell "1,656" [ref=e542]
            - row [ref=e543]:
              - cell "6" [ref=e544]
              - cell "照烧鸡饭 P03" [ref=e545]:
                - generic [ref=e546]:
                  - text: 照烧鸡饭
                  - generic [ref=e547]: P03
              - cell "¥47,866.00" [ref=e548]
              - cell "1,841" [ref=e549]
            - row [ref=e550]:
              - cell "7" [ref=e551]
              - cell "照烧三明治 P10" [ref=e552]:
                - generic [ref=e553]:
                  - text: 照烧三明治
                  - generic [ref=e554]: P10
              - cell "¥45,384.00" [ref=e555]
              - cell "1,891" [ref=e556]
            - row [ref=e557]:
              - cell "8" [ref=e558]
              - cell "灌汤包 P08" [ref=e559]:
                - generic [ref=e560]:
                  - text: 灌汤包
                  - generic [ref=e561]: P08
              - cell "¥34,525.00" [ref=e562]
              - cell "1,381" [ref=e563]
            - row [ref=e564]:
              - cell "9" [ref=e565]
              - cell "吞拿鱼三明治 P11" [ref=e566]:
                - generic [ref=e567]:
                  - text: 吞拿鱼三明治
                  - generic [ref=e568]: P11
              - cell "¥33,904.00" [ref=e569]
              - cell "1,304" [ref=e570]
            - row [ref=e571]:
              - cell "10" [ref=e572]
              - cell "小笼包 P07" [ref=e573]:
                - generic [ref=e574]:
                  - text: 小笼包
                  - generic [ref=e575]: P07
              - cell "¥33,836.00" [ref=e576]
              - cell "1,538" [ref=e577]
    - region "数据质量台账" [ref=e578]:
      - generic [ref=e579]:
        - heading "数据质量" [level=2] [ref=e580]
        - generic [ref=e581]: KB-001 · 现行口径
      - paragraph [ref=e582]: 全量重建结果 · 不随看板筛选变化
      - generic [ref=e583]:
        - generic [ref=e584]:
          - generic [ref=e586]:
            - text: 原始明细
            - generic [ref=e587]: 18,628行
            - paragraph [ref=e588]: 来自 POS 原始数据
          - generic [ref=e590]:
            - text: 有效明细
            - generic [ref=e591]: 18,290行
            - paragraph [ref=e592]: 保留合法销售与退款
          - generic [ref=e594]:
            - text: 剔除明细
            - generic [ref=e595]: 338行
            - paragraph [ref=e596]: 按首个命中原因计数
        - generic [ref=e597]:
          - generic [ref=e598]: 有效数据日期
          - strong [ref=e599]: 2026-05-01 — 2026-08-31
          - generic [ref=e600]: 台账已对齐
        - generic [ref=e601]:
          - generic [ref=e603]:
            - generic [ref=e604]: 剔除原因台账
            - generic [ref=e605]: 按执行顺序
          - generic [ref=e606]:
            - paragraph [ref=e607]: 每行只计入最先命中的原因，避免重复计算剔除数量。
            - table [ref=e614]:
              - rowgroup [ref=e620]:
                - row [ref=e621]:
                  - columnheader "顺序" [ref=e622]
                  - columnheader "剔除原因" [ref=e623]
                  - columnheader "执行口径" [ref=e624]
                  - columnheader "剔除行数" [ref=e625]
              - rowgroup [ref=e626]:
                - row [ref=e627]:
                  - cell "01" [ref=e628]
                  - cell "日期无法解析" [ref=e629]
                  - cell "接受标准日期、斜杠日期与日在前的旧 POS 日期" [ref=e630]
                  - cell [ref=e631]:
                    - strong [ref=e632]: "8"
                - row [ref=e633]:
                  - cell "02" [ref=e634]
                  - cell "实收金额为空" [ref=e635]
                  - cell "直接剔除，不以商品单价回填" [ref=e636]
                  - cell [ref=e637]:
                    - strong [ref=e638]: "150"
                - row [ref=e639]:
                  - cell "03" [ref=e640]
                  - cell "数量小于或等于 0" [ref=e641]
                  - cell "按整数解析后检查数量" [ref=e642]
                  - cell [ref=e643]:
                    - strong [ref=e644]: "30"
                - row [ref=e645]:
                  - cell "04" [ref=e646]
                  - cell "门店编号无效" [ref=e647]
                  - cell "先去除首尾空白并转为大写，再核对门店表" [ref=e648]
                  - cell [ref=e649]:
                    - strong [ref=e650]: "10"
                - row [ref=e651]:
                  - cell "05" [ref=e652]
                  - cell "商品编号无效" [ref=e653]
                  - cell "先规范化编号，再核对商品表" [ref=e654]
                  - cell [ref=e655]:
                    - strong [ref=e656]: "40"
                - row [ref=e657]:
                  - cell "06" [ref=e658]
                  - cell "完全重复的明细" [ref=e659]
                  - cell "七个字段规范化后完全相同，只保留一行" [ref=e660]
                  - cell [ref=e661]:
                    - strong [ref=e662]: "100"
            - generic [ref=e663]:
              - generic [ref=e664]: 台账核对
              - strong [ref=e665]: 18,628 = 18,290 + 338
              - generic [ref=e666]: 原始 = 保留 + 剔除
        - paragraph [ref=e667]: 原始数据保持不变。重建完成后重启服务，再刷新此页查看最新结果。
  - contentinfo [ref=e668]: MONEKI / 数据口径以《指标口径手册 v3》为准
  - button "经营助手" [ref=e669] [cursor=pointer]
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
  23 |   await expect(page.getByRole('dialog')).toBeHidden();
  24 |   await page.getByRole('textbox',{name:'开始日期'}).fill('2026-06-08');await page.getByRole('textbox',{name:'结束日期'}).fill('2026-06-14');
  25 |   const stores=(await(await request.get('/api/stores')).json()).stores;const store=stores.find((s:any)=>s.store_id==='S03');
  26 |   await page.getByRole('combobox',{name:'门店'}).scrollIntoViewIfNeeded();
> 27 |   await page.getByRole('combobox',{name:'门店'}).click();await page.getByTitle(store.store_name+' · S03',{exact:true}).click();
     |                                                ^ Error: locator.click: Test timeout of 30000ms exceeded.
  28 |   await page.getByRole('button',{name:'查询汇总'}).click();await expect(page.getByTestId('applied-filters')).toContainText('S03');
  29 |   await page.getByRole('button',{name:'加入提问',exact:true}).click();
  30 |   const q='那这段时间呢？';await configure(request,q,{mode:'anomaly',tool:'query_metrics',params:{start:'2026-06-08',end:'2026-06-14',store_id:'S03'},metric:'net_revenue',doc:'KB-020',needle:'停业 4 天',role:'reason',query:why});
  31 |   const b=await ask(page,request,q);expect(b.answer.answer_type).toBe('hybrid');expect(b.payload.session_id).toBe(a.payload.session_id);expect(b.payload.context.store_id).toBe('S03');
  32 |   expect(b.answer.data_evidence[0].result.net_revenue).toBe(3630);expect(b.answer.data_evidence[0].params.product_id).toBeUndefined();
  33 |   expect(b.trace.steps.find((s:any)=>s.step==='plan').detail.product_id).toBeNull();
  34 |   const last=page.locator('.chat-answer').last();await last.getByText(/展开数据证据/).click();await last.getByText(/展开文档引用/).click();
  35 |   await expect(last).toContainText(b.answer.citations[0].quote);await expect(last).toContainText(JSON.stringify(b.answer.data_evidence[0].params,null,2));
  36 |   await page.screenshot({path:path.join(out,`trend-${width}.png`)});
  37 |   const next='7月S01鸡肉poke净营业额是多少？';await configure(request,next,{mode:'data',tool:'query_metrics',params:{start:'2026-07-01',end:'2026-07-31',store_id:'S01',product_id:'P05'},metric:'net_revenue'});
  38 |   const c=await ask(page,request,next);expect(c.answer.answer_type).toBe('data');expect(c.payload.context).toBeUndefined();expect(c.answer.data_evidence[0].params.product_id).toBe('P05');
  39 |   fs.writeFileSync(path.join(out,`trend-${width}.json`),JSON.stringify({a,b,c},null,2));
  40 |  });
  41 |  test(`混合价格追问重新取证 ${width}`,async({page,request})=>{
  42 |   await page.setViewportSize({width,height:900});await page.goto('/');await page.getByRole('button',{name:'经营助手',exact:true}).click();
  43 |   const a=await ask(page,request,price);expect(a.answer.answer_type).toBe('hybrid');
  44 |   const q='那7月1日呢？';await configure(request,q,{mode:'price',tool:'unit_price_check',params:{product_id:'P06',start:'2026-07-01',end:'2026-07-01'},metric:'unit_price',doc:'KB-025',needle:'调整为',role:'price',query:'牛肉poke售价调整'});
  45 |   const b=await ask(page,request,q);expect(b.answer.answer_type).toBe('hybrid');expect(b.answer.citations[0].scope.as_of).toBe('2026-07-01');expect(b.answer.citations[0].evidence_id).not.toBe(a.answer.citations[0].evidence_id);
  46 |   const last=page.locator('.chat-answer').last();await last.getByText(/展开数据证据/).click();await expect(last.getByRole('heading',{name:'计算关系与操作数来源'})).toBeVisible();await last.getByText(/展开文档引用/).click();
  47 |   await expect(last).toContainText(b.answer.citations[0].quote);fs.writeFileSync(path.join(out,`price-${width}.json`),JSON.stringify({a,b},null,2));await page.screenshot({path:path.join(out,`price-${width}.png`)});
  48 |  });
  49 | }
  50 | 
```
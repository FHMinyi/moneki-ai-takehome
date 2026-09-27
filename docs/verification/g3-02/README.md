# G3-02 验证记录

起点：`587ae820185cd10839e189efa9fb2ed8863d1ca5`。这是本票修改前定向检查，不是第三关整体前置 baseline。

修改前命令：`starter/.venv/bin/python -m pytest docs/verification/g3-02/test_document_binding.py -q`。结果：8 failed / 1 passed，原始输出 `before.txt`；其中4项复现旧版本/近主题错误陈述可被交付，4项新证据协议尚未实现；48小时无依据数字原本即被拒绝。

测试使用受控模型输出和真实检索，不证明真实模型理解能力。原输入、评分器、历史证据及既有未提交材料共2434文件sha256见 `protected-before.json`。

记录时间：2026-09-27T05:47:50.699329+00:00

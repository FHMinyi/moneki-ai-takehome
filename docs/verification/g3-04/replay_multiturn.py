"""Save complete no-key request/response/trace sequences without fake retrieval."""
from __future__ import annotations

import json
import os
import sys
import tempfile
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "starter"))
from kbqa.config import load_settings
from kbqa.service import Service

CASES = {
    "T01": ["6 月的净营业额是多少？", "那 7 月呢？", "这两个月的客单价差了多少？"],
    "T02": ["三文鱼poke 七月初为什么停售了？", "那停售期间让顾客换成什么？", "供应商后来赔了多少？"],
    "T03": ["牛肉poke 现在多少钱一份？", "那 6 月 18 号那天呢？"],
    "V03": ["储值充值现在的赠送规则是什么？", "那 6 月的时候呢？"],
}


def main():
    out = Path(os.environ.get("G304_EVIDENCE_DIR", ROOT / "docs/verification/g3-04/no-key"))
    out.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="g304-replay-") as work:
        settings = replace(load_settings(), var_dir=Path(work), llm_base_url="",
                           llm_api_key="", llm_model="")
        service = Service(settings)
        for case_id, questions in CASES.items():
            turns = []
            for question in questions:
                request = {"session_id": case_id, "question": question}
                response = service.chat(**request)
                trace = service.get_trace(response["trace_id"])
                turns.append({"request": request, "response": response, "trace": trace})
            (out / f"{case_id}.json").write_text(
                json.dumps(turns, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(case_id, len(turns), [turn["response"]["answer_type"] for turn in turns])


if __name__ == "__main__":
    main()

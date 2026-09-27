"""Pure offline checks of the execution-only budget gate, no network or key."""

import importlib.util
from pathlib import Path

path = Path(__file__).with_name("run_live_eval.py")
spec = importlib.util.spec_from_file_location("g305_runner", path)
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)

for valid in (1, 4096, 8192):
    assert runner.output_limit_allowed(valid), valid
for invalid in (None, True, False, 0, -1, 8193, 8192.0, "8192", {}, []):
    assert not runner.output_limit_allowed(invalid), invalid
worst_case = (1_048_576 * 2 + 8192 * 8) / 1_000_000
assert worst_case == 2.162688
assert worst_case < runner.RESERVE == 2.20
print("10 invalid, 3 valid output limits; 2.162688 < 2.20 CNY reserve; no network")

"""Read exact archived JSONL bytes; compression changes storage only."""
import gzip,json
from pathlib import Path

def read_jsonl(path):
 path=Path(path)
 raw=path.read_bytes() if path.exists() else gzip.decompress(Path(str(path)+'.gz').read_bytes())
 return [json.loads(line) for line in raw.splitlines()]

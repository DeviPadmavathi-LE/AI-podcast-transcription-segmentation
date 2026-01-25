import json
from pathlib import Path

EP = "103"

summaries = json.loads(Path(f"outputs/summaries_{EP}.json").read_text(encoding="utf-8"))
keywords  = json.loads(Path(f"outputs/keywords_{EP}.json").read_text(encoding="utf-8"))

merged = {}

for seg_id, summary_text in summaries.items():
    merged[str(seg_id)] = {
        "summary": summary_text,
        "keywords": keywords.get(str(seg_id), [])
    }

out = Path(f"outputs/final_{EP}_topics.json")
out.write_text(json.dumps(merged, indent=2), encoding="utf-8")

print(f"Saved {len(merged)} topics to {out}")
import json
from pathlib import Path

INPUTS = [
    Path("outputs/summaries_79.json"),
    Path("outputs/summaries_83.json"),
    Path("outputs/summaries_103.json"),
]

OUTPUT = Path("outputs/Week5_summaries_refined.json")

refined = {}

for file in INPUTS:
    data = json.loads(file.read_text(encoding="utf-8"))
    for k, text in data.items():
        sentences = [s.strip() for s in text.split(".") if len(s.strip()) > 20]
        refined[k] = ". ".join(sentences[:3])

OUTPUT.write_text(json.dumps(refined, indent=2), encoding="utf-8")
print("✓ summaries_refined.json created")
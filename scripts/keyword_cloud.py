import json
from pathlib import Path
from collections import Counter

INPUT = Path("outputs/keywords_103.json")
OUTPUT = Path("outputs/Week5_keyword_freq_103.json")

data = json.loads(INPUT.read_text(encoding="utf-8"))

all_keywords = []

for seg in data.values():
    all_keywords.extend(seg)

freq = Counter(all_keywords)

OUTPUT.write_text(json.dumps(freq, indent=2), encoding="utf-8")
print("Keyword frequency saved:", OUTPUT)
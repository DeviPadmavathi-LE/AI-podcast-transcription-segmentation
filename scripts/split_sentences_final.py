import json
from pathlib import Path
from config import EPISODES

TRANSCRIPTS = Path("transcripts")
OUTPUT = Path("outputs")
OUTPUT.mkdir(exist_ok=True)

def split_sentences(text):
    return [s.strip() for s in text.split(".") if len(s.strip()) > 20]

for ep in EPISODES:
    text = (TRANSCRIPTS / f"{ep}.txt").read_text(encoding="utf-8")
    sentences = split_sentences(text)

    out = OUTPUT / f"sentences_{ep}.json"
    json.dump(sentences, out.open("w", encoding="utf-8"), indent=2)

    print(f"✓ sentences saved for {ep}")
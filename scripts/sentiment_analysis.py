import json
from pathlib import Path
from textblob import TextBlob

# Paths
INPUT = Path("outputs/summaries_refined.json")
OUTPUT = Path("../outputs/Week5_sentiment_segments.json")

# Load refined summaries
data = json.loads(INPUT.read_text(encoding="utf-8"))

sentiments = {}

for seg_id, text in data.items():
    polarity = TextBlob(text).sentiment.polarity

    if polarity > 0.1:
        label = "Positive"
    elif polarity < -0.1:
        label = "Negative"
    else:
        label = "Neutral"

    sentiments[seg_id] = {
        "sentiment": label,
        "score": round(polarity, 3)
    }

# Save sentiment output
OUTPUT.write_text(
    json.dumps(sentiments, indent=2),
    encoding="utf-8"
)

print("Sentiment analysis completed. File saved:", OUTPUT)
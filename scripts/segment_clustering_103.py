from pathlib import Path
import json
from sentence_transformers import SentenceTransformer
from sklearn.cluster import AgglomerativeClustering

FILES = ["79", "83", "103"]

model = SentenceTransformer("all-MiniLM-L6-v2")

for file_id in FILES:
    input_file = Path(f"outputs/sentences_{file_id}.json")
    output_file = Path(f"outputs/segments_{file_id}.json")

    sentences = json.loads(input_file.read_text(encoding="utf-8"))

    embeddings = model.encode(sentences)

    clustering = AgglomerativeClustering(
        n_clusters=None,
        metric="cosine",          # ✅ NOT metric
        linkage="average",
        distance_threshold=0.35     # 🔥 THIS IS THE KEY
    )

    labels = clustering.fit_predict(embeddings)

    segments = {}
    for sent, label in zip(sentences, labels):
        segments.setdefault(str(label), []).append(sent)

    output_file.write_text(
        json.dumps(segments, indent=2),
        encoding="utf-8"
    )

    print(f"{file_id}: {len(segments)} segments created")
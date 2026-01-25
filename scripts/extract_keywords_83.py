import json
from pathlib import Path
from sklearn.feature_extraction.text import TfidfVectorizer
import nltk
EP="83"
# Download stopwords if not done
nltk.download('stopwords')
from nltk.corpus import stopwords

# Load clustered segments
input_file = Path("outputs/segments_83.json")
clusters = json.loads(input_file.read_text(encoding="utf-8"))

# Combine sentences into one text per cluster
cluster_texts = []
for cluster_id, sentences in clusters.items():
    combined = " ".join(sentences)
    cluster_texts.append(combined)

# Prepare TF-IDF

vectorizer = TfidfVectorizer(stop_words="english", max_features=10)
X = vectorizer.fit_transform(cluster_texts)

# Extract top keywords per cluster
feature_names = vectorizer.get_feature_names_out()
cluster_keywords = {}

for idx, cluster_id in enumerate(clusters.keys()):
    row = X[idx].toarray().flatten()
    top_indices = row.argsort()[-10:][::-1]
    top_words = [feature_names[i] for i in top_indices]
    cluster_keywords[cluster_id] = top_words

# Save output
output_file = Path(f"outputs/keywords_{EP}.json")
output_file.write_text(json.dumps(cluster_keywords, indent=2))

print("✔ Keyword Extraction Completed! Saved as keywords.json")
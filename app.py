import json
from pathlib import Path
import streamlit as st

# ---------------- CONFIG ----------------
st.set_page_config(
    page_title="Podcast Topic Explorer",
    layout="wide",
    initial_sidebar_state="expanded"
)

BASE = Path("outputs")
AUDIO = Path("audio")

PODCASTS = {
    "79": {
        "speaker": "Iqbal Kadir",
        "title": "How to End Poverty for Good",
        "topics": "final_79_topics.json",
        "sentences": "sentences_79.json",
        "timestamps": "timestamps_79.json",
        "audio": "79.wav",
    },
    "83": {
        "speaker": "E.O. Wilson",
        "title": "What Makes Life Worth Living",
        "topics": "final_83_topics.json",
        "sentences": "sentences_83.json",
        "timestamps": "timestamps_83.json",
        "audio": "83.wav",
    },
    "103": {
        "speaker": "Evelyn Glennie",
        "title": "How We Truly Listen to Music",
        "topics": "final_103_topics.json",
        "sentences": "sentences_103.json",
        "timestamps": "timestamps_103.json",
        "audio": "103.wav",
    },
}

# ---------------- HELPERS ----------------
def load_json(path):
    return json.loads((BASE / path).read_text(encoding="utf-8"))

def short_title(text):
    return text.replace('"', '').split(".")[0].strip()

def full_transcript(sentence_list):
    return " ".join(sentence_list)

# ---------------- DARK THEME ----------------
st.markdown("""
<style>
html, body, [class*="css"] {
    background-color: #0f172a;
    color: #e5e7eb;
}
hr { border: 1px solid #1f2937; }
.keyword {
    display: inline-block;
    padding: 6px 12px;
    margin: 4px;
    background: #1f2937;
    border-radius: 999px;
    font-size: 13px;
}
</style>
""", unsafe_allow_html=True)

# ---------------- HERO ----------------
st.markdown("""
<h1 style="text-align:center;">🎙 Podcast Topic Explorer</h1>
<p style="text-align:center; color:#9ca3af;">
Understand long talks through clean topic segmentation
</p>
<hr>
""", unsafe_allow_html=True)

# ---------------- SIDEBAR ----------------
st.sidebar.header("🎧 Navigation")

talk_id = st.sidebar.selectbox(
    "Choose a Talk",
    options=list(PODCASTS.keys()),
    format_func=lambda k: f"{PODCASTS[k]['speaker']} — {PODCASTS[k]['title']}"
)

search_query = st.sidebar.text_input("Search keywords")

pod = PODCASTS[talk_id]
topics = load_json(pod["topics"])
sentences = load_json(pod["sentences"])
timestamps = load_json(pod["timestamps"])

# ---------------- SEGMENTS ----------------
segment_options = []
segment_map = {}

for i, (sid, data) in enumerate(topics.items(), start=1):
    label = f"Segment {i} — {short_title(data['summary'])}"
    segment_options.append(label)
    segment_map[label] = sid

selected_label = st.sidebar.selectbox(
    "Choose a Segment",
    options=segment_options
)

segment_id = segment_map[selected_label]
segment = topics[segment_id]

# ---------------- SEARCH FILTER ----------------
text_blob = (
    segment["summary"] +
    " " +
    " ".join(segment.get("keywords", [])) +
    " " +
    " ".join(sentences[int(segment_id)])
)

if search_query and search_query.lower() not in text_blob.lower():
    st.warning("No matching content for this search.")
    st.stop()

# ---------------- MAIN CONTENT ----------------
st.markdown(f"## {short_title(segment['summary'])}")

# Keywords
if segment.get("keywords"):
    st.markdown("**Keywords**")
    st.markdown(
        "".join(f"<span class='keyword'>{kw}</span>" for kw in segment["keywords"]),
        unsafe_allow_html=True
    )

# Summary
st.markdown("### Summary")
st.write(segment["summary"])

# Transcript (FIXED)
st.markdown("### Transcript")
st.text_area(
    "",
    full_transcript(sentences[int(segment_id)]),
    height=320
)

# Audio Jump
audio_path = AUDIO / pod["audio"]
if audio_path.exists():
    start_time = timestamps.get(str(segment_id), {}).get("start", 0)
    st.markdown("### 🎧 Listen from this segment")
    st.audio(str(audio_path), start_time=start_time)
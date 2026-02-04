# Automated Podcast Transcription & Topic Segmentation

Infosys Springboard — AI Internship Project

---

## 1. Introduction

Podcasts and long-form audio content contain valuable information, but they are time-consuming to consume and difficult to search. Users often need to listen to entire episodes to find a specific topic, idea, or discussion point.

This project addresses that problem by building an end-to-end AI system that automatically:

- Transcribes podcast audio into text
- Splits long transcripts into meaningful topic-based segments
- Extracts keywords for each segment
- Generates concise summaries
- Provides an interactive interface to explore segments, transcripts, and audio

The objective is to reduce listening effort, improve information accessibility, and enable topic-wise navigation of podcast content.

---

## 2. Dataset Description

Dataset Used: TED Talks Audio Dataset

Key Characteristics:

- Approximately 2000 TED Talk audio files
- Language: English
- Audio format: MP3 (converted to WAV for processing)
- Content type: Talks, interviews, narrative explanations

Evaluation Samples Used:

- Episode IDs: 79, 83, 103
- These episodes were selected to evaluate the system on diverse speakers and topics

---

## 3. System Architecture and Processing Pipeline

The system follows a modular pipeline architecture:

### 3.1 Audio Preprocessing

- MP3 to WAV conversion
- Audio normalization for consistent transcription quality

### 3.2 Speech-to-Text Transcription

- Converts audio streams into continuous textual transcripts

### 3.3 Sentence Splitting

- Long transcripts are split into sentence-level units
- Enables fine-grained semantic analysis

### 3.4 Topic Segmentation

- Sentences are grouped into coherent topic segments

### 3.5 Keyword Extraction

- Important keywords are identified for each segment

### 3.6 Summarization

- Each segment is summarized into concise, readable text

---

## 4. Topic Segmentation Methods

### 4.1 Similarity-Based Segmentation (Baseline)

Model Used: all-MiniLM-L6-v2

Process:

- Sentence embeddings are generated
- Cosine similarity is computed between consecutive sentences
- Topic boundary is created when similarity falls below a threshold

Strengths:

- Simple and computationally efficient
- Detects fine-grained topic transitions

Limitations:

- Sensitive to threshold selection
- Can generate fragmented segments

---

### 4.2 Clustering-Based Segmentation (KMeans)

Model Used: all-MiniLM-L6-v2

Process:

- Sentence embeddings are generated
- KMeans clustering is applied
- Sentences within the same cluster represent a topic

Configuration:

- Number of clusters (k) = 6

Strengths:

- Produces semantically coherent segments
- Suitable for high-level topic understanding

Limitations:

- Requires manual selection of cluster count

---

## 5. Evaluation and Comparison

| Feature             | Similarity-Based | Clustering-Based  |
| ------------------- | ---------------- | ----------------- |
| Segmentation Detail | High             | Medium            |
| Topic Coherence     | Medium           | High              |
| Parameter Control   | Threshold        | Cluster count     |
| Best Use Case       | Fine transitions | Thematic grouping |

Observation:

- Clustering-based segmentation produced more meaningful topic groupings
- Similarity-based segmentation captured subtle topic shifts

---

## 6. Keyword Extraction

Method Used: TF-IDF Vectorization

Purpose:

- Identify important terms per topic segment
- Assist in topic labeling and search

Output:

- Keywords stored in structured JSON format
- Displayed directly in the user interface

---

## 7. Summarization

Model Used: T5-small

Process:

- Sentences within each segment are combined
- Long segments are chunked to respect token limits
- Each chunk is summarized
- Summaries are merged and cleaned

Outputs:

- Raw summaries
- Clean, readable summaries for presentation

---

## 8. Final Generated Outputs

All generated outputs are stored in the outputs directory:

- sentences\_\*.json – Sentence-level transcript splits
- final\_\*\_topics.json – Topic segments with summaries and keywords
- timestamps\_\*.json – Segment-level audio timestamps
- audio/\*.wav – Processed audio files

---

## 9. Conclusion

This project demonstrates an end-to-end AI pipeline for transforming long-form audio into structured, searchable information. By combining speech recognition, semantic segmentation, keyword extraction, summarization, and an interactive interface, the system significantly improves podcast accessibility.

Clustering-based segmentation produced more coherent topics, while similarity-based segmentation captured finer transitions. The final application bridges advanced AI processing with real-world usability.

---

# Milestone 3 – Week 5: Visualization & Detail Enhancements

This milestone focuses on improving presentation and interpretability of previously generated podcast analysis outputs.

## Implemented Components

### 1. Sentiment Analysis
- Applied TextBlob polarity scoring on segment summaries
- Classified each segment as Positive, Neutral, or Negative

### 2. Keyword Visualization Preparation
- Aggregated extracted keywords across segments
- Computed keyword frequencies for visualization

### 3. Summary Refinement
- Cleaned and trimmed summaries to 2–3 concise sentences
- Removed repetition and filler text

## Notes
- No new NLP models were trained
- All enhancements reuse outputs from previous milestones
- Focus was on clarity, readability, and usability

This completes the Week-5 visualization and enhancement objectives.
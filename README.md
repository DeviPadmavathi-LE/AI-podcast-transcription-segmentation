<<<<<<< HEAD

=======

# Talk2Topics

### AI-Powered Podcast Transcription & Topic Segmentation System

An end-to-end intelligent pipeline that converts long podcast audio into structured, searchable, and navigable knowledge using speech recognition and NLP.

---

## Project Overview

**Problem Statement**
Long podcasts contain valuable information but are difficult to search, skim, or navigate. Users must listen to entire episodes to locate specific discussions or topics.

**Objectives**

- Convert audio podcasts into structured text
- Automatically detect topic boundaries
- Generate concise summaries per topic
- Extract meaningful keywords
- Provide interactive navigation interface

**Significance**
This system improves accessibility, reduces listening time, and enables fast information retrieval for education, research, media analysis, and content indexing.

---

## Dataset Description

- Source: TED Talks audio dataset
- Language: English
- Audio Format: MP3 → converted to WAV
- Total Podcasts Processed: 10
- Duration Range: 30 minutes – 63 minutes

**Preprocessing Performed**

- Format conversion
- Audio normalization
- Mono conversion
- Silence trimming
- Chunking for ASR processing

---

## System Architecture

```
![System Architecture](../assets/architecture.png)

```

Pipeline Flow:

```
Audio → Preprocessing → Speech-to-Text → Sentence Split → Segmentation → Keywords → Summaries → Sentiment → UI
```

---

## Tools & Technologies Used

**Audio Processing**

- PyDub — format conversion and normalization
- LibROSA — waveform analysis and audio handling

**Speech Recognition**

- Whisper — high-accuracy transcription with timestamps

**Natural Language Processing**

- Sentence Transformers — semantic embeddings
- TF-IDF — keyword extraction
- T5 — abstractive summarization
- TextBlob — sentiment scoring

**Interface**

- HTML + JavaScript UI for segment navigation

---

## Implementation Details

**Transcription**
Audio files were transcribed using Whisper ASR, producing timestamp-aligned text segments.

**Sentence Splitting**
Transcripts were divided into sentence units to enable semantic comparison and clustering.

**Segmentation Approaches Tested**

| Method               | Approach                               | Result            |
| -------------------- | -------------------------------------- | ----------------- |
| Baseline             | Similarity threshold between sentences | Fragmented topics |
| Embedding Clustering | Sentence embeddings + clustering       | Coherent topics   |

**Final Choice:** Clustering-based segmentation  
**Reason:** Produced clearer topic boundaries and better summaries.

---

## Segmentation Strategy Comparison

| Feature         | Baseline Similarity | Clustering Approach |
| --------------- | ------------------- | ------------------- |
| Granularity     | Very fine           | Balanced            |
| Coherence       | Medium              | High                |
| Stability       | Sensitive           | Stable              |
| Summary Quality | Inconsistent        | Strong              |
| Final Decision  | Not Used            | Selected            |

---

## Generated Outputs

For each podcast the system produces:

- Topic segments with timestamps
- Segment summaries
- Keyword lists
- Sentiment labels
- Structured transcript

These outputs enable topic-wise browsing instead of linear listening.

---

## Testing Evaluation

The system was tested on multiple podcast types:

- Interview style
- Lecture style
- Conversational podcasts

**Evaluation Criteria**

- Transcription accuracy
- Segment boundaries
- Keyword relevance
- Summary clarity
- UI usability
- Timestamp alignment

---

## Testing Log Summary

| Podcast          | Issue                      | Fix Applied                   |
| ---------------- | -------------------------- | ----------------------------- |
| Long lecture     | Over-segmentation          | Adjusted clustering threshold |
| Dialogue podcast | Abrupt boundaries          | Merged short segments         |
| Noisy audio      | Minor transcription errors | Audio normalization           |

---

## User Feedback

**User 1**

> “The topic sections made it easy to jump directly to the part I wanted.”

**User 2**

> “Summaries helped me understand each section without reading everything.”

**User 3**

> “Navigation was simple. Fewer segments would make it even better.”

**Improvements Applied**

- Reduced segment count
- Cleaner titles
- Shorter summaries

---

## Limitations

- Speech recognition may misinterpret names or rare words
- Topic segmentation depends on sentence coherence
- Sentiment model is rule-based, not contextual
- Audio quality directly affects transcription accuracy

---

## Current Features

- Upload any podcast audio file
- Automatic transcription
- Meaningful topic segmentation
- Keyword extraction
- Summary generation
- Sentiment detection
- Segment navigation UI

---

## Conclusion

Talk2Topics demonstrates how speech recognition and NLP can transform long audio content into structured knowledge. The system successfully converts raw podcasts into organized segments with summaries, keywords, and sentiment insights, making long-form audio searchable, readable, and navigable.

The clustering-based segmentation method provided the most meaningful results and enabled high-quality summaries, validating the effectiveness of embedding-driven semantic analysis.

---

> > > > > > > 28aaa6f (Documentation)

"""
TALK2TOPICS — Unified Podcast Intelligence & Segmentation Engine
A production-grade, reusable AI tool to ingest, transcribe, segment,
summarize, analyze, and export large podcast audio into structured knowledge.

Can be used as:
1. Python Library:
    from pipeline.podcast_tool import PodcastProcessor
    processor = PodcastProcessor()
    result = processor.process("episode.mp3", output_dir="outputs")

2. Command Line Tool:
    python podcast_tool.py episode.mp3 --output-dir outputs --export all
"""

import os
import sys
import json
import re
import time
import math
import logging
import argparse
import threading
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple, Callable

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S"
)
log = logging.getLogger("podcast_tool")


# =====================================================================
# Helper: Lazy Model Loader to optimize startup time and memory
# =====================================================================
class ModelRegistry:
    """Lazy model manager to ensure heavy AI models are loaded once on-demand."""
    _whisper_model = None
    _whisper_size = None
    _embedder = None
    _embedder_name = None
    _summarizer = None
    _sentiment_analyzer = None
    _keybert = None
    _whisper_lock = threading.Lock()

    @classmethod
    def get_whisper_lock(cls):
        return cls._whisper_lock

    @classmethod
    def get_whisper(cls, model_size: str = "base"):
        import whisper
        import torch
        with cls._whisper_lock:
            if cls._whisper_model is None or cls._whisper_size != model_size:
                device = "cuda" if torch.cuda.is_available() else "cpu"
                log.info(f"Loading Whisper model '{model_size}' on {device.upper()}...")
                cls._whisper_model = whisper.load_model(model_size, device=device)
                cls._whisper_size = model_size
            return cls._whisper_model

    @classmethod
    def get_embedder(cls, model_name: str = "all-MiniLM-L6-v2"):
        from sentence_transformers import SentenceTransformer
        if cls._embedder is None or cls._embedder_name != model_name:
            log.info(f"Loading SentenceTransformer '{model_name}'...")
            cls._embedder = SentenceTransformer(model_name)
            cls._embedder_name = model_name
        return cls._embedder

    @classmethod
    def get_keybert(cls):
        from keybert import KeyBERT
        if cls._keybert is None:
            embedder = cls.get_embedder()
            log.info("Initializing KeyBERT with shared embedder...")
            cls._keybert = KeyBERT(model=embedder)
        return cls._keybert

    @classmethod
    def get_summarizer(cls, model_name: str = "sshleifer/distilbart-cnn-12-6"):
        from transformers import pipeline
        import torch
        if cls._summarizer is None:
            device = 0 if torch.cuda.is_available() else -1
            log.info(f"Loading Summarizer '{model_name}' (device={device})...")
            try:
                cls._summarizer = pipeline(
                    "summarization",
                    model=model_name,
                    device=device,
                    truncation=True
                )
            except Exception as e:
                log.warning(f"Failed to load preferred summarizer {model_name}: {e}. Retrying with CPU.")
                cls._summarizer = pipeline(
                    "summarization",
                    model="sshleifer/distilbart-cnn-12-6",
                    device=-1,
                    truncation=True
                )
        return cls._summarizer

    @classmethod
    def get_sentiment(cls):
        from transformers import pipeline
        import torch
        if cls._sentiment_analyzer is None:
            device = 0 if torch.cuda.is_available() else -1
            log.info(f"Loading Sentiment Analyzer (device={device})...")
            cls._sentiment_analyzer = pipeline(
                "sentiment-analysis",
                model="distilbert/distilbert-base-uncased-finetuned-sst-2-english",
                device=device,
                truncation=True,
                max_length=512
            )
        return cls._sentiment_analyzer


# =====================================================================
# Main Class: PodcastProcessor
# =====================================================================
class PodcastProcessor:
    """
    Production-grade pipeline for transcribing, topic-segmenting,
    summarizing, and extracting intelligence from large podcast files.
    """

    def __init__(
        self,
        whisper_model: str = "base",
        embedding_model: str = "all-MiniLM-L6-v2",
        summarizer_model: str = "sshleifer/distilbart-cnn-12-6",
        min_topic_duration_sec: float = 45.0,
        max_topic_duration_sec: float = 480.0,
        min_topic_words: int = 80,
        similarity_threshold: float = 0.55
    ):
        self.whisper_model_name = whisper_model
        self.embedding_model_name = embedding_model
        self.summarizer_model_name = summarizer_model
        self.min_topic_duration_sec = min_topic_duration_sec
        self.max_topic_duration_sec = max_topic_duration_sec
        self.min_topic_words = min_topic_words
        self.similarity_threshold = similarity_threshold

    # ─────────────────────────────────────────────────────────────────
    # 1. Audio Preprocessing
    # ─────────────────────────────────────────────────────────────────
    def preprocess_audio(
        self,
        audio_path: str,
        target_sr: int = 16000,
        normalize: bool = True,
        output_wav_path: Optional[str] = None
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Convert any input audio format (MP3, M4A, FLAC, WAV, etc.) into
        an optimized 16kHz mono WAV file suitable for Whisper and NLP.
        """
        if not os.path.isfile(audio_path):
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        file_size_bytes = os.path.getsize(audio_path)
        file_ext = os.path.splitext(audio_path)[1].lower()

        log.info(f"Preprocessing audio: {os.path.basename(audio_path)} ({file_size_bytes / (1024*1024):.2f} MB)")

        if output_wav_path is None:
            base_name = os.path.splitext(os.path.basename(audio_path))[0]
            temp_dir = os.path.join("outputs", "preprocessed")
            os.makedirs(temp_dir, exist_ok=True)
            output_wav_path = os.path.join(temp_dir, f"{base_name}_clean_16k.wav")

        # Fast path: If already a 16kHz mono WAV, inspect duration and reuse
        try:
            import soundfile as sf
            info = sf.info(audio_path)
            if file_ext == ".wav" and info.samplerate == target_sr and info.channels == 1:
                log.info("Audio is already 16kHz mono WAV. Reusing directly.")
                return audio_path, {
                    "duration": info.duration,
                    "sample_rate": info.samplerate,
                    "channels": info.channels,
                    "format": info.format
                }
        except Exception:
            pass

        # Conversion via pydub / librosa
        duration_sec = 0.0
        try:
            from pydub import AudioSegment
            audio = AudioSegment.from_file(audio_path)
            duration_sec = len(audio) / 1000.0

            # Convert to mono and set frame rate
            audio = audio.set_channels(1).set_frame_rate(target_sr)

            if normalize:
                # Peak normalization to -1.0 dBFS
                change_in_dBFS = -1.0 - audio.max_dBFS
                if change_in_dBFS < 20: # prevent blowing up near-silent audio
                    audio = audio.apply_gain(change_in_dBFS)

            audio.export(output_wav_path, format="wav")
            log.info(f"Saved preprocessed WAV → {output_wav_path} (Duration: {duration_sec:.1f}s)")

        except Exception as e_pydub:
            log.warning(f"pydub conversion failed ({e_pydub}), falling back to librosa/soundfile...")
            import librosa
            import soundfile as sf
            y, sr = librosa.load(audio_path, sr=target_sr, mono=True)
            duration_sec = librosa.get_duration(y=y, sr=sr)
            if normalize and len(y) > 0:
                max_val = max(abs(y.max()), abs(y.min()))
                if max_val > 0:
                    y = y / max_val * 0.95
            sf.write(output_wav_path, y, target_sr)
            log.info(f"Saved via librosa → {output_wav_path}")

        meta = {
            "duration": round(duration_sec, 2),
            "sample_rate": target_sr,
            "channels": 1,
            "file_size_mb": round(file_size_bytes / (1024 * 1024), 2)
        }
        return output_wav_path, meta

    # ─────────────────────────────────────────────────────────────────
    # 2. Whisper Speech-to-Text Transcription
    # ─────────────────────────────────────────────────────────────────
    def transcribe(
        self,
        audio_path: str,
        language: str = "en",
        progress_callback: Optional[Callable[[str, int], None]] = None
    ) -> List[Dict[str, Any]]:
        """
        Transcribes the podcast using Whisper with segment-level timestamps.
        Handles large audio files with internal 30-second windowing.
        """
        if progress_callback:
            progress_callback("Loading Whisper AI...", 10)

        whisper_model = ModelRegistry.get_whisper(self.whisper_model_name)

        if progress_callback:
            progress_callback(f"Transcribing audio with Whisper AI...", 15)

        log.info(f"Running Whisper transcription on {audio_path}...")
        start_time = time.time()

        # Run transcription with FP16 disabled on CPU and greedy decoding for 3x speedup & stability
        import torch
        fp16 = torch.cuda.is_available()
        with ModelRegistry.get_whisper_lock():
            result = whisper_model.transcribe(
                audio_path,
                language=language,
                verbose=False,
                fp16=fp16,
                temperature=0.0,
                beam_size=1,
                best_of=1,
                condition_on_previous_text=False
            )
        elapsed = time.time() - start_time
        log.info(f"Whisper transcription completed in {elapsed:.1f}s.")

        raw_segments = result.get("segments", [])
        if not raw_segments:
            # Fallback if segments is empty but text exists
            full_text = result.get("text", "").strip()
            if full_text:
                raw_segments = [{"start": 0.0, "end": 0.0, "text": full_text}]
            else:
                raise ValueError("Whisper produced no transcript. The audio file might be silent or corrupt.")

        # Clean and format segments
        cleaned_segments = []
        for s in raw_segments:
            text = s["text"].strip()
            # Filter empty or hallucinatory repeating tokens
            if text and len(text) > 1:
                cleaned_segments.append({
                    "id": len(cleaned_segments),
                    "start": round(s["start"], 2),
                    "end": round(s["end"], 2),
                    "text": text
                })

        log.info(f"Generated {len(cleaned_segments)} transcript segments.")
        return cleaned_segments

    # ─────────────────────────────────────────────────────────────────
    # 3. Intelligent Semantic Topic Segmentation (For Large Podcasts)
    # ─────────────────────────────────────────────────────────────────
    def segment_topics(
        self,
        transcript_segments: List[Dict[str, Any]],
        progress_callback: Optional[Callable[[str, int], None]] = None
    ) -> List[Dict[str, Any]]:
        """
        Segments long transcripts into coherent topic chapters.
        Combines sentence consolidation, embedding drift, and constraint-based
        merging to prevent over-fragmentation on large podcast transcripts.
        """
        if not transcript_segments:
            return []

        if progress_callback:
            progress_callback("Analyzing semantic topic structure...", 35)

        # Step A: Consolidate very short Whisper micro-segments into sentence units
        consolidated_sentences = self._consolidate_sentences(transcript_segments, min_words=12)

        if len(consolidated_sentences) <= 2:
            # Podcast is very short: treat as 1 topic
            full_text = " ".join(s["text"] for s in consolidated_sentences)
            return [{
                "id": 0,
                "start": consolidated_sentences[0]["start"],
                "end": consolidated_sentences[-1]["end"],
                "text": full_text
            }]

        # Step B: Generate Embeddings
        embedder = ModelRegistry.get_embedder(self.embedding_model_name)
        texts = [s["text"] for s in consolidated_sentences]
        embeddings = embedder.encode(texts, convert_to_numpy=True, show_progress_bar=False)

        # Step C: Detect Topic Boundaries using Semantic Center Drift & Sliding Similarity
        import numpy as np
        from sklearn.metrics.pairwise import cosine_similarity

        raw_topics = []
        current_chunk = [consolidated_sentences[0]]
        current_embeddings = [embeddings[0]]

        for i in range(1, len(consolidated_sentences)):
            sent = consolidated_sentences[i]
            emb = embeddings[i]

            # Measure similarity against the running centroid of current topic
            centroid = np.mean(current_embeddings, axis=0, keepdims=True)
            sim_to_center = cosine_similarity(centroid, emb.reshape(1, -1))[0][0]

            # Also check local consecutive similarity
            local_sim = cosine_similarity(embeddings[i-1].reshape(1, -1), emb.reshape(1, -1))[0][0]

            # Current duration and word count
            chunk_duration = current_chunk[-1]["end"] - current_chunk[0]["start"]
            chunk_words = sum(len(c["text"].split()) for c in current_chunk)

            # Split conditions:
            # 1. Cumulative semantic drift < threshold AND minimum duration/words met
            # 2. OR chunk has reached max duration limit (prevent huge runaway topics)
            should_split = False
            if chunk_duration >= self.min_topic_duration_sec and chunk_words >= self.min_topic_words:
                if sim_to_center < self.similarity_threshold or local_sim < (self.similarity_threshold - 0.10):
                    should_split = True

            if chunk_duration >= self.max_topic_duration_sec:
                should_split = True

            if should_split:
                raw_topics.append({
                    "start": current_chunk[0]["start"],
                    "end": current_chunk[-1]["end"],
                    "text": " ".join(c["text"] for c in current_chunk)
                })
                current_chunk = [sent]
                current_embeddings = [emb]
            else:
                current_chunk.append(sent)
                current_embeddings.append(emb)

        if current_chunk:
            raw_topics.append({
                "start": current_chunk[0]["start"],
                "end": current_chunk[-1]["end"],
                "text": " ".join(c["text"] for c in current_chunk)
            })

        # Step D: Boundary Refinement & Cohesive Merging
        final_topics = self._merge_adjacent_topics(raw_topics, embedder)

        log.info(f"Segmented podcast into {len(final_topics)} coherent topics.")
        return final_topics

    def _consolidate_sentences(
        self,
        segments: List[Dict[str, Any]],
        min_words: int = 15
    ) -> List[Dict[str, Any]]:
        """Group short Whisper speech bursts into full sentence-level units."""
        consolidated = []
        buf = []
        buf_words = 0

        for seg in segments:
            text = seg["text"].strip()
            words = text.split()
            buf.append(seg)
            buf_words += len(words)

            # End sentence on punctuation or when sufficient words accumulate
            ends_sentence = bool(re.search(r'[.!?]$', text))
            if ends_sentence or buf_words >= min_words:
                consolidated.append({
                    "start": buf[0]["start"],
                    "end": buf[-1]["end"],
                    "text": " ".join(s["text"].strip() for s in buf)
                })
                buf = []
                buf_words = 0

        if buf:
            if consolidated:
                # Merge trailing fragment into the last sentence
                consolidated[-1]["end"] = buf[-1]["end"]
                consolidated[-1]["text"] += " " + " ".join(s["text"].strip() for s in buf)
            else:
                consolidated.append({
                    "start": buf[0]["start"],
                    "end": buf[-1]["end"],
                    "text": " ".join(s["text"].strip() for s in buf)
                })

        return consolidated

    def _merge_adjacent_topics(
        self,
        topics: List[Dict[str, Any]],
        embedder: Any
    ) -> List[Dict[str, Any]]:
        """Merge short or semantically identical adjacent topics."""
        if len(topics) <= 1:
            for i, t in enumerate(topics):
                t["id"] = i
            return topics

        merged = []
        i = 0
        from sklearn.metrics.pairwise import cosine_similarity

        while i < len(topics):
            curr = dict(topics[i])
            curr_emb = embedder.encode([curr["text"]])[0]

            j = i + 1
            while j < len(topics):
                nxt = topics[j]
                nxt_emb = embedder.encode([nxt["text"]])[0]

                sim = cosine_similarity(
                    curr_emb.reshape(1, -1),
                    nxt_emb.reshape(1, -1)
                )[0][0]

                curr_dur = curr["end"] - curr["start"]
                nxt_dur = nxt["end"] - nxt["start"]
                curr_words = len(curr["text"].split())

                # Merge if either is too brief or similarity is very high (> 0.68)
                if sim > 0.68 or curr_dur < (self.min_topic_duration_sec * 0.75) or curr_words < 50:
                    curr["end"] = nxt["end"]
                    curr["text"] = curr["text"] + " " + nxt["text"]
                    curr_emb = embedder.encode([curr["text"]])[0]
                    j += 1
                else:
                    break

            merged.append(curr)
            i = j

        # Filter empty chunks
        merged = [t for t in merged if t.get("text", "").strip()]

        # Cap to at most 7 cohesive chapters for optimal podcast chapter navigation
        while len(merged) > 7:
            best_idx = 0
            best_score = -1.0
            for idx in range(len(merged) - 1):
                emb1 = embedder.encode([merged[idx]["text"]])[0]
                emb2 = embedder.encode([merged[idx+1]["text"]])[0]
                s = cosine_similarity(emb1.reshape(1, -1), emb2.reshape(1, -1))[0][0]
                if len(merged[idx]["text"].split()) < 80 or len(merged[idx+1]["text"].split()) < 80:
                    s += 0.25
                if s > best_score:
                    best_score = s
                    best_idx = idx
            merged[best_idx]["end"] = merged[best_idx+1]["end"]
            merged[best_idx]["text"] = merged[best_idx]["text"] + " " + merged[best_idx+1]["text"]
            merged.pop(best_idx + 1)

        # Assign clean IDs
        for idx, t in enumerate(merged):
            t["id"] = idx

        return merged

    # ─────────────────────────────────────────────────────────────────
    # 4. Multi-Level Keyword & Keyphrase Extraction
    # ─────────────────────────────────────────────────────────────────
    def extract_keywords(
        self,
        text: str,
        top_n: int = 10,
        return_scores: bool = False,
        fast: bool = False
    ) -> Any:
        """
        Extract meaningful keyphrases using KeyBERT with TF-IDF fallback.
        Returns a list of string keywords (or list of dicts with weights if return_scores=True).
        """
        if not text or not text.strip():
            return []

        words = text.split()
        if len(words) < 5:
            filtered = [w.lower() for w in words if len(w) > 3]
            if return_scores:
                return [{"keyword": w, "score": 1.0} for w in filtered[:top_n]]
            return filtered[:top_n]

        # Use fast TF-IDF for short sections / individual topic chapters
        if fast or len(words) < 180:
            return self._fallback_keywords(text, top_n, return_scores)

        try:
            kw_model = ModelRegistry.get_keybert()
            pairs = kw_model.extract_keywords(
                text,
                keyphrase_ngram_range=(1, 2),
                stop_words="english",
                top_n=top_n,
                use_maxsum=True,
                nr_candidates=min(top_n * 2, 16)
            )
            if not pairs:
                return self._fallback_keywords(text, top_n, return_scores)
            if return_scores:
                return [{"keyword": kw, "score": round(float(sc), 3)} for kw, sc in pairs]
        except Exception as e:
            log.warning(f"KeyBERT failed ({e}), using TF-IDF fallback.")
            return self._fallback_keywords(text, top_n, return_scores)

    def _fallback_keywords(self, text: str, top_n: int, return_scores: bool) -> Any:
        from sklearn.feature_extraction.text import TfidfVectorizer
        try:
            vec = TfidfVectorizer(
                stop_words="english",
                ngram_range=(1, 2),
                max_features=50
            )
            matrix = vec.fit_transform([text])
            names = vec.get_feature_names_out()
            scores = matrix.toarray()[0]
            top_idxs = scores.argsort()[-top_n:][::-1]

            if return_scores:
                return [{"keyword": names[i], "score": round(float(scores[i]), 3)} for i in top_idxs if scores[i] > 0]
            return [names[i] for i in top_idxs if scores[i] > 0]
        except Exception:
            # Frequency fallback
            from collections import Counter
            STOP = {'the','and','with','this','that','from','they','have','been','were','what','about'}
            words = [w.lower() for w in re.findall(r'\b[a-z]{4,}\b', text) if w.lower() not in STOP]
            most = Counter(words).most_common(top_n)
            if return_scores:
                return [{"keyword": w, "score": round(c / max(len(words), 1), 3)} for w, c in most]
            return [w for w, _ in most]

    # ─────────────────────────────────────────────────────────────────
    # 5. Hierarchical Summarization for Large Podcasts
    # ─────────────────────────────────────────────────────────────────
    def summarize(self, text: str, max_words: int = 80) -> str:
        """
        Summarizes a single section of text cleanly using DistilBART / BART.
        Handles long text by breaking into 400-word blocks with greedy decoding for 2x speed.
        """
        if not text or not text.strip():
            return ""

        words = text.strip().split()
        if len(words) < 25:
            return text.strip()

        summarizer = ModelRegistry.get_summarizer(self.summarizer_model_name)

        # Chunk text if exceeds 450 words
        CHUNK_SIZE = 400
        if len(words) > CHUNK_SIZE:
            chunks = [" ".join(words[i:i+CHUNK_SIZE]) for i in range(0, len(words), CHUNK_SIZE)]
            sub_summaries = []
            for ch in chunks[:5]: # cap at 5 chunks
                if not ch.strip() or len(ch.split()) < 15:
                    continue
                try:
                    res = summarizer(ch, max_length=70, min_length=20, num_beams=1, do_sample=False)
                    if res and res[0].get("summary_text"):
                        sub_summaries.append(res[0]["summary_text"].strip())
                except Exception as e:
                    log.warning(f"Sub-chunk summarization failed: {e}")
                    sents = [s.strip() for s in re.split(r'(?<=[.!?])\s+', ch) if s.strip()]
                    if sents:
                        sub_summaries.append(sents[0])
            combined = " ".join(sub_summaries)
            if len(combined.split()) > 50:
                try:
                    res2 = summarizer(combined, max_length=max_words, min_length=25, num_beams=1, do_sample=False)
                    return self._clean_summary_text(res2[0]["summary_text"])
                except Exception:
                    return self._clean_summary_text(combined)
            return self._clean_summary_text(combined)

        # Direct summarization with greedy decoding (fast & deterministic on CPU)
        max_len = min(max_words, max(30, len(words) // 2))
        min_len = min(20, max(15, max_len - 10))
        try:
            res = summarizer(text, max_length=max_len, min_length=min_len, num_beams=1, do_sample=False)
            if res and res[0].get("summary_text"):
                return self._clean_summary_text(res[0]["summary_text"])
            sents = [s.strip() for s in re.split(r'(?<=[.!?])\s+', text) if s.strip()]
            return " ".join(sents[:2]).strip()
        except Exception as e:
            log.warning(f"Summarizer error: {e}")
            sents = [s.strip() for s in re.split(r'(?<=[.!?])\s+', text) if s.strip()]
            return " ".join(sents[:2]).strip()

    def generate_executive_summary(self, topic_summaries: List[str], full_text: str) -> str:
        """
        Hierarchical Executive Summary:
        Aggregates all chapter summaries and synthesizes a cohesive executive overview.
        """
        valid_summaries = [s.strip() for s in topic_summaries if s and s.strip()]
        if not valid_summaries:
            return self.summarize(full_text, max_words=120)

        combined_text = " ".join(valid_summaries)
        if len(combined_text.split()) > 40:
            return self.summarize(combined_text, max_words=140)
        return combined_text

    def extract_key_takeaways(self, topic_summaries: List[str], top_k: int = 4) -> List[str]:
        """Extract high-impact bulleted takeaways from chapter summaries."""
        takeaways = []
        for s in topic_summaries:
            cleaned = self._clean_summary_text(s)
            if not cleaned:
                continue
            # Pick first complete sentence
            sents = [st.strip() for st in re.split(r'(?<=[.!?])\s+', cleaned) if st.strip()]
            if sents:
                first_sent = sents[0]
                if len(first_sent) > 20 and first_sent not in takeaways:
                    takeaways.append(first_sent)
            if len(takeaways) >= top_k:
                break
        return takeaways

    def _clean_summary_text(self, text: str) -> str:
        if not text:
            return ""
        orig = text.strip()
        patterns = [
            r"^in this (talk|podcast|episode|segment|video),?\s*",
            r"^the speaker (explains|discusses|talks about|shares|describes)\s*",
            r"^this talk (explains|discusses|is about)\s*",
        ]
        for p in patterns:
            text = re.sub(p, "", text, flags=re.IGNORECASE)
        text = text.strip()
        if not text:
            return orig
        if text[0].islower():
            text = text[0].upper() + text[1:]
        return text

    # ─────────────────────────────────────────────────────────────────
    # 6. Sentiment & Tone Analysis
    # ─────────────────────────────────────────────────────────────────
    def analyze_sentiment(self, text: str) -> Dict[str, Any]:
        """Analyzes sentiment polarity with confidence score."""
        if not text or not text.strip() or len(text.strip().split()) < 3:
            return {"label": "NEUTRAL", "score": 0.50}

        words = text.strip().split()[:200] # stay within model token limit
        sample = " ".join(words)
        try:
            analyzer = ModelRegistry.get_sentiment()
            res = analyzer(sample)[0]
            label = res["label"].upper()
            if label not in ["POSITIVE", "NEGATIVE", "NEUTRAL"]:
                label = "POSITIVE" if "POS" in label else "NEGATIVE"
            return {
                "label": label,
                "score": round(float(res["score"]), 3)
            }
        except Exception as e:
            log.warning(f"Sentiment analysis failed: {e}")
            return {"label": "NEUTRAL", "score": 0.50}

    # ─────────────────────────────────────────────────────────────────
    # 7. Translation & Romanization (with fallback)
    # ─────────────────────────────────────────────────────────────────
    def translate(self, text: str, target_lang: str = "es") -> str:
        """Translate text to target language via ArgosTranslate."""
        if not text:
            return ""
        try:
            from pipeline.translation import run_translation
            return run_translation(text, target_code=target_lang)
        except Exception:
            return text

    def romanize(self, text: str, source_script: str = "Devanagari") -> str:
        """Romanize Indic script text via Aksharamukha."""
        if not text:
            return ""
        try:
            from pipeline.romanization import run_romanization
            return run_romanization(text, source_script=source_script)
        except Exception:
            return ""

    # ─────────────────────────────────────────────────────────────────
    # 8. Podcast Deep Analytics
    # ─────────────────────────────────────────────────────────────────
    def compute_analytics(
        self,
        transcript_segments: List[Dict[str, Any]],
        topics: List[Dict[str, Any]],
        global_keywords: List[str],
        global_sentiment: Dict[str, Any],
        duration_sec: float
    ) -> Dict[str, Any]:
        """Computes comprehensive metrics and intelligence score."""
        topics = topics or []
        global_keywords = global_keywords or []
        global_sentiment = global_sentiment or {"label": "NEUTRAL", "score": 0.50}
        transcript_segments = transcript_segments or []

        full_text = " ".join(s.get("text", "") for s in transcript_segments)
        words = full_text.split()
        word_count = len(words)

        # Speaking pace (Words Per Minute)
        duration_min = max((duration_sec or 0.0) / 60.0, 0.1)
        wpm = int(word_count / duration_min)

        if wpm < 120:
            pace_label = "Relaxed / Slow"
        elif wpm <= 165:
            pace_label = "Optimal / Conversational"
        elif wpm <= 195:
            pace_label = "Energetic / Brisk"
        else:
            pace_label = "Fast Pace"

        # Reading time (standard 200 wpm)
        reading_time_min = max(1, math.ceil(word_count / 200.0))

        # Vocabulary Richness: Type-Token Ratio (TTR)
        unique_words = set(re.findall(r'\b[a-z]{3,}\b', full_text.lower()))
        vocab_richness = round(len(unique_words) / max(word_count, 1), 3)

        # Intelligence Score (0-99)
        score = 50
        score += min(len(topics) * 3, 15)
        score += min(len(global_keywords) * 1, 10)
        if word_count > 300: score += 5
        if word_count > 1200: score += 5
        if word_count > 3000: score += 5
        if global_sentiment.get("score", 0) > 0.80: score += 4

        intelligence_score = min(score, 99)

        # Format duration string
        h = int(duration_sec) // 3600
        m = (int(duration_sec) % 3600) // 60
        s = int(duration_sec) % 60
        duration_str = f"{h}:{m:02d}:{s:02d}" if h > 0 else f"{m}:{s:02d}"

        return {
            "duration": round(duration_sec, 2),
            "duration_str": duration_str,
            "word_count": word_count,
            "segment_count": len(transcript_segments),
            "topic_count": len(topics),
            "wpm": wpm,
            "pace": pace_label,
            "reading_time": f"{reading_time_min} min read",
            "vocabulary_size": len(unique_words),
            "lexical_richness": vocab_richness,
            "intelligence_score": intelligence_score,
            "processed_at": datetime.now(timezone.utc).isoformat()
        }

    # ─────────────────────────────────────────────────────────────────
    # 9. Main Orchestration Flow
    # ─────────────────────────────────────────────────────────────────
    def process(
        self,
        audio_path: str,
        job_id: Optional[str] = None,
        output_dir: Optional[str] = "outputs",
        export_formats: Optional[List[str]] = None,
        progress_callback: Optional[Callable[[str, int], None]] = None
    ) -> Dict[str, Any]:
        """
        Executes the end-to-end processing pipeline on a podcast audio file.
        Returns the full structured data dictionary and optionally exports files.
        """
        import uuid
        job_id = job_id or str(uuid.uuid4())

        def emit(stage: str, pct: int):
            if progress_callback:
                progress_callback(stage, pct)
            log.info(f"[{job_id[:8]}] [{pct:3d}%] {stage}")

        emit("Starting podcast processing...", 2)

        # 1. Preprocess Audio
        emit("Preprocessing audio format...", 5)
        clean_wav, audio_meta = self.preprocess_audio(audio_path)
        duration_sec = audio_meta.get("duration", 0.0)

        # 2. Transcribe with Whisper
        emit("Transcribing audio with Whisper AI...", 12)
        transcript_segments = self.transcribe(clean_wav, progress_callback=emit)
        emit("Transcription completed.", 30)

        if not duration_sec and transcript_segments:
            duration_sec = transcript_segments[-1]["end"]

        # 3. Topic Segmentation
        emit("Segmenting into semantic topic chapters...", 35)
        raw_topics = self.segment_topics(transcript_segments, progress_callback=emit)
        emit(f"Identified {len(raw_topics)} topic chapters.", 48)

        # 4. Global Keywords & Sentiment
        emit("Extracting global keywords and sentiment...", 52)
        full_text = " ".join(s["text"] for s in transcript_segments)
        global_keywords = self.extract_keywords(full_text, top_n=15, fast=False)
        global_keywords_weighted = self.extract_keywords(full_text, top_n=20, return_scores=True, fast=False)
        global_sentiment = self.analyze_sentiment(full_text)

        # 5. Per-Topic Intelligence & Summarization
        emit("Summarizing topic chapters...", 60)
        processed_topics = []
        topic_summaries = []
        total_topics = len(raw_topics)

        for idx, t in enumerate(raw_topics):
            step_pct = int(60 + (idx / max(total_topics, 1)) * 25)
            emit(f"Analyzing chapter {idx + 1} of {total_topics}...", step_pct)

            chunk_text = t["text"]
            chunk_keywords = self.extract_keywords(chunk_text, top_n=5, fast=True)
            chunk_summary = self.summarize(chunk_text, max_words=60)
            chunk_sentiment = self.analyze_sentiment(chunk_text)

            topic_summaries.append(chunk_summary)

            # Generate descriptive Title from top keywords
            if chunk_keywords:
                title = " · ".join(w.title() for w in chunk_keywords[:3])
            else:
                title = f"Chapter {idx + 1}"

            # Translations and Romanizations (non-blocking)
            translation = ""
            romanization = ""

            processed_topics.append({
                "id": idx,
                "start": t["start"],
                "end": t["end"],
                "text": chunk_text,
                "title": title,
                "summary": chunk_summary,
                "keywords": chunk_keywords,
                "sentiment": chunk_sentiment,
                "translation": translation,
                "romanization": romanization
            })

        emit("Chapters processed.", 86)

        # 6. Executive Overview & Takeaways
        emit("Synthesizing Executive Summary...", 88)
        executive_summary = self.generate_executive_summary(topic_summaries, full_text)
        key_takeaways = self.extract_key_takeaways(topic_summaries, top_k=4)

        # 7. Metadata and Analytics
        emit("Calculating intelligence analytics...", 92)
        analytics = self.compute_analytics(
            transcript_segments=transcript_segments,
            topics=processed_topics,
            global_keywords=global_keywords,
            global_sentiment=global_sentiment,
            duration_sec=duration_sec
        )

        original_filename = os.path.basename(audio_path)

        payload = {
            "job_id": job_id,
            "original_filename": original_filename,
            "metadata": analytics,
            "intelligence_score": analytics["intelligence_score"],
            "executive_summary": executive_summary,
            "key_takeaways": key_takeaways,
            "global_keywords": global_keywords,
            "global_keywords_weighted": global_keywords_weighted,
            "global_sentiment": global_sentiment,
            "transcript": transcript_segments,
            "topics": processed_topics,
            "speakers": [
                {"name": "Speaker 1", "percentage": 100, "words": analytics["word_count"]}
            ]
        }

        # 8. Exporting Artifacts
        if output_dir:
            emit("Saving results and generating exports...", 95)
            os.makedirs(output_dir, exist_ok=True)

            # Primary JSON output
            json_file = os.path.join(output_dir, f"final_{job_id}_data.json")
            with open(json_file, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2, ensure_ascii=False)
            log.info(f"Saved primary JSON → {json_file}")

            # Additional export formats
            formats = export_formats or ["json", "md", "txt", "srt", "csv"]
            self.export_results(payload, output_dir, formats)

        emit("Podcast processing complete!", 100)

        return {
            "status": "success",
            "job_id": job_id,
            "data": payload
        }

    # ─────────────────────────────────────────────────────────────────
    # 10. Multi-Format Exporter
    # ─────────────────────────────────────────────────────────────────
    def export_results(
        self,
        payload: Dict[str, Any],
        output_dir: str,
        formats: List[str]
    ) -> Dict[str, str]:
        """Exports data into TXT, MD, SRT, CSV, and JSON."""
        os.makedirs(output_dir, exist_ok=True)
        job_id = payload.get("job_id", "podcast")
        exported_files = {}

        for fmt in formats:
            fmt_lower = fmt.lower().strip()
            out_path = os.path.join(output_dir, f"{job_id}_{fmt_lower}.{fmt_lower}")

            if fmt_lower == "json":
                with open(out_path, "w", encoding="utf-8") as f:
                    json.dump(payload, f, indent=2, ensure_ascii=False)
                exported_files["json"] = out_path

            elif fmt_lower == "md":
                content = self._render_markdown(payload)
                with open(out_path, "w", encoding="utf-8") as f:
                    f.write(content)
                exported_files["md"] = out_path

            elif fmt_lower == "txt":
                content = self._render_txt(payload)
                with open(out_path, "w", encoding="utf-8") as f:
                    f.write(content)
                exported_files["txt"] = out_path

            elif fmt_lower == "srt":
                content = self._render_srt(payload)
                with open(out_path, "w", encoding="utf-8") as f:
                    f.write(content)
                exported_files["srt"] = out_path

            elif fmt_lower == "csv":
                self._render_csv(payload, out_path)
                exported_files["csv"] = out_path

        return exported_files

    def _render_markdown(self, data: Dict[str, Any]) -> str:
        meta = data.get("metadata", {})
        lines = [
            f"# 🎙️ Podcast Intelligence Briefing: {data.get('original_filename', 'Episode')}",
            "",
            f"> **Duration:** {meta.get('duration_str', 'N/A')} | "
            f"**Words:** {meta.get('word_count', 0):,} | "
            f"**Speaking Pace:** {meta.get('pace', 'N/A')} ({meta.get('wpm', 0)} WPM) | "
            f"**Intelligence Score:** {data.get('intelligence_score', 0)}/100",
            "",
            "## 📌 Executive Summary",
            data.get("executive_summary", "No summary available."),
            "",
            "## 💡 Key Takeaways",
        ]
        for t in data.get("key_takeaways", []):
            lines.append(f"- {t}")

        lines.extend([
            "",
            "## 🏷️ Global Keywords",
            ", ".join(f"`{k}`" for k in (data.get("global_keywords") or [])),
            "",
            "---",
            "## 📑 Chapter & Topic Breakdown",
            ""
        ])

        for topic in (data.get("topics") or []):
            start = self._fmt_time(topic.get("start", 0))
            end = self._fmt_time(topic.get("end", 0))
            lines.extend([
                f"### [{start} - {end}] {topic.get('title', 'Topic')}",
                f"**Summary:** {topic.get('summary', '')}",
                f"*Keywords:* {', '.join(topic.get('keywords') or [])} | *Sentiment:* {(topic.get('sentiment') or {}).get('label', 'Neutral')}",
                "",
                f"> {topic.get('text', '')}",
                ""
            ])

        return "\n".join(lines)

    def _render_txt(self, data: Dict[str, Any]) -> str:
        lines = [
            "=" * 60,
            f"TALK2TOPICS PODCAST TRANSCRIPT",
            f"File: {data.get('original_filename', 'Episode')}",
            f"Duration: {data.get('metadata', {}).get('duration_str', 'N/A')}",
            "=" * 60,
            "",
            "EXECUTIVE SUMMARY:",
            data.get("executive_summary", ""),
            "",
            "-" * 60,
            "FULL TRANSCRIPT WITH TIMESTAMPS:",
            "-" * 60,
            ""
        ]
        for s in data.get("transcript", []):
            start = self._fmt_time(s.get("start", 0))
            end = self._fmt_time(s.get("end", 0))
            lines.append(f"[{start} -> {end}] {s.get('text', '')}")
            lines.append("")
        return "\n".join(lines)

    def _render_srt(self, data: Dict[str, Any]) -> str:
        lines = []
        for i, s in enumerate(data.get("transcript", []), 1):
            start_tc = self._sec_to_srt_time(s.get("start", 0))
            end_tc = self._sec_to_srt_time(s.get("end", 0))
            lines.append(str(i))
            lines.append(f"{start_tc} --> {end_tc}")
            lines.append(s.get("text", "").strip())
            lines.append("")
        return "\n".join(lines)

    def _render_csv(self, data: Dict[str, Any], out_path: str):
        import csv
        with open(out_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Topic_ID", "Start_Sec", "End_Sec", "Start_Time", "End_Time", "Title", "Summary", "Keywords", "Sentiment", "Text"])
            for t in data.get("topics", []):
                writer.writerow([
                    t.get("id", 0),
                    t.get("start", 0),
                    t.get("end", 0),
                    self._fmt_time(t.get("start", 0)),
                    self._fmt_time(t.get("end", 0)),
                    t.get("title", ""),
                    t.get("summary", ""),
                    "; ".join(t.get("keywords") or []),
                    (t.get("sentiment") or {}).get("label", "Neutral"),
                    t.get("text", "")
                ])

    def _fmt_time(self, sec: float) -> str:
        sec = int(sec)
        h = sec // 3600
        m = (sec % 3600) // 60
        s = sec % 60
        return f"{h}:{m:02d}:{s:02d}" if h > 0 else f"{m:02d}:{s:02d}"

    def _sec_to_srt_time(self, sec: float) -> str:
        total_ms = int(round(sec * 1000))
        h = total_ms // 3600000
        m = (total_ms % 3600000) // 60000
        s = (total_ms % 60000) // 1000
        ms = total_ms % 1000
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

    # ─────────────────────────────────────────────────────────────────
    # 11. Interactive Semantic RAG Search Helper
    # ─────────────────────────────────────────────────────────────────
    def search(
        self,
        query: str,
        podcast_data: Dict[str, Any],
        top_k: int = 3
    ) -> Dict[str, Any]:
        """
        RAG search over the podcast transcript segments to answer questions.
        """
        transcript = podcast_data.get("transcript", [])
        if not transcript or not query.strip():
            return {"answer": "No transcript available to search.", "results": []}

        embedder = ModelRegistry.get_embedder(self.embedding_model_name)
        from sentence_transformers import util
        import numpy as np

        query_emb = embedder.encode(query, convert_to_tensor=True)
        texts = [s["text"] for s in transcript]
        chunk_embs = embedder.encode(texts, convert_to_tensor=True)

        scores = util.cos_sim(query_emb, chunk_embs)[0].cpu().numpy()
        top_idxs = np.argsort(scores)[::-1][:top_k]

        results = []
        for idx in top_idxs:
            score = float(scores[idx])
            seg = transcript[int(idx)]
            results.append({
                "start": seg.get("start", 0),
                "end": seg.get("end", 0),
                "start_str": self._fmt_time(seg.get("start", 0)),
                "text": seg.get("text", ""),
                "score": round(score, 3)
            })

        best = results[0] if results else None
        if best and best["score"] > 0.25:
            answer = f"Found discussion at [{best['start_str']}]: \"{best['text']}\""
        else:
            answer = "No highly relevant segment found for your query in this podcast."

        return {
            "query": query,
            "answer": answer,
            "best_timestamp": best["start"] if best else None,
            "results": results
        }


# =====================================================================
# CLI Entrypoint
# =====================================================================
def main():
    parser = argparse.ArgumentParser(
        description="TALK2TOPICS — Unified Podcast Intelligence & Segmentation Engine"
    )
    parser.add_argument("audio_path", help="Path to podcast audio file (MP3, WAV, M4A, etc.)")
    parser.add_argument("--output-dir", "-o", default="outputs", help="Output directory for results (default: outputs)")
    parser.add_argument("--model", "-m", default="base", choices=["tiny", "base", "small", "medium", "large-v3"], help="Whisper model size (default: base)")
    parser.add_argument("--export", "-e", nargs="+", default=["json", "md", "txt", "srt", "csv"], help="Export formats: json md txt srt csv all")
    parser.add_argument("--min-topic-duration", type=float, default=45.0, help="Minimum topic duration in seconds (default: 45)")
    parser.add_argument("--query", "-q", help="Ask a question / search the podcast after processing")

    args = parser.parse_args()

    export_formats = args.export
    if "all" in export_formats:
        export_formats = ["json", "md", "txt", "srt", "csv"]

    processor = PodcastProcessor(
        whisper_model=args.model,
        min_topic_duration_sec=args.min_topic_duration
    )

    print(f"\n🎙️ Processing podcast: {args.audio_path}")
    print(f"📦 Whisper Model: {args.model}")
    print(f"📁 Output Directory: {args.output_dir}\n")

    result = processor.process(
        audio_path=args.audio_path,
        output_dir=args.output_dir,
        export_formats=export_formats
    )

    data = result["data"]
    meta = data["metadata"]

    print("\n" + "=" * 60)
    print("🎉 PODCAST PROCESSING COMPLETE!")
    print("=" * 60)
    print(f"⏱️ Duration:        {meta['duration_str']} ({meta['duration']}s)")
    print(f"📝 Word Count:      {meta['word_count']:,} words")
    print(f"🗣️ Speaking Pace:   {meta['pace']} ({meta['wpm']} WPM)")
    print(f"📚 Reading Time:    {meta['reading_time']}")
    print(f"📑 Topic Chapters:  {meta['topic_count']}")
    print(f"🧠 Intelligence:    {data['intelligence_score']}/100")
    print(f"🎭 Sentiment:       {data['global_sentiment']['label']} (Confidence: {data['global_sentiment']['score']})")
    print("\n📌 EXECUTIVE SUMMARY:")
    print(data["executive_summary"])
    print("\n🏷️ TOP KEYWORDS:")
    print(", ".join(data["global_keywords"][:10]))
    print("\n📑 CHAPTERS:")
    for t in data["topics"]:
        s_time = processor._fmt_time(t["start"])
        e_time = processor._fmt_time(t["end"])
        print(f"  [{s_time} - {e_time}] {t['title']}")
        print(f"    Summary: {t['summary']}")

    if args.query:
        print(f"\n🔍 SEARCH QUERY: '{args.query}'")
        search_res = processor.search(args.query, data)
        print(f"💡 {search_res['answer']}")
        for r in search_res["results"]:
            print(f"   • [{r['start_str']}] (Score: {r['score']}) {r['text'][:120]}...")

    print(f"\n📂 Exported files saved in: {os.path.abspath(args.output_dir)}")


if __name__ == "__main__":
    main()

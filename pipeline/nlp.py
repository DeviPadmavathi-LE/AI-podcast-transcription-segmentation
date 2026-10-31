"""
TALK2TOPICS — NLP Pipeline
Keyword extraction (KeyBERT), summarization (DistilBART), and sentiment analysis.

Fixes:
- Summarizer now handles long texts by chunking before summarizing
- extract_keywords always returns a list of strings (never score tuples)
- Proper fallbacks for very short or empty text
"""

import logging
import warnings
warnings.filterwarnings('ignore')

from keybert import KeyBERT
from transformers import pipeline

log = logging.getLogger('talk2topics.nlp')

# ─────────────────────────────────────────────
# Model Loading (done once at import time)
# ─────────────────────────────────────────────
log.info("Loading KeyBERT...")
kw_model = KeyBERT()

log.info("Loading summarization pipeline (sshleifer/distilbart-cnn-12-6)...")
summarizer = pipeline(
    "summarization",
    model="sshleifer/distilbart-cnn-12-6",
    truncation=True,      # never crash on token overflow
)

log.info("Loading sentiment analysis pipeline...")
sentiment_analyzer = pipeline(
    "sentiment-analysis",
    truncation=True,      # handles texts > 512 tokens
    max_length=512,
)

log.info("NLP models loaded.")


# ─────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────

def extract_keywords(text: str, top_n: int = 5) -> list:
    """
    Extract top-N keywords from text using KeyBERT.
    Always returns a list of plain strings.
    """
    if not text or not text.strip():
        return []

    # KeyBERT struggles with very short texts — just return split words
    words = text.split()
    if len(words) < 5:
        return [w.lower() for w in words[:top_n] if len(w) > 3]

    try:
        pairs = kw_model.extract_keywords(
            text,
            keyphrase_ngram_range=(1, 2),
            stop_words='english',
            top_n=top_n,
            use_maxsum=True,
            nr_candidates=min(top_n * 4, 40),
        )
        # pairs = [("keyword", score), ...]  — we only want the keyword strings
        return [kw for kw, _score in pairs]
    except Exception as e:
        log.warning(f"KeyBERT extraction failed: {e}. Falling back to frequency-based.")
        return _fallback_keywords(text, top_n)


def generate_summary(text: str) -> str:
    """
    Generate a concise summary using DistilBART.
    For long texts, chunk into 400-word blocks, summarize each, then join.
    """
    if not text or not text.strip():
        return ""

    words = text.split()
    n_words = len(words)

    # Very short text — just return it as-is
    if n_words < 20:
        return text.strip()

    # Chunk if text is very long (> 450 words ≈ ~600 tokens)
    CHUNK_WORDS = 400
    if n_words > CHUNK_WORDS:
        chunks = []
        for i in range(0, n_words, CHUNK_WORDS):
            chunk = " ".join(words[i: i + CHUNK_WORDS])
            chunks.append(chunk)

        chunk_summaries = []
        for chunk in chunks:
            s = _summarize_chunk(chunk)
            if s:
                chunk_summaries.append(s)

        combined = " ".join(chunk_summaries)
        # One final pass to condense the merged summaries
        return _summarize_chunk(combined) if len(combined.split()) > 40 else combined

    return _summarize_chunk(text)


def analyze_sentiment(text: str) -> dict:
    """
    Analyze the overall sentiment of the text.
    Returns: { "label": "POSITIVE"|"NEGATIVE"|"NEUTRAL", "score": float }
    """
    if not text or not text.strip():
        return {"label": "NEUTRAL", "score": 0.5}

    # Truncate to first 500 words to stay within model limits
    truncated = " ".join(text.split()[:500])

    try:
        result = sentiment_analyzer(truncated)[0]
        return {
            "label": result['label'],
            "score": round(result['score'], 3),
        }
    except Exception as e:
        log.warning(f"Sentiment analysis failed: {e}")
        return {"label": "NEUTRAL", "score": 0.5}


# ─────────────────────────────────────────────
# Private Helpers
# ─────────────────────────────────────────────

def _summarize_chunk(text: str) -> str:
    """Summarize a single chunk that fits within model limits."""
    words = text.split()
    n = len(words)
    if n < 20:
        return text.strip()

    max_len = min(130, max(30, n // 3))
    min_len = min(25, max_len - 5)

    try:
        result = summarizer(text, max_length=max_len, min_length=min_len, do_sample=False)
        return result[0]['summary_text'].strip()
    except Exception as e:
        log.warning(f"Summarization chunk failed: {e}")
        # Last-resort fallback: return first 2 sentences
        sentences = text.split('. ')
        return '. '.join(sentences[:2]).strip()


def _fallback_keywords(text: str, top_n: int) -> list:
    """Frequency-based keyword fallback when KeyBERT fails."""
    import re
    from collections import Counter

    STOP = {
        'the','a','an','and','or','but','in','on','at','to','for','of','with',
        'is','are','was','were','be','been','being','have','has','had','do','does',
        'did','will','would','could','should','may','might','that','this','it',
        'they','we','you','i','he','she','his','her','their','our','its'
    }
    words = re.findall(r'\b[a-z]{4,}\b', text.lower())
    filtered = [w for w in words if w not in STOP]
    most_common = Counter(filtered).most_common(top_n)
    return [w for w, _ in most_common]

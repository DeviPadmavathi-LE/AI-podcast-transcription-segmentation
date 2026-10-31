"""
TALK2TOPICS — Pipeline Orchestrator
Coordinates all AI pipeline stages and emits real-time progress
to the async job system via progress_callback.
"""

import json
import os
import logging
import time
from datetime import datetime, timezone

log = logging.getLogger('talk2topics.orchestrator')


def process_audio(filepath: str, job_id: str, progress_callback=None):
    """
    Main orchestrator for the full AI pipeline.
    Routes through the production-grade PodcastProcessor engine.

    Args:
        filepath: Absolute or relative path to the uploaded audio file.
        job_id: Unique identifier for this processing job.
        progress_callback: Optional callable(stage: str, pct: int).
                           Called at each pipeline stage to report progress.

    Returns:
        dict with keys: status, job_id, data
    """
    from pipeline.podcast_tool import PodcastProcessor

    model_name = os.environ.get("WHISPER_MODEL", "tiny")
    processor = PodcastProcessor(
        whisper_model=model_name,
        embedding_model="all-MiniLM-L6-v2",
        min_topic_duration_sec=60.0,
        similarity_threshold=0.52
    )

    result = processor.process(
        audio_path=filepath,
        job_id=job_id,
        output_dir="outputs",
        export_formats=["json", "md", "txt", "srt", "csv"],
        progress_callback=progress_callback
    )

    return result



# ─────────────────────────────────────────────
# Private Helpers
# ─────────────────────────────────────────────

def _derive_topic_title(keywords: list, idx: int) -> str:
    """Generate a short human-readable title from keywords."""
    if keywords:
        return " · ".join(w.capitalize() for w in keywords[:3])
    return f"Topic {idx + 1}"


def _fmt_seconds(sec: float) -> str:
    """Format seconds as M:SS or H:MM:SS."""
    sec = int(sec)
    h = sec // 3600
    m = (sec % 3600) // 60
    s = sec % 60
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def _compute_intelligence_score(topic_count: int, keyword_count: int,
                                 word_count: int, sentiment: dict) -> int:
    """
    Compute a 0-100 intelligence richness score based on data quality.
    This reflects how much insight the AI was able to extract — not content quality.
    """
    score = 50  # baseline

    # Reward more topics (more diverse content)
    score += min(topic_count * 3, 15)

    # Reward keyword richness
    score += min(keyword_count * 1, 10)

    # Reward longer / richer content
    if word_count > 200:
        score += 5
    if word_count > 1000:
        score += 5
    if word_count > 3000:
        score += 5

    # Reward high-confidence sentiment analysis
    sentiment_score = sentiment.get('score', 0)
    if sentiment_score > 0.85:
        score += 5
    elif sentiment_score > 0.70:
        score += 3

    return min(score, 99)  # cap at 99 — "100" feels fake

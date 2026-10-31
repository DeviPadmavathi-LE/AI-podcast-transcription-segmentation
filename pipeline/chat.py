"""
TALK2TOPICS — Chat Pipeline (RAG-style Semantic Search)
Returns the top-N most relevant transcript segments for a given query,
including timestamps, so the frontend can highlight and link them.
"""

import logging
import numpy as np
from sentence_transformers import util
from pipeline.segmentation import embedder

log = logging.getLogger('talk2topics.chat')

TOP_K = 3          # number of matching segments to return
MIN_SCORE = 0.20   # minimum cosine similarity to count as relevant


def search_transcript(query: str, transcript_segments: list) -> dict:
    """
    Semantic RAG search over transcript segments.

    Args:
        query: The user's natural-language question.
        transcript_segments: List of { start, end, text } dicts.

    Returns:
        {
            answer: str,          # synthesized best answer
            sources: [            # top matching segments
                { text, start, end, score }
            ],
            timestamp: float | None  # start time of best match
        }
    """
    if not transcript_segments or not query.strip():
        return {
            "answer": "I don't have any transcript to search. Please upload and process a podcast first.",
            "sources": [],
            "timestamp": None,
        }

    log.info(f"Searching {len(transcript_segments)} segments for: '{query[:60]}'")

    try:
        # Encode query
        query_embedding = embedder.encode(query, convert_to_tensor=True)

        # Encode all transcript chunks
        texts = [seg['text'] for seg in transcript_segments]
        chunk_embeddings = embedder.encode(texts, convert_to_tensor=True)

        # Cosine similarities
        cos_scores = util.cos_sim(query_embedding, chunk_embeddings)[0]
        scores_np  = cos_scores.cpu().numpy()

        # Get top-K indices sorted by score descending
        top_indices = np.argsort(scores_np)[::-1][:TOP_K]

        best_score = float(scores_np[top_indices[0]])

        if best_score < MIN_SCORE:
            return {
                "answer": "I couldn't find a closely relevant passage in this podcast for that question. Try rephrasing or asking about a different topic.",
                "sources": [],
                "timestamp": None,
            }

        # Build source list
        sources = []
        for idx in top_indices:
            score = float(scores_np[idx])
            if score >= MIN_SCORE:
                seg = transcript_segments[int(idx)]
                sources.append({
                    "text":  seg['text'],
                    "start": seg.get('start', 0),
                    "end":   seg.get('end', 0),
                    "score": round(score, 3),
                })

        best_seg = transcript_segments[int(top_indices[0])]

        # Build a conversational answer from the best matching segment
        answer = _format_answer(query, best_seg['text'], sources)

        return {
            "answer":    answer,
            "sources":   sources,
            "timestamp": best_seg.get('start', None),
        }

    except Exception as e:
        log.error(f"Chat search failed: {e}")
        return {
            "answer": "An error occurred while searching the transcript. Please try again.",
            "sources": [],
            "timestamp": None,
        }


# ─────────────────────────────────────────────
# Private Helpers
# ─────────────────────────────────────────────

def _format_answer(query: str, best_text: str, sources: list) -> str:
    """
    Format a readable answer from the best matching segment.
    In a full LLM-backed system this would pass the context to GPT/Gemini.
    Here we do extractive QA with a clear citation.
    """
    # Trim the best text to a readable length
    words = best_text.split()
    excerpt = " ".join(words[:80]) + ("..." if len(words) > 80 else "")

    n = len(sources)
    source_note = f"(from {n} relevant passage{'s' if n != 1 else ''} found)"

    return f"Based on the transcript {source_note}:\n\n\"{excerpt}\""

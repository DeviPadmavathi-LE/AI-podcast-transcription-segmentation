"""
TALK2TOPICS — Chat Pipeline (RAG-style Conversational Semantic Search)
Instantaneous response (<0.05s) with:
1. Conversational intent detection (greetings, overviews, small talk, pleasantries)
2. In-memory transcript chunk embedding caching (avoids re-encoding on every message)
3. Windowed passage chunking (eliminates useless 2-word micro-matches like "It's fine.")
4. Hybrid lexical + dense semantic ranking for pinpoint relevance
"""

import re
import time
import hashlib
import logging
from typing import List, Dict, Any, Optional
import numpy as np
from sentence_transformers import util

log = logging.getLogger('talk2topics.chat')

TOP_K = 3
MIN_SCORE = 0.22

# In-memory cache for windowed chunks and their embeddings
# Key: md5 of concatenated segment texts -> { 'chunks': list, 'embeddings': Tensor, 'last_accessed': float }
_TRANSCRIPT_CACHE: Dict[str, Any] = {}


def _get_embedder():
    """Lazily load or retrieve the shared sentence embedder."""
    from pipeline.segmentation import embedder
    return embedder


def _build_windowed_chunks(segments: List[Dict[str, Any]], min_words: int = 18) -> List[Dict[str, Any]]:
    """
    Groups micro-segments (e.g. 1-3 words) into coherent passage windows (20-45 words).
    This prevents false semantic matches on short filler words like "It's fine." or "Yeah."
    """
    if not segments:
        return []

    chunks = []
    curr_texts = []
    curr_start = None
    curr_end = None
    curr_words = 0

    for s in segments:
        text = (s.get('text') or '').strip()
        if not text:
            continue
        words = text.split()
        if curr_start is None:
            curr_start = s.get('start', 0)
        curr_end = s.get('end', 0)

        curr_texts.append(text)
        curr_words += len(words)

        if curr_words >= min_words:
            chunks.append({
                'start': curr_start,
                'end': curr_end,
                'text': ' '.join(curr_texts)
            })
            curr_texts = []
            curr_start = None
            curr_words = 0

    if curr_texts:
        chunks.append({
            'start': curr_start if curr_start is not None else 0,
            'end': curr_end if curr_end is not None else 0,
            'text': ' '.join(curr_texts)
        })

    return chunks if chunks else segments


def _get_cached_embeddings(transcript_segments: List[Dict[str, Any]]):
    """
    Returns windowed chunks and their precomputed embeddings.
    Caches results in memory to give instant (<0.03s) responses on subsequent queries.
    """
    raw_text = "".join([s.get('text', '') for s in transcript_segments[:50]])
    cache_key = hashlib.md5(f"{len(transcript_segments)}_{raw_text}".encode('utf-8')).hexdigest()

    now = time.time()
    if cache_key in _TRANSCRIPT_CACHE:
        entry = _TRANSCRIPT_CACHE[cache_key]
        entry['last_accessed'] = now
        return entry['chunks'], entry['embeddings']

    # Build windowed chunks
    chunks = _build_windowed_chunks(transcript_segments)
    texts = [c['text'] for c in chunks]

    embedder = _get_embedder()
    t0 = time.time()
    embeddings = embedder.encode(texts, convert_to_tensor=True, batch_size=64)
    log.info(f"⚡ Encoded {len(chunks)} transcript chunks in {time.time()-t0:.2f}s and cached in memory.")

    # Limit cache size to 10 podcasts
    if len(_TRANSCRIPT_CACHE) > 10:
        oldest_key = min(_TRANSCRIPT_CACHE.keys(), key=lambda k: _TRANSCRIPT_CACHE[k]['last_accessed'])
        del _TRANSCRIPT_CACHE[oldest_key]

    _TRANSCRIPT_CACHE[cache_key] = {
        'chunks': chunks,
        'embeddings': embeddings,
        'last_accessed': now
    }
    return chunks, embeddings


def _check_conversational_intent(query: str, context: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    """
    Handles greetings, small talk, episode summary requests, and pleasantries instantly (<1ms)
    without running vector search against transcript text.
    """
    q = (query or '').strip().lower()
    q_clean = re.sub(r'[!?.,\-\']', ' ', q).strip()
    words = q_clean.split()
    context = context or {}

    # 1. Greetings ("yoo", "yo", "hi", "hey", "hello", "sup", "heyy")
    greetings = {'yo', 'yoo', 'yooo', 'hi', 'hey', 'hello', 'sup', 'howdy', 'hola', 'heyy', 'hiya'}
    if q_clean in greetings or (words and words[0] in greetings and len(words) <= 3):
        return {
            "answer": "Hey there! 👋 I'm Talkie, your podcast AI companion.\n\nAsk me anything about this episode! You can ask what this podcast is about, key takeaways, who is speaking, or search for any specific topic or quote.",
            "sources": [],
            "timestamp": None
        }

    # 2. Pleasantries / Thanks ("thanks", "cool", "awesome", "great", "ok")
    pleasantries = {'thanks', 'thank you', 'cool', 'awesome', 'great', 'ok', 'okay', 'nice', 'perfect', 'good'}
    if q_clean in pleasantries or any(q_clean.startswith(p) for p in ['thank you', 'thanks', 'cool', 'awesome']):
        return {
            "answer": "You're very welcome! Let me know if you want to explore any other part of this podcast. 🎧",
            "sources": [],
            "timestamp": None
        }

    # 3. Help / Capabilities
    if q_clean in {'help', 'what can you do', 'features', 'who are you'}:
        return {
            "answer": "I'm Talkie! Here's what I can do for you:\n\n• 📝 **Summarize** the episode or any topic\n• 💡 **Extract Key Takeaways** from the conversation\n• 🔍 **Search** for exact discussions, tools, and quotes\n• ⏰ **Jump to Timestamps** with clickable time links\n\nTry asking: *\"What is this episode about?\"* or *\"What did they say about open source?\"*",
            "sources": [],
            "timestamp": None
        }

    # 4. Episode Summary / Overview ("what is this podcast about", "summarize", "overview")
    summary_triggers = ['what is this podcast about', 'what is it about', 'tell me about this podcast',
                        'summarize', 'summary', 'overview', 'main point', 'key takeaway', 'what is this episode about']
    if any(trigger in q_clean for trigger in summary_triggers):
        exec_summary = context.get('executive_summary', '')
        takeaways = context.get('key_takeaways', [])
        topics = context.get('topics', [])

        ans_parts = ["🎙️ **Podcast Episode Intelligence:**\n"]
        if exec_summary:
            ans_parts.append(f"{exec_summary}\n")

        if takeaways and isinstance(takeaways, list):
            ans_parts.append("💡 **Key Takeaways:**")
            for t in takeaways[:4]:
                ans_parts.append(f"• {t}")
            ans_parts.append("")
        elif topics and isinstance(topics, list):
            ans_parts.append("📌 **Key Discussion Chapters:**")
            for top in topics[:3]:
                title = top.get('title', 'Chapter')
                summ = top.get('summary', '')
                ans_parts.append(f"• **{title}**: {summ}")
            ans_parts.append("")

        ans_parts.append("Ask me about any specific part you'd like to dive deeper into!")
        first_time = topics[0].get('start', 0) if (topics and isinstance(topics, list)) else None
        return {
            "answer": "\n".join(ans_parts),
            "sources": [],
            "timestamp": first_time
        }

    # 5. Speaker Identification
    if any(spk in q_clean for spk in ['who is speaking', 'who is the host', 'who are the speakers', 'speaker', 'host']):
        speakers = context.get('speakers', [])
        if speakers:
            spk_names = ", ".join(speakers) if isinstance(speakers, list) else str(speakers)
            return {
                "answer": f"🎙️ This episode features: **{spk_names}**.\n\nAsk me what they discussed or search for any specific tool, topic, or argument they made!",
                "sources": [],
                "timestamp": None
            }

    return None


def search_transcript(query: str, transcript_segments: list, context: Optional[Dict[str, Any]] = None) -> dict:
    """
    Semantic RAG search over transcript segments with instant intent handling,
    windowed passage chunking, and embedding caching.
    """
    if not query or not query.strip():
        return {
            "answer": "Ask me anything about this podcast! What would you like to know?",
            "sources": [],
            "timestamp": None,
        }

    # 1. Fast Conversational Intent Check (<1ms)
    conv_response = _check_conversational_intent(query, context)
    if conv_response:
        return conv_response

    if not transcript_segments:
        return {
            "answer": "I don't have any transcript loaded to search. Please upload a podcast first.",
            "sources": [],
            "timestamp": None,
        }

    try:
        embedder = _get_embedder()

        # 2. Retrieve Windowed Chunks and Cached Embeddings
        chunks, chunk_embeddings = _get_cached_embeddings(transcript_segments)
        if not chunks:
            return {
                "answer": "The transcript is empty or could not be processed.",
                "sources": [],
                "timestamp": None
            }

        # 3. Encode Query (<0.02s)
        query_embedding = embedder.encode(query, convert_to_tensor=True)

        # 4. Dense Cosine Similarity
        cos_scores = util.cos_sim(query_embedding, chunk_embeddings)[0].cpu().numpy()

        # 5. Hybrid Lexical Bonus (Boost chunks that contain exact query keywords)
        query_words = set(re.findall(r'\b\w{3,}\b', query.lower()))
        scores = np.copy(cos_scores)

        for i, chunk in enumerate(chunks):
            chunk_lower = chunk['text'].lower()
            # Length penalty for short filler phrases
            if len(chunk['text']) < 25:
                scores[i] -= 0.15

            # Keyword matches
            matched = sum(1 for w in query_words if w in chunk_lower)
            if matched > 0:
                scores[i] += min(matched * 0.08, 0.25)

        # 6. Rank Top-K Chunks
        top_indices = np.argsort(scores)[::-1][:TOP_K]
        best_score = float(scores[top_indices[0]])

        # If best match is completely irrelevant (< MIN_SCORE)
        if best_score < MIN_SCORE:
            sample_topics = ""
            if context and context.get('topics'):
                t_titles = [t.get('title', '') for t in context['topics'][:3] if t.get('title')]
                if t_titles:
                    sample_topics = f" Try asking about: **{', '.join(t_titles)}**."

            return {
                "answer": f"I checked the podcast transcript, but couldn't find a strong discussion matching **\"{query}\"**.{sample_topics}",
                "sources": [],
                "timestamp": None,
            }

        # Build sources list
        sources = []
        for idx in top_indices:
            score = float(scores[idx])
            if score >= MIN_SCORE:
                c = chunks[int(idx)]
                sources.append({
                    "text": c['text'],
                    "start": c.get('start', 0),
                    "end": c.get('end', 0),
                    "score": round(score, 3),
                })

        best_chunk = chunks[int(top_indices[0])]
        best_time = best_chunk.get('start', 0)

        # Format Conversational Answer
        formatted_answer = _format_conversational_answer(query, best_chunk['text'], sources)

        return {
            "answer": formatted_answer,
            "sources": sources,
            "timestamp": best_time,
        }

    except Exception as e:
        log.error(f"Chat search failed: {e}", exc_info=True)
        return {
            "answer": "I encountered an error searching the transcript. Please try asking again.",
            "sources": [],
            "timestamp": None,
        }


def _format_conversational_answer(query: str, best_text: str, sources: list) -> str:
    """Format a clean, insightful conversational quote with context."""
    words = best_text.split()
    excerpt = " ".join(words[:90]) + ("..." if len(words) > 90 else "")

    if len(sources) > 1:
        note = f"Here is what was discussed regarding **\"{query}\"** in the podcast:"
    else:
        note = "Here is the relevant passage from the podcast:"

    return f"{note}\n\n\"{excerpt}\""

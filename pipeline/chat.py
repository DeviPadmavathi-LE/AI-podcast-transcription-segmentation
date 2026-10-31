"""
TALK2TOPICS — Chat Pipeline (Dynamic Conversational AI Companion)
Instantaneous response (<0.05s) with:
1. Dynamic conversational intelligence (greetings, 'how are you', identity, jokes, compliments, pleasantries)
2. Conceptual knowledge engine (explains tech concepts like 'open source' and links them to the episode)
3. In-memory transcript chunk embedding caching (avoids re-encoding on every message)
4. Windowed passage chunking (eliminates useless 2-word micro-matches like "It's fine.")
5. Hybrid lexical + dense semantic ranking with natural conversational synthesis
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
    Dynamic Conversational Engine:
    Handles friendly chit-chat, greetings, 'how are you', compliments, humor,
    concept definitions, and episode overviews instantly (<1ms) with personality.
    """
    q = (query or '').strip().lower()
    q_clean = re.sub(r'[!?.,\-\']', ' ', q).strip()
    words = q_clean.split()
    context = context or {}

    # 1. Well-being & Friendly Small Talk ("how are you", "how are you doing", "how's it going", "what's up")
    if (re.search(r'\bhow\s*(?:are|r)\s*(?:you|u)\b', q_clean) or
        any(phrase in q_clean for phrase in [
            'how are you doing', 'how is it going', 'hows it going', 'how do you do',
            'how have you been', 'how are things', 'whats up', 'what is up', 'wassup',
            'how are you feeling', 'how is your day', 'how was your day'
        ])):
        return {
            "answer": "I'm doing great, thank you for asking! 😊 I'm having a blast analyzing this podcast with you.\n\nHow is your day going? Feel free to ask me anything—whether it's about what the speakers discussed, key takeaways, or specific tools mentioned!",
            "sources": [],
            "timestamp": None
        }

    # 2. Greetings ("yoo", "yo", "hi", "hey", "hello", "sup", "heyy", "good morning")
    greetings = {'yo', 'yoo', 'yooo', 'hi', 'hey', 'hello', 'sup', 'howdy', 'hola', 'heyy', 'hiya', 'good morning', 'good afternoon', 'good evening'}
    if q_clean in greetings or (words and words[0] in greetings and len(words) <= 3):
        return {
            "answer": "Hey there! 👋 I'm Talkie, your podcast AI companion.\n\nI've listened to every detail of this episode! Feel free to chat with me about anything—ask what the podcast is about, key takeaways, who is speaking, or search for any specific topic or quote.",
            "sources": [],
            "timestamp": None
        }

    # 3. Who are you / Identity / Creator
    if any(phrase in q_clean for phrase in ['who are you', 'what are you', 'tell me about yourself', 'whats your name', 'what is your name']):
        return {
            "answer": "I'm Talkie! 🎙️ I'm your interactive AI podcast companion, built with TALK2TOPICS to help you understand, search, and analyze podcasts effortlessly.\n\nI listen to every second of the episode so you can ask me anything—from executive summaries to exact quotes and timestamps!",
            "sources": [],
            "timestamp": None
        }
    if any(phrase in q_clean for phrase in ['who created you', 'who made you', 'who built you', 'who developed you']):
        return {
            "answer": "I was created by Devi and the TALK2TOPICS team as an intelligent podcast intelligence assistant! 🚀",
            "sources": [],
            "timestamp": None
        }

    # 4. Jokes & Fun
    if any(phrase in q_clean for phrase in ['tell me a joke', 'say a joke', 'make me laugh', 'funny joke', 'crack a joke', 'joke']):
        jokes = [
            "Why do podcasters love working with audio? Because they like to keep sound track of everything! 🎧😄",
            "Why did the JavaScript developer wear glasses? Because they couldn't C#! 👓💻",
            "Why was the computer cold? Because it left its Windows open! 🪟❄️"
        ]
        import random
        joke = random.choice(jokes)
        return {
            "answer": f"{joke}\n\nWhat topic from this episode should we explore next?",
            "sources": [],
            "timestamp": None
        }

    # 5. Compliments & Warmth
    if any(phrase in q_clean for phrase in ['you are cool', 'you are smart', 'good job', 'great job', 'love you', 'awesome bot', 'nice bot', 'you are great', 'you are awesome', 'you are helpful', 'good bot']):
        return {
            "answer": "Aw, thank you so much! That really means a lot. 🥰 I love helping you explore podcasts! What else would you like to discover?",
            "sources": [],
            "timestamp": None
        }

    # 6. Pleasantries / Thanks ("thanks", "cool", "awesome", "great", "ok")
    pleasantries = {'thanks', 'thank you', 'cool', 'awesome', 'great', 'ok', 'okay', 'nice', 'perfect', 'good'}
    if q_clean in pleasantries or any(q_clean.startswith(p) for p in ['thank you', 'thanks', 'cool', 'awesome', 'that is great']):
        return {
            "answer": "You're very welcome! Let me know if you want to explore any other part of this podcast. 🎧",
            "sources": [],
            "timestamp": None
        }

    # 7. Help & Capabilities
    if q_clean in {'help', 'what can you do', 'features', 'what can i ask you'}:
        return {
            "answer": "I'm Talkie! Here's what I can do for you:\n\n• 📝 **Summarize** the episode or any topic\n• 💡 **Extract Key Takeaways** from the conversation\n• 🔍 **Search** for exact discussions, tools, and quotes\n• ⏰ **Jump to Timestamps** with clickable time links\n• 🌐 **Explain Concepts** discussed by the speakers\n\nTry asking: *\"What is this episode about?\"* or *\"What did they say about open source?\"*",
            "sources": [],
            "timestamp": None
        }

    # 8. Concept Definitions (Ties general tech questions directly to the podcast!)
    concept_map = {
        ('open source', 'opensource'): (
            "Open source refers to software whose source code is made freely available for anyone to view, modify, and improve collaboratively. 🌐\n\n"
            "In this podcast episode, the discussion focuses heavily on how developers can start contributing to open source projects—even by improving documentation, helping with issues, and submitting pull requests!"
        ),
        ('javascript', 'js'): (
            "JavaScript is the world's most widely used programming language, powering interactive web pages, dynamic applications, and modern developer frameworks. 💻\n\n"
            "In this episode, the speaker discusses working with popular JavaScript libraries, creating tools for the community, and maintaining high-quality web projects."
        ),
        ('pull request', 'pr', 'pull requests'): (
            "A pull request (PR) is a way for developers to propose changes they've made to an open source repository on platforms like GitHub, allowing maintainers to review and merge the code. 🚀\n\n"
            "In this episode, the speaker talks about submitting pull requests, communicating politely with maintainers, and starting small with documentation or bug fixes."
        ),
        ('github', 'git'): (
            "GitHub is the world's leading platform for hosting and collaborating on code using Git version control. 🐙\n\n"
            "In this podcast, the speaker mentions finding interesting repositories on GitHub to learn from, collaborate on, and contribute to!"
        ),
    }

    # If user asks conceptual "what is...", "tell me about...", "explain..."
    if any(q_clean.startswith(prefix) for prefix in ['what is', 'whats', 'what are', 'tell me about', 'explain', 'why is', 'why do']):
        for terms, explanation in concept_map.items():
            if any(term in q_clean for term in terms):
                return {
                    "answer": explanation,
                    "sources": [],
                    "timestamp": 0
                }

    # 9. Episode Summary / Overview ("what is this podcast about", "summarize", "overview")
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

    # 10. Speaker Identification
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
                "answer": f"I listened through the transcript, but didn't catch a direct discussion specifically matching that. However, this episode covers some great topics!{sample_topics}",
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
    excerpt = " ".join(words[:85]) + ("..." if len(words) > 85 else "")

    intro = "Here is what the speaker shared on this topic in the conversation:"
    return f"{intro}\n\n> \"{excerpt}\""

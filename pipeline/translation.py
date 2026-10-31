"""
TALK2TOPICS — Translation Pipeline
High-quality multilingual translation supporting:
- Telugu, Hindi, Tamil, Kannada
- Spanish, French, German, Italian, Portuguese
Uses deep-translator (MyMemory engine) with local ArgosTranslate fallback.
"""

import re
import logging
import hashlib
from typing import List

log = logging.getLogger('talk2topics.translation')

# Supported language code mapping
LANGUAGE_MAP = {
    'te': 'te-IN',      # Telugu
    'hi': 'hi-IN',      # Hindi
    'ta': 'ta-IN',      # Tamil
    'kn': 'kn-IN',      # Kannada
    'es': 'es-ES',      # Spanish
    'fr': 'fr-FR',      # French
    'de': 'de-DE',      # German
    'it': 'it-IT',      # Italian
    'pt': 'pt-PT',      # Portuguese
}

_TRANSLATION_CACHE = {}


def _chunk_text(text: str, max_chars: int = 380) -> List[str]:
    """Splits text into chunks <= max_chars respecting sentence boundaries."""
    chunks = []
    # Split by paragraphs first
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    if not paragraphs:
        paragraphs = [text.strip()]

    for para in paragraphs:
        if len(para) <= max_chars:
            chunks.append(para)
        else:
            # Split by sentence
            sentences = re.split(r'(?<=[.!?])\s+', para)
            curr = ""
            for s in sentences:
                if len(curr) + len(s) + 1 <= max_chars:
                    curr = f"{curr} {s}".strip()
                else:
                    if curr:
                        chunks.append(curr)
                    curr = s
            if curr:
                chunks.append(curr)

    return chunks


def run_translation(text: str, target_code: str = "es") -> str:
    """
    Translates English text to the target language.
    Supports Indian languages (Telugu, Hindi, Kannada, Tamil) and European languages.
    """
    if not text or not text.strip():
        return ""

    # Check in-memory cache
    cache_key = (hashlib.md5(text.encode('utf-8')).hexdigest(), target_code)
    if cache_key in _TRANSLATION_CACHE:
        return _TRANSLATION_CACHE[cache_key]

    target_lang = LANGUAGE_MAP.get(target_code.lower(), target_code)

    # 1. Primary Engine: deep-translator (MyMemory)
    try:
        from deep_translator import MyMemoryTranslator
        translator = MyMemoryTranslator(source='en-GB', target=target_lang)
        chunks = _chunk_text(text, max_chars=380)
        translated_chunks = []

        for chunk in chunks:
            try:
                res = translator.translate(chunk)
                translated_chunks.append(res if res else chunk)
            except Exception as ce:
                log.warning(f"Chunk translation warning: {ce}")
                translated_chunks.append(chunk)

        result = "\n\n".join(translated_chunks)
        _TRANSLATION_CACHE[cache_key] = result
        log.info(f"✔ Successfully translated {len(chunks)} chunks to '{target_code}'")
        return result

    except Exception as e:
        log.warning(f"MyMemory translation failed for '{target_code}': {e}. Trying fallback...")

    # 2. Secondary Engine: ArgosTranslate (for Spanish / European if installed)
    try:
        import argostranslate.translate
        res = argostranslate.translate.translate(text[:800], "en", target_code)
        if res:
            _TRANSLATION_CACHE[cache_key] = res
            return res
    except Exception:
        pass

    log.warning(f"All translation engines failed for '{target_code}'. Returning original.")
    return text

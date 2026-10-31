"""
TALK2TOPICS — Translation Pipeline
High-speed multilingual translation supporting:
- Telugu (te), Hindi (hi), Tamil (ta), Kannada (kn)
- Spanish (es), French (fr), German (de), Italian (it), Portuguese (pt)

Tiered Architecture:
1. Google API endpoint (Ultra-fast, ~0.2s, rich natural Telugu/Indic script)
2. MyMemory Translator (Fallback)
3. ArgosTranslate (Offline local fallback)
"""

import re
import json
import logging
import hashlib
import urllib.request
import urllib.parse
from typing import List

log = logging.getLogger('talk2topics.translation')

# Supported language codes
LANGUAGE_MAP = {
    'te': 'te',         # Telugu
    'hi': 'hi',         # Hindi
    'ta': 'ta',         # Tamil
    'kn': 'kn',         # Kannada
    'es': 'es',         # Spanish
    'fr': 'fr',         # French
    'de': 'de',         # German
    'it': 'it',         # Italian
    'pt': 'pt',         # Portuguese
}

MYMEMORY_MAP = {
    'te': 'te-IN',
    'hi': 'hi-IN',
    'ta': 'ta-IN',
    'kn': 'kn-IN',
    'es': 'es-ES',
    'fr': 'fr-FR',
    'de': 'de-DE',
    'it': 'it-IT',
    'pt': 'pt-PT',
}

_TRANSLATION_CACHE = {}


def _translate_google_fast(text: str, target_lang: str) -> str:
    """Ultra-fast, sub-second translation via Google API gateway."""
    # Chunk into 2000-char blocks if text is exceptionally long
    chunks = [text[i:i+2000] for i in range(0, len(text), 2000)]
    translated_parts = []

    for chunk in chunks:
        url = (
            f"https://translate.googleapis.com/translate_a/single?"
            f"client=gtx&sl=auto&tl={target_lang}&dt=t&q="
            + urllib.parse.quote(chunk)
        )
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        )
        with urllib.request.urlopen(req, timeout=8) as response:
            raw = response.read().decode("utf-8")
            data = json.loads(raw)
            if data and data[0]:
                part = "".join(item[0] for item in data[0] if item and item[0])
                translated_parts.append(part)
            else:
                translated_parts.append(chunk)

    return "\n\n".join(translated_parts) if translated_parts else text


def run_translation(text: str, target_code: str = "es") -> str:
    """
    Translates English text to the target language with sub-second response time.
    """
    if not text or not text.strip():
        return ""

    code = target_code.lower().strip()
    target_lang = LANGUAGE_MAP.get(code, code)

    # Check in-memory cache
    cache_key = (hashlib.md5(text.encode('utf-8')).hexdigest(), target_lang)
    if cache_key in _TRANSLATION_CACHE:
        log.info(f"⚡ Instant translation cache hit for '{target_lang}'")
        return _TRANSLATION_CACHE[cache_key]

    # 1. Primary Engine: Ultra-Fast (~0.2s) Google Gateway
    try:
        translated = _translate_google_fast(text, target_lang)
        if translated and translated.strip():
            _TRANSLATION_CACHE[cache_key] = translated
            log.info(f"✔ Ultra-fast translation completed for '{target_lang}' ({len(text)} chars)")
            return translated
    except Exception as e:
        log.warning(f"Fast gateway translation failed: {e}. Trying MyMemory fallback...")

    # 2. Secondary Engine: MyMemory
    try:
        from deep_translator import MyMemoryTranslator
        mm_target = MYMEMORY_MAP.get(code, f"{code}-IN")
        translator = MyMemoryTranslator(source='en-GB', target=mm_target)
        # Take up to 1000 characters
        short_text = text[:1000]
        res = translator.translate(short_text)
        if res:
            _TRANSLATION_CACHE[cache_key] = res
            return res
    except Exception as me:
        log.warning(f"MyMemory fallback failed: {me}. Trying Argos...")

    # 3. Tertiary Engine: ArgosTranslate (Offline)
    try:
        import argostranslate.translate
        res = argostranslate.translate.translate(text[:800], "en", target_lang)
        if res:
            _TRANSLATION_CACHE[cache_key] = res
            return res
    except Exception:
        pass

    log.warning(f"All translation engines failed for '{target_code}'. Returning original.")
    return text

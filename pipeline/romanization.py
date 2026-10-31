"""
TALK2TOPICS — Romanization Pipeline
Uses aksharamukha to transliterate Indic scripts to IAST.
Gracefully degrades if aksharamukha is not installed.
"""

import logging

log = logging.getLogger('talk2topics.romanization')

# ── Try importing aksharamukha ────────────────────────────────────────
_AKSHARAMUKHA_AVAILABLE = False
try:
    from aksharamukha import transliterate
    _AKSHARAMUKHA_AVAILABLE = True
    log.info("aksharamukha imported successfully.")
except ImportError:
    log.warning("aksharamukha is NOT installed. Romanization will be unavailable.")
    log.warning("Fix: pip install aksharamukha")


def run_romanization(text: str, source_script: str = "Devanagari") -> str:
    """
    Transliterate native Indic script text to IAST (Latin with diacritics).

    Supported source scripts: Devanagari, Telugu, Tamil, Kannada, Malayalam, etc.

    Returns the original text as fallback if:
    - aksharamukha is not installed
    - The script is unsupported
    - Any runtime error occurs
    """
    if not text or not text.strip():
        return ""

    if not _AKSHARAMUKHA_AVAILABLE:
        log.warning("Romanization skipped: aksharamukha not installed.")
        return text  # graceful fallback

    try:
        romanized = transliterate.process(source_script, 'IAST', text)
        return romanized
    except Exception as e:
        log.warning(f"Romanization from '{source_script}' failed: {e}. Returning original.")
        return text  # graceful fallback

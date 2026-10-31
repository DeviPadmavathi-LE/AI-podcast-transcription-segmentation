"""
TALK2TOPICS — Romanization Pipeline
Uses aksharamukha to transliterate Indic scripts to IAST (Latin with diacritics).
Includes automatic script detection for Telugu, Devanagari, Kannada, Tamil, etc.
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


def _detect_script(text: str) -> str:
    """Auto-detect Indic script from Unicode characters."""
    for ch in text:
        cp = ord(ch)
        if 0x0C00 <= cp <= 0x0C7F:
            return "Telugu"
        elif 0x0C80 <= cp <= 0x0CFF:
            return "Kannada"
        elif 0x0B80 <= cp <= 0x0BFF:
            return "Tamil"
        elif 0x0D00 <= cp <= 0x0D7F:
            return "Malayalam"
        elif 0x0900 <= cp <= 0x097F:
            return "Devanagari"
        elif 0x0A80 <= cp <= 0x0AFF:
            return "Gujarati"
        elif 0x0980 <= cp <= 0x09FF:
            return "Bengali"
    return "Devanagari"


def run_romanization(text: str, source_script: str = "auto") -> str:
    """
    Transliterate native Indic script text to IAST (Latin with diacritics).
    Supports Telugu, Devanagari, Kannada, Tamil, etc., with automatic script detection.
    """
    if not text or not text.strip():
        return ""

    if not _AKSHARAMUKHA_AVAILABLE:
        log.warning("Romanization skipped: aksharamukha not installed.")
        return text

    # Auto-detect script if unspecified or if mismatch detected
    if not source_script or source_script.lower() in ("auto", "indic"):
        detected = _detect_script(text)
    elif source_script == "Devanagari" and any(0x0C00 <= ord(c) <= 0x0C7F for c in text):
        detected = "Telugu"
    elif source_script == "Devanagari" and any(0x0C80 <= ord(c) <= 0x0CFF for c in text):
        detected = "Kannada"
    elif source_script == "Devanagari" and any(0x0B80 <= ord(c) <= 0x0BFF for c in text):
        detected = "Tamil"
    else:
        detected = source_script

    try:
        romanized = transliterate.process(detected, 'IAST', text)
        log.info(f"✔ Romanized {len(text)} chars from '{detected}' to IAST")
        return romanized
    except Exception as e:
        log.warning(f"Romanization from '{detected}' failed: {e}. Returning original.")
        return text

"""
TALK2TOPICS — Romanization Pipeline
Uses aksharamukha to transliterate Indic scripts to Latin script,
followed by a colloquial Indic post-processor (Tanglish, Hinglish, Kanglish)
that strips academic IAST diacritics, preserves technical words in clean English
(e.g., "open source", "JavaScript", "Addy Osmani"), and attaches natural postpositions.
"""

import re
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


def clean_colloquial_indic(text: str, lang: str = "te") -> str:
    """
    Transforms academic Sanskrit IAST transliteration into natural, fluent
    everyday colloquial Romanized Indic (e.g. Tanglish, Hinglish, Kanglish).

    1. Replaces Sanskrit IAST diacritics with plain Latin English letters (no ā, ī, ĕ, ŏ, ṃ, ṭ, ḍ).
    2. Preserves technical words and loanwords in standard English ('open source', 'JavaScript', 'Addy Osmani').
    3. Formats postpositional case suffixes cleanly (e.g. 'open source lo', NOT 'opĕn sorslo' or 'open source low').
    4. Handles natural phonetic conversational nuances for native speakers.
    """
    if not text:
        return ""

    # 1. Strip IAST Diacritics -> Natural English Letters
    diacritics = {
        'ā': 'a', 'ī': 'i', 'ū': 'u', 'ē': 'e', 'ō': 'o', 'ĕ': 'e', 'ŏ': 'o',
        'ṃ': 'm', 'ḥ': 'h', 'ṭ': 't', 'ḍ': 'd', 'ṇ': 'n', 'ś': 'sh', 'ṣ': 'sh',
        'ṛ': 'ri', 'ṝ': 'ri', 'ḷ': 'l', 'ḹ': 'l', 'l̤': 'l', 'ñ': 'n', 'ṅ': 'n',
        'ṟ': 'r', 'ṯ': 't', 'zh': 'z'
    }
    for char, repl in diacritics.items():
        text = text.replace(char, repl)
        text = text.replace(char.upper(), repl.capitalize())

    # Indic suffix capture pattern:
    # Telugu/Kannada/Tamil/Hindi suffixes (in, to, with, from, about, for, among)
    suf = r'(lo|low|lalo|laku|lato|laki|ku|ki|to|tho|nunchi|nundi|gurinchi|kosam|ga|ni|nu|meeda|valana|valla|se|me|ko|par|keliye)?'

    def repl_tech(term):
        def _sub(m):
            suffix = m.group(1) if m.lastindex and m.lastindex >= 1 else None
            if not suffix:
                return term
            suffix = suffix.strip()
            # If suffix was transliterated as 'low' for Telugu 'లో' (lo)
            if suffix.lower() == 'low':
                suffix = 'lo'
            return f"{term} {suffix}"
        return _sub

    # 2. Technology Terms, Loanwords, and Creator Names
    tech_patterns = [
        # Open source patterns (handles opĕn sors, opensors, open source low, open sorslo)
        (r'\bop[eēĕ]n\s*sors' + suf, 'open source'),
        (r'\bopensors' + suf, 'open source'),
        (r'\bopen\s*source\s*(?:low|lo)\b', 'open source lo'),
        (r'\bj[aā]v[aā]skrip[tṭ]' + suf, 'JavaScript'),
        (r'\ba[dḍ]+[iī]\s*[uōo]sm[aā]n[iī]' + suf, 'Addy Osmani'),
        (r'\bp[aāo]d[kktṭ]+[aā]s[tṭ]' + suf, 'podcast'),
        (r'\bpul\s*rikves[tṭ]' + suf, 'pull request'),
        (r'\bgi[tṭ]\s*hab' + suf, 'GitHub'),
        (r'\bvebsai[tṭ]' + suf, 'website'),
        (r'\b[iī]m[eē]yil' + suf, 'email'),
        (r'\bs[aā]ph[tṭ]v[eē]r' + suf, 'software'),
        (r'\bh[aā]r[dḍ]v[eē]r' + suf, 'hardware'),
        (r'\b[dḍ]evalapar' + suf, 'developer'),
        (r'\bpr[aā]jek[tṭ]' + suf, 'project'),
        (r'\bkampy[uū][tṭ]ar' + suf, 'computer'),
        (r'\bin[tṭ]arnet' + suf, 'internet'),
        (r'\bbr[aā]uzar' + suf, 'browser'),
        (r'\bk[oō][dḍ]' + suf, 'code'),
        (r'\bl[aā]ibrar[iī]' + suf, 'library'),
        (r'\bphr[eē]mvark' + suf, 'framework'),
        (r'\bg[uū]gal' + suf, 'Google'),
        (r'\bby[aā]kbon' + suf, 'Backbone'),
        (r'\bj[eē]-?kveri' + suf, 'jQuery'),
        (r'\b[dḍ][oō]j[oō]' + suf, 'Dojo'),
        (r'\bp[aā]ithan' + suf, 'Python'),
        (r'\bphran[tṭ]en[dḍ]' + suf, 'frontend'),
        (r'\bby[aā]ken[dḍ]' + suf, 'backend'),
        (r'\b[eē]p[iī]ai' + suf, 'API'),
    ]

    for pat, term in tech_patterns:
        text = re.sub(pat, repl_tech(term), text, flags=re.IGNORECASE)

    # 3. Telugu-specific colloquial natural phrasing (Tanglish)
    lang_code = (lang or '').lower().strip()
    if lang_code == 'te' or any(w in text.lower() for w in ['mariyu', 'roju', 'manam', 'gurinchi', 'abbayilu', 'sahakar']):
        text = re.sub(r'\b[iI]\s+roju\b', 'ee roju', text)
        text = re.sub(r'\b[iI]\b', 'ee', text)  # 'ఈ' (this) -> 'ee'
        # Anusvara before palatal/dental -> 'nch' (e.g., 'prapancham', 'gurinchi', 'manchi')
        text = re.sub(r'mc', 'nch', text)
        text = re.sub(r'\bgurinci\b', 'gurinchi', text)
        text = re.sub(r'\bmanaṃ\b', 'manam', text)
        text = re.sub(r'\bdeveloper\s*(?:lato|tho)\b', 'developers tho', text, flags=re.IGNORECASE)
        text = re.sub(r'\babbāyilu\b', 'abbayilu', text)
        text = re.sub(r'\babbāyila\b', 'abbayila', text)

    # 4. Normalize spaces and punctuation
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def run_romanization(text: str, source_script: str = "auto", lang: str = "te") -> str:
    """
    Transliterate native Indic script text to natural, colloquial Roman English alphabet.
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
        raw_romanized = transliterate.process(detected, 'IAST', text)
        log.info(f"✔ Raw romanized {len(text)} chars from '{detected}' to IAST")
        # Apply colloquial Indic clean up (strip diacritics, restore tech terms like 'open source')
        colloquial = clean_colloquial_indic(raw_romanized, lang=lang)
        log.info(f"✔ Formatted colloquial {lang} romanization ({len(colloquial)} chars)")
        return colloquial
    except Exception as e:
        log.warning(f"Romanization from '{detected}' failed: {e}. Returning original.")
        return text

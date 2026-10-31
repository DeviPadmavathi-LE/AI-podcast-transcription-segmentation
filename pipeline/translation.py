"""
TALK2TOPICS — Translation Pipeline
Uses Argos Translate for offline, local translation.
Gracefully degrades if argostranslate is not installed.
"""

import logging

log = logging.getLogger('talk2topics.translation')

# ── Try importing argostranslate ──────────────────────────────────────
_ARGOS_AVAILABLE = False
try:
    import argostranslate.package
    import argostranslate.translate
    _ARGOS_AVAILABLE = True
    log.info("argostranslate imported successfully.")
except ImportError:
    log.warning("argostranslate is NOT installed. Translation will be unavailable.")
    log.warning("Fix: pip install argostranslate")


# ── Install en→es package on first use ───────────────────────────────
_PACKAGES_INSTALLED = False

def _ensure_packages():
    """Attempt to install the en→es language package if not present."""
    global _PACKAGES_INSTALLED
    if _PACKAGES_INSTALLED or not _ARGOS_AVAILABLE:
        return
    try:
        argostranslate.package.update_package_index()
        available = argostranslate.package.get_available_packages()
        pkg = next(
            (p for p in available if p.from_code == "en" and p.to_code == "es"),
            None
        )
        if pkg:
            argostranslate.package.install_from_path(pkg.download())
            log.info("argostranslate en→es package installed.")
        _PACKAGES_INSTALLED = True
    except Exception as e:
        log.warning(f"Could not install argostranslate packages: {e}")
        _PACKAGES_INSTALLED = True  # mark as done to avoid retrying on every call


def run_translation(text: str, target_code: str = "es") -> str:
    """
    Translate text from English to the target language code.

    Returns the original text as fallback if:
    - argostranslate is not installed
    - The language pair is not supported
    - Any runtime error occurs
    """
    if not text or not text.strip():
        return ""

    if not _ARGOS_AVAILABLE:
        log.warning("Translation skipped: argostranslate not installed.")
        return text  # graceful fallback

    _ensure_packages()

    try:
        translated = argostranslate.translate.translate(text, "en", target_code)
        return translated
    except Exception as e:
        log.warning(f"Translation to '{target_code}' failed: {e}. Returning original.")
        return text  # graceful fallback

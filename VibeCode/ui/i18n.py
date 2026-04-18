"""ui/i18n.py — Simple bilingual helper for VibeCode Tool.

Usage:
    from ui.i18n import tr, set_lang, get_lang

    set_lang("en")          # switch to English
    label = tr("儲存", "Save")  # returns "Save" when lang == "en"
"""
from __future__ import annotations

_lang: str = "zh"


def set_lang(lang: str) -> None:
    """Set current language: 'zh' (繁中) or 'en' (English)."""
    global _lang
    _lang = lang if lang in ("zh", "en") else "zh"


def get_lang() -> str:
    """Return current language code ('zh' or 'en')."""
    return _lang


def tr(zh: str, en: str) -> str:
    """Return zh or en string depending on current language."""
    return en if _lang == "en" else zh

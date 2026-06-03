"""Dịch văn bản sang tiếng Việt qua Google Translate (deep-translator).

Caching theo text gốc để tránh dịch lại các text giống nhau.
"""

from __future__ import annotations

from typing import Iterable

from deep_translator import GoogleTranslator

_TRANSLATOR = GoogleTranslator(source="auto", target="vi")
_TRANSLATION_CACHE: dict[str, str] = {}

# Ký tự tối thiểu để detect ngôn ngữ không phải Việt
_MIN_LENGTH_FOR_DETECT = 30

# Từ/dấu hiệu nhận biết văn bản đã là tiếng Việt
_VIETNAMESE_MARKERS = {
    "à", "á", "ạ", "ả", "ã", "â", "ầ", "ấ", "ậ", "ẩ", "ẫ", "ă", "ằ", "ắ",
    "ặ", "ẳ", "ẵ", "è", "é", "ẹ", "ẻ", "ẽ", "ê", "ề", "ế", "ệ", "ể", "ễ",
    "ì", "í", "ị", "ỉ", "ĩ", "ò", "ó", "ọ", "ỏ", "õ", "ô", "ồ", "ố", "ộ",
    "ổ", "ỗ", "ơ", "ờ", "ớ", "ợ", "ở", "ỡ", "ù", "ú", "ụ", "ủ", "ũ", "ư",
    "ừ", "ứ", "ự", "ử", "ữ", "ỳ", "ý", "ỵ", "ỷ", "ỹ",
    "đ",
}


def _is_likely_vietnamese(text: str) -> bool:
    """Heuristic nhanh: nếu text có chứa ký tự tiếng Việt → coi là tiếng Việt."""
    lower = text.lower()
    for char in lower:
        if char in _VIETNAMESE_MARKERS:
            return True
    return False


def translate_to_vi(text: str) -> str:
    """Dịch text sang tiếng Việt nếu có thể detect là không phải tiếng Việt."""
    if not text or not isinstance(text, str):
        return text

    stripped = text.strip()
    if not stripped:
        return text

    # Nếu text có chứa ký tự tiếng Việt → giữ nguyên
    if _is_likely_vietnamese(stripped):
        return text

    # Kiểm tra cache
    if stripped in _TRANSLATION_CACHE:
        return _TRANSLATION_CACHE[stripped]

    try:
        translated = _TRANSLATOR.translate(stripped)
        _TRANSLATION_CACHE[stripped] = translated
        return translated
    except Exception:
        # Fail silently, giữ text gốc
        return text


def translate_batch(texts: Iterable[str]) -> list[str]:
    return [translate_to_vi(t) for t in texts]


__all__ = [
    "translate_to_vi",
    "translate_batch",
]

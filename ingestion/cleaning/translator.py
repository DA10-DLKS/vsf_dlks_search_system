"""Dịch văn bản sang tiếng Việt qua Google Translate (deep-translator).

Caching theo text gốc để tránh dịch lại các text giống nhau.
Hỗ trợ batch + parallel via ThreadPoolExecutor.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Iterable

from deep_translator import GoogleTranslator

_TRANSLATION_CACHE: dict[str, str] = {}

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
    lower = text.lower()
    for char in lower:
        if char in _VIETNAMESE_MARKERS:
            return True
    return False


_NON_VN_CACHE = set()


_EXECUTOR = ThreadPoolExecutor(max_workers=1)


def _translate_one(text: str, translator: GoogleTranslator | None = None) -> str:
    if translator is None:
        translator = GoogleTranslator(source="auto", target="vi")
    try:
        fut = _EXECUTOR.submit(translator.translate, text)
        return fut.result(timeout=15)
    except Exception:
        return text


def translate_to_vi(text: str) -> str:
    if not text or not isinstance(text, str):
        return text

    stripped = text.strip()
    if not stripped:
        return text

    if _is_likely_vietnamese(stripped):
        return text

    if stripped in _TRANSLATION_CACHE:
        return _TRANSLATION_CACHE[stripped]

    try:
        t = GoogleTranslator(source="auto", target="vi")
        translated = t.translate(stripped)
        _TRANSLATION_CACHE[stripped] = translated
        return translated
    except Exception:
        return text


def translate_batch_parallel(texts: list[str], max_workers: int = 8) -> list[str]:
    """Translate multiple texts in parallel using a thread pool.

    Falls back to sequential if any text is Vietnamese or cached.
    """
    results: dict[int, str] = {}
    futures: dict = {}

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        for i, text in enumerate(texts):
            stripped = text.strip() if isinstance(text, str) else ""
            if not stripped or _is_likely_vietnamese(stripped):
                results[i] = text
                continue
            if stripped in _TRANSLATION_CACHE:
                results[i] = _TRANSLATION_CACHE[stripped]
                continue
            t = GoogleTranslator(source="auto", target="vi")
            futures[pool.submit(_translate_one, stripped, t)] = i

        for future in as_completed(futures):
            i = futures[future]
            translated = future.result()
            stripped = texts[i].strip()
            _TRANSLATION_CACHE[stripped] = translated
            results[i] = translated

    return [results[i] for i in range(len(texts))]


def translate_batch(texts: Iterable[str]) -> list[str]:
    return [translate_to_vi(t) for t in texts]


__all__ = [
    "translate_to_vi",
    "translate_batch",
    "translate_batch_parallel",
]

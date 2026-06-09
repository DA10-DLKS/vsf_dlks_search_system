"""Dịch văn bản sang tiếng Việt qua Google Translate (deep-translator).

Cách nhanh nhất: batch theo họ (CJK / non-CJK) + concatenated API call,
mỗi request ~15k chars. Cache theo text gốc để tránh dịch lại.
"""

from __future__ import annotations

import json
import random
import secrets
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from deep_translator import GoogleTranslator

_HERE = Path(__file__).resolve()
_PROJECT_ROOT = _HERE.parents[2]
_CACHE_FILE = _PROJECT_ROOT / "data" / "_translation_cache.json"


def _load_cache() -> dict[str, str]:
    if _CACHE_FILE.exists():
        try:
            data = json.loads(_CACHE_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
        except Exception:
            pass
    return {}


def _save_cache(cache: dict[str, str]) -> None:
    try:
        _CACHE_FILE.write_text(
            json.dumps(cache, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except Exception:
        pass


_TRANSLATION_CACHE: dict[str, str] = _load_cache()

_VIETNAMESE_MARKERS = (
    "àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơ"
    "ờớợởỡùúụủũưừứựửữỳýỵỷỹđ"
)
_VIETNAMESE_MARKERS_SET = frozenset(_VIETNAMESE_MARKERS)


def _is_likely_vietnamese(text: str) -> bool:
    text_lower = text.lower()
    return any(ch in _VIETNAMESE_MARKERS_SET for ch in text_lower)


_CJK_RANGES = (
    (0x4E00, 0x9FFF),
    (0x3040, 0x309F),
    (0x30A0, 0x30FF),
    (0xAC00, 0xD7AF),
)


def _detect_cjk_source(text: str) -> str | None:
    has_cjk = False
    has_hira = False
    has_kata = False
    has_hangul = False
    for ch in text:
        cp = ord(ch)
        if 0x4E00 <= cp <= 0x9FFF:
            has_cjk = True
        elif 0x3040 <= cp <= 0x309F:
            has_hira = True
        elif 0x30A0 <= cp <= 0x30FF:
            has_kata = True
        elif 0xAC00 <= cp <= 0xD7AF:
            has_hangul = True
    if has_hira or has_kata:
        return "ja"
    if has_hangul:
        return "ko"
    if has_cjk:
        return "zh-CN"
    return None


_SEPARATOR_ESTIMATE = " __||__ "
_MAX_CHARS_PER_CALL = 4500
_MAX_SINGLE_TEXT_CHARS = 4000


def _split_long_text(text: str, max_chars: int = _MAX_SINGLE_TEXT_CHARS) -> list[str]:
    if len(text) <= max_chars:
        return [text]
    parts: list[str] = []
    current = ""
    for sentence in text.replace("! ", "!\n").replace("? ", "?\n").replace(". ", ".\n").split("\n"):
        if len(current) + len(sentence) + 1 <= max_chars:
            current = (current + " " + sentence).strip() if current else sentence
        else:
            if current:
                parts.append(current)
            if len(sentence) > max_chars:
                for start in range(0, len(sentence), max_chars):
                    parts.append(sentence[start:start + max_chars])
                current = ""
            else:
                current = sentence
    if current:
        parts.append(current)
    return parts if parts else [text]


def _chunk_texts(texts: list[str]) -> list[list[str]]:
    batches: list[list[str]] = []
    current: list[str] = []
    current_len = 0
    for text in texts:
        sep_len = len(_SEPARATOR_ESTIMATE) if current else 0
        if current_len + sep_len + len(text) > _MAX_CHARS_PER_CALL and current:
            batches.append(current)
            current = []
            current_len = 0
        current.append(text)
        current_len += sep_len + len(text)
    if current:
        batches.append(current)
    return batches


def _translate_chunk(
    chunk: list[str],
    source: str | None = None,
    cache: dict[str, str] | None = None,
) -> dict[str, str]:
    cache = cache or _TRANSLATION_CACHE
    sep = f"||{secrets.token_hex(8)}||"
    joined = sep.join(chunk)
    last_exc: Exception | None = None
    for attempt in range(5):
        try:
            t = GoogleTranslator(source=source or "auto", target="vi")
            translated = t.translate(joined)
            if not translated:
                return {t: t for t in chunk}
            parts = translated.split(sep)
            result: dict[str, str] = {}
            for i, part in enumerate(parts):
                if i < len(chunk):
                    value = part.strip() if part.strip() else chunk[i]
                    result[chunk[i]] = value
                    cache[chunk[i]] = value
            if len(result) < len(chunk) * 0.5:
                raise ValueError(f"Too few parts: {len(result)}/{len(chunk)}")
            return result
        except Exception as exc:
            last_exc = exc
            if attempt < 4:
                time.sleep(min(2 ** attempt + random.random(), 10))

    # Batch failed → fallback: translate each text individually with rate limiting
    print(f"  Batch failed ({len(chunk)} texts), translating individually...", flush=True)
    result: dict[str, str] = {}
    for text in chunk:
        if text in result:
            continue
        cached = cache.get(text)
        if cached is not None:
            result[text] = cached
            continue
        for attempt in range(3):
            try:
                time.sleep(0.25 + random.random() * 0.25)
                t = GoogleTranslator(source=source or "auto", target="vi")
                tr = t.translate(text)
                value = tr.strip() if tr.strip() else text
                result[text] = value
                cache[text] = value
                break
            except Exception as exc:
                if attempt < 2:
                    time.sleep(1 + random.random())
                else:
                    print(f"    Individual failed after 3 retries: {exc}", flush=True)
                    result[text] = text
                    cache[text] = text
    return result


def translate_texts(
    texts: list[str],
    workers: int = 6,
) -> list[str]:
    if not texts:
        return []

    flat: list[str] = []
    needs_translation: list[str] = []
    for text in texts:
        stripped = (text or "").strip()
        if not stripped:
            flat.append(text)
            continue
        flat.append(stripped)
        cached = _TRANSLATION_CACHE.get(stripped)
        if cached is not None:
            continue
        if _is_likely_vietnamese(stripped):
            _TRANSLATION_CACHE[stripped] = stripped
            continue
        needs_translation.append(stripped)

    if not needs_translation:
        print(f"  All {len(flat)} texts already cached, nothing to translate", flush=True)
        _save_cache(_TRANSLATION_CACHE)
        return flat

    cjk_by_source: dict[str | None, list[str]] = {}
    for text in needs_translation:
        src = _detect_cjk_source(text)
        cjk_by_source.setdefault(src, []).append(text)

    result_map: dict[str, str] = {}

    all_batches: list[tuple[list[str], str | None]] = []
    for source, group in cjk_by_source.items():
        for batch in _chunk_texts(group):
            all_batches.append((batch, source))
    total_batches = len(all_batches)
    done_batches = 0

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(_translate_chunk, batch, source) for batch, source in all_batches]
        for future in as_completed(futures):
            result_map.update(future.result())
            done_batches += 1
            if done_batches % 50 == 0 or done_batches == total_batches:
                pct = done_batches / total_batches * 100
                print(f"  [{done_batches}/{total_batches}] {pct:.0f}%", end=" ", flush=True)

    translated: list[str] = []
    for text in flat:
        key = text.strip() if text else ""
        translated.append(_TRANSLATION_CACHE.get(key, result_map.get(key, key)))

    _save_cache(_TRANSLATION_CACHE)
    return translated


FIELDS_TO_TRANSLATE: dict[str, tuple[str, ...]] = {
    "activities": ("title", "description"),
    "reviews_detail": (),
}
REVIEW_TEXT_FIELDS = ("text", "title", "positives", "negatives", "response")


def collect_translatable(
    doc: dict[str, Any],
) -> tuple[list[tuple[Any, str]], list[str]]:
    refs: list[tuple[Any, str]] = []
    texts: list[str] = []

    for act in doc.get("activities") or []:
        if not isinstance(act, dict):
            continue
        for field in ("title", "description"):
            value = act.get(field)
            if isinstance(value, str) and value.strip():
                refs.append((act, field))
                texts.append(value.strip())

    for comment in (doc.get("reviews_detail") or {}).get("sample_comments") or []:
        if not isinstance(comment, dict):
            continue
        for field in REVIEW_TEXT_FIELDS:
            value = comment.get(field)
            if isinstance(value, str) and value.strip():
                refs.append((comment, field))
                texts.append(value.strip())

    return refs, texts


def apply_translations(
    doc: dict[str, Any],
    refs: list[tuple[Any, str]],
    translated: list[str],
) -> None:
    for (obj, key), value in zip(refs, translated):
        if isinstance(obj, dict):
            obj[key] = value


def translate_document(doc: dict[str, Any]) -> dict[str, Any]:
    refs, texts = collect_translatable(doc)
    if not refs:
        return doc
    translated = translate_texts(texts)
    apply_translations(doc, refs, translated)
    return doc


__all__ = [
    "translate_texts",
    "translate_document",
    "collect_translatable",
    "apply_translations",
    "_TRANSLATION_CACHE",
    "_is_likely_vietnamese",
]

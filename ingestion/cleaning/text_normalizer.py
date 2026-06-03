"""Chuẩn hóa văn bản tiếng Việt (Layer 2 — cleaning).

Module này chịu trách nhiệm chuẩn hóa chuỗi sau khi đã strip HTML:
- Unicode NFC normalization
- Lowercase / giữ nguyên (tùy cờ preserve_case)
- Loại bỏ whitespace thừa, ký tự điều khiển
- Chuẩn hóa dấu câu tiếng Việt
"""

from __future__ import annotations

import unicodedata
from typing import Iterable

# TODO(hieudm): Bổ sung regex / rule chuẩn hóa dấu tiếng Việt
# (ví dụ: thống nhất "òa"/"oà", "uý"/"úy") khi crawl dữ liệu thật.
# TODO(hieudm): Cân nhắc tách riêng config cho từng domain (hotel, attraction, FAQ).


def normalize_unicode(text: str, form: str = "NFC") -> str:
    """Chuẩn hóa Unicode (mặc định NFC)."""
    # TODO(hieudm): implement
    raise NotImplementedError("normalize_unicode not implemented")


def collapse_whitespace(text: str) -> str:
    """Gộp nhiều khoảng trắng / xuống dòng thành 1 space; strip đầu-cuối."""
    # TODO(hieudm): implement
    raise NotImplementedError("collapse_whitespace not implemented")


def remove_control_chars(text: str) -> str:
    """Loại bỏ ký tự điều khiển (Cc category) trừ \\n \\t hợp lệ."""
    # TODO(hieudm): implement
    raise NotImplementedError("remove_control_chars not implemented")


def normalize_punctuation(text: str) -> str:
    """Thống nhất dấu câu (',', '"', '...', dấu gạch nối, v.v.)."""
    # TODO(hieudm): implement
    raise NotImplementedError("normalize_punctuation not implemented")


def normalize_text(
    text: str,
    *,
    preserve_case: bool = True,
    strip: bool = True,
) -> str:
    """Pipeline chuẩn hóa đầy đủ.

    Thứ tự: unicode → control chars → whitespace → punctuation → (lowercase) → strip.
    """
    # TODO(hieudm): orchestrate các bước trên
    raise NotImplementedError("normalize_text not implemented")


def normalize_batch(texts: Iterable[str], **kwargs) -> list[str]:
    """Áp dụng `normalize_text` cho một batch."""
    # TODO(hieudm): implement (cân nhắc dùng pandas nếu batch lớn)
    raise NotImplementedError("normalize_batch not implemented")


__all__ = [
    "normalize_unicode",
    "collapse_whitespace",
    "remove_control_chars",
    "normalize_punctuation",
    "normalize_text",
    "normalize_batch",
]

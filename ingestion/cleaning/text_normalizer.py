"""Chuẩn hóa văn bản tiếng Việt (Layer 2 — cleaning).
"""

from __future__ import annotations

import re
import unicodedata
from typing import Iterable

_RE_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]")
_RE_MULTI_SPACE = re.compile(r"[ \t]+")
_RE_MULTI_NEWLINE = re.compile(r"\n{3,}")
_RE_LEADING_TRAILING_NL = re.compile(r"^\n+|\n+$")
_RE_EMOJI = re.compile(
    "["
    "\U0001F1E0-\U0001F1FF"  # flags
    "\U0001F300-\U0001F5FF"  # misc symbols & pictographs
    "\U0001F600-\U0001F64F"  # emoticons
    "\U0001F680-\U0001F6FF"  # transport & map
    "\U0001F700-\U0001F77F"  # alchemical
    "\U0001F780-\U0001F7FF"  # geometric shapes
    "\U0001F800-\U0001F8FF"  # supplemental arrows
    "\U0001F900-\U0001F9FF"  # supplemental symbols
    "\U0001FA00-\U0001FA6F"  # chess symbols
    "\U0001FA70-\U0001FAFF"  # symbols extended-a
    "\U00002702-\U000027B0"  # dingbats
    "\u2600-\u27BF"          # misc symbols
    "\uFE00-\uFE0F"          # variation selectors
    "\u200D"                 # zero width joiner
    "]+",
    flags=re.UNICODE,
)


def normalize_unicode(text: str, form: str = "NFC") -> str:
    return unicodedata.normalize(form, text)


def collapse_whitespace(text: str) -> str:
    text = _RE_MULTI_NEWLINE.sub("\n\n", text)
    text = _RE_MULTI_SPACE.sub(" ", text)
    text = _RE_LEADING_TRAILING_NL.sub("", text)
    return text.strip()


def remove_control_chars(text: str) -> str:
    return _RE_CONTROL.sub("", text)


def remove_emoji(text: str) -> str:
    return _RE_EMOJI.sub("", text)


def normalize_punctuation(text: str) -> str:
    text = text.replace("\u2010", "-").replace("\u2011", "-")
    text = text.replace("\u2012", "-").replace("\u2013", "-")
    text = text.replace("\u2014", "---").replace("\u2015", "---")
    text = text.replace("\u2018", "'").replace("\u2019", "'")
    text = text.replace("\u201c", '"').replace("\u201d", '"')
    text = text.replace("\u2026", "...")
    text = text.replace("\u00a0", " ")
    return text


def normalize_text(
    text: str,
    *,
    preserve_case: bool = True,
    strip: bool = True,
    remove_icons: bool = True,
) -> str:
    text = normalize_unicode(text)
    text = remove_control_chars(text)
    if remove_icons:
        text = remove_emoji(text)
    text = collapse_whitespace(text)
    text = normalize_punctuation(text)
    if not preserve_case:
        text = text.lower()
    if strip:
        text = text.strip()
    return text


def normalize_batch(texts: Iterable[str], **kwargs) -> list[str]:
    return [normalize_text(t, **kwargs) for t in texts]


__all__ = [
    "normalize_unicode",
    "collapse_whitespace",
    "remove_control_chars",
    "normalize_punctuation",
    "remove_emoji",
    "normalize_text",
    "normalize_batch",
]

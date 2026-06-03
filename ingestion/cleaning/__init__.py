"""Làm sạch văn bản (Layer 2 — cleaning)."""

from ingestion.cleaning.html_stripper import StrippedDocument, strip_html, strip_html_batch
from ingestion.cleaning.text_normalizer import (
    collapse_whitespace,
    normalize_batch,
    normalize_punctuation,
    normalize_text,
    normalize_unicode,
    remove_control_chars,
)

__all__ = [
    "StrippedDocument",
    "strip_html",
    "strip_html_batch",
    "collapse_whitespace",
    "normalize_batch",
    "normalize_punctuation",
    "normalize_text",
    "normalize_unicode",
    "remove_control_chars",
]

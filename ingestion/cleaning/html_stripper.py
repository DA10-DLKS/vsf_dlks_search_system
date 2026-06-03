"""Loại bỏ HTML, decode entity, tách văn bản thuần (Layer 2 — cleaning).

Input: HTML thô từ crawler (article, mô tả khách sạn, FAQ…).
Output: văn bản thuần + danh sách URL ảnh/link đã trích.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

# TODO(hieudm): Chọn parser (BeautifulSoup + lxml) đã có trong requirements.txt:13-15.
# TODO(hieudm): Quy ước giữ lại thẻ nào (<p>, <br>, <li>…) trước khi strip.


@dataclass
class StrippedDocument:
    """Kết quả sau khi strip HTML.

    Attributes:
        text: Văn bản thuần đã nối các block bằng newline.
        image_urls: Danh sách URL ảnh tìm được.
        links: Danh sách (anchor_text, href).
    """

    text: str
    image_urls: list[str]
    links: list[tuple[str, str]]


def strip_html(html: str) -> StrippedDocument:
    """Parse HTML và trả về text + metadata."""
    # TODO(hieudm): implement bằng BeautifulSoup
    raise NotImplementedError("strip_html not implemented")


def strip_html_batch(htmls: Iterable[str]) -> list[StrippedDocument]:
    """Áp dụng `strip_html` cho batch."""
    # TODO(hieudm): implement
    raise NotImplementedError("strip_html_batch not implemented")


__all__ = ["StrippedDocument", "strip_html", "strip_html_batch"]

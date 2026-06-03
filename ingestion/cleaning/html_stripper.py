"""Loại bỏ HTML, decode entity, tách văn bản thuần (Layer 2 — cleaning).

Input: HTML thô từ crawler (article, mô tả khách sạn…).
Output: văn bản thuần + danh sách URL ảnh/link.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

from bs4 import BeautifulSoup, Tag

_BLOCK_TAGS = {"p", "br", "li", "div", "h1", "h2", "h3", "h4", "h5", "h6", "tr", "td", "th"}
_REMOVE_TAGS = {"script", "style", "iframe", "noscript", "svg", "nav", "footer", "header"}


@dataclass
class StrippedDocument:
    text: str
    image_urls: list[str] = field(default_factory=list)
    links: list[tuple[str, str]] = field(default_factory=list)


def strip_html(html: str) -> StrippedDocument:
    soup = BeautifulSoup(html, "lxml")

    # Remove unwanted tags
    for tag in _REMOVE_TAGS:
        for el in soup.find_all(tag):
            el.decompose()

    # Extract metadata
    image_urls: list[str] = []
    for img in soup.find_all("img"):
        src = img.get("src") or img.get("data-src", "")
        if src and src.startswith("http"):
            image_urls.append(src)

    links: list[tuple[str, str]] = []
    for a in soup.find_all("a"):
        href = a.get("href", "")
        text = a.get_text(strip=True)
        if href:
            links.append((text, href))

    # Extract text with block separators
    parts: list[str] = []
    for el in soup.find_all(string=True):
        parent = el.parent
        if isinstance(parent, Tag) and parent.name in _BLOCK_TAGS:
            stripped = el.strip()
            if stripped:
                parts.append(stripped)
        else:
            stripped = el.strip()
            if stripped:
                parts.append(stripped)

    text = "\n".join(parts)

    return StrippedDocument(text=text, image_urls=image_urls, links=links)


def strip_html_batch(htmls: Iterable[str]) -> list[StrippedDocument]:
    return [strip_html(h) for h in htmls]


__all__ = ["StrippedDocument", "strip_html", "strip_html_batch"]

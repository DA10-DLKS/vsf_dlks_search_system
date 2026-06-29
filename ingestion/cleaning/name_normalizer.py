"""name_normalizer.py — Chuẩn hóa TÊN khách sạn (Layer 2 cleaning). Feedback DA09 (#1).

VẤN ĐỀ: tên crawl từ Agoda rất loạn:
  1. NGOẶC LẶP (430/520 hotel): "Tên VN (Tên EN)" — phần ngoặc là bản dịch EN, thừa khi hiển thị.
  2. ĐUÔI MARKETING sau '-' hoặc ',': "... - Đưa đón sân bay miễn phí & Tour", "... - Sea View,
     Hồ bơi vô cực, gần Bàu Trắng", "... - Managed by Flamingo". Chủ KS nhồi từ khóa vào tên.

NGUYÊN TẮC AN TOÀN (tên sai = hỏng hiển thị + search):
  - KHÔNG vứt dữ liệu: giữ `name_original` (gốc) + `name_alt` (phần ngoặc EN) làm alias search.
  - CHỈ cắt đuôi marketing khi đuôi chứa CUE RÕ RÀNG (đưa đón/tour/miễn phí/gần/cách...m/managed
    by/included/sea view...). KHÔNG cắt mọi dấu '-'/',' (vì "Resort & Spa Hạ Long" cũng có dấu,
    "Mường Thanh Sài Gòn Centre" hợp lệ). Thà GIỮ THỪA còn hơn cắt nhầm tên thật.
  - Tên sau cắt KHÔNG được rỗng/quá ngắn -> fallback giữ nguyên.

Trả dict gồm name (đã chuẩn hóa) + name_original + name_alt. clean_pipeline gắn vào doc.
"""

from __future__ import annotations

import re

# CUE marketing trong đuôi tên (đã lower, không dấu để bắt cả 2 dạng). Đuôi sau '-'/',' CHỨA cue
# này -> coi là quảng cáo, cắt. Bám sát pattern THẬT thấy trong data (khảo sát 520 hotel).
_MARKETING_CUES = [
    "dua don", "đưa đón", "tour", "mien phi", "miễn phí", "free ", "shuttle",
    "managed by", "quan ly boi", "quản lý bởi", "included", "bao gom", "bao gồm",
    "gan ", "gần ", "near ", "cach ", "cách ", " to the beach", "sea view", "city view",
    "ho boi", "hồ bơi", "infinity pool", "bedroom", "phong ngu", "phòng ngủ",
    "alacarte", "retreat", "sauna & steam",
]

# Số + đơn vị khoảng cách trong tên ("300m to the beach", "17m to ...") = marketing.
_RE_DISTANCE = re.compile(r"\b\d+\s*(m|km|mét|met)\b", re.IGNORECASE)

_RE_PARENS = re.compile(r"\s*\(([^)]*)\)\s*$")   # ngoặc Ở CUỐI tên (bản dịch EN)
_MIN_NAME_LEN = 4                                 # tên sau cắt ngắn hơn -> không tin, giữ nguyên


def _has_marketing_cue(segment: str) -> bool:
    seg = segment.lower()
    if _RE_DISTANCE.search(seg):
        return True
    return any(cue in seg for cue in _MARKETING_CUES)


def _strip_marketing_tail(name: str) -> str:
    """Cắt đuôi marketing sau dấu '-' hoặc ',' nếu đuôi chứa cue. CHỈ cắt đuôi (giữ phần đầu =
    tên chính). Lặp để cắt nhiều đuôi ("Tên - Sea View, gần X" -> cắt cả 2). An toàn: phần giữ
    lại phải đủ dài, nếu không -> trả nguyên."""
    cur = name
    # tách theo dấu phân cách CUỐI cùng, xét đuôi; lặp tối đa vài lần
    for _ in range(4):
        m = re.search(r"^(.*?)\s*[-,]\s*([^-,]+)$", cur)
        if not m:
            break
        head, tail = m.group(1).strip(), m.group(2).strip()
        if _has_marketing_cue(tail) and len(head) >= _MIN_NAME_LEN:
            cur = head
        else:
            break
    return cur


def normalize_hotel_name(raw_name: str | None) -> dict[str, str | None]:
    """Chuẩn hóa 1 tên KS. Trả {name, name_original, name_alt}.

    name          = tên chính đã làm sạch (bỏ ngoặc EN cuối + đuôi marketing).
    name_original = tên gốc nguyên văn (audit / fallback).
    name_alt      = phần trong ngoặc EN (alias search; None nếu không có).
    """
    if not raw_name or not str(raw_name).strip():
        return {"name": raw_name, "name_original": raw_name, "name_alt": None}

    original = str(raw_name).strip()
    name = original
    name_alt = None

    # 1) tách ngoặc EN ở CUỐI ("Tên VN (Tên EN)")
    m = _RE_PARENS.search(name)
    if m:
        inside = m.group(1).strip()
        candidate = name[: m.start()].strip()
        if len(candidate) >= _MIN_NAME_LEN:
            name = candidate
            name_alt = inside or None

    # 2) cắt đuôi marketing (trên CẢ name và name_alt nếu có)
    name = _strip_marketing_tail(name)
    if name_alt:
        name_alt = _strip_marketing_tail(name_alt)

    # 3) an toàn: name rỗng/ngắn bất thường -> fallback nguyên gốc
    if not name or len(name) < _MIN_NAME_LEN:
        name = original
        name_alt = None

    return {"name": name, "name_original": original, "name_alt": name_alt}


__all__ = ["normalize_hotel_name"]

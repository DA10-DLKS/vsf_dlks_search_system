"""query_negation.py — phát hiện PHỦ ĐỊNH trong câu hỏi (negation phía QUERY).

VẤN ĐỀ: parser hiện chỉ bắt concept "có gì" (khẳng định). Câu thật hay nêu điều KHÔNG muốn:
    "khách sạn KHÔNG sát mặt đường lớn"        -> loại SETTING gần đường
    "resort KHÔNG có trẻ em ồn ào"             -> KHÔNG phải PURPOSE_FAMILY
    "hồ bơi nhưng KHÔNG phải hồ bơi chung"     -> vẫn muốn hồ bơi (giữ), chỉ chê 'chung'
Nếu bỏ qua "không", parser hiểu NGƯỢC ý (lọc đúng cái user từ chối).

KHÁC với negative_style_profile trong build_objects (đó là phía DATA: hotel BỊ REVIEW CHÊ cùng
STYLE). Đây là phía QUERY: chính người dùng NÓI không muốn.

THIẾT KẾ: tách câu thành các SPAN phủ định (từ cue "không/tránh/đừng..." tới ranh giới mệnh đề
kế tiếp), chạy bộ tra concept của intent_parser TRÊN RIÊNG span đó. Concept tìm được trong span
phủ định -> đưa vào exclude_concepts. NGUYÊN TẮC AN TOÀN: concept nào CŨNG xuất hiện ở phần
KHẲNG ĐỊNH (ngoài span phủ định) thì KHÔNG exclude — tránh "có hồ bơi nhưng không phải hồ bơi
chung" lỡ loại luôn AMEN_POOL mà user đang muốn.
"""

from __future__ import annotations

import re

from knowledge_engineering.common.normalize import normalize

# Cue phủ định. Đặt "không phải"/"không có" trước "không" để regex ưu tiên cụm dài.
_NEG_CUES = r"(?:không phải|không có|ko phải|chẳng có|đừng|tránh|no |không|ko)"
# Ranh giới kết thúc span phủ định: dấu câu, liên từ chuyển mệnh đề. Span phủ định kéo từ sau
# cue tới ranh giới gần nhất (hoặc hết câu). Giữ ngắn để không nuốt cả vế khẳng định kế tiếp.
_CLAUSE_BOUNDARY = re.compile(r"[,.;]|(?:\bvà\b|\bvới\b|\bcòn\b|\bnhưng\b|\bmà\b)")

_NEG_SPAN_RE = re.compile(_NEG_CUES + r"\s+(.*?)(?=" + _CLAUSE_BOUNDARY.pattern + r"|$)", re.IGNORECASE)


def negation_spans(q: str) -> list[str]:
    """Trả các đoạn text NẰM SAU cue phủ định (tới ranh giới mệnh đề). Dùng câu gốc (chưa fold)
    để giữ dấu cho bộ tra concept. Bỏ span quá ngắn (<3 ký tự, nhiễu)."""
    out: list[str] = []
    for m in _NEG_SPAN_RE.finditer(q):
        span = m.group(1).strip()
        if len(span) >= 3:
            out.append(span)
    return out


def parse_negated_concepts(q: str, lookup, positive_concepts: set[str]) -> set[str]:
    """Concept người dùng KHÔNG muốn (exclude_concepts).

    lookup: callable(text) -> set[concept_id] (truyền _lookup_concepts đã bind syn+max_gram từ
            intent_parser, để 1 nguồn surface form duy nhất, không lặp logic).
    positive_concepts: concept đã parse ở phần khẳng định của câu. Concept vừa xuất hiện ở span
            phủ định VỪA ở positive -> KHÔNG exclude (user muốn nó, chỉ chê thuộc tính phụ).
    """
    negated: set[str] = set()
    for span in negation_spans(q):
        negated |= lookup(span)
    # Giữ lại concept cũng có ở vế khẳng định (vd "có hồ bơi nhưng không phải hồ bơi chung").
    return negated - positive_concepts

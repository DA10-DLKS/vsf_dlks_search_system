"""Chuẩn hóa danh sách tiện ích (amenities) — Layer 2 cleaning.

Xử lý:
1. Loại bỏ nội dung trong [...] và (...)
2. Chuẩn hóa Unicode/thin space/ký tự đặc biệt
3. Loại bỏ hậu tố thừa (ở nơi công cộng, trong tất cả các phòng…)
4. Gom nhóm các amenity tương tự bằng fuzzy matching
5. Mapping canonical cho các amenity đặc thù
"""

from __future__ import annotations

import re
import unicodedata
from difflib import SequenceMatcher
from typing import Sequence

from ingestion.cleaning.text_normalizer import normalize_text

# Regex patterns
_RE_BRACKETS = re.compile(r"\[|\]")
_RE_PARENS = re.compile(r"\(|\)")
_RE_THIN_SPACE = re.compile(r"[\u2000-\u200a]")
_RE_SPECIAL_CHARS = re.compile(r"[!@#$%^&*_+=<>:;/\"'~`]+")

# Amenity cơ bản — khách sạn nào cũng có, không giúp phân biệt → loại bỏ
_BASIC_AMENITIES: list[re.Pattern] = [
    re.compile(r"^máy sấy tóc$", re.IGNORECASE),
    re.compile(r"^két sắt", re.IGNORECASE),
    re.compile(r"^bình chữa cháy$", re.IGNORECASE),
    re.compile(r"^cân$", re.IGNORECASE),
    re.compile(r"^gương$", re.IGNORECASE),
    re.compile(r"^nước rửa tay$", re.IGNORECASE),
    re.compile(r"^tủ có khoá$|^tủ có khóa$", re.IGNORECASE),
    re.compile(r"^tủ quần áo$", re.IGNORECASE),
    re.compile(r"^giá treo quần áo$", re.IGNORECASE),
    re.compile(r"^vật dụng tắm rửa$", re.IGNORECASE),
    re.compile(r"^các loại khăn$", re.IGNORECASE),
    re.compile(r"^vải trải giường$", re.IGNORECASE),
    re.compile(r"^dép đi trong nhà$", re.IGNORECASE),
    re.compile(r"^quần áo ngủ$", re.IGNORECASE),
    re.compile(r"^vòi sen$", re.IGNORECASE),
    re.compile(r"^bồn tắm$", re.IGNORECASE),
    re.compile(r"^bồn tắm vòi sen riêng$", re.IGNORECASE),
    re.compile(r"^phòng tắm riêng$", re.IGNORECASE),
    re.compile(r"^áo choàng tắm$", re.IGNORECASE),
    re.compile(r"^đầu báo khói$", re.IGNORECASE),
    re.compile(r"^thiết bị báo cháy$", re.IGNORECASE),
    re.compile(r"^bộ dụng cụ sơ cứu$", re.IGNORECASE),
    re.compile(r"^thùng rác$", re.IGNORECASE),
    re.compile(r"^quạt$", re.IGNORECASE),
    re.compile(r"^ấm nước$|^ấm nước điện$", re.IGNORECASE),
    re.compile(r"^bàn làm việc$", re.IGNORECASE),
    re.compile(r"^rèm che ánh sáng$", re.IGNORECASE),
    re.compile(r"^cửa sổ$", re.IGNORECASE),
    re.compile(r"^điện thoại$", re.IGNORECASE),
    re.compile(r"^đồng hồ báo thức$", re.IGNORECASE),
    re.compile(r"^dịch vụ báo thức$", re.IGNORECASE),
    re.compile(r"^ghế sofa$", re.IGNORECASE),
    re.compile(r"^thảm$", re.IGNORECASE),
    re.compile(r"^tủ lạnh nhỏ", re.IGNORECASE),
    re.compile(r"^ổ cắm điện", re.IGNORECASE),
    re.compile(r"^nước đóng chai", re.IGNORECASE),
    re.compile(r"^trà miễn phí$", re.IGNORECASE),
    re.compile(r"^cà phê hòa tan miễn phí$", re.IGNORECASE),
    re.compile(r"^tiện nghi$", re.IGNORECASE),
    re.compile(r"^tiện nghi là ủi$|^tiện nghi là/ủi$", re.IGNORECASE),
    re.compile(r"^tivi$|^ti vi$", re.IGNORECASE),
]

# Hậu tố thừa (chỉ giữ lại các pattern rõ ràng là verbose, không phải nội dung từ bracket)
_SUFFIX_REMOVE: list[tuple[str, str]] = [
    (r"\s+ở nơi công cộng", ""),
    (r"\s+trong tất cả các phòng!?", ""),
    (r"\s+trong tất cả các phòng nghỉ", ""),
    (r"\s+trong khuôn viên", ""),
    (r"\s+trong vòng \d+ km", ""),
    (r"\s+-\s+không dây", ""),
    (r"\s+-\s+mạng LAN", ""),
    (r"\s+phục vụ bữa sáng", " bữa sáng"),
]

# Mapping canonical: (pattern_regex, canonical_name)
_CANONICAL_MAP: list[tuple[re.Pattern, str]] = [
    (re.compile(r"^wifi|^wi.?fi|^internet|^dịch vụ internet|^truy cập internet", re.IGNORECASE), "WiFi"),
    (re.compile(r"^bãi đỗ xe|^đỗ xe", re.IGNORECASE), "Đỗ xe"),
    (re.compile(r"^thuê xe đạp", re.IGNORECASE), "Thuê xe đạp"),
    (re.compile(r"^bãi đỗ xe đạp", re.IGNORECASE), "Đỗ xe đạp"),
    (re.compile(r"^bữa sáng|^bữa ăn sáng", re.IGNORECASE), "Bữa sáng"),
    (re.compile(r"^bể bơi|^bể bơi|^hồ bơi", re.IGNORECASE), "Bể bơi"),
    (re.compile(r"^bồn tắm", re.IGNORECASE), "Bồn tắm"),
    (re.compile(r"^bàn tiếp tân", re.IGNORECASE), "Bàn tiếp tân"),
    (re.compile(r"^bảo vệ", re.IGNORECASE), "Bảo vệ"),
    (re.compile(r"^nhận phòng|^nhận/trả phòng", re.IGNORECASE), "Nhận/trả phòng"),
    (re.compile(r"^cà phê", re.IGNORECASE), "Cà phê"),
    (re.compile(r"^trà", re.IGNORECASE), "Trà"),
    (re.compile(r"^sân gôn|^sân golf", re.IGNORECASE), "Sân gôn"),
    (re.compile(r"^phòng họp|^phòng tổ chức họp", re.IGNORECASE), "Phòng họp"),
    (re.compile(r"^máy lạnh|^điều hòa|^máy điều hòa", re.IGNORECASE), "Điều hòa"),
    (re.compile(r"^nhà hàng", re.IGNORECASE), "Nhà hàng"),
    (re.compile(r"^quán bar|^bar", re.IGNORECASE), "Quán bar"),
    (re.compile(r"^spa", re.IGNORECASE), "Spa"),
    (re.compile(r"^phòng tập|^gym|^phòng gym", re.IGNORECASE), "Phòng tập"),
    (re.compile(r"^bãi biển", re.IGNORECASE), "Bãi biển"),
    (re.compile(r"^sân chơi", re.IGNORECASE), "Sân chơi"),
    (re.compile(r"^cctv", re.IGNORECASE), "CCTV"),
    (re.compile(r"^clb", re.IGNORECASE), "CLB"),
    (re.compile(r"^tiếng anh", re.IGNORECASE), "Tiếng Anh"),
    (re.compile(r"^tiếng việt|^tieng viet", re.IGNORECASE), "Tiếng Việt"),
    (re.compile(r"^trung quốc|^tiếng trung", re.IGNORECASE), "Trung Quốc"),
    (re.compile(r"^tiếng nga", re.IGNORECASE), "Tiếng Nga"),
    (re.compile(r"^tv|^tivi|^ti vi", re.IGNORECASE), "TV"),
]


def _clean_amenity_text(text: str) -> str:
    """Làm sạch 1 amenity: strip brackets, normalize, loại hậu tố."""
    t = text

    # Remove bracket/paren characters, keep content
    t = _RE_BRACKETS.sub("", t)
    t = _RE_PARENS.sub("", t)

    # Remove thin spaces (Unicode \u2009 etc.)
    t = _RE_THIN_SPACE.sub(" ", t)

    # Normalize Unicode and whitespace
    t = normalize_text(t, preserve_case=False)

    # Remove special chars (but keep tiếng Việt letters)
    t = _RE_SPECIAL_CHARS.sub(" ", t)

    # Apply suffix removal patterns
    for pattern, replacement in _SUFFIX_REMOVE:
        t = re.sub(pattern, replacement, t, flags=re.IGNORECASE)

    # Collapse multiple spaces again
    t = re.sub(r"\s+", " ", t).strip()

    # Dedup repeated words (vd: "sàn gỗ gỗ miếng" → "sàn gỗ miếng")
    words = t.split()
    deduped = []
    for w in words:
        if not deduped or w != deduped[-1]:
            deduped.append(w)
    t = " ".join(deduped)

    return t


def _fuzzy_similarity(a: str, b: str) -> float:
    """Tính similarity ratio giữa 2 amenity strings."""
    return SequenceMatcher(None, a, b).ratio()


def _merge_cluster(items: list[str], canonical: str | None = None) -> str:
    """Chọn canonical form cho 1 cluster amenity.

    Rules:
    1. Nếu có canonical mapping → dùng canonical (giữ "miễn phí" nếu cluster có)
    2. Nếu không → chọn item ngắn nhất, ưu tiên item có "miễn phí"
    """
    has_free = any("miễn phí" in it for it in items)
    if canonical:
        if has_free and "miễn phí" not in canonical:
            return canonical + " miễn phí"
        return canonical

    # Sort by length (shortest first), ưu tiên item có "miễn phí"
    sorted_items = sorted(set(items), key=lambda x: (0 if "miễn phí" in x else 1, len(x), x))
    chosen = sorted_items[0]

    # Title-case the first letter (giữ nguyên phần còn lại)
    if chosen and chosen[0].islower():
        chosen = chosen[0].upper() + chosen[1:]

    return chosen


def _is_basic_amenity(text: str) -> bool:
    """Kiểm tra nếu amenity là đồ cơ bản, không có giá trị phân biệt."""
    for pattern in _BASIC_AMENITIES:
        if pattern.search(text):
            return True
    return False


def _remove_generic_subsets(items: list[str]) -> list[str]:
    """Loại bỏ amenity generic nếu có phiên bản chi tiết hơn.

    Ví dụ: 'WiFi' bị loại nếu đã có 'WiFi miễn phí' hoặc 'WiFi có dây'.
    Chỉ áp dụng với các base term đã biết tránh false positive.
    """
    base_terms: dict[str, str] = {
        "wifi": "wifi",
        "internet": "internet",
        "bữa sáng": "bữa sáng",
        "nhà hàng": "nhà hàng",
        "quán bar": "quán bar",
        "spa": "spa",
        "bể bơi": "bể bơi",
        "đỗ xe": "đỗ xe",
        "bãi đỗ xe": "bãi đỗ xe",
        "cửa hàng": "cửa hàng",
        "sân hiên": "sân hiên",
        "tv": "TV",
    }

    lowered_map: dict[str, str] = {a.lower(): a for a in items}
    result: list[str] = []

    for a in items:
        al = a.lower()
        # Check if this amenity is a known base term AND a more specific version exists
        if al in base_terms:
            # Does any OTHER item start with this same base + extra content?
            has_specific = any(
                other != a and other.lower().startswith(al + " ")
                for other in items
            )
            if has_specific:
                continue  # skip generic version
        result.append(a)

    return result


def normalize_amenities(
    amenities: Sequence[str],
    *,
    merge_similar: bool = True,
    similarity_threshold: float = 0.80,
) -> list[str]:
    """Chuẩn hóa + dedup danh sách amenities.

    Args:
        amenities: Danh sách amenity gốc.
        merge_similar: Có gom nhóm fuzzy không.
        similarity_threshold: Ngưỡng similarity để merge (0-1).

    Returns:
        Danh sách amenity đã chuẩn hóa, dedup, sắp xếp theo alphabet.
    """
    # Phase 1: clean từng item
    cleaned: list[str] = []
    raw_to_cleaned: dict[str, str] = {}
    for a in amenities:
        if not a or not a.strip():
            continue
        c = _clean_amenity_text(a)
        if not c:
            continue
        cleaned.append(c)
        raw_to_cleaned[a] = c

    if not merge_similar:
        # Chỉ dedup đơn giản
        return sorted(set(cleaned))

    # Phase 2: gom nhóm bằng canonical mapping
    groups: list[list[str]] = []
    assigned: set[int] = set()

    for i, c in enumerate(cleaned):
        if i in assigned:
            continue
        group: list[str] = [c]
        assigned.add(i)

        # Check canonical map — replace only matched prefix, keep qualifiers
        canonical_result = None
        for pattern, name in _CANONICAL_MAP:
            m = pattern.match(c)
            if m:
                rest = c[m.end():]
                canonical_result = name + (" " + rest.strip() if rest.strip() else "")
                break

        for j, d in enumerate(cleaned):
            if j in assigned:
                continue
            # Use token overlap + fuzzy similarity
            if _fuzzy_similarity(c, d) >= similarity_threshold:
                group.append(d)
                assigned.add(j)

        groups.append((group, canonical_result))

    # Phase 3: chọn canonical form cho mỗi nhóm
    result: list[str] = []
    for group_items, canonical_name in groups:
        merged = _merge_cluster(group_items, canonical_name)
        # Loại bỏ amenity cơ bản (không giúp phân biệt khách sạn)
        if not _is_basic_amenity(merged):
            result.append(merged)

    # Phase 4: loại bỏ generic amenity nếu đã có phiên bản chi tiết
    result = _remove_generic_subsets(result)

    return sorted(set(result))


def normalize_amenities_batch(
    docs: Sequence[dict],
    *,
    field: str = "amenities",
    inplace: bool = True,
) -> list[dict] | None:
    """Apply normalize_amenities cho toàn bộ batch documents.

    Args:
        docs: Danh sách document.
        field: Tên field chứa amenities list.
        inplace: True = sửa trực tiếp, False = trả về copy.

    Returns:
        Nếu inplace=False, trả về list document mới.
    """
    if not inplace:
        docs = [dict(d) for d in docs]

    for doc in docs:
        amenities = doc.get(field)
        if isinstance(amenities, list):
            doc[field] = normalize_amenities(amenities)

        # Also clean amenity_groups if present
        groups = doc.get("amenity_groups")
        if isinstance(groups, dict):
            for group_name, items in groups.items():
                if isinstance(items, list):
                    groups[group_name] = normalize_amenities(items)

    return None if inplace else docs


__all__ = [
    "normalize_amenities",
    "normalize_amenities_batch",
    "_clean_amenity_text",
    "_fuzzy_similarity",
]

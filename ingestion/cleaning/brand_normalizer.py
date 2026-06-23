"""brand_normalizer.py — Trích THƯƠNG HIỆU (chuỗi khách sạn) từ tên KS. Feedback: query brand.

VẤN ĐỀ: user hỏi "khách sạn THUỘC Vinpearl ở Phú Quốc" — "Vinpearl" là BRAND (chuỗi KS), không
phải concept/location/landmark. Trước đây bị bỏ rơi khi parse. Brand ẩn trong TÊN (25 hotel
Vinpearl, 36 Mường Thanh...), KHÔNG có field riêng.

CÁCH: brand là tên riêng thương mại, tập HỮU HẠN (vài chục chuỗi lớn ở VN) -> KHÔNG đưa vào
ontology (ontology = khái niệm chung; brand mở rộng vô hạn, không mang ngữ nghĩa du lịch). Trích
thành FIELD `brand` ở cleaning -> filter cứng được + index BM25. Giống name_alt: metadata mới.

Khớp theo BẢNG brand (canonical) + biến thể (có/không dấu, EN/VN). Quét trên name + name_alt.
Trả brand canonical (1 chuỗi) hoặc None. Không match -> None (KHÔNG đoán bừa).
"""

from __future__ import annotations

import re

# Bảng brand: canonical -> các biến thể (lower) để khớp. Canonical là dạng hiển thị/filter.
# Chỉ brand THỰC SỰ là chuỗi KS có >=2 hotel trong corpus (khảo sát). Sub-brand giữ riêng nếu
# user hay gọi tên đó (Sheraton/Four Points/Pullman... — khách hỏi đích danh, không hỏi tập đoàn mẹ).
_BRANDS: dict[str, list[str]] = {
    "Vinpearl": ["vinpearl"],
    "Mường Thanh": ["mường thanh", "muong thanh"],
    "FLC": ["flc"],
    "Hilton": ["hilton"],            # gồm "Tru by Hilton" (sub-brand Hilton)
    "Sheraton": ["sheraton"],
    "Four Points": ["four points"],
    "Marriott": ["marriott"],
    "Mercure": ["mercure"],          # "Grand Mercure" cũng khớp "mercure"
    "Novotel": ["novotel"],
    "Pullman": ["pullman"],
    "Ibis": ["ibis"],
    "Sofitel": ["sofitel"],
    "Meliá": ["meliá", "melia"],
    "Wyndham": ["wyndham"],
    "Radisson": ["radisson"],
    "TTC": ["ttc"],
    "Fusion": ["fusion"],
    "Sojo": ["sojo"],
}

# build index biến thể -> canonical, ưu tiên biến thể DÀI trước (tránh "melia" nuốt "amelia"...).
_VARIANT_INDEX: list[tuple[str, str]] = sorted(
    ((v, canon) for canon, vs in _BRANDS.items() for v in vs),
    key=lambda x: -len(x[0]),
)


def extract_brand(name: str | None, name_alt: str | None = None) -> str | None:
    """Trả brand canonical nếu tên KS thuộc 1 chuỗi đã biết, ngược lại None.

    Khớp theo WORD-BOUNDARY để tránh false match (vd 'ibis' ⊄ 'hibiscus'). Quét cả name + name_alt
    (tên EN có thể chứa brand rõ hơn). KHÔNG đoán brand lạ — chỉ nhận brand trong bảng."""
    blob = " ".join(x for x in (name, name_alt) if x).lower()
    if not blob:
        return None
    for variant, canon in _VARIANT_INDEX:
        # word-boundary 2 đầu (variant có thể chứa khoảng trắng -> \b vẫn đúng ở mép từ)
        if re.search(rf"(?<![a-zà-ỹ]){re.escape(variant)}(?![a-zà-ỹ])", blob):
            return canon
    return None


__all__ = ["extract_brand"]

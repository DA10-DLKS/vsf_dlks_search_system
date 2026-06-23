"""amenity_miner.py — Đào tiện ích ỨNG VIÊN từ trường `amenities` (Sprint 2+, bịt lỗ "rớt im lặng").

Owner: Trương Anh Long (KE, DA10).

VẤN ĐỀ ĐÓNG: ontology_mapper map amenity bằng BẢNG TAY khớp-chuỗi-chính-xác
(ontology/source_tag_map.yaml > amenities). Chuỗi amenity nào KHÔNG có trong bảng -> rớt LẶNG LẼ:
không log, không hàng đợi, không ai biết để thêm. Khách sạn mới có tiện ích MỚI đáng giá (vd
"Tiện nghi bbq", "Bể bơi nước mặn") biến mất cho tới khi tình cờ phát hiện.

CÁCH LÀM (song song candidate_mining.py — nhưng nguồn = trường amenities, KHÔNG phải review):
  - Quét `amenities` + `amenity_groups[*]` của TOÀN corpus data/cleaned.
  - Bỏ chuỗi ĐÃ map (có trong source_tag_map > amenities).
  - Bỏ chuỗi ĐÃ DUYỆT-LOẠI/HOÃN: source_tag_map > _unmapped.amenities_reject / amenities_defer
    + khớp _skip.groups (ngôn ngữ/khoảng cách/vệ sinh tạm thời/lễ tân chung...). KHÔNG đẩy lại
    rác người duyệt đã gạt — nếu không hàng đợi đầy nhiễu lặp.
  - Lọc TRẦN IDF: chuỗi quá phổ biến (> max_hotel_ratio corpus) = dịch vụ vận hành ai cũng có
    ("Bàn tiếp tân 24 giờ" 1171 hotel) -> không phân biệt -> loại. SÀN support: phải đủ hotel.
  - Xếp theo rank_score = freq * log(N/hotel_count): tiện ích ĐẶC TRƯNG (ít hotel, nhắc nhiều)
    nổi lên đầu cho người duyệt.

ĐẦU RA: merge candidate vào ontology/candidate/candidate_queue.yaml (1 NGUỒN DUYỆT — chung với
candidate từ review, đúng quyết định 2026-06-10). Idempotent theo candidate_keyword: chạy lại
KHÔNG nhân bản; chỉ THÊM cái mới, KHÔNG đụng candidate cũ / status người duyệt đã đặt.
Người duyệt đặt status=approved + suggested_concept_id rồi promote_candidate.py đẩy lên core.

Chạy:
  # xem candidate sẽ thêm (KHÔNG ghi):
  .venv/Scripts/python.exe -X utf8 -m knowledge_engineering.enrichment.amenity_miner --dry-run
  # ghi (merge vào candidate_queue.yaml):
  .venv/Scripts/python.exe -X utf8 -m knowledge_engineering.enrichment.amenity_miner --apply
"""

from __future__ import annotations

import argparse
import glob
import json
import math
import re
from collections import defaultdict
from pathlib import Path

import yaml

HOTELS_GLOB = "data/cleaned/hotel_*.json"
SOURCE_TAG_MAP = "ontology/source_tag_map.yaml"
QUEUE = "ontology/candidate/candidate_queue.yaml"

# Lọc support (giữ rộng — KHÔNG cắt mất tiện ích thật, để người duyệt quyết).
MIN_FREQ = 5            # tổng số hotel nhắc tới chuỗi (amenity là per-hotel nên freq≈hotel_count)
MIN_HOTELS = 5
MAX_HOTEL_RATIO = 0.40  # TRẦN IDF: > 40% corpus = dịch vụ vận hành phổ thông -> loại
TOP = 500               # giữ rộng đuôi hiếm; người duyệt lướt từ trên (đặc trưng) xuống


def _norm(s: str) -> str:
    """So khớp lỏng: lower + gộp khoảng trắng. Dùng để đối chiếu chuỗi amenity giữa data và bảng
    map/reject (tránh lệch do hoa-thường / thừa space). KHÔNG bỏ dấu — amenity VN cần giữ dấu."""
    return re.sub(r"\s+", " ", str(s).strip().lower())


def load_source_tag_map(path: str = SOURCE_TAG_MAP) -> dict:
    return yaml.safe_load(open(path, encoding="utf-8")) or {}


def build_blocklist(stmap: dict) -> tuple[set[str], list[re.Pattern]]:
    """Trả (chuỗi đã-xử-lý cần bỏ [norm], regex pattern _skip cần bỏ).

    Đã-xử-lý = đã map (amenities) + đã reject + đã defer. Không đẩy lại cái người duyệt đã thấy.
    """
    blocked: set[str] = set()
    for v in (stmap.get("amenities") or {}):
        blocked.add(_norm(v))
    um = stmap.get("_unmapped") or {}
    for key in ("amenities_reject", "amenities_defer"):
        for x in um.get(key) or []:
            val = x.get("value") if isinstance(x, dict) else x
            if val:
                blocked.add(_norm(val))

    # _skip.groups: mô tả NHÓM cần bỏ. Mô tả là văn xuôi cho người đọc, KHÔNG phải regex chạy
    # được. Ta chuyển các nhóm đó thành pattern lọc tương ứng. Đây là RÁC VẬN HÀNH (vệ sinh tạm
    # thời/lễ tân/an ninh chung/thuộc tính phòng vụn vặt) — phổ biến nhưng < trần IDF nên IDF
    # KHÔNG chặn được; phải lọc theo nội dung. Bám sát lý do từng nhóm trong source_tag_map.
    skip_patterns = [
        # ngôn ngữ nhân viên — không phải tiện ích lọc
        re.compile(r"^tiếng\s", re.IGNORECASE),
        re.compile(r"quan thoại|quảng đông", re.IGNORECASE),
        # khoảng cách -> range_filters/nearby
        re.compile(r"\bcách\b.*\b(mét|met|km|cây số)\b", re.IGNORECASE),
        # location, không phải amenity
        re.compile(r"^tọa lạc tại trung tâm", re.IGNORECASE),
        # vệ sinh / an toàn COVID tạm thời (nhóm "an toàn COVID / khử trùng / khẩu trang")
        re.compile(r"khử trùng|khẩu trang|giãn cách|chống virus|niêm phong|không tiếp xúc"
                   r"|vệ sinh giữa|chứng nhận vệ sinh|đeo khẩu trang|nhiệt kế|sát khuẩn"
                   r"|màn bảo vệ|không khử trùng|làm sạch|che mặt|hướng dẫn về y tế"
                   r"|của agoda", re.IGNORECASE),
        # dịch vụ hành chính / lễ tân chung (nhóm "dịch vụ hành chính / lễ tân chung")
        re.compile(r"bưu chính|đổi (tiền|ngoại tệ)|cung cấp hóa đơn|giữ hành lý|rút tiền"
                   r"|dịch vụ vé|văn phòng phẩm|dịch vụ photo|thủ tục", re.IGNORECASE),
        # an ninh chung (nhóm "an ninh chung")
        re.compile(r"\bcctv\b|bảo vệ 24|an ninh|báo cháy|bình chữa cháy", re.IGNORECASE),
        # thuộc tính phòng / vật dụng vụn vặt (nhóm "vật dụng phòng vụn vặt" + "không hút thuốc")
        re.compile(r"không hút thuốc|hút thuốc|có gương|đèn đọc|bộ kim chỉ|móc treo"
                   r"|ổ điện|ổ cắm|gia vị", re.IGNORECASE),
    ]
    return blocked, skip_patterns


def mine(hotels_glob: str = HOTELS_GLOB, stmap: dict | None = None) -> dict:
    """Đếm chuỗi amenity CHƯA xử lý -> rows candidate đã lọc + xếp hạng. Trả dict thống kê."""
    stmap = stmap or load_source_tag_map()
    blocked, skip_patterns = build_blocklist(stmap)

    freq: dict[str, int] = defaultdict(int)        # chuỗi GỐC (norm) -> số hotel
    display: dict[str, str] = {}                    # norm -> 1 dạng hiển thị gốc (giữ hoa/dấu)
    hotels: dict[str, set] = defaultdict(set)
    n_hotels = 0

    def is_blocked(norm_v: str, raw_v: str) -> bool:
        if norm_v in blocked:
            return True
        return any(p.search(raw_v) for p in skip_patterns)

    for f in sorted(glob.glob(hotels_glob)):
        d = json.load(open(f, encoding="utf-8"))
        hid = d.get("hotel_id")
        n_hotels += 1
        vals = list(d.get("amenities") or [])
        for group in (d.get("amenity_groups") or {}).values():
            vals.extend(group or [])
        # amenity là per-hotel: mỗi chuỗi đếm 1 lần / hotel (set khử trùng trong cùng hotel)
        seen_this_hotel: set[str] = set()
        for v in vals:
            if not isinstance(v, str) or not v.strip():
                continue
            nv = _norm(v)
            if len(nv) < 3 or is_blocked(nv, v):
                continue
            if nv in seen_this_hotel:
                continue
            seen_this_hotel.add(nv)
            freq[nv] += 1
            display.setdefault(nv, v.strip())
            if hid is not None:
                hotels[nv].add(hid)

    n_all = max(1, n_hotels)
    max_hotels = int(n_all * MAX_HOTEL_RATIO)
    rows = []
    n_too_common = 0
    for nv, f in freq.items():
        nh = len(hotels.get(nv, ()))
        if nh > max_hotels:                  # TRẦN IDF: quá phổ biến -> dịch vụ vận hành, loại
            n_too_common += 1
            continue
        if f < MIN_FREQ or nh < MIN_HOTELS:  # SÀN support
            continue
        # rank theo IDF thuần = log(N/nh). KHÁC candidate_mining (review): ở đó freq (số LẦN nhắc)
        # ≠ hotel_count nên TF-IDF có nghĩa. Amenity đếm 1 lần/hotel -> freq≈hotel_count -> freq*IDF
        # hóa ra TĂNG theo độ phổ biến (đẩy rác phổ thông lên đầu). Tiện ích ĐẶC TRƯNG = HIẾM (ít
        # hotel) -> IDF cao -> nổi lên. Cái phổ biến (nhưng < trần) chìm xuống cuối.
        rank_score = round(math.log(n_all / nh), 3)
        rows.append({
            "candidate_keyword": display[nv],
            "suggested_facet": "amenity",
            "suggested_concept_id": "",      # người duyệt điền (vd AMEN_BBQ)
            "frequency": f,
            "hotel_count": nh,
            "rank_score": rank_score,
            # hotels: để promote_candidate/absa --backfill khoanh đúng hotel khi gán concept mới
            "hotels": sorted(hotels.get(nv, ())),
            "examples": [display[nv]],
            "source": "amenity_field",       # phân biệt nguồn với review/description
            "status": "pending",
        })
    rows.sort(key=lambda r: -r["rank_score"])
    rows = rows[:TOP]
    return {"n_hotels": n_all, "max_hotels": max_hotels, "n_too_common": n_too_common,
            "n_candidates": len(rows), "candidates": rows}


def merge_into_queue(rows: list[dict], queue_path: str = QUEUE, apply: bool = False) -> dict:
    """Merge candidate amenity vào candidate_queue.yaml. Idempotent theo candidate_keyword (norm):
    candidate đã có (bất kỳ nguồn nào) -> BỎ QUA, KHÔNG ghi đè status người duyệt. Chỉ THÊM mới.
    """
    q = yaml.safe_load(open(queue_path, encoding="utf-8")) or {}
    existing = q.get("candidates") or []
    have = {_norm(c.get("candidate_keyword", "")) for c in existing}

    new = [r for r in rows if _norm(r["candidate_keyword"]) not in have]

    if apply and new:
        q.setdefault("candidates", [])
        q["candidates"].extend(new)
        # giữ header comment gốc (đọc thô) — yaml.safe_dump bỏ comment.
        txt = Path(queue_path).read_text(encoding="utf-8")
        head = "".join(
            l for l in txt.splitlines(keepends=True) if l.lstrip().startswith("#")
        )
        with open(queue_path, "w", encoding="utf-8") as fh:
            if head:
                fh.write(head)
                if not head.endswith("\n"):
                    fh.write("\n")
            yaml.safe_dump(q, fh, allow_unicode=True, sort_keys=False)

    return {"n_existing": len(existing), "n_new": len(new), "new": new}


if __name__ == "__main__":
    ap = argparse.ArgumentParser(
        description="Đào tiện ích ứng viên từ trường amenities -> candidate_queue.yaml."
    )
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--dry-run", action="store_true",
                   help="CHỈ in candidate sẽ thêm (mặc định)")
    g.add_argument("--apply", action="store_true",
                   help="GHI: merge candidate mới vào candidate_queue.yaml")
    args = ap.parse_args()

    res = mine()
    print(f"Quét {res['n_hotels']} hotel | trần IDF={res['max_hotels']} hotel "
          f"(>{int(MAX_HOTEL_RATIO*100)}% = loại {res['n_too_common']} chuỗi phổ thông)")
    print(f"Candidate amenity (chưa map, chưa reject/defer, đủ support): {res['n_candidates']}\n")

    merge = merge_into_queue(res["candidates"], apply=args.apply)
    print(f"candidate_queue hiện có: {merge['n_existing']} | SẼ THÊM mới: {merge['n_new']}\n")
    for r in merge["new"][:30]:
        print(f"  score {r['rank_score']:7.1f} | {r['hotel_count']:4d} hotel | "
              f"{r['candidate_keyword']}")
    if len(merge["new"]) > 30:
        print(f"  ... và {len(merge['new']) - 30} candidate nữa.")

    if args.apply:
        print(f"\n[ghi] đã merge {merge['n_new']} candidate amenity -> {QUEUE}")
        print("BƯỚC TIẾP: người duyệt đặt status=approved + suggested_concept_id (vd AMEN_BBQ),")
        print("  rồi: promote_candidate.py --apply -> backfill cho hotel cũ.")
    else:
        print("\n[dry-run] CHƯA ghi. Chạy lại với --apply để merge vào candidate_queue.yaml.")

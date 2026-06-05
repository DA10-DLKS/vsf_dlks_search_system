"""build_locations.py — TỰ SINH location ontology toàn cầu từ data. Lớp A (Task 1.5 mở rộng).

Owner: Trương Anh Long (Knowledge Engineering, DA10).

VÌ SAO TỰ SINH: corpus đã 555 hotel / 39 quốc gia / 205 thành phố (target VOTA: VN trước,
scale ra nước ngoài theo từng đất nước — chỉ đạo mentor Phạm Văn Toàn). Gõ tay từng địa danh
như mốc 51 hotel không còn khả thi và dễ sai. Script quét field địa lý THẬT trong data/cleaned
rồi sinh concept LOC_* có phân cấp country > city > area.

CÂY 3 TẦNG (thực dụng — KHÔNG 4 tầng):
    country  (kind: country)  <- field `country`
      city   (kind: place)    <- field `city`   (gộp `province`, vì Agoda crawl province==city)
        area (kind: area)     <- field `area`   (gộp `district`, vì area==district)
Lý do gộp: trong data này province trùng city và district trùng area gần như 100% -> nếu sinh
đủ 4 tầng sẽ tạo concept trùng lặp. Giữ 3 tầng đúng với độ phân giải thật của dữ liệu.

OUTPUT: ontology/core/location.generated.yaml (TỰ SINH — không sửa tay; chạy lại khi corpus đổi).
    Tách khỏi location.yaml (curated: landmark LMK_* + alias tinh chỉnh tay) để 2 phần không đè nhau.

Mỗi concept có: facet, fact_type=hard, tier=core, kind, parent, label{vi,en}, surface_forms{vi}
(tên gốc + bản không dấu để build_synonym_index nhận diện query địa danh), description (đếm hotel).

Chạy:  .venv/Scripts/python.exe -X utf8 -m knowledge_engineering.entity_extraction.build_locations
"""

import glob
import json
import re
from collections import Counter, defaultdict

from knowledge_engineering.common.normalize import strip_diacritics, to_nfc

HOTELS_GLOB = "data/cleaned/hotel_*.json"
OUT_YAML = "ontology/core/location.generated.yaml"

# Map tên country (tiếng Việt trong data) -> slug ID en chuẩn quốc tế. Đây là phần CURATED
# nhỏ duy nhất (39 nước, ổn định) — tên quốc gia en là định danh chuẩn, không slug máy móc từ vi.
COUNTRY_SLUG = {
    "Việt Nam": "VIETNAM",
    "Hoa Kỳ": "USA",
    "Trung Quốc": "CHINA",
    "Thái Lan": "THAILAND",
    "Malaysia": "MALAYSIA",
    "Indonesia": "INDONESIA",
    "Nhật Bản": "JAPAN",
    "Các Tiểu Vương Quốc Ả Rập Thống nhất": "UAE",
    "Ấn Độ": "INDIA",
    "Hàn Quốc": "SOUTH_KOREA",
    "Philippines": "PHILIPPINES",
    "Pháp": "FRANCE",
    "Brazil": "BRAZIL",
    "Fiji": "FIJI",
    "Hồng Kông": "HONG_KONG",
    "Ý": "ITALY",
    "Úc": "AUSTRALIA",
    "Ma Cao": "MACAU",
    "Mexico": "MEXICO",
    "Hà Lan": "NETHERLANDS",
    "Đài Loan": "TAIWAN",
    "Ả Rập Xê Út": "SAUDI_ARABIA",
    "Puerto Rico": "PUERTO_RICO",
    "Đức": "GERMANY",
    "Singapore": "SINGAPORE",
    "Oman": "OMAN",
    "Polynesia thuộc Pháp": "FRENCH_POLYNESIA",
    "Argentina": "ARGENTINA",
    "Bermuda": "BERMUDA",
    "Canada": "CANADA",
    "Aruba": "ARUBA",
    "Panama": "PANAMA",
    "Ba Lan": "POLAND",
    "Guam": "GUAM",
    "Campuchia": "CAMBODIA",
    "Kazakhstan": "KAZAKHSTAN",
    "Nam Phi": "SOUTH_AFRICA",
    "Nepal": "NEPAL",
    "Qatar": "QATAR",
}

# PROVINCE override (CURATED) — data Agoda KHÔNG có tầng tỉnh (province==city). Khi muốn
# city VN nằm dưới một tỉnh, khai báo ở đây: city_slug (từ data) -> (province_id, label_vi).
# city có trong bảng -> parent = tỉnh; tỉnh -> parent = LOC_VIETNAM. city KHÔNG có -> parent thẳng VN.
VN_PROVINCE = {
    "DAO_PHU_QUOC": ("LOC_KIEN_GIANG", "Kiên Giang"),   # Phú Quốc thuộc Kiên Giang
    "DONG_HOI_QUANG_BINH": ("LOC_QUANG_BINH_TINH", "Quảng Bình"),
    "PHU_LY_HA_NAM": ("LOC_HA_NAM_TINH", "Hà Nam"),
    # Nha Trang -> Khánh Hòa: xử lý qua CITY_OVERRIDE bên dưới (vì city cũng đổi ID)
}

# ── OVERRIDE ID + QUAN HỆ (Phương án 1) ─────────────────────────────────────────
# generated slug theo tên data (Agoda kèm "Đảo/Biển/Đồng Hới") -> ID dài, lệch ID quen Sprint 1.
# Bảng dưới ÉP ID generated về ID curated + gắn `related`/`parent` curated, để:
#   (a) 1 ID duy nhất / nơi (location.yaml KHÔNG còn place — chỉ landmark),
#   (b) KHÔNG phải sửa tham chiếu ở ontology.yaml / facets.yaml / query_expansion / golden.
#
# CITY_OVERRIDE: city_slug (từ data) -> {id, related?, parent?}. parent ưu tiên hơn VN_PROVINCE.
# extra: cách gõ bổ sung (tên data có tiền tố "Đảo/Biển" hoặc tỉnh trong ngoặc -> thêm tên trần).
CITY_OVERRIDE = {
    "DAO_PHU_QUOC":          {"id": "LOC_PHU_QUOC",   "related": ["SETTING_ISLAND"], "parent": "LOC_KIEN_GIANG", "extra": ["phú quốc", "đảo phú quốc"]},
    "BIEN_CUA_LO":           {"id": "LOC_CUA_LO",     "related": ["SETTING_COASTAL"], "extra": ["cửa lò", "biển cửa lò"]},
    "DONG_HOI_QUANG_BINH":   {"id": "LOC_QUANG_BINH", "parent": "LOC_QUANG_BINH_TINH", "extra": ["quảng bình", "đồng hới"]},
    "PHU_LY_HA_NAM":         {"id": "LOC_HA_NAM",     "parent": "LOC_HA_NAM_TINH", "extra": ["hà nam", "phủ lý"]},
    "NHA_TRANG":             {"id": "LOC_NHA_TRANG",  "parent": "LOC_KHANH_HOA"},
}

# AREA_OVERRIDE: (city_slug, area_slug từ data) -> {id, related?}. parent = id của city (đã override).
# Cho các sub-area Sprint 1 (Hòn Tre/Gành Dầu/Cửa Đại) giữ ID ngắn + related.
AREA_OVERRIDE = {
    ("NHA_TRANG", "HON_TRE"):     {"id": "LOC_HON_TRE",  "related": ["SETTING_ISLAND"]},
    ("DAO_PHU_QUOC", "GANH_DAU"): {"id": "LOC_GANH_DAU"},
    ("HOI_AN", "CUA_DAI"):        {"id": "LOC_CUA_DAI",  "related": ["SETTING_COASTAL"]},
}

# Tỉnh curated cần label (cho VN_PROVINCE + parent override). province_id -> label_vi.
PROVINCE_LABEL = {
    "LOC_KHANH_HOA": "Khánh Hòa",
    "LOC_KIEN_GIANG": "Kiên Giang",
    "LOC_QUANG_BINH_TINH": "Quảng Bình",
    "LOC_HA_NAM_TINH": "Hà Nam",
}

COUNTRY_LABEL_EN = {
    "Việt Nam": "Vietnam", "Hoa Kỳ": "United States", "Trung Quốc": "China",
    "Thái Lan": "Thailand", "Nhật Bản": "Japan", "Hàn Quốc": "South Korea",
    "Các Tiểu Vương Quốc Ả Rập Thống nhất": "United Arab Emirates", "Ấn Độ": "India",
    "Pháp": "France", "Hồng Kông": "Hong Kong", "Ý": "Italy", "Úc": "Australia",
    "Ma Cao": "Macau", "Hà Lan": "Netherlands", "Đài Loan": "Taiwan",
    "Ả Rập Xê Út": "Saudi Arabia", "Đức": "Germany", "Polynesia thuộc Pháp": "French Polynesia",
    "Ba Lan": "Poland", "Campuchia": "Cambodia", "Nam Phi": "South Africa",
}


def slug(name: str) -> str:
    """Tên địa danh (có dấu) -> hậu tố ID: bỏ dấu, in hoa, _ thay khoảng trắng/ký tự lạ."""
    s = strip_diacritics(to_nfc(name)).upper()
    s = re.sub(r"[^A-Z0-9]+", "_", s).strip("_")
    return s


def surface_forms(name: str) -> list[str]:
    """Các cách gõ địa danh: tên gốc + bản rút gọn (bỏ '(...)' / phần sau '/') + bản không dấu.

    Tên Agoda hay kèm tỉnh/bang trong ngoặc ("Quy Nhơn (Bình Định)", "Anaheim (CA)") hoặc ghép
    bằng '/' ("Hua Hin / Cha-am"). Người dùng gõ phần chính ("quy nhon", "anaheim", "hua hin")
    -> sinh thêm các biến thể đó để synonym khớp.
    """
    base = to_nfc(name).lower().strip()
    variants = {base}
    short = re.sub(r"\s*\(.*?\)\s*", " ", base).strip()        # bỏ "(...)"
    if short:
        variants.add(short)
    if "/" in base:                                           # "hua hin / cha-am" -> "hua hin", "cha-am"
        for part in base.split("/"):
            part = re.sub(r"\s*\(.*?\)\s*", " ", part).strip()
            if part:
                variants.add(part)
    out = set()
    for v in variants:
        out.add(v)
        out.add(strip_diacritics(v))
    return sorted(f for f in out if f)


def scan(hotels_glob: str = HOTELS_GLOB):
    """Quét data -> đếm hotel ở mỗi (country, city, area) + ghi quan hệ cha-con."""
    country_n = Counter()
    city_n = Counter()                       # key: (country, city)
    area_n = Counter()                       # key: (country, city, area)
    unknown_country = set()
    for f in sorted(glob.glob(hotels_glob)):
        d = json.load(open(f, encoding="utf-8"))
        co = (d.get("country") or "").strip()
        ci = (d.get("city") or d.get("province") or "").strip()
        ar = (d.get("area") or d.get("district") or "").strip()
        if not co:
            continue
        if co not in COUNTRY_SLUG:
            unknown_country.add(co)
            continue
        country_n[co] += 1
        if ci:
            city_n[(co, ci)] += 1
            if ar and ar != ci:              # bỏ area trùng tên city (vô nghĩa)
                area_n[(co, ci, ar)] += 1
    return country_n, city_n, area_n, unknown_country


def concept_block(cid, kind, label_vi, label_en, parent, sf, desc, related=None) -> str:
    lines = [
        f"  {cid}:",
        f"    facet: location",
        f"    fact_type: hard",
        f"    tier: core",
        f"    kind: {kind}",
    ]
    if parent:
        lines.append(f"    parent: {parent}")
    if related:
        lines.append(f"    related: [{', '.join(related)}]")
    lines += [
        f"    label: {{vi: {yq(label_vi)}, en: {yq(label_en)}}}",
        f"    surface_forms:",
        f"      vi: [{', '.join(yq(s) for s in sf)}]",
        f"    description: {{vi: {yq(desc)}, en: {yq(desc)}}}",
    ]
    return "\n".join(lines)


def yq(s: str) -> str:
    """Quote YAML an toàn cho chuỗi có dấu/ký tự đặc biệt."""
    s = str(s).replace('"', "'")
    return f'"{s}"'


def build(hotels_glob: str = HOTELS_GLOB) -> str:
    country_n, city_n, area_n, unknown = scan(hotels_glob)

    # CITY-STATE: city trùng slug với chính country của nó (Singapore, Hong Kong, Macau, Guam...)
    # -> KHÔNG sinh city concept (sẽ đè key country trong YAML). Hotel gắn thẳng vào country.
    country_slugs = {f"LOC_{COUNTRY_SLUG[co]}" for co in country_n}
    city_state = {(co, ci) for (co, ci) in city_n if f"LOC_{slug(ci)}" == f"LOC_{COUNTRY_SLUG[co]}"}

    # ID city: ưu tiên CITY_OVERRIDE (ép ID quen); rồi tránh trùng giữa 2 nước + đụng country slug.
    city_id = {}
    seen_city_slug = Counter()
    for (co, ci), n in sorted(city_n.items(), key=lambda x: (-x[1], x[0])):
        if (co, ci) in city_state:
            city_id[(co, ci)] = f"LOC_{COUNTRY_SLUG[co]}"   # trỏ thẳng về country
            continue
        if slug(ci) in CITY_OVERRIDE:
            city_id[(co, ci)] = CITY_OVERRIDE[slug(ci)]["id"]
            continue
        base = slug(ci)
        cand = f"LOC_{base}"
        seen_city_slug[base] += 1
        if seen_city_slug[base] > 1 or cand in country_slugs:
            cand = f"LOC_{COUNTRY_SLUG[co]}_{base}"
        city_id[(co, ci)] = cand

    out = []
    out.append("# ontology/core/location.generated.yaml — TỰ SINH bởi build_locations.py (Lớp A).")
    out.append("# KHÔNG sửa tay. Nguồn: data/cleaned/*.json (field country/city/area).")
    out.append("# Cây: country > city > area. Landmark (LMK_*) + alias curated nằm ở location.yaml.")
    out.append(f"# Thống kê: {sum(country_n.values())} hotel / {len(country_n)} country / "
               f"{len(city_n)} city / {len(area_n)} area.")
    if unknown:
        out.append(f"# ⚠ Country CHƯA map slug (bỏ qua, cần bổ sung COUNTRY_SLUG): {sorted(unknown)}")
    out.append("")
    out.append("concepts:")
    out.append("")

    # 1) COUNTRY
    out.append("  # ===== COUNTRY (kind: country) — nhánh điểm đến theo từng đất nước =====")
    for co, n in sorted(country_n.items(), key=lambda x: (-x[1], x[0])):
        cid = f"LOC_{COUNTRY_SLUG[co]}"
        label_en = COUNTRY_LABEL_EN.get(co, co)
        out.append(concept_block(cid, "country", co, label_en, None,
                                 surface_forms(co), f"{co} ({n} hotel trong corpus)"))
        out.append("")

    # 2) PROVINCE node (curated override) — sinh tỉnh nào có city tham chiếu (qua VN_PROVINCE hoặc
    #    CITY_OVERRIDE.parent). parent của city ưu tiên CITY_OVERRIDE > VN_PROVINCE > country.
    def city_parent(co, ci):
        ov = CITY_OVERRIDE.get(slug(ci))
        if ov and ov.get("parent"):
            return ov["parent"]
        if co == "Việt Nam" and slug(ci) in VN_PROVINCE:
            return VN_PROVINCE[slug(ci)][0]
        return f"LOC_{COUNTRY_SLUG[co]}"

    used_provinces = {}   # province_id -> label_vi
    for (co, ci) in city_n:
        if (co, ci) in city_state:
            continue
        p = city_parent(co, ci)
        if p in PROVINCE_LABEL:
            used_provinces[p] = PROVINCE_LABEL[p]
    if used_provinces:
        out.append("  # ===== PROVINCE (kind: place) — tầng tỉnh VN curated (data không có; override) =====")
        for pid, plabel in sorted(used_provinces.items()):
            out.append(concept_block(pid, "place", plabel, plabel, "LOC_VIETNAM",
                                     surface_forms(plabel), f"Tỉnh {plabel}, Việt Nam (tầng curated)"))
            out.append("")

    # 3) CITY (parent = province/country). ID + related có thể bị CITY_OVERRIDE ép.
    out.append("  # ===== CITY (kind: place) — gộp province (province==city trong data) =====")
    out.append("  # (city-state như Singapore/Hong Kong: hotel gắn thẳng country, không sinh city riêng)")
    out.append("  # (ID/related vài nơi ép theo CITY_OVERRIDE để khớp ID quen Sprint 1: Phú Quốc, Cửa Lò...)")
    for (co, ci), n in sorted(city_n.items(), key=lambda x: (-x[1], x[0])):
        if (co, ci) in city_state:
            continue
        cid = city_id[(co, ci)]
        ov = CITY_OVERRIDE.get(slug(ci), {})
        sf = surface_forms(ci)
        for ex in ov.get("extra", []):                    # thêm cách gõ trần (bỏ tiền tố Đảo/Biển)
            sf += [s for s in surface_forms(ex) if s not in sf]
        out.append(concept_block(cid, "place", ci, ci, city_parent(co, ci),
                                 sf, f"{ci}, {co} ({n} hotel)", related=ov.get("related")))
        out.append("")

    # 4) AREA (parent = city). ID + related có thể bị AREA_OVERRIDE ép (sub-area Sprint 1).
    out.append("  # ===== AREA (kind: area) — gộp district (area==district trong data) =====")
    out.append("  # (ID vài sub-area ép theo AREA_OVERRIDE để khớp ID quen: Hòn Tre, Gành Dầu, Cửa Đại)")
    for (co, ci, ar), n in sorted(area_n.items(), key=lambda x: (-x[1], x[0])):
        parent = city_id[(co, ci)]
        ov = AREA_OVERRIDE.get((slug(ci), slug(ar)))
        if ov:
            cid = ov["id"]
            related = ov.get("related")
        else:
            cid = f"{parent}__{slug(ar)}"     # area id = <city_id>__<area_slug> tránh trùng toàn cục
            related = None
        out.append(concept_block(cid, "area", ar, ar, parent,
                                 surface_forms(ar), f"{ar} (thuộc {ci}, {co}; {n} hotel)", related=related))
        out.append("")

    return "\n".join(out).rstrip() + "\n"


def main():
    text = build()
    with open(OUT_YAML, "w", encoding="utf-8") as fh:
        fh.write(text)
    # tóm tắt ra stdout
    country_n, city_n, area_n, unknown = scan()
    print(f"Đã ghi {OUT_YAML}")
    print(f"  country={len(country_n)}  city={len(city_n)}  area={len(area_n)}  "
          f"(hotel có country hợp lệ={sum(country_n.values())})")
    if unknown:
        print(f"  ⚠ country chưa map slug: {sorted(unknown)}")


if __name__ == "__main__":
    main()

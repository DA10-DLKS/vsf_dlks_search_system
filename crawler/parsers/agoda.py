"""
Cac ham parse cho TUNG nguon graphql/api cua trang chi tiet khach san Agoda.
Moi ham nhan response_body tho -> tra ve phan du lieu sach.

Cac nguon:
  - propertyDetailsSearch  (graphql/property)         -> thong tin chinh
  - room-grid              (/api/v1/property/room-grid)-> loai phong + gia
  - HotelReviews           (/api/.../review/HotelReviews) -> danh gia chi tiet
  - GetSecondaryData       (/api/.../BelowFoldParams/..) -> chinh sach, FAQ, phong
  - activities             (/api/activities/graphql)   -> hoat dong quanh do
"""


def fix_url(u):
    if not u:
        return None
    return ("https:" + u) if u.startswith("//") else u


# Map 14 nhom tien ich cua Agoda -> 3 nhom lon kieu mau A
_GROUP_TO_A = {
    "Thư giãn & Vui chơi giải trí": "leisure",
    "Hoạt động thể thao trên cạn ": "leisure",
    "Cho thuê dụng cụ thể thao": "leisure",
    "Ăn uống": "dining",
}
# con lai -> general


def _classify_amenity_groups(amenity_groups: dict) -> dict:
    """Gom 14 nhom Agoda -> general / leisure / dining (kieu mau A)."""
    out = {"general": [], "leisure": [], "dining": []}
    for gname, items in amenity_groups.items():
        bucket = _GROUP_TO_A.get(gname, "general")
        out[bucket].extend(items)
    return {k: sorted(set(v)) for k, v in out.items()}


def safe(d, *keys, default=None):
    cur = d
    for k in keys:
        if isinstance(cur, dict) and k in cur and cur[k] is not None:
            cur = cur[k]
        else:
            return default
    return cur


# ---------------------------------------------------------------------------
# 1) propertyDetailsSearch — thong tin chinh
# ---------------------------------------------------------------------------
def parse_property_details(body: dict) -> dict:
    details = safe(body, "data", "propertyDetailsSearch", "propertyDetails", default=[])
    if not details:
        return {}
    cd = details[0].get("contentDetail", {}) or {}
    summary = cd.get("contentSummary", {}) or {}
    addr = summary.get("address", {}) or {}

    parts = [addr.get("address1"), safe(addr, "area", "name"),
             safe(addr, "city", "name"), safe(addr, "country", "name")]
    full_address = ", ".join([p for p in parts if p])

    cum = safe(cd, "contentReviewScore", "combinedReviewScore", "cumulative", default={}) or {}

    # Anh: lay url 'main' + caption + category (group) — du lieu THAT
    images = []
    for img in (safe(cd, "contentImages", "hotelImages", default=[]) or []):
        url = None
        for u in (img.get("urls") or []):
            if u.get("key") == "main":
                url = fix_url(u.get("value"))
                break
        if url:
            images.append({"url": url,
                           "caption": (img.get("caption") or "").strip(),
                           "category": img.get("group")})
    image_urls = [im["url"] for im in images]

    # Tien ich: gom phang + PHAN NHOM theo featureGroups (Agoda co san ten nhom)
    # highlights = favoriteFeatures (diem noi bat Agoda chon san)
    highlights = []
    for f in (safe(cd, "contentHighlights", "favoriteFeatures", default=[]) or []):
        if f.get("name"):
            highlights.append(f["name"])

    # location_tags = locations + atfPropertyHighlights + locationHighlights
    location_tags = []
    hl = cd.get("contentHighlights", {}) or {}
    for loc in (hl.get("locations") or []):
        if isinstance(loc, dict) and loc.get("name"):
            location_tags.append(loc["name"])
    for atf in (hl.get("atfPropertyHighlights") or []):
        if isinstance(atf, dict) and atf.get("name"):
            location_tags.append(atf["name"])
    for lh in (hl.get("locationHighlights") or []):
        if isinstance(lh, dict) and lh.get("message"):
            location_tags.append(lh["message"])
    location_tags = sorted(set(location_tags))

    amenities = list(highlights)  # highlights cung la 1 phan tien ich
    amenity_groups = {}
    for grp in (safe(cd, "contentFeatures", "featureGroups", default=[]) or []):
        gname = grp.get("groupName") or grp.get("name") or grp.get("title") or "Khác"
        items = []
        for f in (grp.get("features") or []):
            if f.get("available") and f.get("featureName"):
                amenities.append(f["featureName"])
                items.append(f["featureName"])
        if items:
            amenity_groups.setdefault(gname, [])
            amenity_groups[gname].extend(items)
    amenities = sorted(set(amenities))
    # bo trung trong tung nhom
    amenity_groups = {k: sorted(set(v)) for k, v in amenity_groups.items()}

    useful = {}
    for grp in (safe(cd, "contentInformation", "usefulInfoGroups", default=[]) or []):
        for it in (grp.get("usefulInfo") or []):
            if it.get("name"):
                useful[it["name"]] = it.get("description")

    nearby = []
    for pl in (safe(cd, "contentLocalInformation", "nearbyPlaces", default=[]) or [])[:10]:
        nearby.append({"name": pl.get("name"), "type": pl.get("typeName"),
                       "distance_km": pl.get("distanceInKm")})

    return {
        "hotel_id": summary.get("propertyId") or cd.get("propertyId"),
        "name": summary.get("displayName"),
        "property_type": summary.get("propertyType"),
        "accommodation_type": safe(summary, "accommodation", "accommodationName"),
        "star_rating": summary.get("rating"),
        "is_luxury": summary.get("isLuxuryHotel"),
        "gold_circle_award_year": safe(summary, "awardsAndAccolades", "goldCircleAward", "year"),
        "review_score": cum.get("score"),
        "review_count": cum.get("reviewCount"),
        "address": full_address,
        "area": safe(addr, "area", "name"),
        "city": safe(addr, "city", "name"),
        "country": safe(addr, "country", "name"),
        "postal_code": addr.get("postalCode"),
        "latitude": safe(summary, "geoInfo", "latitude"),
        "longitude": safe(summary, "geoInfo", "longitude"),
        "description": safe(cd, "contentInformation", "description", "short"),
        "check_in_from": useful.get("Nhận phòng từ"),
        "check_out_until": useful.get("Trả phòng đến"),
        "year_built": useful.get("Khách sạn được xây vào năm"),
        "number_of_floors": useful.get("Số tầng khách sạn"),
        "number_of_rooms": useful.get("Số lượng phòng"),
        "useful_info": useful,
        "highlights": highlights,
        "location_tags": location_tags,
        "amenities": amenities,
        "amenities_count": len(amenities),
        "amenity_groups": amenity_groups,
        "amenities_general": _classify_amenity_groups(amenity_groups)["general"],
        "amenities_leisure": _classify_amenity_groups(amenity_groups)["leisure"],
        "amenities_dining": _classify_amenity_groups(amenity_groups)["dining"],
        "nearby_places": nearby,
        "image_count": len(image_urls),
        "image_urls": image_urls,
        "images": images,  # co caption + category
    }


# ---------------------------------------------------------------------------
# 2) room-grid — loai phong + gia (gia co the rong neu chua load)
# ---------------------------------------------------------------------------
def _num_size(text):
    """ '32 m²' -> 32.0 """
    if not text:
        return None
    import re
    m = re.search(r"(\d+[\.,]?\d*)", str(text))
    return float(m.group(1).replace(",", ".")) if m else None


def _num_occupancy(text):
    """ 'Tối đa 3 người lớn' -> 3 """
    if not text:
        return None
    import re
    m = re.search(r"(\d+)", str(text))
    return int(m.group(1)) if m else None


def parse_room_grid(body: dict) -> dict:
    rooms = []
    for r in (body.get("rooms") or []):
        # Tach features theo type (du lieu THAT tu Agoda)
        by_type = {}
        bed_texts = []
        for f in (r.get("features") or []):
            t = f.get("type")
            txt = f.get("text")
            if t and txt:
                by_type[t] = txt
            # cac feature ve giuong (BEDROOM, BED...) khong co type chuan -> bat theo chu 'giường'
            if txt and "giường" in txt.lower():
                bed_texts.append(txt)

        room_size_text = by_type.get("ROOM_SIZE") or r.get("roomSize")
        max_occ_text = by_type.get("MAX_OCCUPANCY")

        # room_view tu roomHighlights (type ROOM_VIEW) hoac facilities (type VIEW)
        room_view = None
        for h in (r.get("roomHighlights") or []):
            if h.get("type") == "ROOM_VIEW" and h.get("text"):
                room_view = h["text"]
                break
        if not room_view:
            for fa in (r.get("facilities") or []):
                if fa.get("type") == "VIEW" and fa.get("text"):
                    room_view = fa["text"]
                    break

        # gia (neu co) nam trong offers — thuong RONG tren Agoda load tu dong
        price = None
        offers = r.get("offers") or []
        if offers:
            price = safe(offers[0], "price", "final", "text") or safe(offers[0], "displayPrice")

        imgs = [fix_url(im.get("url")) for im in (r.get("images") or [])[:5] if im.get("url")]
        facs = [f.get("text") for f in (r.get("facilities") or []) if f.get("text")]

        # room_amenities: gom tu amenities.top/featured/grouped (du lieu THAT bi bo qua truoc day)
        room_amenities = []
        am = r.get("amenities") or {}
        for it in (am.get("top") or []):
            if it.get("title"):
                room_amenities.append(it["title"])
        for it in (am.get("featured") or []):
            if it.get("title"):
                room_amenities.append(it["title"])
        for grp in (am.get("grouped") or []):
            for sub in (grp.get("items") or []):
                if sub:
                    room_amenities.append(sub)
            if grp.get("text"):
                room_amenities.append(grp["text"])
        room_amenities = sorted(set(room_amenities))

        rooms.append({
            "room_type_id": r.get("typeId"),
            "name": r.get("name"),
            "name_en": r.get("nameInEnglish"),
            "room_size": room_size_text,
            "size_sqm": _num_size(room_size_text),
            "max_occupancy": _num_occupancy(max_occ_text),
            "max_occupancy_text": max_occ_text,
            "bed_type": bed_texts[0] if bed_texts else None,
            "bed_types": bed_texts,
            "room_view": room_view,
            "is_sold_out": r.get("isSoldOut"),
            "facilities": facs,
            "room_amenities": room_amenities,
            "price": price,  # null neu Agoda khong tra ve (KHONG bia)
            "image_count": len(r.get("images") or []),
            "images": imgs,
            "review_score": safe(r, "reviewInformation", "score"),
        })
    cheapest = safe(body, "cheapestPrice", "price", "final", "text")
    if cheapest in ("0 ₫", "0\xa0₫", "0"):
        cheapest = None  # gia 0 = chua co gia that
    return {"is_sold_out": body.get("isSoldOut"),
            "cheapest_price": cheapest,
            "room_count": len(rooms),
            "rooms": rooms}


# ---------------------------------------------------------------------------
# 3) HotelReviews — danh gia chi tiet
# ---------------------------------------------------------------------------
def parse_reviews(body: dict) -> dict:
    combined = safe(body, "combinedReview", "score", default={}) or {}
    grades = []
    for g in (safe(body, "combinedReview", "grades", default=[]) or []):
        grades.append({"name": g.get("name"), "score": g.get("score")})

    comments = []
    for c in (safe(body, "commentList", "comments", default=[]) or [])[:10]:
        info = c.get("reviewerInfo") or {}
        comments.append({
            "rating": c.get("rating"),
            "rating_text": c.get("ratingText"),
            "date": c.get("formattedReviewDate"),
            "check_in": c.get("checkInDateMonthAndYear"),
            "text": c.get("reviewComments"),
            "title": c.get("reviewTitle"),
            "positives": c.get("reviewPositives"),
            "negatives": c.get("reviewNegatives"),
            "response": c.get("responseText"),
            # bo sung tu reviewerInfo (du lieu THAT)
            "reviewer_name": info.get("displayMemberName"),
            "reviewer_type": info.get("reviewGroupName"),   # Cap doi/Gia dinh/Don le...
            "reviewer_country": info.get("countryName"),
            "room_type": info.get("roomTypeName"),
        })

    tags = []
    for t in (safe(body, "reviewTagsV2", "reviewTagsV2", default=[]) or []):
        tags.append({"tag": t.get("tagName"), "mentioned": t.get("mentionedNumber"),
                     "positive_pct": t.get("positivePercentage")})

    word_cloud = []
    for wc in (safe(body, "reviewWordCloud", "reviewWordCloud", default=[]) or []):
        for w in (wc.get("wordCloudList") or []):
            word_cloud.append({"word": w.get("representors"), "count": w.get("count")})

    # demographics = cac nhom khach (de suy suitable_for): Cap doi, Gia dinh, Cong tac...
    demographics = []
    for d in (safe(body, "score", "demographics", default=[]) or []):
        name = d.get("name")
        if name and name != "Tất cả mọi du khách":
            demographics.append({"name": name, "count": d.get("count"),
                                 "score": d.get("score")})

    return {
        "score": combined.get("score"),
        "score_text": combined.get("scoreText"),
        "review_count": combined.get("reviewCount"),
        "comments_count": combined.get("reviewCommentsCount"),
        "grades": grades,
        "tags": tags,
        "word_cloud": word_cloud,
        "demographics": demographics,
        "sample_comments": comments,
    }


# ---------------------------------------------------------------------------
# 4) GetSecondaryData — chinh sach, FAQ, phong (dateless), places
# ---------------------------------------------------------------------------
def _strip_html(text):
    """Go HTML tags + giai ma vai entity pho bien -> text thuan."""
    if not text:
        return ""
    import re
    import html
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.I)   # <br> -> xuong dong
    text = re.sub(r"</p>|</div>", "\n", text, flags=re.I)
    text = re.sub(r"<[^>]+>", "", text)                    # bo moi tag con lai
    text = html.unescape(text)                             # &amp; -> &
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def parse_secondary(body: dict) -> dict:
    about = body.get("aboutHotel", {}) or {}

    # Mo ta DAY DU (bai van dai) — overview co HTML, can lam sach
    desc_full = _strip_html(safe(about, "hotelDesc", "overview"))

    # Chinh sach
    policy = about.get("hotelPolicy", {}) or {}
    other_policies = []
    for pol in (about.get("otherPolicies") or []):
        if isinstance(pol, dict):
            other_policies.append({"title": pol.get("title"),
                                   "content": pol.get("content") or pol.get("description")})

    # Phong (dateless — on dinh, khong phu thuoc ngay)
    rooms = []
    for r in (body.get("datelessMasterRoomInfo") or []):
        feats = [f.get("text") if isinstance(f, dict) else f
                 for f in (r.get("features") or [])]
        rooms.append({
            "room_id": r.get("id") or r.get("roomid"),
            "name": r.get("name"),
            "features": [x for x in feats if x],
            "image_count": len(r.get("images") or []),
            "bed_summary": safe(r, "bedConfigurationSummary"),
        })

    # LUU Y: translations.hotelFaq CHI la label giao dien (title, viewMap, showMore...)
    # KHONG phai FAQ that. FAQ that lay tu /api/cronos/geo/hotel/faq (xem parse_faq).

    return {
        "description_full": desc_full,   # bai van dai (~14k ky tu)
        "hotel_policy": policy,
        "other_policies": other_policies,
        "dateless_rooms_count": len(rooms),
        "dateless_rooms": rooms,
    }


# ---------------------------------------------------------------------------
# FAQ that — tu /api/cronos/geo/hotel/faq (cau hoi + tra loi)
# ---------------------------------------------------------------------------
def parse_faq(body, hotel_name=None) -> list:
    """body co the la list cac {questionId, question, answer, questionCategoryName}."""
    items = body if isinstance(body, list) else (body.get("faqs") or body.get("data") or [])
    out = []
    for it in items:
        if not isinstance(it, dict):
            continue
        q = it.get("question") or ""
        a = it.get("answer") or ""
        # Agoda dung placeholder [hotel_name] -> thay bang ten that
        if hotel_name:
            q = q.replace("[hotel_name]", hotel_name)
            a = a.replace("[hotel_name]", hotel_name)
        if q:
            out.append({"question": q, "answer": a,
                        "category": it.get("questionCategoryName")})
    return out


# ---------------------------------------------------------------------------
# Suy 'suitable_for' tu propertyDetailsSearch (contentHighlights/synopsis)
# ---------------------------------------------------------------------------
def parse_suitable_for(body: dict) -> list:
    """Lay 'phu hop voi ai' tu contentHighlights neu Agoda co cung cap."""
    details = safe(body, "data", "propertyDetailsSearch", "propertyDetails", default=[])
    if not details:
        return []
    cd = details[0].get("contentDetail", {}) or {}
    out = []
    # synopsis / engagement co the chua suitableFor
    hl = cd.get("contentHighlights") or {}
    for key in ("suitableFor", "travellerTypes", "goodFor"):
        for it in (hl.get(key) or []):
            name = it.get("name") if isinstance(it, dict) else it
            if name:
                out.append(name)
    return sorted(set(out))


# ---------------------------------------------------------------------------
# 5) activities — hoat dong quanh do
# ---------------------------------------------------------------------------
def parse_activities(body: dict) -> list:
    acts = safe(body, "data", "search", "result", "activities", default=[]) or []
    out = []
    for a in acts:
        act = safe(a, "content", "activity", default={}) or {}
        price = None
        pricing = safe(a, "activityRepresentativeInfo", "pricingSummary", "pricing", default=[])
        if pricing:
            price = pricing[0]
        out.append({
            "activity_id": a.get("masterActivityId"),
            "title": act.get("title"),
            "description": (act.get("description") or "")[:200],
            "review_score": safe(a, "content", "reviewSummary", "averageScore"),
            "review_count": safe(a, "content", "reviewSummary", "totalCount"),
            "price": price,
        })
    return out


# ---------------------------------------------------------------------------
# build_record — gop TAT CA nguon + cac field tong hop (crawled_at, embedding_text...)
# ---------------------------------------------------------------------------
def build_record(stores: dict, hotel_meta: dict, source_url: str) -> dict:
    """
    stores: {'details':..., 'rooms':..., 'reviews':..., 'secondary':..., 'activities':...}
    hotel_meta: 1 phan tu tu hotels_list.json (co city_id, property_page)
    """
    from datetime import datetime

    rec = {}
    rec["crawled_at"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    rec["source_url"] = source_url

    # 1) Thong tin chinh
    if "details" in stores:
        rec.update(parse_property_details(stores["details"]))

    # district / province (alias de giong mau A) — KHONG bia, lay tu area/city
    rec["district"] = rec.get("area")
    rec["province"] = rec.get("city")

    rec["city_id"] = hotel_meta.get("city_id")
    rec["property_page"] = hotel_meta.get("property_page")

    # 2) Phong
    if "rooms" in stores:
        rec["room_grid"] = parse_room_grid(stores["rooms"])
        rec["rooms"] = rec["room_grid"]["rooms"]  # alias giong mau A (truy cap truc tiep)

    # 3) Danh gia chi tiet
    if "reviews" in stores:
        rec["reviews_detail"] = parse_reviews(stores["reviews"])
        # alias giong mau A: rating_overall, rating_breakdown
        rv = rec["reviews_detail"]
        if rv.get("score"):
            rec["rating_overall"] = rv["score"]
            rec["rating_count"] = rv.get("review_count")
            rec["rating_breakdown"] = {g["name"]: g["score"] for g in rv.get("grades", []) if g.get("name")}

    # 4) Chinh sach + phong dateless + MO TA DAY DU
    if "secondary" in stores:
        rec["secondary"] = parse_secondary(stores["secondary"])
        # Mo ta day du (bai van dai) lam description chinh; giu ban short rieng
        full = rec["secondary"].get("description_full")
        if full:
            rec["description_short"] = rec.get("description")  # ban 350 ky tu
            rec["description"] = full                          # ban day du ~14k

    # 5) Hoat dong
    if "activities" in stores:
        rec["activities"] = parse_activities(stores["activities"])

    # 6) FAQ that (cau hoi + tra loi)
    if "faq" in stores:
        rec["faq"] = parse_faq(stores["faq"], rec.get("name"))

    # suitable_for: uu tien demographics tu reviews (Cap doi/Gia dinh/Cong tac...),
    # fallback parse_suitable_for tu details
    suitable = []
    for d in rec.get("reviews_detail", {}).get("demographics", []):
        if d["name"] not in suitable:   # bo trung, giu thu tu
            suitable.append(d["name"])
    if not suitable and "details" in stores:
        suitable = parse_suitable_for(stores["details"])
    rec["suitable_for"] = suitable

    # view_types: gom tu room_view cua cac phong (du lieu THAT)
    views = set()
    for r in (rec.get("room_grid", {}).get("rooms") or []):
        if r.get("room_view"):
            views.add(r["room_view"])
    rec["view_types"] = sorted(views)

    # tags: gop tong hop (highlights + location_tags + view_types + suitable_for)
    tags = []
    tags += rec.get("highlights", [])
    tags += rec.get("location_tags", [])
    tags += rec.get("view_types", [])
    tags += rec.get("suitable_for", [])
    rec["tags"] = sorted(set(t for t in tags if t))

    # embedding_text: ghep mo ta + thong tin chinh de lam AI/vector search
    rec["embedding_text"] = _build_embedding_text(rec)

    rec["_sources_captured"] = sorted(stores.keys())
    return rec


def _build_embedding_text(rec: dict) -> str:
    """Tao 1 doan text mo ta tong hop tu cac field THAT (khong bia)."""
    parts = []
    name = rec.get("name") or ""
    star = rec.get("star_rating")
    city = rec.get("city") or ""
    parts.append(f"{name} - khách sạn {star} sao tại {city}." if star else f"{name} tại {city}.")
    if rec.get("address"):
        parts.append(f"Địa chỉ: {rec['address']}.")
    # Dung ban short cho embedding (ban full ~14k qua dai cho vector)
    desc = rec.get("description_short") or rec.get("description") or ""
    if desc:
        parts.append(desc[:1500])
    if rec.get("amenities"):
        parts.append("Tiện ích: " + ", ".join(rec["amenities"][:30]) + ".")
    rv = rec.get("reviews_detail", {})
    if rv.get("score"):
        parts.append(f"Điểm đánh giá {rv['score']}/10 dựa trên {rv.get('review_count')} đánh giá.")
        if rv.get("tags"):
            parts.append("Khách hay nhắc đến: " + ", ".join(t["tag"] for t in rv["tags"][:8] if t.get("tag")) + ".")
    if rec.get("room_grid", {}).get("rooms"):
        names = [r["name"] for r in rec["room_grid"]["rooms"] if r.get("name")][:8]
        parts.append("Các loại phòng: " + "; ".join(names) + ".")
    if rec.get("nearby_places"):
        parts.append("Gần: " + ", ".join(p["name"] for p in rec["nearby_places"][:6] if p.get("name")) + ".")
    return "\n".join(parts)

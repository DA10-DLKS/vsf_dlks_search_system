"""Test parser intent: range giá (kép + superlative), negation, gia-đình-đè-lãng-mạn.

Các case này là kết quả sửa từ benchmark 30 câu (so với chatbot công ty). Mỗi test gắn với 1
câu cụ thể để khỏi tái diễn regression.
"""

from retrieval.query_processing.intent_parser import parse_intent, parse_range


# ── B. Range giá KÉP (câu 26) ────────────────────────────────────────────────
def test_price_range_double_mixed_units():
    # "800k đến 1tr2": vế đầu nghìn, vế sau triệu; "1tr2" = 1.200.000 (1 triệu 2 trăm nghìn).
    r = parse_range("khách sạn tầm 800k đến 1tr2 một đêm")
    assert r["price_min"] == 800_000
    assert r["price_max"] == 1_200_000


def test_price_range_double_same_unit():
    r = parse_range("từ 1 đến 2 triệu")
    assert r == {"price_min": 1_000_000, "price_max": 2_000_000}


def test_star_range_not_parsed_as_price():
    # "4-5 sao" KHÔNG được hiểu thành range giá (vế sau không có đơn vị tiền).
    r = parse_range("resort 4-5 sao có bao ăn sáng")
    assert "price_min" not in r and r.get("star_eq") == 5


# ── C. Superlative sort (câu 27, 28) ─────────────────────────────────────────
def test_superlative_cheapest():
    assert parse_range("chỗ nào rẻ nhất ở Sa Pa")["sort"] == "price_asc"


def test_superlative_most_expensive():
    assert parse_range("resort sang nhất Nha Trang")["sort"] == "price_desc"


# ── A. Negation (câu 20, 21, 22) ─────────────────────────────────────────────
def test_negation_excludes_family():
    # "không có trẻ em" -> KHÔNG phải chuyến gia đình: PURPOSE_FAMILY vào exclude, không vào purpose.
    p = parse_intent("Resort không có trẻ em chạy nhảy ồn ào, muốn yên tĩnh")
    assert "PURPOSE_FAMILY" in p.exclude_concepts
    assert "PURPOSE_FAMILY" not in p.purposes


def test_negation_keeps_wanted_pool():
    # "có hồ bơi nhưng không phải hồ bơi chung": user VẪN muốn hồ bơi -> AMEN_POOL giữ, không exclude.
    p = parse_intent("Chỗ nào có hồ bơi nhưng không phải hồ bơi chung đông người")
    assert "AMEN_POOL" in p.hard_concepts
    assert "AMEN_POOL" not in p.exclude_concepts


def test_no_negation_no_exclude():
    p = parse_intent("Khách sạn ở Đà Nẵng gần biển")
    assert p.exclude_concepts == []


# ── F. Gia đình đè lãng mạn (câu 1) ──────────────────────────────────────────
def test_family_suppresses_romantic():
    # "2 vợ chồng với 2 đứa nhỏ": có con -> chuyến gia đình, KHÔNG gán romantic dù có "vợ chồng".
    p = parse_intent("Nhà tôi đi 2 vợ chồng với 2 đứa nhỏ, tìm chỗ ở Đà Nẵng")
    assert "PURPOSE_FAMILY" in p.purposes
    assert "PURPOSE_ROMANTIC" not in p.purposes


def test_honeymoon_keeps_romantic():
    # Cue romantic mạnh ("trăng mật") -> giữ ROMANTIC kể cả khi không có con.
    p = parse_intent("Vợ chồng tôi nghỉ tuần trăng mật ở Phú Quốc")
    assert "PURPOSE_ROMANTIC" in p.purposes


# ── D2. Sa Pa biến thể tách-từ ───────────────────────────────────────────────
def test_sapa_split_form_maps_to_loc():
    p = parse_intent("khách sạn ở Sa Pa")
    assert "LOC_SAPA" in p.location_concepts

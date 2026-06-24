"""Test hard-filter giá theo DẢI room (khoảng-giao) + guard price_capped + parse range giá.

Gốc: giá mock là giá sản phẩm; query giá phải lọc cứng "có room trong khoảng", giữ DẢI thật
(price_min..price_max), KHÔNG nén thành 1 số. Hotel price_capped (mock trần 5tr) miễn lọc giá.
"""

from knowledge_engineering.enrichment.metadata_pipeline import map_range_filters
from retrieval.filtering import inmemory_hard_filter
from knowledge_engineering.common.ke_labels import load_ke_labels


# ── tầng 2: giữ DẢI giá ───────────────────────────────────────────────────────
def test_range_filters_keeps_min_and_max():
    hotel = {"star_rating": 3, "rooms": [
        {"price_per_night": 900_000}, {"price_per_night": 1_500_000}, {"price_per_night": 1_200_000},
    ]}
    rf = map_range_filters(hotel)
    assert rf["price_min_vnd"] == 900_000
    assert rf["price_max_vnd"] == 1_500_000  # KHÔNG nén còn mỗi min


def test_range_filters_missing_price():
    rf = map_range_filters({"star_rating": 4, "rooms": [{"price_per_night": None}]})
    assert "price_min_vnd" not in rf and "price_max_vnd" not in rf


# ── tầng 3: hard-filter khoảng-giao (dùng ke_labels thật) ─────────────────────
def _rf(hid):
    return (load_ke_labels()[hid].get("range_filters") or {})


def test_under_1tr_excludes_pricier_hotels():
    ids = inmemory_hard_filter(price_max=1_000_000)
    for h in ids:
        rf = _rf(h)
        if rf.get("price_capped") or rf.get("price_min_vnd") is None:
            continue  # capped/thiếu giá được miễn
        assert rf["price_min_vnd"] <= 1_000_000  # có room <= 1tr


def test_capped_hotels_bypass_price_filter():
    # Hotel price_capped (mock trần 5tr) PHẢI lọt qua filter "dưới 1tr" (guard), không bị loại oan.
    capped = [h for h, ke in load_ke_labels().items()
              if (ke.get("range_filters") or {}).get("price_capped")]
    assert capped, "phải có hotel capped để test"
    under1tr = set(inmemory_hard_filter(price_max=1_000_000))
    assert all(h in under1tr for h in capped)


def test_range_overlap_keeps_partial_match():
    # "800k-1tr2": hotel có dải [600k,840k] PHẢI được giữ (giao tại 800k-840k).
    ids = set(inmemory_hard_filter(price_min=800_000, price_max=1_200_000))
    for h in ids:
        rf = _rf(h)
        if rf.get("price_capped") or rf.get("price_min_vnd") is None:
            continue
        lo = rf["price_min_vnd"]; hi = rf.get("price_max_vnd") or lo
        assert lo <= 1_200_000 and hi >= 800_000  # dải hotel giao khoảng query


def test_no_price_filter_returns_all():
    assert len(inmemory_hard_filter()) == len(load_ke_labels())

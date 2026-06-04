"""Tests cho helper parse review (tool crawl_reviews).

Chi test ham THUAN (khong can browser): detect_lang, parse_review_date,
parse_review_comment. Phan crawl that (phan trang qua browser) khong test o day.
"""
from crawler.parsers.agoda import (
    detect_lang,
    parse_review_date,
    parse_review_comment,
)


# --- detect_lang -----------------------------------------------------------
def test_detect_lang_vietnamese():
    assert detect_lang("Phòng sạch sẽ, nhân viên thân thiện") == "vi"
    assert detect_lang("Khách sạn tuyệt vời") == "vi"


def test_detect_lang_english():
    assert detect_lang("Great snorkeling, nice staff") == "en"
    assert detect_lang("Lovely room and beautiful view") == "en"


def test_detect_lang_other_and_empty():
    assert detect_lang("12345 !!!") == "other"
    assert detect_lang("") == "other"
    assert detect_lang(None) == "other"


# --- parse_review_date -----------------------------------------------------
def test_parse_date_vietnamese_full():
    assert parse_review_date("03 tháng 8 2025") == "2025-08-03"
    assert parse_review_date("21 tháng 12 2024") == "2024-12-21"


def test_parse_date_vietnamese_month_only():
    # "Thang N nam YYYY" khong co ngay -> chi thang
    assert parse_review_date("Tháng 7 năm 2025") == "2025-07"


def test_parse_date_english():
    assert parse_review_date("August 03, 2025") == "2025-08-03"
    assert parse_review_date("February 16, 2013") == "2013-02-16"
    assert parse_review_date("January 24, 2020") == "2020-01-24"


def test_parse_date_unparseable():
    assert parse_review_date("") is None
    assert parse_review_date(None) is None
    assert parse_review_date("hôm qua") is None       # khong co thang/nam
    assert parse_review_date("Foobar 99, 2020") is None  # thang khong hop le


# --- parse_review_comment --------------------------------------------------
def _raw_comment(**over):
    base = {
        "hotelReviewId": 123456,
        "rating": 7.2,
        "ratingText": "Rất tốt",
        "formattedReviewDate": "03 tháng 8 2025",
        "checkInDateMonthAndYear": "Tháng 7 năm 2025",
        "reviewTitle": "Tuyệt",
        "reviewComments": "Phòng đẹp, nhân viên thân thiện",
        "reviewPositives": "",
        "reviewNegatives": "",
        "responseText": "Cảm ơn quý khách",   # phai bi BO (#5)
        "reviewerInfo": {
            "displayMemberName": "Long",
            "reviewGroupName": "Cặp đôi",
            "countryName": "Việt Nam",
            "roomTypeName": "Deluxe",
        },
    }
    base.update(over)
    return base


def test_parse_comment_keeps_review_id():
    out = parse_review_comment(_raw_comment())
    assert out["review_id"] == 123456          # Task 2.4d can review_id THAT


def test_parse_comment_drops_response():
    out = parse_review_comment(_raw_comment())
    assert "response" not in out
    assert "responseText" not in out


def test_parse_comment_adds_date_iso_and_lang():
    out = parse_review_comment(_raw_comment())
    assert out["date_iso"] == "2025-08-03"
    assert out["lang"] == "vi"


def test_parse_comment_maps_reviewer_info():
    out = parse_review_comment(_raw_comment())
    assert out["reviewer_name"] == "Long"
    assert out["reviewer_type"] == "Cặp đôi"
    assert out["reviewer_country"] == "Việt Nam"
    assert out["room_type"] == "Deluxe"


def test_parse_comment_lang_from_title_when_text_empty():
    # review khong co text nhung co title/pos/neg -> lang suy tu title
    c = _raw_comment(reviewComments="", reviewTitle="Nice place",
                     reviewPositives="Great pool", reviewNegatives="")
    out = parse_review_comment(c)
    assert out["text"] == ""
    assert out["positives"] == "Great pool"
    assert out["lang"] == "en"

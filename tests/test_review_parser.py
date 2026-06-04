"""Tests cho helper parse review (tool crawl_reviews).

Chi test ham THUAN (khong can browser): parse_review_comment.
Phan crawl that (phan trang qua browser) khong test o day.
"""
from crawler.parsers.agoda import parse_review_comment


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
        "responseText": "Cảm ơn quý khách",
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


def test_parse_comment_keeps_response():
    # team chot them lai response cua KS vao review
    out = parse_review_comment(_raw_comment())
    assert out["response"] == "Cảm ơn quý khách"


def test_parse_comment_response_null_when_absent():
    out = parse_review_comment(_raw_comment(responseText=None))
    assert out["response"] is None


def test_parse_comment_no_lang_no_date_iso():
    # team chot bo lang va date_iso khoi review
    out = parse_review_comment(_raw_comment())
    assert "lang" not in out
    assert "date_iso" not in out
    assert out["date"] == "03 tháng 8 2025"   # van giu date tho cua Agoda


def test_parse_comment_maps_reviewer_info():
    out = parse_review_comment(_raw_comment())
    assert out["reviewer_name"] == "Long"
    assert out["reviewer_type"] == "Cặp đôi"
    assert out["reviewer_country"] == "Việt Nam"
    assert out["room_type"] == "Deluxe"


def test_parse_comment_text_empty_keeps_pos_neg():
    # review khong co text nhung co positives/negatives -> van giu
    c = _raw_comment(reviewComments="", reviewTitle="Nice place",
                     reviewPositives="Great pool", reviewNegatives="Small room")
    out = parse_review_comment(c)
    assert out["text"] == ""
    assert out["positives"] == "Great pool"
    assert out["negatives"] == "Small room"

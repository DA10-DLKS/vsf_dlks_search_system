"""Test _is_semantic_only: cổng quyết định vector có ĐỀ CỬ hotel vào pool hay không.

Câu cảm tính thuần (không concept/city/loc/brand/range, OBJ_HOTEL không tính) -> True -> union vector.
Câu có bất kỳ tín hiệu cấu trúc nào -> False -> pool dựng như cũ (không đụng).
"""

from retrieval.hybrid_search.pipeline import _is_semantic_only
from retrieval.query_processing.intent_parser import parse_intent


def test_semantic_only_true_for_pure_feeling():
    # Concept rỗng hoàn toàn
    assert _is_semantic_only(parse_intent("chỗ ở ấm cúng như nhà mình")) is True


def test_semantic_only_true_when_only_obj_hotel():
    # "khách sạn cũ kỹ hoài niệm" -> chỉ OBJ_HOTEL (trống nghĩa) -> vẫn semantic-only
    p = parse_intent("khách sạn cũ kỹ hoài niệm thời bao cấp")
    assert p.concepts == ["OBJ_HOTEL"]
    assert _is_semantic_only(p) is True


def test_semantic_only_false_with_city():
    assert _is_semantic_only(parse_intent("khách sạn ở Đà Nẵng")) is False


def test_semantic_only_false_with_concept():
    # SETTING_VIEW là tín hiệu cấu trúc -> đi luồng concept, không union
    assert _is_semantic_only(parse_intent("khách sạn view đẹp ở Đà Lạt")) is False


def test_semantic_only_false_with_specific_obj():
    # OBJ_RESORT (loại cụ thể) KHÁC OBJ_HOTEL -> là tín hiệu lọc -> không semantic-only
    p = parse_intent("resort đẹp lung linh buổi tối")
    assert "OBJ_RESORT" in p.object_types
    assert _is_semantic_only(p) is False


def test_semantic_only_false_with_price_range():
    assert _is_semantic_only(parse_intent("khách sạn tầm 1 triệu")) is False

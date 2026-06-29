"""test_fusion_ranking.py — Test tầng fusion/ranking (V13: trước đây 0 test).

Bảo vệ 2 fix cốt lõi:
  V1 — business_rerank chuẩn hóa text-signal [0,1] trước fuse (không bị review nuốt ~24×).
  V9 — RRF hợp nhất ở cấp hotel: doc xuất hiện ở CẢ 2 nguồn phải > doc chỉ 1 nguồn.
"""

from __future__ import annotations

from retrieval.reranking.fusion import (
    business_rerank,
    reciprocal_rank_fusion,
    rrf_by_hotel,
)


def _doc(hotel_id, rrf, review=0.0, concepts=None):
    return {
        "chunk_id": f"c_{hotel_id}",
        "hotel_id": hotel_id,
        "rrf_score": rrf,
        "metadata": {
            "ke_review_score": review,
            "ontology_concepts": concepts or [],
        },
    }


# ---- V1: text-signal không bị review nuốt -------------------------------------

def test_v1_text_signal_dominates_when_review_equal():
    """2 hotel review BẰNG nhau, hotel có rrf cao hơn (dù raw chỉ chênh 0.005) phải đứng trên.
    Trước fix: chênh rrf 0.005 * 0.5 = 0.0025, vô nghĩa -> thua. Sau chuẩn hóa min-max -> thắng."""
    docs = [
        _doc(1, rrf=0.010, review=8.0),   # rrf thấp
        _doc(2, rrf=0.016, review=8.0),   # rrf cao nhất -> phải top
    ]
    out = business_rerank(docs, concepts=[])
    assert out[0]["hotel_id"] == 2, "Hotel rrf cao nhất phải đứng đầu khi review bằng nhau"


def test_v1_text_signal_normalized_to_unit_range():
    """Sau chuẩn hóa, text_signal_norm của doc rrf cao nhất = 1.0, thấp nhất = 0.0."""
    docs = [_doc(1, rrf=0.004), _doc(2, rrf=0.016), _doc(3, rrf=0.010)]
    business_rerank(docs, concepts=[])
    by_id = {d["hotel_id"]: d["text_signal_norm"] for d in docs}
    assert by_id[2] == 1.0
    assert by_id[1] == 0.0
    assert 0.0 < by_id[3] < 1.0


def test_v1_text_signal_breaks_ties_measurably():
    """Sau calibrate (neural=0.05), text-signal là TIN HIỆU TINH CHỈNH, không áp đảo review.
    Khi review BẰNG nhau, text-signal phá thế hòa với mức đóng góp đo được (0.05 * range[0,1]).
    Đây là vai trò đúng: text bổ sung thứ hạng, KHÔNG lật đổ nhãn KE (vốn mạnh hơn trên corpus này)."""
    docs = [
        _doc(1, rrf=0.000, review=5.0),   # review giống nhau, text yếu
        _doc(2, rrf=0.016, review=5.0),   # review giống nhau, text mạnh -> thắng nhờ tie-break
    ]
    out = business_rerank(docs, concepts=[])
    assert out[0]["hotel_id"] == 2
    # chênh business_score đúng bằng đóng góp text-signal đã chuẩn hóa: 0.05 * (1.0 - 0.0)
    diff = out[0]["business_score"] - out[1]["business_score"]
    assert abs(diff - 0.05) < 1e-9


def test_v1_no_crash_when_all_rrf_zero():
    """Tất cả rrf=0 (không có text retrieval) -> span=0 -> neural=0, không chia 0."""
    docs = [_doc(1, rrf=0.0, review=9.0), _doc(2, rrf=0.0, review=5.0)]
    out = business_rerank(docs, concepts=[])
    assert out[0]["hotel_id"] == 1  # review quyết định khi không có text-signal


# ---- V9: RRF hợp nhất ở cấp hotel ---------------------------------------------

def test_v9_both_sources_beat_single_source():
    """Doc ở CẢ bm25 + vector phải có rrf > doc chỉ 1 nguồn (cùng rank). Đây là TOÀN BỘ lý do
    dùng RRF. Trước fix (chunk_id lệch nhau) điều này KHÔNG xảy ra."""
    bm25 = [{"hotel_id": 1, "chunk_id": "bm25_hotel_1"},
            {"hotel_id": 2, "chunk_id": "bm25_hotel_2"}]
    vector = [{"hotel_id": 1, "chunk_id": "chunk_1_a"},   # hotel 1 ở cả 2 nguồn
              {"hotel_id": 3, "chunk_id": "chunk_3_a"}]   # hotel 3 chỉ vector
    fused = rrf_by_hotel(bm25, vector)
    by_id = {d["hotel_id"]: d["rrf_score"] for d in fused}
    assert by_id[1] > by_id[3], "Hotel ở cả 2 nguồn phải > hotel chỉ 1 nguồn"
    assert by_id[1] > by_id[2]


def test_v9_dedup_by_hotel_not_chunk():
    """rrf_by_hotel gom theo hotel_id, mỗi hotel 1 entry (không nhân bản theo chunk)."""
    bm25 = [{"hotel_id": 1, "chunk_id": "bm25_hotel_1"}]
    vector = [{"hotel_id": 1, "chunk_id": "chunk_1_a"},
              {"hotel_id": 1, "chunk_id": "chunk_1_b"}]
    fused = rrf_by_hotel(bm25, vector)
    assert len([d for d in fused if d["hotel_id"] == 1]) == 1


# ---- V5: IDF concept weighting ưu tiên concept đặc trưng ----------------------

def test_v5_rare_concept_outranks_common_in_candidate():
    """Hotel khớp concept HIẾM (idf cao) phải vượt hotel khớp concept PHỔ THÔNG dù review thấp hơn.
    Tái hiện GS-015: hotel STYLE_LIVELY (hiếm) phải lọt cap trước hotel OBJ_HOTEL (phổ thông)."""
    from retrieval.filtering.hard_filter import build_candidates

    # hotel 1: khớp concept hiếm (idf cao), review thấp
    # hotel 2: khớp concept phổ thông (idf thấp), review cao
    cands = build_candidates(
        None, [1, 2], cap=1,
        review_score_by_hotel={1: 7.0, 2: 9.5},
        idf_score_by_hotel={1: 6.5, 2: 0.3},
    )
    assert cands == [1], "Hotel khớp concept hiếm (idf cao) phải được giữ khi cắt cap"


def test_v5_idf_score_higher_for_rarer_concept():
    """lookup_hotels_by_concepts: concept càng ít hotel (df nhỏ) → idf_score càng cao."""
    from retrieval.filtering.concept_index import lookup_hotels_by_concepts

    # index giả: RARE chỉ 1 hotel, COMMON 100 hotel
    index = {"RARE": {1}, "COMMON": set(range(1, 101))}
    res = lookup_hotels_by_concepts(["RARE", "COMMON"], index=index)
    # hotel 1 khớp cả 2; hotel 2..100 chỉ khớp COMMON → hotel 1 idf cao hơn
    assert res.idf_score[1] > res.idf_score[2]


# ---- V3: candidate rỗng → fallback (không màn hình trắng) ---------------------

class _FakeVector:
    """Vector service giả trả hotel cố định (cho nhánh fallback vector)."""
    def __init__(self, hotel_ids):
        self._ids = hotel_ids

    def search(self, query, candidate_hotel_ids=None, top_k=100):
        return {"results": [{"hotel_id": h, "chunk_id": f"c_{h}", "text": "x"} for h in self._ids]}


def test_v3_empty_candidate_falls_back_to_vector(monkeypatch):
    """Khi build_candidates ra rỗng + có vector service → lấy hotel từ vector (không trả rỗng)."""
    import retrieval.hybrid_search.pipeline as pl

    monkeypatch.setattr(pl, "build_candidates", lambda *a, **k: [])
    monkeypatch.setattr(pl, "review_scores", lambda: {1: 9.0, 2: 8.0})
    res = pl.run_hybrid_search("q", vector_service=_FakeVector([7, 8, 9]), bm25_service=None, top_n=5)
    assert res["n_candidates"] > 0, "Fallback vector phải lấp candidate rỗng"
    assert res["top_hotels"], "V3: phải có kết quả, không màn hình trắng"


def test_v3_empty_candidate_no_vector_uses_review_top(monkeypatch):
    """Candidate rỗng + KHÔNG vector → fallback top hotel theo review (vẫn không rỗng)."""
    import retrieval.hybrid_search.pipeline as pl

    monkeypatch.setattr(pl, "build_candidates", lambda *a, **k: [])
    monkeypatch.setattr(pl, "review_scores", lambda: {101: 9.5, 102: 9.0, 103: 8.0})
    res = pl.run_hybrid_search("q", vector_service=None, bm25_service=None, top_n=5)
    assert res["n_candidates"] > 0
    assert res["top_hotels"], "V3: fallback review-top phải trả kết quả"

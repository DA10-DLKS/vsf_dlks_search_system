import json

import pytest

from knowledge_engineering.common.normalize import normalize
from knowledge_engineering.enrichment import absa, ontology_mapper, query_demo


def test_normalize_fold_keeps_accented_and_unaccented_queries_compatible():
    assert normalize("hồ bơi", fold=True) == "ho boi"
    assert normalize("ho boi", fold=True) == "ho boi"
    assert normalize("yên tĩnh", fold=True) == "yen tinh"
    assert normalize("yen tinh", fold=True) == "yen tinh"


def test_synonym_dictionary_contains_folded_pool_surface_form():
    synonyms = ontology_mapper.load_synonyms()

    assert "ho boi" in synonyms
    assert "AMEN_POOL" in synonyms["ho boi"]


def test_query_demo_hotel_intent_wins_over_nearby_place_phrase():
    q = "tìm cho tôi khách sạn ở Nha Trang, có bể bơi trẻ con, gần biển, gần khu vui chơi"

    assert query_demo.is_place_intent(q)
    assert query_demo.is_hotel_intent(q)
    assert "AMEN_KIDS_POOL" in query_demo.parse_concepts(q)[0]
    assert "OBJ_HOTEL" in query_demo.parse_concepts(q)[0]


def test_query_demo_keeps_pure_place_intent():
    q = "Nha Trang có gì chơi?"

    assert query_demo.is_place_intent(q)
    assert not query_demo.is_hotel_intent(q)


def test_mapper_fuses_source_tag_and_rule_evidence():
    hotel = {
        "hotel_id": 1,
        "accommodation_type": "Hotel",
        "amenities": ["Pool"],
        "description_short": "Khach san co ho boi ngoai troi.",
    }
    source_tag_map = {
        "accommodation_type": {"Hotel": "OBJ_HOTEL"},
        "amenities": {"Pool": "AMEN_POOL"},
    }
    synonyms = {"ho boi": ["AMEN_POOL"]}
    facets = {"OBJ_HOTEL": "object_type", "AMEN_POOL": "amenity"}

    tags = ontology_mapper.map_hotel(hotel, source_tag_map, synonyms, facets)
    by_concept = {tag["concept"]: tag for tag in tags}

    assert by_concept["OBJ_HOTEL"]["sources"] == ["source_tag"]
    assert by_concept["AMEN_POOL"]["sources"] == ["rule", "source_tag"]
    assert by_concept["AMEN_POOL"]["confidence"] == pytest.approx(1.0)
    assert by_concept["AMEN_POOL"]["nature"] == "presence"


def test_mapper_rule_skips_negated_surface_forms_and_non_presence_facets():
    facets = {
        "AMEN_POOL": "amenity",
        "LOC_PHU_QUOC": "location",
        "STYLE_BOUTIQUE": "style",
    }

    negated = ontology_mapper.tag_rule(
        {"description_short": "Khach san khong co ho boi."},
        {"ho boi": ["AMEN_POOL"]},
        facets,
    )
    non_presence = ontology_mapper.tag_rule(
        {"description_short": "Khach san boutique o Phu Quoc."},
        {"boutique": ["STYLE_BOUTIQUE"], "phu quoc": ["LOC_PHU_QUOC"]},
        facets,
    )

    assert negated == []
    assert non_presence == []


def test_backfill_uses_surface_filter_and_per_concept_versions(tmp_path, monkeypatch):
    reviews_dir = tmp_path / "reviews"
    evidence_dir = tmp_path / "evidence"
    reviews_dir.mkdir()
    evidence_dir.mkdir()

    (reviews_dir / "hotel_1_reviews.json").write_text(
        json.dumps(
            {
                "reviews": [
                    {
                        "review_id": 101,
                        "rating": 9,
                        "text": "A small boutique hotel with a distinctive design.",
                    },
                    {
                        "review_id": 102,
                        "rating": 8,
                        "text": "A normal city hotel with clean rooms.",
                    },
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (evidence_dir / "hotel_1.json").write_text(
        json.dumps(
            {
                "101": {
                    "review_id": 101,
                    "items": [{"concept": "ASPECT_ROOM", "sentiment": "positive", "span": "clean"}],
                    "backfilled_versions": {"STYLE_VINTAGE": "old-version"},
                },
                "102": {
                    "review_id": 102,
                    "items": [{"concept": "ASPECT_ROOM", "sentiment": "positive", "span": "clean"}],
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    vocab = {
        "STYLE_BOUTIQUE": {"facet": "style", "label_vi": "boutique", "label_en": "Boutique"},
        "STYLE_VINTAGE": {"facet": "style", "label_vi": "vintage", "label_en": "Vintage"},
    }
    monkeypatch.setattr(absa, "REVIEWS_DIR", str(reviews_dir))
    monkeypatch.setattr(absa, "EVIDENCE_DIR", evidence_dir)
    monkeypatch.setattr(absa, "VOCAB", vocab)
    expected_version = absa.effective_prompt_version(vocab)
    calls = []

    def fake_analyze_review(text, system=absa.SYSTEM, allowed=None, want_novel=True):
        calls.append(text)
        assert allowed == {"STYLE_BOUTIQUE"}
        assert want_novel is False
        return {
            "overall_sentiment": "positive",
            "items": [
                {"concept": "STYLE_BOUTIQUE", "sentiment": "positive", "span": "boutique hotel"}
            ],
            "novel": [],
        }

    monkeypatch.setattr(absa, "analyze_review", fake_analyze_review)

    changed = absa.backfill_concepts(
        1,
        ["STYLE_BOUTIQUE"],
        max_workers=1,
        forms=["boutique"],
    )
    changed_again = absa.backfill_concepts(
        1,
        ["STYLE_BOUTIQUE"],
        max_workers=1,
        forms=["boutique"],
    )

    store = json.loads((evidence_dir / "hotel_1.json").read_text(encoding="utf-8"))
    review_101 = store["101"]
    review_102 = store["102"]

    assert changed == 1
    assert changed_again == 0
    assert len(calls) == 1
    assert any(item["concept"] == "STYLE_BOUTIQUE" for item in review_101["items"])
    assert review_101["backfilled_versions"]["STYLE_BOUTIQUE"] == expected_version
    assert review_101["backfilled_versions"]["STYLE_VINTAGE"] == "old-version"
    assert "backfilled_versions" not in review_102

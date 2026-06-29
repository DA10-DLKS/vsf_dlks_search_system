"""Tests cho relation_loader (Bước 4 roadmap)."""

import pytest

from knowledge_engineering.common import relation_loader as rl


CONCEPTS = {"LOC_PHU_QUOC", "SETTING_ISLAND", "AMEN_SPA", "PURPOSE_WELLNESS", "OBJ_RESORT"}


def make_row(**over):
    base = dict(
        source="PURPOSE_WELLNESS", target="AMEN_SPA", type="evidence_for",
        source_type="curated", confidence=0.9, use_as="boost", status="verified",
    )
    base.update(over)
    return base


def validate_row(**over):
    rel = rl._row_to_relation(make_row(**over), origin="curated", default_source_type="curated")
    rl._validate(rel, CONCEPTS)
    return rel


# ---- happy path ----

def test_valid_relation_passes():
    validate_row()


def test_real_files_load_and_validate():
    rels = rl.load_all_relations()
    assert rels, "phải có relation"
    # filter chỉ verified
    for r in rels:
        if r.use_as == "filter":
            assert r.status == "verified"


def test_load_relations_default_verified_only():
    verified = rl.load_relations(status={"verified"})
    assert verified
    assert all(r.status == "verified" for r in verified)


# ---- validation fail loud ----

def test_missing_target_raises():
    with pytest.raises(rl.RelationError, match="target không tồn tại"):
        validate_row(target="AMEN_DOES_NOT_EXIST")


def test_missing_source_raises():
    with pytest.raises(rl.RelationError, match="source không tồn tại"):
        validate_row(source="NOPE")


def test_bad_enum_type_raises():
    with pytest.raises(rl.RelationError, match="type không hợp lệ"):
        validate_row(type="loves")


def test_bad_use_as_raises():
    with pytest.raises(rl.RelationError, match="use_as không hợp lệ"):
        validate_row(use_as="lol")


def test_confidence_out_of_range_raises():
    with pytest.raises(rl.RelationError, match="confidence ngoài"):
        validate_row(confidence=1.5)


def test_filter_requires_verified():
    with pytest.raises(rl.RelationError, match="use_as=filter chỉ cho status=verified"):
        validate_row(use_as="filter", status="candidate")


def test_generated_cannot_be_verified():
    with pytest.raises(rl.RelationError, match="không được status=verified"):
        validate_row(source_type="generated_lift", status="verified", use_as="boost")


def test_rejected_needs_reason():
    with pytest.raises(rl.RelationError, match="thiếu reject_reason"):
        validate_row(status="rejected", use_as="boost")


# ---- dedup / precedence ----

def test_dedup_curated_beats_legacy():
    curated = rl.Relation(
        source="PURPOSE_WELLNESS", target="AMEN_SPA", type="evidence_for",
        source_type="curated", confidence=0.9, use_as="boost", status="verified",
        origin="curated",
    )
    legacy = rl.Relation(
        source="PURPOSE_WELLNESS", target="AMEN_SPA", type="cooccurs_with",
        source_type="legacy_related", confidence=0.6, use_as="suggestion", status="candidate",
        origin="legacy",
    )
    out = rl._dedup([legacy, curated])
    assert len(out) == 1
    assert out[0].origin == "curated"
    assert out[0].status == "verified"


def test_dedup_rejected_beats_candidate():
    rejected = rl.Relation(
        source="PRICE_LUXURY", target="STYLE_LUXURY", type="cooccurs_with",
        source_type="generated_lift", confidence=0.5, use_as="suggestion",
        status="rejected", origin="rejected", reject_reason="x",
    )
    candidate = rl.Relation(
        source="PRICE_LUXURY", target="STYLE_LUXURY", type="cooccurs_with",
        source_type="generated_lift", confidence=0.5, use_as="boost",
        status="candidate", origin="candidates",
    )
    out = rl._dedup([candidate, rejected])
    assert len(out) == 1
    assert out[0].origin == "rejected"


def test_phu_quoc_island_is_filter():
    filters = rl.load_relations(status={"verified"}, use_as={"filter"})
    pairs = {(r.source, r.target) for r in filters}
    assert ("LOC_PHU_QUOC", "SETTING_ISLAND") in pairs


# ---- status hàng đợi pending/approved (luồng STYLE) ----

def test_pending_status_is_valid():
    validate_row(status="pending", source_type="generated_lift", use_as="boost")


def test_approved_status_is_valid():
    validate_row(status="approved", source_type="generated_lift", use_as="boost")


def test_pending_not_in_verified_load():
    """Candidate pending KHÔNG được lọt vào tập verified mà query layer dùng."""
    verified = rl.load_relations(status={"verified"})
    assert all(r.status == "verified" for r in verified)
    # các status hàng đợi không phải verified
    assert "pending" in rl.VALID_STATUS and "approved" in rl.VALID_STATUS
    assert rl.NOT_LIVE_STATUS == {"pending", "approved", "candidate"}

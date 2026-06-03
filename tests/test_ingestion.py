"""Tests for ingestion (Layer 2)."""

from __future__ import annotations

import pytest

# TODO(hieudm): bỏ skip và implement từng test theo dưới.
pytestmark = pytest.mark.skip(reason="TODO(hieudm): implement ingestion tests")


# ---------------------------------------------------------------------------
# cleaning
# ---------------------------------------------------------------------------

def test_normalize_unicode_nfc() -> None:
    # TODO(hieudm): assert NFC applied
    pass


def test_collapse_whitespace() -> None:
    # TODO(hieudm): "a  b\\n\\nc" -> "a b c"
    pass


def test_strip_html_removes_tags_and_keeps_text() -> None:
    # TODO(hieudm): "<p>Hello <b>world</b></p>" -> "Hello world"
    pass


def test_strip_html_extracts_image_urls() -> None:
    # TODO(hieudm): assert image_urls populated
    pass


# ---------------------------------------------------------------------------
# validation
# ---------------------------------------------------------------------------

def test_validate_document_valid_passes() -> None:
    # TODO(hieudm): doc đúng schema -> is_valid=True, issues=[]
    pass


def test_validate_document_missing_required_field() -> None:
    # TODO(hieudm): thiếu field bắt buộc -> is_valid=False, có error
    pass


def test_validate_document_wrong_type() -> None:
    # TODO(hieudm): sai kiểu dữ liệu -> error
    pass


def test_filter_valid_drops_invalid_when_requested() -> None:
    # TODO(hieudm): mix valid/invalid -> chỉ giữ valid khi drop_on_error=True
    pass


# ---------------------------------------------------------------------------
# quality checks (Missing Rate, Duplicate Rate)
# ---------------------------------------------------------------------------

def test_compute_missing_rate_under_target() -> None:
    # TODO(hieudm): batch có < 5% missing -> returned_rate < MISSING_RATE_TARGET
    pass


def test_compute_duplicate_rate_under_target() -> None:
    # TODO(hieudm): batch có < 2% trùng -> returned_rate < DUPLICATE_RATE_TARGET
    pass


def test_build_report_passes_both_targets() -> None:
    # TODO(hieudm): passed_missing=True and passed_duplicate=True
    pass


# ---------------------------------------------------------------------------
# deduplication
# ---------------------------------------------------------------------------

def test_shingle_ngram_size() -> None:
    # TODO(hieudm): "abcde", n=3 -> {"abc","bcd","cde"}
    pass


def test_minhash_signature_deterministic() -> None:
    # TODO(hieudm): cùng input -> cùng signature (cùng seed)
    pass


def test_find_duplicates_groups_near_identical_docs() -> None:
    # TODO(hieudm): 2 doc gần giống + 1 doc khác -> 1 group size=2
    pass


def test_dedup_documents_keeps_one_per_group() -> None:
    # TODO(hieudm): đầu vào 3 doc trùng -> đầu ra 1 doc
    pass


# ---------------------------------------------------------------------------
# pipeline orchestration
# ---------------------------------------------------------------------------

def test_run_ingest_end_to_end_on_samples(tmp_path) -> None:
    # TODO(hieudm): tạo mock raw -> chạy run() -> assert cleaned/ có file,
    # data_quality_report.md được tạo
    pass

"""Sprint 2 pipeline: clean raw documents và ghi ra data/cleaned/.

Luồng:
    data/raw/*.json  ──▶  strip HTML  ──▶  normalize text  ──▶  data/cleaned/*.json
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

# TODO(hieudm): Import module thật khi đã implement:
# from ingestion.cleaning.html_stripper import strip_html
# from ingestion.cleaning.text_normalizer import normalize_text
# from ingestion.connectors import read_raw_documents  # nếu cần

DEFAULT_INPUT_DIR: Path = Path(__file__).resolve().parents[1] / "data" / "raw"
DEFAULT_OUTPUT_DIR: Path = Path(__file__).resolve().parents[1] / "data" / "cleaned"


def read_raw(input_dir: Path = DEFAULT_INPUT_DIR) -> Iterable[dict[str, Any]]:
    """Đọc tất cả JSON trong data/raw/. Yield từng document."""
    # TODO(hieudm): implement (json.load, generator)
    raise NotImplementedError("read_raw not implemented")


def clean_document(doc: dict[str, Any]) -> dict[str, Any]:
    """Strip HTML + normalize text cho 1 document, giữ nguyên metadata."""
    # TODO(hieudm): gọi strip_html(), normalize_text() và trả về dict mới
    raise NotImplementedError("clean_document not implemented")


def write_cleaned(
    docs: Iterable[dict[str, Any]],
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> list[Path]:
    """Ghi các document đã clean ra data/cleaned/. Trả về danh sách file path."""
    # TODO(hieudm): implement (ghi theo doc_id hoặc gộp 1 file JSONL)
    raise NotImplementedError("write_cleaned not implemented")


def run(
    input_dir: Path = DEFAULT_INPUT_DIR,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> list[Path]:
    """Entry point: đọc raw → clean → ghi cleaned. Trả về danh sách file output."""
    # TODO(hieudm): orchestrate read_raw → clean_document → write_cleaned
    raise NotImplementedError("clean_pipeline.run not implemented")


def main() -> None:
    # TODO(hieudm): parse CLI args + gọi run()
    raise NotImplementedError("clean_pipeline.main not implemented")


if __name__ == "__main__":
    main()

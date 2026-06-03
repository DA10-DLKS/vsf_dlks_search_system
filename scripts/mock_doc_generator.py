"""Sinh mock documents hợp lệ + không hợp lệ (Sprint 1 output).

Dùng để phát triển và test pipeline ingestion khi chưa có dữ liệu thật
từ crawler. Mỗi document sinh ra phải tuân theo `contracts/data_schema.json`.

Output mặc định: `data/samples/mock_documents_v1.json` (200 docs theo plan).
"""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any

# TODO(hieudm): Đọc contracts/data_schema.json để sinh doc bám sát schema thật
# (đặc biệt enum, format, required field) thay vì hardcode tại đây.
# TODO(hieudm): Sinh thêm tỷ lệ cố định document "không hợp lệ" (vd: 10-15%) để
# test validation pipeline — bật/tắt bằng tham số.

DEFAULT_OUTPUT: Path = Path(__file__).resolve().parents[1] / "data" / "samples" / "mock_documents_v1.json"
DEFAULT_NUM_DOCS: int = 200
DEFAULT_INVALID_RATIO: float = 0.0
RANDOM_SEED: int = 42


def _generate_valid_doc(doc_id: str) -> dict[str, Any]:
    """Sinh 1 document hợp lệ theo schema (placeholder)."""
    # TODO(hieudm): implement — tham chiếu data_schema.json
    raise NotImplementedError("_generate_valid_doc not implemented")


def _generate_invalid_doc(doc_id: str) -> dict[str, Any]:
    """Sinh 1 document cố tình vi phạm schema (placeholder)."""
    # TODO(hieudm): implement — thiếu field, sai kiểu, vượt min/max length…
    raise NotImplementedError("_generate_invalid_doc not implemented")


def generate_mock_documents(
    n: int = DEFAULT_NUM_DOCS,
    *,
    invalid_ratio: float = DEFAULT_INVALID_RATIO,
    seed: int = RANDOM_SEED,
) -> list[dict[str, Any]]:
    """Sinh `n` mock document (gồm cả hợp lệ & không hợp lệ)."""
    # TODO(hieudm): implement
    raise NotImplementedError("generate_mock_documents not implemented")


def write_mock_documents(
    output_path: Path | str = DEFAULT_OUTPUT,
    n: int = DEFAULT_NUM_DOCS,
    **kwargs,
) -> Path:
    """Generate + ghi ra file JSON, trả về path."""
    # TODO(hieudm): implement (dùng generate_mock_documents + json.dump)
    raise NotImplementedError("write_mock_documents not implemented")


def main() -> None:
    """CLI: `python -m scripts.mock_doc_generator`."""
    # TODO(hieudm): parse argparse nếu cần (--n, --invalid-ratio, --output)
    raise NotImplementedError("mock_doc_generator.main not implemented")


if __name__ == "__main__":
    main()

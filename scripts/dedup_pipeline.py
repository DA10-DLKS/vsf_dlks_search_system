"""Sprint 2 pipeline: khử trùng lặp cleaned documents (near-duplicate).

Luồng:
    data/cleaned/*.json  ──▶  MinHash + LSH  ──▶  bỏ trùng  ──▶  data/cleaned/ (in-place)
                                                       │
                                                       └─▶  data/dedup_groups.json
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

# TODO(hieudm): Import module thật khi đã implement:
# from ingestion.deduplication.minhash import dedup_documents, DuplicateGroup

DEFAULT_INPUT_DIR: Path = Path(__file__).resolve().parents[1] / "data" / "cleaned"
DEFAULT_GROUPS_PATH: Path = Path(__file__).resolve().parents[1] / "data" / "dedup_groups.json"


def find_duplicate_groups(
    docs: Iterable[dict[str, Any]],
    *,
    text_field: str = "content",
    id_field: str = "id",
) -> list[Any]:
    """Trả về danh sách DuplicateGroup."""
    # TODO(hieudm): gọi dedup_documents hoặc find_duplicates từ minhash module
    raise NotImplementedError("find_duplicate_groups not implemented")


def write_groups(
    groups: Iterable[Any],
    output_path: Path = DEFAULT_GROUPS_PATH,
) -> Path:
    """Persist các nhóm trùng ra JSON (để audit + tính duplicate rate)."""
    # TODO(hieudm): implement (json.dump với dataclass.asdict)
    raise NotImplementedError("write_groups not implemented")


def run(
    input_dir: Path = DEFAULT_INPUT_DIR,
    *,
    groups_path: Path = DEFAULT_GROUPS_PATH,
) -> dict[str, int]:
    """Entry point: tìm trùng + ghi nhóm. Trả về summary {total, kept, removed}."""
    # TODO(hieudm): orchestrate
    raise NotImplementedError("dedup_pipeline.run not implemented")


def main() -> None:
    # TODO(hieudm): parse CLI args + gọi run()
    raise NotImplementedError("dedup_pipeline.main not implemented")


if __name__ == "__main__":
    main()

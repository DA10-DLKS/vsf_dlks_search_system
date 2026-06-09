"""Sinh synonym_dictionary.yaml từ ontology — Task 1.6, Sprint 1.

LỚP A (tự sinh từ ontology): bản đồ surface form (đã chuẩn hóa) -> concept_id.
Bàn giao Anh Tài: dùng trong query_processor lúc query. Bạn cũng dùng ở Tầng 1 tagger.

Sinh từ surface_forms của ontology/core/*.yaml, mỗi form index ở CẢ HAI dạng normalize
(có dấu + bỏ dấu) để query gõ kiểu nào cũng khớp.

XUNG ĐỘT (một form -> nhiều concept): GIỮ LIST, không ghi đè. Ví dụ "lãng mạn" ->
[PURPOSE_ROMANTIC, STYLE_ROMANTIC], "ẩm thực" -> [AMEN_RESTAURANT, ASPECT_FOOD].
Query match được mọi ứng viên, tầng score/context phân xử sau. (Khác mẫu DA10 1-1 — có chủ đích.)

Output schema (ontology/synonym_dictionary.yaml):
    version: "..."
    synonyms:
      "<surface form đã normalize>": [CONCEPT_ID, ...]   # list, sort

Chạy: .venv/Scripts/python.exe -X utf8 -m knowledge_engineering.common.build_synonym_index
"""

import glob

import yaml

from knowledge_engineering.common.normalize import normalize

CORE_GLOB = "ontology/core/*.yaml"
OUT_YAML = "ontology/synonym_dictionary.yaml"
VERSION = "2.0.0"


def build_index(core_glob: str = CORE_GLOB) -> dict[str, list[str]]:
    """surface form (normalize, cả 2 dạng) -> sorted list concept_id."""
    idx: dict[str, set] = {}

    def add(form: str, cid: str) -> None:
        idx.setdefault(form, set()).add(cid)

    for f in sorted(glob.glob(core_glob)):
        d = yaml.safe_load(open(f, encoding="utf-8"))
        for cid, v in (d.get("concepts") or {}).items():
            sf = v.get("surface_forms", {}) or {}
            for lang in ("vi", "en"):
                for lb in sf.get(lang, []) or []:
                    add(normalize(lb), cid)
                    add(normalize(lb, fold=True), cid)
    return {form: sorted(cids) for form, cids in sorted(idx.items())}


def write(out_yaml: str = OUT_YAML) -> tuple[int, int]:
    """Ghi synonym_dictionary.yaml. Trả (số form, số form xung đột >1 concept)."""
    idx = build_index()
    conflicts = sum(1 for cids in idx.values() if len(cids) > 1)
    header = (
        "# AUTO-GENERATED — KHÔNG sửa tay. Sinh bởi "
        "knowledge_engineering/common/build_synonym_index.py\n"
        "# Nguồn: ontology/core/*.yaml (surface_forms). Bàn giao -> Anh Tài (query_processor).\n"
        "# Mỗi form -> LIST concept_id (giữ mọi ứng viên khi một form ứng nhiều concept).\n"
    )
    with open(out_yaml, "w", encoding="utf-8") as fh:
        fh.write(header)
        yaml.safe_dump(
            {"version": VERSION, "synonyms": idx},
            fh,
            allow_unicode=True,
            sort_keys=False,
        )
    return len(idx), conflicts


if __name__ == "__main__":
    n, conf = write()
    print(f"Đã ghi {n} surface form ({conf} form đa-concept) -> {OUT_YAML}")

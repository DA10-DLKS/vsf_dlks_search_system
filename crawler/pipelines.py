"""pipelines — luu / tach record ra file, slugify ten, checkpoint.

Tach phan I/O ra khoi logic crawl. Duong dan data nam o `data/` cung cap
voi package `crawler/` (xem DATA_DIR).
"""
import json
import os
import re

# data/ cung cap voi crawler/  (../data tinh tu file nay)
_PKG_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.normpath(os.path.join(_PKG_DIR, "..", "data", "raw"))
HOTELS_DIR = os.path.join(DATA_DIR, "hotels")
REVIEWS_DIR = os.path.join(DATA_DIR, "reviews")

LIST_FILE = os.path.join(DATA_DIR, "hotels_list.json")
DETAIL_FILE = os.path.join(DATA_DIR, "hotels_detail.json")
FAIL_FILE = os.path.join(DATA_DIR, "failed.json")


# ---------------------------------------------------------------------------
# Ten file
# ---------------------------------------------------------------------------
_VN_TABLE = str.maketrans(
    "áàảãạâấầẩẫậăắằẳẵặéèẻẽẹêếềểễệíìỉĩịóòỏõọôốồổỗộơớờởỡợúùủũụưứừửữựýỳỷỹỵđ",
    "aaaaaaaaaaaaaaaaaeeeeeeeeeeeiiiiiooooooooooooooooouuuuuuuuuuuyyyyyd")


def slugify(name: str) -> str:
    """Ten khach san -> phan slug de doc cho ten file (bo dau, ky tu la)."""
    if not name:
        return ""
    name = name.split("(")[0].strip()   # bo phan trong ngoac (ten tieng anh)
    s = name.lower().translate(_VN_TABLE)
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s[:50]


def hotel_filename(hotel_id, name: str) -> str:
    slug = slugify(name)
    return f"hotel_{hotel_id}_{slug}.json" if slug else f"hotel_{hotel_id}.json"


# ---------------------------------------------------------------------------
# Doc / ghi
# ---------------------------------------------------------------------------
def _read_json(path, default):
    if not os.path.exists(path):
        return default
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def _write_json(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def save_list(hotels: list):
    _write_json(LIST_FILE, hotels)


def load_list() -> list:
    return _read_json(LIST_FILE, [])


def save_failed(failed: list):
    if failed:
        _write_json(FAIL_FILE, failed)


def save_detail_record(record: dict) -> str:
    """Luu 1 record ra data/hotels/hotel_<id>_<slug>.json. Tra ve path."""
    os.makedirs(HOTELS_DIR, exist_ok=True)
    fname = hotel_filename(record["hotel_id"], record.get("name", ""))
    path = os.path.join(HOTELS_DIR, fname)
    _write_json(path, record)
    return path


def save_reviews(record: dict) -> str:
    """Luu review record ra data/reviews/hotel_<id>_reviews.json (ghi de).

    File rieng, doc lap voi file KS (sample_comments giu nguyen lam preview).
    Tra ve path."""
    os.makedirs(REVIEWS_DIR, exist_ok=True)
    path = os.path.join(REVIEWS_DIR, f"hotel_{record['hotel_id']}_reviews.json")
    _write_json(path, record)
    return path


def reviews_done_ids() -> set:
    """hotel_id da co file review (de bo qua khi chay batch)."""
    if not os.path.isdir(REVIEWS_DIR):
        return set()
    ids = set()
    for f in os.listdir(REVIEWS_DIR):
        m = re.match(r"hotel_(\d+)_reviews\.json$", f)
        if m:
            ids.add(int(m.group(1)))
    return ids


def hotel_file_done_ids() -> set:
    """hotel_id da co file detail rieng trong data/raw/hotels."""
    if not os.path.isdir(HOTELS_DIR):
        return set()
    ids = set()
    for f in os.listdir(HOTELS_DIR):
        m = re.match(r"hotel_(\d+)(?:_|\.json)", f)
        if m:
            ids.add(int(m.group(1)))
    return ids


# ---------------------------------------------------------------------------
# Checkpoint cho nhanh batch (gop tat ca record vao 1 file de resume)
# ---------------------------------------------------------------------------
def load_detail_progress():
    """Tra ve (list_records, set_done_ids) tu data/hotels_detail.json."""
    existing = _read_json(DETAIL_FILE, [])
    if not isinstance(existing, list):
        return [], set()
    return existing, {h.get("hotel_id") for h in existing}


def save_detail_progress(records: list):
    _write_json(DETAIL_FILE, records)


def upsert_detail(record: dict) -> str:
    """Them/cap nhat 1 record vao kho tong data/hotels_detail.json theo hotel_id.

    Dam bao khong trung id: neu hotel_id da co -> ghi de record cu; chua co ->
    them moi. Dung cho nhanh link de dong bo vao kho tong (giong nhanh batch).
    Tra ve 'updated' hoac 'added'.
    """
    records = _read_json(DETAIL_FILE, [])
    if not isinstance(records, list):
        records = []
    hid = record.get("hotel_id")
    for i, r in enumerate(records):
        if r.get("hotel_id") == hid:
            records[i] = record
            _write_json(DETAIL_FILE, records)
            return "updated"
    records.append(record)
    _write_json(DETAIL_FILE, records)
    return "added"


def split_detail_file(records: list = None):
    """Tach data/hotels_detail.json (mang) -> moi KS 1 file data/hotels/."""
    if records is None:
        records = _read_json(DETAIL_FILE, [])
    os.makedirs(HOTELS_DIR, exist_ok=True)
    n = 0
    for h in records:
        save_detail_record(h)
        n += 1
    return n

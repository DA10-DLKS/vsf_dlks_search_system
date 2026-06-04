"""validate — quet output data/raw/hotels/ -> tim record THIEU do loi crawl.

Dung sau khi crawl (nhat la o quy mo lon: vai tram KS, luon co % loi ngau
nhien). Thay vi crawl lai ca luot, validate.py xac dinh dung cac KS con thieu
field BAT BUOC va xuat ra recrawl_queue.json de `main.py --recrawl` chay lai
dung nhung cai do.

Phan biet 2 loai thieu (dua vao field `_incomplete` do spider gan):
  - crawl_miss  : thieu do crawl loi (review lazy-load chua kip ve...) -> RECRAWL
  - few_reviews : thieu THAT (KS qua it review, Agoda khong render) -> BO QUA

Cach dung:
    python -m crawler.validate            # quet + in bao cao + ghi queue
    python -m crawler.validate --quiet    # chi ghi queue, it log
"""
import json
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

if __package__ in (None, ""):
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from crawler import pipelines as PL

RECRAWL_FILE = os.path.join(PL.DATA_DIR, "recrawl_queue.json")

# Cac key top-level BAT BUOC phai co (lay tu schema chuan: hotel co day du nguon).
# Cac field tong hop/optional (faq, activities, word_cloud...) KHONG nam o day vi
# co the vang mat hop le.
REQUIRED_TOP_KEYS = [
    "hotel_id", "name", "address", "city",
    "description", "amenities",
    "rooms", "room_grid",
    "reviews_detail", "rating_overall", "rating_breakdown", "rating_count",
]

# Cac sub-field trong reviews_detail can co (khi reviews_detail ton tai)
REVIEW_SUBFIELDS = ["score", "grades", "tags", "demographics", "sample_comments"]


def _is_empty(v):
    return v is None or (isinstance(v, (list, dict, str)) and len(v) == 0)


def _incomplete_real_fields(record: dict) -> set:
    """Cac field ma spider da danh dau la THIEU THAT (khong nen recrawl)."""
    real = set()
    for it in (record.get("_incomplete") or []):
        if isinstance(it, dict) and it.get("reason") == "few_reviews":
            real.add(it.get("field"))
    return real


def check_record(record: dict) -> list:
    """Tra ve danh sach field thieu DO LOI CRAWL (da loai thieu-that).

    Rong = record day du (theo tieu chi bat buoc).
    """
    real_missing = _incomplete_real_fields(record)
    # Neu KS thieu review THAT thi cac field review-related khong tinh la loi
    skip_review = "reviews_detail.grades" in real_missing

    missing = []
    for k in REQUIRED_TOP_KEYS:
        if skip_review and k in (
            "reviews_detail", "rating_overall", "rating_breakdown", "rating_count"
        ):
            continue
        if k not in record or _is_empty(record.get(k)):
            missing.append(k)

    # Kiem tra sau trong reviews_detail neu no ton tai va khong phai thieu-that
    if not skip_review:
        rv = record.get("reviews_detail")
        if isinstance(rv, dict):
            for sf in REVIEW_SUBFIELDS:
                if _is_empty(rv.get(sf)):
                    missing.append(f"reviews_detail.{sf}")

    return missing


def validate_dir(hotels_dir: str = None, quiet: bool = False) -> dict:
    """Quet thu muc -> {ok, incomplete_real, recrawl}. Ghi recrawl_queue.json."""
    hotels_dir = hotels_dir or PL.HOTELS_DIR
    files = sorted(
        os.path.join(hotels_dir, f)
        for f in os.listdir(hotels_dir)
        if f.endswith(".json")
    )

    ok, real, recrawl = [], [], []
    for fpath in files:
        try:
            with open(fpath, encoding="utf-8") as f:
                rec = json.load(f)
        except Exception as e:
            if not quiet:
                print(f"  [!] doc loi {os.path.basename(fpath)}: {e}")
            continue

        hid = rec.get("hotel_id")
        missing = check_record(rec)
        if missing:
            recrawl.append({
                "hotel_id": hid,
                "name": rec.get("name"),
                "property_page": rec.get("property_page"),
                "source_url": rec.get("source_url"),
                "missing": missing,
            })
        elif rec.get("_incomplete"):
            real.append({"hotel_id": hid, "name": rec.get("name"),
                         "incomplete": rec["_incomplete"]})
        else:
            ok.append(hid)

    PL._write_json(RECRAWL_FILE, recrawl)

    if not quiet:
        print("=" * 60)
        print(f"  Tong: {len(files)} file")
        print(f"  OK day du            : {len(ok)}")
        print(f"  Thieu THAT (bo qua)  : {len(real)}")
        print(f"  Can RECRAWL          : {len(recrawl)}")
        print("=" * 60)
        for it in recrawl:
            print(f"  [recrawl] {it['hotel_id']} {str(it['name'])[:35]:35} "
                  f"thieu={it['missing']}")
        for it in real:
            reasons = {x.get("field"): x.get("reason") for x in it["incomplete"]}
            print(f"  [thieu that] {it['hotel_id']} {str(it['name'])[:35]:35} "
                  f"{reasons}")
        print(f"\n  -> da ghi {len(recrawl)} muc vao {RECRAWL_FILE}")

    return {"ok": ok, "incomplete_real": real, "recrawl": recrawl}


def load_recrawl_queue() -> list:
    return PL._read_json(RECRAWL_FILE, [])


if __name__ == "__main__":
    validate_dir(quiet="--quiet" in sys.argv[1:])

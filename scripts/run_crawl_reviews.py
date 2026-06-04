"""run_crawl_reviews — tool crawl REVIEW chi tiet cua khach san Agoda.

Khac voi crawl KS (lay sample_comments ~10 cai), tool nay phan trang endpoint
review/HotelReviews de lay nhieu review (cap dong, mac dinh 250) phuc vu
trich xuat entity/ontology (DA10 KE). Output: data/raw/reviews/hotel_<id>_reviews.json

Cach dung:
  # 1 link KS
  .venv\\Scripts\\python scripts\\run_crawl_reviews.py "https://www.agoda.com/...hotel=1973..."

  # 1 hotel_id (doc URL tu file KS da crawl trong data/raw/hotels/)
  .venv\\Scripts\\python scripts\\run_crawl_reviews.py --id 1973

  # batch: tat ca KS da crawl trong data/raw/hotels/ (bo qua cai da co review)
  .venv\\Scripts\\python scripts\\run_crawl_reviews.py --all
  .venv\\Scripts\\python scripts\\run_crawl_reviews.py --all --limit 5 --force

Tham so:
  --id N        crawl review cho 1 hotel_id (tim source_url trong file KS)
  --all         crawl review cho moi KS trong data/raw/hotels/
  --limit N     gioi han so KS (di voi --all)
  --force       crawl lai ca KS da co file review (mac dinh: bo qua)
  --headful     hien trinh duyet
  --site S      site (mac dinh agoda)
"""
import argparse
import glob
import json
import os
import random
import sys
import time
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from crawler import pipelines as PL  # noqa: E402
from crawler.browser import browser_context  # noqa: E402
from crawler.configs import load_config  # noqa: E402
from crawler.spiders import SPIDERS  # noqa: E402


def _hotel_from_file(path: str) -> dict | None:
    """Doc file KS da crawl -> hotel dict du de crawl review (id + url)."""
    try:
        with open(path, encoding="utf-8") as f:
            rec = json.load(f)
    except Exception:
        return None
    hid = rec.get("hotel_id")
    if not hid:
        return None
    return {
        "hotel_id": hid,
        "name": rec.get("name"),
        # source_url cua file KS la link detail chuan -> goto thang
        "full_url": rec.get("source_url"),
        "property_page": None,
        # bu khi seed Agoda thieu reviewCount (KS multi-provider)
        "review_count": rec.get("review_count"),
    }


def _find_hotel_by_id(hotel_id: int) -> dict | None:
    for path in glob.glob(os.path.join(PL.HOTELS_DIR, f"hotel_{hotel_id}_*.json")):
        h = _hotel_from_file(path)
        if h:
            return h
    # fallback: ten file khong co slug
    p = os.path.join(PL.HOTELS_DIR, f"hotel_{hotel_id}.json")
    if os.path.exists(p):
        return _hotel_from_file(p)
    return None


def _all_hotels() -> list:
    hotels = []
    for path in sorted(glob.glob(os.path.join(PL.HOTELS_DIR, "hotel_*.json"))):
        h = _hotel_from_file(path)
        if h:
            hotels.append(h)
    return hotels


def _run_one(spider, context, hotel: dict, n=None, total=None, retries=2) -> bool:
    prefix = f"[{n}/{total}] " if n else ""
    hid = hotel.get("hotel_id")
    # Retry ca quy trinh: KS review nang tra response muon / post phan trang lo
    # giua batch -> thu lai (moi lan mo trang moi). retries=so lan thu THEM.
    err = None
    for attempt in range(retries + 1):
        record, err = spider.crawl_reviews(context, hotel)
        if not err:
            path = PL.save_reviews(record)
            tag = f" (sau {attempt+1} lan)" if attempt else ""
            print(f"  {prefix}{hid} OK -> {record['crawled_count']}/{record['comments_count_total']} "
                  f"review (tier={record['cap_tier']}, cap={record['cap_applied']}){tag} "
                  f"-> {os.path.basename(path)}")
            return True
        if attempt < retries:
            print(f"  {prefix}{hid} thu lai ({attempt+1}/{retries}): {err}")
            time.sleep(random.uniform(2, 4))
    print(f"  {prefix}{hid} LOI: {err}")
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("target", nargs="?", help="link KS Agoda")
    ap.add_argument("--id", type=int, help="hotel_id (tim url trong file KS da crawl)")
    ap.add_argument("--all", action="store_true", help="moi KS trong data/raw/hotels/")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--force", action="store_true", help="crawl lai ca KS da co review")
    ap.add_argument("--headful", action="store_true")
    ap.add_argument("--site", default="agoda")
    args = ap.parse_args()

    if args.site not in SPIDERS:
        print(f"[X] Chua ho tro site '{args.site}'. Co san: {list(SPIDERS)}")
        sys.exit(1)
    spider = SPIDERS[args.site](load_config(args.site), headful=args.headful)
    delay = spider.cfg["rate_limit"]["between_details"]

    # --- xac dinh danh sach hotel can crawl ---
    if args.target:
        hotel = spider.parse_url(args.target)
        if not hotel:
            print("[X] Khong parse duoc link.")
            sys.exit(1)
        hotels = [hotel]
    elif args.id:
        hotel = _find_hotel_by_id(args.id)
        if not hotel:
            print(f"[X] Khong tim thay file KS cho hotel_id={args.id} trong {PL.HOTELS_DIR}")
            sys.exit(1)
        hotels = [hotel]
    elif args.all:
        hotels = _all_hotels()
        if not args.force:
            done = PL.reviews_done_ids()
            before = len(hotels)
            hotels = [h for h in hotels if h["hotel_id"] not in done]
            if before - len(hotels):
                print(f"[i] Bo qua {before - len(hotels)} KS da co file review (--force de crawl lai).")
        if args.limit:
            hotels = hotels[:args.limit]
    else:
        ap.print_help()
        sys.exit(1)

    if not hotels:
        print("[i] Khong co KS nao de crawl review.")
        return

    print(f"[i] Crawl review ({args.site}) | {len(hotels)} khach san | headful={args.headful}")
    ok = 0
    # Lam moi browser sau moi REFRESH_EVERY KS: KS review nang lam browser
    # tich luy mem (memory phinh, JS cham dan) -> response review den muon ->
    # lo timeout. Mo context moi dinh ky giu browser "tuoi".
    refresh_every = spider.cfg["review_crawl"].get("refresh_browser_every", 15)

    i = 0
    while i < len(hotels):
        batch = hotels[i:i + refresh_every]
        with browser_context(spider.cfg, args.headful) as context:
            retries = spider.cfg["review_crawl"].get("retries", 2)
            for h in batch:
                i += 1
                if _run_one(spider, context, h, i, len(hotels), retries=retries):
                    ok += 1
                if i < len(hotels):
                    time.sleep(random.uniform(*delay))

    print("\n" + "=" * 60)
    print(f"  XONG: {ok}/{len(hotels)} KS co review | output: {PL.REVIEWS_DIR}")
    print("=" * 60)


if __name__ == "__main__":
    main()

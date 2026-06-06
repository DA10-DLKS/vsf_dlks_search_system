"""main — entry point: 1 cua chay duy nhat cho moi site/2 kieu dau vao.

  1) LINK khach san -> crawl DUY NHAT khach san do -> 1 file json
       python -m crawler.main "https://www.agoda.com/.../hotel.html?hotel=65153&..."

  2) TU KHOA (khong phai link) -> search hang loat -> nhieu file
       python -m crawler.main "Vinpearl"
       python -m crawler.main "Muong Thanh" --limit 5

Tham so:
  --site <ten>   site dung cho nhanh TU KHOA (mac dinh agoda). Nhanh LINK tu
                 nhan dien site theo domain.
  --headful      hien trinh duyet
  --limit N      gioi han so hotel (nhanh tu khoa)

Output: data/hotels/hotel_<id>_<slug>.json (giong dinh dang cu).
"""
import sys
import time
import random

# In duoc tieng Viet co dau tren console Windows (cp1252) — tranh crash khi print
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

# Cho phep chay ca `python -m crawler.main` lan `python crawler/main.py`
if __package__ in (None, ""):
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from crawler import pipelines as PL
from crawler.browser import browser_context
from crawler.configs import load_config, available_sites
from crawler.spiders import SPIDERS


def _is_url(text: str) -> bool:
    return text.strip().lower().startswith(("http://", "https://"))


def _make_spider(site: str, headful: bool):
    if site not in SPIDERS:
        print(f"[X] Chua ho tro site '{site}'. Co san: {list(SPIDERS)}")
        sys.exit(1)
    return SPIDERS[site](load_config(site), headful=headful)


def _is_filtered_country(err: str | None) -> bool:
    return bool(err and str(err).startswith("filtered_country:"))


# ---------------------------------------------------------------------------
# Nhanh 1: LINK -> 1 khach san
# ---------------------------------------------------------------------------
def run_single(url: str, headful: bool = False):
    # Chon spider theo domain cua link
    spider = None
    for site in available_sites():
        if site in SPIDERS:
            cand = SPIDERS[site](load_config(site), headful=headful)
            if cand.is_site_url(url):
                spider = cand
                break
    if spider is None:
        print(f"[X] Khong nhan dien duoc site tu link. Co san: {available_sites()}")
        sys.exit(1)

    hotel = spider.parse_url(url)
    if not hotel:
        print("[X] Khong parse duoc link nay.")
        sys.exit(1)

    if hotel.get("hotel_id"):
        print(f"[i] Nhanh LINK ({spider.site}) | hotel_id={hotel['hotel_id']}")
    else:
        print(f"[i] Nhanh LINK ({spider.site}) | link khong co hotel_id "
              f"-> goto thang, lay propertyId tu trang")
    print(f"    property_page={hotel['property_page']}")

    with browser_context(spider.cfg, headful) as context:
        record, err = spider.crawl_detail(context, hotel)

    if err:
        if _is_filtered_country(err):
            country = err.split(":", 1)[1]
            print(f"[SKIP] Khach san khong thuoc Viet Nam: country={country}")
            return
        print(f"[X] Loi crawl: {err}")
        sys.exit(1)

    path = PL.save_detail_record(record)
    action = PL.upsert_detail(record)   # dong bo vao kho tong (khong trung id)
    rg = record.get("room_grid", {})
    print(f"[OK] {record['name']} -> {path}")
    print(f"     phong={rg.get('room_count', 0)} | nguon={record.get('_sources_captured')} | detail.json: {action}")


# ---------------------------------------------------------------------------
# Nhanh 2: TU KHOA -> hang loat (3 tang trong cung 1 tien trinh)
# ---------------------------------------------------------------------------
def run_batch(keyword: str, site: str = "agoda", headful: bool = False,
              limit: int = None, target_total: int = None):
    spider = _make_spider(site, headful)
    print(f"[i] Nhanh TU KHOA ({site}) '{keyword}' | headful={headful}")

    existing_ids = PL.hotel_file_done_ids()
    if target_total and len(existing_ids) >= target_total:
        print(f"[i] Da co {len(existing_ids)} khach san trong {PL.HOTELS_DIR} "
              f">= target {target_total} -> dung.")
        return

    print("\n" + "=" * 60 + "\n  Buoc 1/3: lay danh sach (crawl_list)\n" + "=" * 60)
    hotels = spider.crawl_list(keyword)
    if existing_ids:
        before = len(hotels)
        hotels = [h for h in hotels if h.get("hotel_id") not in existing_ids]
        skipped = before - len(hotels)
        if skipped:
            print(f"  -> bo qua {skipped} khach san da co file raw/hotels")
    PL.save_list(hotels)
    print(f"  -> {len(hotels)} khach san khop '{keyword}'")
    effective_limit = limit
    if target_total:
        remaining = max(target_total - len(existing_ids), 0)
        effective_limit = remaining if effective_limit is None else min(effective_limit, remaining)
    if effective_limit:
        hotels = hotels[:effective_limit]

    print("\n" + "=" * 60 + "\n  Buoc 2/3: lay slug (resolve_slugs)\n" + "=" * 60)
    hotels = spider.resolve_slugs(hotels)
    PL.save_list(hotels)
    n_slug = sum(1 for h in hotels if h.get("property_page"))
    print(f"  -> co slug cho {n_slug}/{len(hotels)}")

    print("\n" + "=" * 60 + "\n  Buoc 3/3: lay chi tiet (crawl_detail)\n" + "=" * 60)
    results, done_ids = PL.load_detail_progress()
    done_ids |= existing_ids
    failed = []
    between = spider.cfg["rate_limit"]["between_details"]

    with browser_context(spider.cfg, headful) as context:
        for n, h in enumerate(hotels, 1):
            if target_total and len(done_ids) >= target_total:
                print(f"  [i] Dat target {target_total} khach san -> dung batch.")
                break
            hid = h["hotel_id"]
            if hid in done_ids:
                print(f"  [{n}/{len(hotels)}] {hid} da co -> bo qua")
                continue
            record, err = spider.crawl_detail(context, h)
            if err:
                if _is_filtered_country(err):
                    country = err.split(":", 1)[1]
                    print(f"  [{n}/{len(hotels)}] {hid} '{h.get('name')}' SKIP: country={country}")
                    continue
                print(f"  [{n}/{len(hotels)}] {hid} '{h.get('name')}' LOI: {err}")
                failed.append({"hotel_id": hid, "name": h.get("name"), "error": err})
                continue
            results.append(record)
            done_ids.add(hid)
            PL.save_detail_progress(results)   # checkpoint sau moi cai
            PL.save_detail_record(record)       # co file rieng ngay de target/resume chinh xac
            rg = record.get("room_grid", {})
            print(f"  [{n}/{len(hotels)}] {hid} OK -> {record['name'][:35]} | "
                  f"phong={rg.get('room_count', 0)} | nguon={record['_sources_captured']}")
            if n < len(hotels):
                time.sleep(random.uniform(*between))

    PL.save_failed(failed)
    n_files = PL.split_detail_file(results)   # tach ra data/hotels/
    print("\n" + "=" * 60)
    print(f"  XONG: {len(results)} record batch | {len(failed)} loi | tach {n_files} file")
    if target_total:
        print(f"  Tong file raw/hotels hien tai: {len(PL.hotel_file_done_ids())}/{target_total}")
    print(f"  Output: {PL.HOTELS_DIR}")
    print("=" * 60)


# ---------------------------------------------------------------------------
# Nhanh 3: RECRAWL -> chay lai dung cac KS thieu (tu recrawl_queue.json)
# ---------------------------------------------------------------------------
def run_recrawl(site: str = "agoda", headful: bool = False):
    """Doc data/raw/recrawl_queue.json -> crawl lai tung KS thieu field.

    Queue do `crawler.validate` sinh ra. Sau khi crawl xong, tu chay validate
    lai de cap nhat queue (cac KS da day du se bi loai khoi queue).
    """
    from crawler import validate as V

    spider = _make_spider(site, headful)
    queue = V.load_recrawl_queue()
    if not queue:
        print("[i] recrawl_queue.json rong -> khong co gi de crawl lai.")
        print("    Chay `python -m crawler.validate` truoc de sinh queue.")
        return

    print(f"[i] Nhanh RECRAWL ({site}) | {len(queue)} khach san trong queue")
    between = spider.cfg["rate_limit"]["between_details"]
    redone, still_failed = 0, []

    with browser_context(spider.cfg, headful) as context:
        for n, item in enumerate(queue, 1):
            hid = item.get("hotel_id")
            hotel = {
                "hotel_id": hid,
                "name": item.get("name"),
                "property_page": item.get("property_page"),
                "full_url": item.get("source_url"),
            }
            record, err = spider.crawl_detail(context, hotel)
            if err:
                print(f"  [{n}/{len(queue)}] {hid} VAN LOI: {err}")
                still_failed.append({"hotel_id": hid, "name": item.get("name"),
                                     "error": err})
                continue
            path = PL.save_detail_record(record)
            PL.upsert_detail(record)   # dong bo vao kho tong
            inc = record.get("_incomplete")
            tag = f" | _incomplete={[i['field'] for i in inc]}" if inc else ""
            print(f"  [{n}/{len(queue)}] {hid} OK -> {record['name'][:35]}{tag}")
            redone += 1
            if n < len(queue):
                time.sleep(random.uniform(*between))

    if still_failed:
        PL.save_failed(still_failed)
    print("\n" + "=" * 60)
    print(f"  RECRAWL XONG: {redone} thanh cong | {len(still_failed)} van loi")
    print("=" * 60)
    print("\n[i] Cap nhat lai queue (validate):")
    V.validate_dir(quiet=False)


# ---------------------------------------------------------------------------
def main():
    args = sys.argv[1:]
    headful = "--headful" in args

    # Nhanh recrawl: khong can target, doc tu queue
    if "--recrawl" in args:
        site = "agoda"
        if "--site" in args:
            try:
                site = args[args.index("--site") + 1]
            except IndexError:
                pass
        run_recrawl(site=site, headful=headful)
        return

    def opt(name, cast=str, default=None):
        if name in args:
            try:
                return cast(args[args.index(name) + 1])
            except (IndexError, ValueError):
                return default
        return default

    limit = opt("--limit", int, None)
    target_total = opt("--target-total", int, None)
    site = opt("--site", str, "agoda")

    key_flag = "--keys" if "--keys" in args else "--keywords" if "--keywords" in args else None
    if key_flag:
        raw_keys = opt(key_flag, str, "")
        keys = [k.strip() for k in raw_keys.split(",") if k.strip()]
        if not keys:
            print("[X] --keys/--keywords can co danh sach keyword, vi du: --keys \"Vinpearl,Muong Thanh,Fusion\"")
            sys.exit(1)
        for i, key in enumerate(keys, 1):
            if target_total and len(PL.hotel_file_done_ids()) >= target_total:
                print(f"[i] Da dat target {target_total} -> dung truoc KEY {i}.")
                break
            print("\n" + "#" * 70)
            print(f"# KEY {i}/{len(keys)}: {key}")
            print("#" * 70)
            run_batch(key, site=site, headful=headful, limit=limit, target_total=target_total)
        return

    # Tham so dau tien khong phai --flag va khong phai gia tri cua flag
    flag_values = {str(limit), site}
    positional = [a for a in args
                  if not a.startswith("--") and a not in flag_values]
    if not positional:
        print("Cach dung:")
        print('  python -m crawler.main "https://www.agoda.com/...hotel=65153..."  (1 KS)')
        print('  python -m crawler.main "Vinpearl"                                 (hang loat)')
        print('  python -m crawler.main "Muong Thanh" --limit 5 --headful')
        print('  python -m crawler.main --keys "Vinpearl,Muong Thanh,Fusion" --limit 5')
        print('  python -m crawler.main --keys "Sa Pa,Can Tho" --target-total 520')
        print('  python -m crawler.main --recrawl                                  (crawl lai KS thieu)')
        print("  (truoc --recrawl: chay `python -m crawler.validate` de sinh queue)")
        sys.exit(1)

    target = positional[0]
    if _is_url(target):
        run_single(target, headful=headful)
    else:
        run_batch(target, site=site, headful=headful, limit=limit, target_total=target_total)


if __name__ == "__main__":
    main()

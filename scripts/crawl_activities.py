"""Crawl Agoda Activities theo tỉnh thành.

Usage:
    python scripts/crawl_activities.py                                  # crawl all 63 provinces
    python scripts/crawl_activities.py --provinces "Da Nang,Nha Trang"  # chỉ crawl 2 tỉnh
    python scripts/crawl_activities.py --resume                         # tiếp tục từ checkpoint
    python scripts/crawl_activities.py --headful                        # show browser
"""

from __future__ import annotations

import json
import os
import random
import sys
import time
import math
from datetime import datetime, timezone
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_PROJECT_ROOT = _HERE.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from crawler.browser import browser_context
from crawler.parsers.agoda_activities import parse_activity_list, parse_autocomplete

RAW_DIR = _PROJECT_ROOT / "data" / "raw"
ACTIVITIES_DIR = RAW_DIR / "activities"
CHECKPOINT_FILE = ACTIVITIES_DIR / "_checkpoint.json"
RAW_CAPTURES_DIR = ACTIVITIES_DIR / "_captures"

PROVINCES: list[dict] = [
    # ===== Đồng bằng sông Hồng (8) =====
    {"name": "Hà Nội", "slug": "ha-noi", "region": "northern"},
    {"name": "Hải Phòng", "slug": "hai-phong", "region": "northern"},
    {"name": "Quảng Ninh", "slug": "quang-ninh", "region": "northern"},
    {"name": "Hải Dương", "slug": "hai-duong", "region": "northern"},
    {"name": "Bắc Ninh", "slug": "bac-ninh", "region": "northern"},
    {"name": "Hà Nam", "slug": "ha-nam", "region": "northern"},
    {"name": "Nam Định", "slug": "nam-dinh", "region": "northern"},
    {"name": "Thái Bình", "slug": "thai-binh", "region": "northern"},
    {"name": "Ninh Bình", "slug": "ninh-binh", "region": "northern"},
    {"name": "Vĩnh Phúc", "slug": "vinh-phuc", "region": "northern"},
    {"name": "Bắc Giang", "slug": "bac-giang", "region": "northern"},
    # ===== Đông Bắc Bộ (9) =====
    {"name": "Hà Giang", "slug": "ha-giang", "region": "northern"},
    {"name": "Cao Bằng", "slug": "cao-bang", "region": "northern"},
    {"name": "Lào Cai", "slug": "lao-cai", "region": "northern"},
    {"name": "Yên Bái", "slug": "yen-bai", "region": "northern"},
    {"name": "Tuyên Quang", "slug": "tuyen-quang", "region": "northern"},
    {"name": "Lạng Sơn", "slug": "lang-son", "region": "northern"},
    {"name": "Thái Nguyên", "slug": "thai-nguyen", "region": "northern"},
    {"name": "Phú Thọ", "slug": "phu-tho", "region": "northern"},
    {"name": "Bắc Kạn", "slug": "bac-kan", "region": "northern"},
    # ===== Tây Bắc Bộ (6) =====
    {"name": "Sơn La", "slug": "son-la", "region": "northern"},
    {"name": "Điện Biên", "slug": "dien-bien", "region": "northern"},
    {"name": "Lai Châu", "slug": "lai-chau", "region": "northern"},
    {"name": "Hòa Bình", "slug": "hoa-binh", "region": "northern"},
    # ===== Bắc Trung Bộ (6) =====
    {"name": "Thanh Hóa", "slug": "thanh-hoa", "region": "central"},
    {"name": "Nghệ An", "slug": "nghe-an", "region": "central"},
    {"name": "Hà Tĩnh", "slug": "ha-tinh", "region": "central"},
    {"name": "Quảng Bình", "slug": "quang-binh", "region": "central"},
    {"name": "Quảng Trị", "slug": "quang-tri", "region": "central"},
    {"name": "Thừa Thiên Huế", "slug": "thua-thien-hue", "region": "central"},
    # ===== Duyên hải Nam Trung Bộ (7) =====
    {"name": "Đà Nẵng", "slug": "da-nang", "region": "central"},
    {"name": "Quảng Nam", "slug": "quang-nam", "region": "central"},
    {"name": "Quảng Ngãi", "slug": "quang-ngai", "region": "central"},
    {"name": "Bình Định", "slug": "binh-dinh", "region": "central"},
    {"name": "Phú Yên", "slug": "phu-yen", "region": "central"},
    {"name": "Khánh Hòa", "slug": "khanh-hoa", "region": "central"},
    {"name": "Ninh Thuận", "slug": "ninh-thuan", "region": "central"},
    {"name": "Bình Thuận", "slug": "binh-thuan", "region": "central"},
    # ===== Tây Nguyên (5) =====
    {"name": "Kon Tum", "slug": "kon-tum", "region": "highlands"},
    {"name": "Gia Lai", "slug": "gia-lai", "region": "highlands"},
    {"name": "Đắk Lắk", "slug": "dak-lak", "region": "highlands"},
    {"name": "Đắk Nông", "slug": "dak-nong", "region": "highlands"},
    {"name": "Lâm Đồng", "slug": "lam-dong", "region": "highlands"},
    # ===== Đông Nam Bộ (6) =====
    {"name": "Hồ Chí Minh", "slug": "ho-chi-minh", "region": "southern"},
    {"name": "Đồng Nai", "slug": "dong-nai", "region": "southern"},
    {"name": "Bình Dương", "slug": "binh-duong", "region": "southern"},
    {"name": "Bà Rịa - Vũng Tàu", "slug": "ba-ria-vung-tau", "region": "southern"},
    {"name": "Tây Ninh", "slug": "tay-ninh", "region": "southern"},
    {"name": "Bình Phước", "slug": "binh-phuoc", "region": "southern"},
    # ===== Đồng bằng sông Cửu Long (13) =====
    {"name": "Cần Thơ", "slug": "can-tho", "region": "southern"},
    {"name": "Long An", "slug": "long-an", "region": "southern"},
    {"name": "Tiền Giang", "slug": "tien-giang", "region": "southern"},
    {"name": "Bến Tre", "slug": "ben-tre", "region": "southern"},
    {"name": "Trà Vinh", "slug": "tra-vinh", "region": "southern"},
    {"name": "Vĩnh Long", "slug": "vinh-long", "region": "southern"},
    {"name": "Đồng Tháp", "slug": "dong-thap", "region": "southern"},
    {"name": "An Giang", "slug": "an-giang", "region": "southern"},
    {"name": "Kiên Giang", "slug": "kien-giang", "region": "southern"},
    {"name": "Hậu Giang", "slug": "hau-giang", "region": "southern"},
    {"name": "Sóc Trăng", "slug": "soc-trang", "region": "southern"},
    {"name": "Bạc Liêu", "slug": "bac-lieu", "region": "southern"},
    {"name": "Cà Mau", "slug": "ca-mau", "region": "southern"},
]

AGODA_BASE = "https://www.agoda.com"
AUTOCOMPLETE_API = "/api/cronos/search/GetUnifiedSuggestResult/3/24/24/0/vi-vn/"
SEARCH_DELAY = (3, 6)
DETAIL_DELAY = (4, 8)
PROVINCE_DELAY = (10, 20)
DETAIL_TIMEOUT = 45000
PAGE_TIMEOUT = 60000


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------
def slugify(name: str) -> str:
    s = name.lower().replace(" ", "-")
    s = s.replace("đ", "d").replace("Đ", "d")
    table = str.maketrans(
        "áàảãạâấầẩẫậăắằẳẵặéèẻẽẹêếềểễệíìỉĩịóòỏõọôốồổỗộơớờởỡợúùủũụưứừửữựýỳỷỹỵ",
        "aaaaaaaaaaaaaaaaaeeeeeeeeeeeiiiiiooooooooooooooooouuuuuuuuuuuyyyyy")
    return s.translate(table)


def write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def read_json(path: Path, default=None):
    if not path.exists():
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def haversine_km(lat1, lon1, lat2, lon2) -> float:
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon / 2) ** 2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


# ---------------------------------------------------------------------------
# Checkpoint helpers
# ---------------------------------------------------------------------------
def load_checkpoint() -> dict:
    return read_json(CHECKPOINT_FILE, {"done": [], "skipped": []})


def save_checkpoint(state: dict) -> None:
    write_json(CHECKPOINT_FILE, state)


# ---------------------------------------------------------------------------
# Core crawl
# ---------------------------------------------------------------------------
def _find_city_id(page, province_name: str) -> int | None:
    """Use Agoda autocomplete API -> find city_id for province."""
    api_url = AGODA_BASE + AUTOCOMPLETE_API + f"?searchText={province_name}"
    try:
        resp = page.request.get(api_url, headers={
            "Accept": "application/json",
            "Referer": AGODA_BASE + "/",
        })
        if not resp.ok:
            return None
        data = resp.json()
        cities = parse_autocomplete(data)
        for c in cities:
            if province_name.lower() in c["name"].lower():
                return c["city_id"]
        if cities:
            return cities[0]["city_id"]
    except Exception:
        return None
    return None


def _try_activities_api(page, store: dict, cfg: dict):
    """Hook onto page responses to capture activities GraphQL data.

    Intercepts any XHR/fetch containing /api/activities/ or similar.
    """
    captured: list[dict] = []
    signals = cfg.get("activity_signals",
                      ["/api/activities/", "/graphql/activity"])

    def on_response(response):
        u = response.url
        if response.request.resource_type not in ("xhr", "fetch"):
            return
        if not any(sig in u for sig in signals):
            return
        try:
            data = json.loads(response.body().decode("utf-8", "replace"))
            captured.append({"url": u, "body": data})
        except Exception:
            pass

    page.on("response", on_response)
    return captured


def crawl_province_activities(context, province: dict,
                              headful: bool = False) -> list[dict]:
    """Crawl all activities for one province from Agoda.

    Strategy:
      1. Find city_id via autocomplete API
      2. Open activities listing page for the city
      3. Intercept API responses to capture activity data
      4. Try multiple URL patterns to trigger the activities API
      5. Parse activities from captured responses
    """
    province_name = province["name"]
    slug = province["slug"]
    print(f"\n{'='*60}")
    print(f"  Province: {province_name} ({slug})")
    print(f"{'='*60}")

    page = context.new_page()
    captured_api = _try_activities_api(page, context,
                                       {"activity_signals":
                                        ["/api/activities/", "/graphql"]})
    all_activities: list[dict] = []
    seen_ids: set[int] = set()

    try:
        # Step 1: Find city_id
        print(f"  [1/3] Looking up city ID for '{province_name}'...")
        city_id = _find_city_id(page, province_name)
        if city_id:
            print(f"        → city_id = {city_id}")
        else:
            print(f"        → city_id not found, will use search fallback")

        # Step 2: Try multiple URL patterns to trigger activities API
        print(f"  [2/3] Opening activities page...")
        urls_to_try = [
            f"{AGODA_BASE}/vi-vn/activities",
            f"{AGODA_BASE}/vi-vn/activities/{slugify(province_name)}",
        ]
        if city_id:
            urls_to_try.insert(0,
                               f"{AGODA_BASE}/vi-vn/activities?cityId={city_id}")

        loaded = False
        for url in urls_to_try:
            print(f"        Trying: {url}")
            try:
                page.goto(url, wait_until="commit", timeout=PAGE_TIMEOUT)
                page.wait_for_timeout(5000)
                # Scroll to trigger lazy loading
                for _ in range(10):
                    page.mouse.wheel(0, 1200)
                    page.wait_for_timeout(600)
                loaded = True
                break
            except Exception as e:
                print(f"        Failed: {e}")
                continue

        if not loaded:
            print(f"  [!] Could not load any activities page")
            return []

        # Step 3: Try searching on Agoda if no activities captured yet
        if not captured_api or not any(
                safe(c, "body", "data", "search", "result") for c in captured_api):
            print(f"  [2b/3] Trying search fallback...")
            try:
                page.goto(f"{AGODA_BASE}/vi-vn", wait_until="commit",
                          timeout=PAGE_TIMEOUT)
                page.wait_for_timeout(3000)
                search_input = page.query_selector(
                    "input[type='search'], input[placeholder*='tìm'], "
                    "input[name='search']")
                if search_input:
                    search_input.click()
                    search_input.fill(f"activities {province_name}")
                    page.wait_for_timeout(2000)
                    search_input.press("Enter")
                    page.wait_for_timeout(8000)
                    for _ in range(8):
                        page.mouse.wheel(0, 1200)
                        page.wait_for_timeout(600)
            except Exception as e:
                print(f"        Search fallback failed: {e}")

        # Step 4: Parse activities from captured API data
        print(f"  [3/3] Parsing {len(captured_api)} captured API responses...")
        for cap in captured_api:
            acts = parse_activity_list(cap["body"])
            for a in acts:
                aid = a.get("activity_id")
                if aid and aid not in seen_ids:
                    a["province"] = province_name
                    a["province_slug"] = slug
                    a["region"] = province.get("region")
                    all_activities.append(a)
                    seen_ids.add(aid)

        # Save raw captures for debugging
        if captured_api:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            capture_path = RAW_CAPTURES_DIR / f"{slug}_{ts}.json"
            write_json(capture_path, captured_api)
            print(f"        Raw captures saved to {capture_path}")

        print(f"        → Found {len(all_activities)} unique activities")

    except Exception as e:
        print(f"  [X] Error crawling {province_name}: {e}")
    finally:
        page.close()

    return all_activities


def crawl_activity_detail(context, activity: dict) -> dict | None:
    """Crawl the detail page of a single activity.

    Tries multiple URL patterns to find the activity detail page,
    intercepts API responses, and merges detail data.
    """
    aid = activity.get("activity_id")
    if not aid:
        return None

    title_slug = slugify(activity.get("title", "") or "")[:60]
    detail_urls = [
        f"{AGODA_BASE}/vi-vn/activities/{aid}/details",
        f"{AGODA_BASE}/vi-vn/activities/{title_slug}/{aid}",
        f"{AGODA_BASE}/vi-vn/activities/detail?activityId={aid}",
    ]

    page = context.new_page()

    # Intercept detail API
    detail_store: list[dict] = []

    def on_response(response):
        u = response.url
        if response.request.resource_type not in ("xhr", "fetch"):
            return
        if any(sig in u for sig in ["/api/activities/", "/graphql"]):
            try:
                data = json.loads(response.body().decode("utf-8", "replace"))
                detail_store.append({"url": u, "body": data})
            except Exception:
                pass

    page.on("response", on_response)

    try:
        for url in detail_urls:
            try:
                page.goto(url, wait_until="commit", timeout=DETAIL_TIMEOUT)
                page.wait_for_timeout(5000)
                for _ in range(5):
                    page.mouse.wheel(0, 1000)
                    page.wait_for_timeout(500)
                if detail_store:
                    break
            except Exception:
                continue

        if detail_store:
            from crawler.parsers.agoda_activities import parse_detail
            for cap in detail_store:
                detail = parse_detail(cap["body"])
                if detail.get("activity_id") == aid:
                    return {**activity, **{k: v for k, v in detail.items()
                                           if v is not None}}
            return detail
    except Exception as e:
        print(f"  [!] Detail crawl error for activity {aid}: {e}")
    finally:
        page.close()

    return None


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def run(provinces: list[dict] | None = None,
        headful: bool = False,
        resume: bool = False,
        skip_detail: bool = False) -> dict[str, int]:
    if provinces is None:
        provinces = PROVINCES

    ACTIVITIES_DIR.mkdir(parents=True, exist_ok=True)
    RAW_CAPTURES_DIR.mkdir(parents=True, exist_ok=True)

    cp = load_checkpoint() if resume else {"done": [], "skipped": []}
    if not resume:
        save_checkpoint(cp)

    total_activities = 0
    total_provinces = 0
    skipped = 0

    cfg = {
        "user_agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/131.0.0.0 Safari/537.36"
        ),
        "locale": "vi-vn",
        "viewport": {"width": 1366, "height": 900},
    }

    with browser_context(cfg, headful=headful) as context:
        for province in provinces:
            slug = province["slug"]

            if slug in cp.get("done", []):
                print(f"  [SKIP] {province['name']} already done")
                skipped += 1
                continue
            if slug in cp.get("skipped", []):
                skipped += 1
                continue

            activities = crawl_province_activities(context, province,
                                                   headful=headful)

            if not activities:
                print(f"  [SKIP] No activities for {province['name']}")
                cp["skipped"].append(slug)
                save_checkpoint(cp)
                skipped += 1
                time.sleep(random.uniform(2, 4))
                continue

            # Optionally crawl detail pages
            if not skip_detail and len(activities) > 0:
                print(f"  Crawling detail for {len(activities)} activities...")
                detailed = []
                for i, act in enumerate(activities, 1):
                    print(f"    [{i}/{len(activities)}] activity {act.get('activity_id')}...")
                    detail = crawl_activity_detail(context, act)
                    if detail:
                        detailed.append(detail)
                    else:
                        detailed.append(act)  # keep listing data as fallback
                    time.sleep(random.uniform(*DETAIL_DELAY))
                activities = detailed

            # Save province file
            output = {
                "province": province["name"],
                "province_slug": slug,
                "region": province.get("region"),
                "crawled_at": datetime.now(timezone.utc).isoformat(),
                "activity_count": len(activities),
                "activities": activities,
            }
            out_path = ACTIVITIES_DIR / f"{slug}.json"
            write_json(out_path, output)
            print(f"  Saved {len(activities)} activities to {out_path}")

            cp["done"].append(slug)
            save_checkpoint(cp)
            total_activities += len(activities)
            total_provinces += 1

            # Throttle between provinces
            if total_provinces < len(provinces):
                delay = random.uniform(*PROVINCE_DELAY)
                print(f"  Waiting {delay:.0f}s before next province...")
                time.sleep(delay)

    summary = {
        "provinces_crawled": total_provinces,
        "total_activities": total_activities,
        "skipped": skipped,
    }
    print(f"\n{'='*60}")
    print(f"  Done: {total_provinces}/{len(provinces)} provinces, "
          f"{total_activities} activities")
    print(f"{'='*60}")

    # Write summary
    write_json(ACTIVITIES_DIR / "_summary.json", {
        **summary,
        "finished_at": datetime.now(timezone.utc).isoformat(),
    })
    return summary


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def _parse_args(argv: list[str] | None = None):
    import argparse
    parser = argparse.ArgumentParser(
        description="Crawl Agoda Activities by province")
    parser.add_argument("--provinces", type=str, default=None,
                        help="Comma-separated province names to crawl")
    parser.add_argument("--headful", action="store_true",
                        help="Show browser window")
    parser.add_argument("--resume", action="store_true",
                        help="Resume from checkpoint")
    parser.add_argument("--skip-detail", action="store_true",
                        help="Skip detail page crawling")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = _parse_args(argv)
    provinces = PROVINCES
    if args.provinces:
        names = [n.strip() for n in args.provinces.split(",")]
        provinces = [p for p in PROVINCES if p["name"] in names]
        found = {p["name"] for p in provinces}
        missing = set(names) - found
        if missing:
            print(f"[!] Unknown provinces: {missing}")
            sys.exit(1)

    run(provinces, headful=args.headful, resume=args.resume,
        skip_detail=args.skip_detail)


# Re-export for other scripts
def safe(d, *keys, default=None):
    for k in keys:
        if not isinstance(d, dict):
            return default
        d = d.get(k)
        if d is None:
            return default
    return d


if __name__ == "__main__":
    main()

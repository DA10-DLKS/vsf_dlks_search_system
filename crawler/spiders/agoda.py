"""agoda — AgodaSpider: hien thuc 3 tang crawl cho Agoda, dieu khien boi config.

Gom logic tu cac file cu (crawl_list / resolve_slugs / crawl_details) vao 1
class, doc tham so tu configs/agoda.yaml thay vi hardcode.
"""
import json
import time
from datetime import datetime, timedelta
from urllib.parse import urlparse, parse_qs

from ..parsers import agoda as P
from .base import BaseSpider


class AgodaSpider(BaseSpider):
    site = "agoda"

    # =====================================================================
    # TANG 1: tu khoa -> danh sach hotel (autocomplete API)
    # =====================================================================
    def _build_keywords(self, keyword: str) -> list:
        """Tu 1 tu khoa goc -> goc + cac bien the 'goc + vung' (tu config)."""
        keyword = keyword.strip()
        variants = [keyword] + [f"{keyword} {h}" for h in self.cfg.get("region_hints", [])]
        seen, out = set(), []
        for v in variants:
            k = v.lower()
            if k not in seen:
                seen.add(k)
                out.append(v)
        return out

    def crawl_list(self, keyword: str = "Vinpearl") -> list:
        """Goi autocomplete voi cac bien the cua keyword -> list hotel.

        Loc: chi giu muc co ten chua chinh `keyword` (khong phan biet hoa/thuong).
        """
        from ..browser import browser_context

        base = self.cfg["base_url"]
        api = base + self.cfg["autocomplete_api"]
        needle = keyword.strip().lower()
        delay = self.cfg["rate_limit"]["autocomplete_delay"]
        hotels = {}  # hotel_id -> record (bo trung)

        with browser_context(self.cfg, self.headful) as context:
            page = context.new_page()
            print("[i] Mo Agoda de lay cookie/session...")
            page.goto(base, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(2500)

            for kw in self._build_keywords(keyword):
                url = f"{api}?searchText={kw}"
                try:
                    resp = page.request.get(url, headers={
                        "Accept": "application/json", "Referer": base + "/"})
                    if not resp.ok:
                        print(f"  [!] '{kw}': HTTP {resp.status}")
                        continue
                    data = resp.json()
                except Exception as e:
                    print(f"  [!] '{kw}': loi {e}")
                    continue

                found = 0
                for s in (data.get("SuggestionList") or []):
                    name = s.get("Name") or ""
                    hid = s.get("ObjectID")
                    if hid and needle in name.lower() and hid not in hotels:
                        hotels[hid] = {
                            "hotel_id": hid,
                            "name": name,
                            "object_type_id": s.get("ObjectTypeID"),
                            "url_path": s.get("Url"),
                        }
                        found += 1
                for v in (data.get("ViewModelList") or []):
                    if v.get("IsHotel") and v.get("ObjectId") in hotels:
                        hotels[v["ObjectId"]]["city_id"] = v.get("CityId")
                print(f"  [+] '{kw}': them {found} moi (tong {len(hotels)})")
                page.wait_for_timeout(int(delay * 1000))

        return sorted(hotels.values(), key=lambda h: h["hotel_id"])

    # =====================================================================
    # TANG 1.5: bo sung property_page (slug) tu citySearch
    # =====================================================================
    @staticmethod
    def _collect_pages(obj, mapping):
        """Duyet citySearch, gom propertyId -> propertyPage."""
        if isinstance(obj, dict):
            if "propertyId" in obj and "content" in obj:
                info = (obj.get("content") or {}).get("informationSummary") or {}
                page = (info.get("propertyLinks") or {}).get("propertyPage")
                if page:
                    mapping[obj["propertyId"]] = page
            for v in obj.values():
                AgodaSpider._collect_pages(v, mapping)
        elif isinstance(obj, list):
            for it in obj:
                AgodaSpider._collect_pages(it, mapping)

    def resolve_slugs(self, hotels: list) -> list:
        """Mo trang tung hotel (url_path) -> bat citySearch -> gom slug.

        Cap nhat field 'property_page' cho moi hotel (None neu khong thay).
        """
        from ..browser import browser_context

        base = self.cfg["base_url"]
        locale = self.cfg.get("locale", "vi-vn")
        delay = self.cfg["rate_limit"]["resolve_delay"]
        slug_map = {}

        with browser_context(self.cfg, self.headful) as context:
            for n, h in enumerate(hotels, 1):
                hid = h["hotel_id"]
                if hid in slug_map:
                    print(f"  [{n}/{len(hotels)}] {hid} da co slug -> bo qua")
                    continue
                if not h.get("url_path"):
                    print(f"  [{n}/{len(hotels)}] {hid} khong co url_path")
                    continue

                page = context.new_page()
                got = {"body": None}

                def on_resp(r, store=got):
                    if "graphql/search" not in r.url:
                        return
                    try:
                        d = json.loads(r.body().decode("utf-8", "replace"))
                        txt = json.dumps(d)
                        if '"propertyId"' in txt[:5000] or "citySearch" in txt[:200]:
                            if store["body"] is None or len(txt) > len(json.dumps(store["body"])):
                                store["body"] = d
                    except Exception:
                        pass

                page.on("response", on_resp)
                url = f"{base}/{locale}" + h["url_path"]
                try:
                    page.goto(url, wait_until="commit", timeout=60000)
                    for _ in range(30):
                        if got["body"]:
                            break
                        page.wait_for_timeout(500)
                except Exception as e:
                    print(f"  [{n}/{len(hotels)}] {hid} loi goto: {e}")
                    page.close()
                    continue

                before = len(slug_map)
                if got["body"]:
                    self._collect_pages(got["body"], slug_map)
                page.close()
                print(f"  [{n}/{len(hotels)}] {hid} '{h['name'][:35]}' "
                      f"-> them {len(slug_map)-before} slug (tong {len(slug_map)})")
                time.sleep(delay)

        for h in hotels:
            h["property_page"] = slug_map.get(h["hotel_id"])
        return hotels

    # =====================================================================
    # TANG 2: 1 hotel -> 1 record day du
    # =====================================================================
    def _detail_url(self, hotel: dict) -> str:
        # Can ca property_page va hotel_id de ghep URL chuan; thieu 1 trong 2
        # -> tra None (crawl_detail se fallback sang full_url neu co).
        page_path = hotel.get("property_page")
        if not page_path or not hotel.get("hotel_id"):
            return None
        q = self.cfg["detail_query"]
        ci = (datetime.now() + timedelta(days=self.cfg["checkin_offset_days"])).strftime("%Y-%m-%d")
        co = (datetime.now() + timedelta(days=self.cfg["checkin_offset_days"]
                                         + self.cfg["los_nights"])).strftime("%Y-%m-%d")
        return (f"{self.cfg['base_url']}{page_path}"
                f"?hotel={hotel['hotel_id']}&currency={q['currency']}"
                f"&checkIn={ci}&checkOut={co}"
                f"&rooms={q['rooms']}&adults={q['adults']}&children={q['children']}")

    def _make_handler(self, store):
        """Response handler: bat cac nguon khai bao trong capture_endpoints."""
        eps = self.cfg["capture_endpoints"]

        def on_response(response):
            u = response.url
            if response.request.resource_type not in ("xhr", "fetch"):
                return
            if not any(sig in u for sig in eps.values()):
                return
            try:
                data = json.loads(response.body().decode("utf-8", "replace"))
            except Exception:
                return

            if eps["details"] in u and P.safe(data, "data", "propertyDetailsSearch"):
                store["details"] = data
            elif eps["rooms"] in u:
                store["rooms"] = data
            elif eps["reviews"] in u:
                store["reviews"] = data
            elif eps["secondary"] in u:
                store["secondary"] = data
            elif eps["activities"] in u:
                store["activities"] = data
            elif eps["faq"] in u:
                store["faq"] = data
        return on_response

    def crawl_detail(self, context, hotel: dict):
        """1 hotel -> (record, error). Tai dung 1 browser context cho ca batch.

        URL de mo trang:
          - Co property_page + hotel_id -> ghep URL chuan (_detail_url).
          - Khong co (link tho khong id) -> goto THANG `full_url`; hotel_id se
            lay tu propertyId trong record sau khi parse.
        """
        url = self._detail_url(hotel) or hotel.get("full_url")
        if not url:
            return None, "no slug"

        page = context.new_page()
        store = {}
        page.on("response", self._make_handler(store))
        try:
            page.goto(url, wait_until="commit", timeout=60000)
            try:
                page.wait_for_selector("h1", timeout=20000, state="visible")
            except Exception:
                pass
            for _ in range(18):          # cuon het xuong (FAQ o cuoi trang)
                page.mouse.wheel(0, 1500)
                page.wait_for_timeout(800)
            deadline = time.time() + 18  # cho details + faq (faq den muon nhat)
            while time.time() < deadline:
                if "details" in store and "faq" in store:
                    break
                page.wait_for_timeout(700)
        except Exception as e:
            page.close()
            return None, f"goto/scroll: {e}"
        page.close()

        if "details" not in store:
            return None, "no propertyDetailsSearch"

        record = P.build_record(store, hotel, url)
        # Link tho khong co hotel_id: lay propertyId tu record (parse tu details)
        if not hotel.get("hotel_id") and record.get("hotel_id"):
            hotel["hotel_id"] = record["hotel_id"]
        if not record.get("hotel_id"):
            return None, "khong xac dinh duoc hotel_id (propertyId rong)"
        return record, None

    # =====================================================================
    # NHANH LINK: 1 url -> hotel dict
    # =====================================================================
    def is_site_url(self, url: str) -> bool:
        return "agoda.com" in urlparse(url).netloc.lower()

    def parse_url(self, url: str) -> dict:
        """Link hotel Agoda -> hotel dict.

        2 truong hop:
          - Link CO ?hotel=<id>: lay id + slug tu path (ghep URL chuan khi crawl).
          - Link KHONG co id (vd copy tho tu trinh duyet): de hotel_id=None va
            luu `full_url` de goto THANG link do; id se lay tu propertyId trong
            response propertyDetailsSearch khi crawl_detail.
        """
        parsed = urlparse(url)
        qs = parse_qs(parsed.query)
        hid = None
        for key in ("hotel", "hotelId", "hid"):
            if qs.get(key):
                try:
                    hid = int(qs[key][0])
                except ValueError:
                    hid = qs[key][0]
                break
        path = parsed.path if parsed.path.startswith("/") else "/" + parsed.path
        return {"hotel_id": hid, "name": None, "property_page": path,
                "city_id": None, "full_url": url}

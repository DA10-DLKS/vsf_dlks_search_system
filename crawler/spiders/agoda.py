"""agoda — AgodaSpider: hien thuc 3 tang crawl cho Agoda, dieu khien boi config.

Gom logic tu cac file cu (crawl_list / resolve_slugs / crawl_details) vao 1
class, doc tham so tu configs/agoda.yaml thay vi hardcode.
"""
import json
import random
import time
import unicodedata
from datetime import datetime, timedelta
from urllib.parse import urlparse, parse_qs

from ..parsers import agoda as P
from .base import BaseSpider


class AgodaSpider(BaseSpider):
    site = "agoda"

    @staticmethod
    def _norm_text(value) -> str:
        """Normalize text for country comparison."""
        if value is None:
            return ""
        text = str(value).strip().lower()
        text = unicodedata.normalize("NFD", text)
        text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
        return " ".join(text.replace("_", " ").replace("-", " ").split())

    def _allowed_country_keys(self) -> set:
        configured = self.cfg.get("allowed_countries") or ["Việt Nam", "Vietnam", "Viet Nam", "VN"]
        keys = {self._norm_text(c) for c in configured}
        keys.update({"viet nam", "vietnam", "vn"})
        return keys

    def _is_allowed_country(self, country) -> bool:
        return self._norm_text(country) in self._allowed_country_keys()

    # =====================================================================
    # TANG 1: tu khoa -> danh sach hotel (autocomplete API)
    # =====================================================================
    def _build_keywords(self, keyword: str) -> list:
        """Tu 1 tu khoa goc -> bien the co dia diem/quoc gia Viet Nam."""
        keyword = keyword.strip()
        base_variants = [keyword]
        if self.cfg.get("expand_region_hints", False):
            base_variants += [f"{keyword} {h}" for h in self.cfg.get("region_hints", [])]
        suffixes = self.cfg.get("country_search_suffixes", [])
        variants = list(base_variants)
        for base in base_variants:
            for suffix in suffixes:
                suffix = str(suffix).strip()
                if suffix and self._norm_text(suffix) not in self._norm_text(base):
                    variants.append(f"{base} {suffix}")
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
                hotel_ids = {
                    str(v.get("ObjectId"))
                    for v in (data.get("ViewModelList") or [])
                    if v.get("IsHotel") and v.get("ObjectId") is not None
                }
                for s in (data.get("SuggestionList") or []):
                    name = s.get("Name") or ""
                    hid = s.get("ObjectID")
                    hid_key = str(hid) if hid is not None else ""
                    if hotel_ids and hid_key not in hotel_ids:
                        continue
                    name_matches = needle in name.lower()
                    is_hotel_suggestion = bool(hotel_ids and hid_key in hotel_ids)
                    if hid and (is_hotel_suggestion or name_matches) and hid_key not in hotels:
                        hotels[hid_key] = {
                            "hotel_id": hid,
                            "name": name,
                            "object_type_id": s.get("ObjectTypeID"),
                            "url_path": s.get("Url"),
                        }
                        found += 1
                for v in (data.get("ViewModelList") or []):
                    hid_key = str(v.get("ObjectId"))
                    if v.get("IsHotel") and hid_key in hotels:
                        hotels[hid_key]["city_id"] = v.get("CityId")
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
                    mapping[str(obj["propertyId"])] = page
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
            h["property_page"] = slug_map.get(str(h["hotel_id"]))
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

    def _open_and_capture(self, context, url: str, store: dict) -> str | None:
        """Mo 1 trang detail, cuon, cho cac REQUIRED nguon ve het (hoac het gio).

        Ghi cac response bat duoc vao `store` (dung chung de tich luy qua nhieu
        lan thu). Tra ve None neu OK, hoac chuoi loi neu goto that bai.
        """
        dc = self.cfg.get("detail_crawl", {})
        required = self.cfg.get("required_sources", ["details"])
        steps = dc.get("scroll_steps", 18)
        pause = dc.get("scroll_pause_ms", 800)
        wait_secs = dc.get("wait_after_scroll", 30)

        page = context.new_page()
        page.on("response", self._make_handler(store))
        try:
            page.goto(url, wait_until="commit", timeout=60000)
            try:
                page.wait_for_selector("h1", timeout=20000, state="visible")
            except Exception:
                pass
            # Cuon co chu dich: keo het trang de ep cac widget lazy-load
            # (review, FAQ) ban response ra; dung som neu da du required.
            for _ in range(steps):
                if all(s in store for s in required):
                    break
                page.mouse.wheel(0, 1500)
                page.wait_for_timeout(pause)
            # Sau khi cuon, cho them cho cac response den muon (review hay cham)
            deadline = time.time() + wait_secs
            while time.time() < deadline:
                if all(s in store for s in required):
                    break
                page.wait_for_timeout(700)
        except Exception as e:
            return f"goto/scroll: {e}"
        finally:
            page.close()
        return None

    def _missing_required(self, store: dict) -> list:
        """Cac REQUIRED nguon chua bat duoc trong store."""
        required = self.cfg.get("required_sources", ["details"])
        return [s for s in required if s not in store]

    def crawl_detail(self, context, hotel: dict):
        """1 hotel -> (record, error). Tai dung 1 browser context cho ca batch.

        URL de mo trang:
          - Co property_page + hotel_id -> ghep URL chuan (_detail_url).
          - Khong co (link tho khong id) -> goto THANG `full_url`; hotel_id se
            lay tu propertyId trong record sau khi parse.

        Co RETRY: neu sau khi mo trang van thieu REQUIRED nguon (vd review
        lazy-load chua kip ve) -> mo lai toi `max_attempts` lan. `store` duoc
        TICH LUY qua cac lan (nguon nao da co thi giu). Het luot van thieu ->
        van build record + danh dau `_incomplete` (KHONG vut), tru khi thieu
        ca `details` (khong co gi de parse).
        """
        url = self._detail_url(hotel) or hotel.get("full_url")
        if not url:
            return None, "no slug"

        dc = self.cfg.get("detail_crawl", {})
        max_attempts = dc.get("max_attempts", 2)

        store = {}
        last_err = None
        for attempt in range(max_attempts):
            err = self._open_and_capture(context, url, store)
            if err:
                last_err = err
            if not self._missing_required(store):
                break  # da du required -> khong can thu lai

        if "details" not in store:
            return None, last_err or "no propertyDetailsSearch"

        record = P.build_record(store, hotel, url)
        # Link tho khong co hotel_id: lay propertyId tu record (parse tu details)
        if not hotel.get("hotel_id") and record.get("hotel_id"):
            hotel["hotel_id"] = record["hotel_id"]
        if not record.get("hotel_id"):
            return None, "khong xac dinh duoc hotel_id (propertyId rong)"

        country = record.get("country")
        if not self._is_allowed_country(country):
            return None, f"filtered_country:{country or 'missing'}"

        # Danh gia day du / thieu that / thieu do loi crawl
        self._annotate_completeness(record, store)
        return record, None

    def _annotate_completeness(self, record: dict, store: dict):
        """Gan record['_incomplete'] = danh sach field con thieu.

        Phan biet 2 loai:
          - THIEU THAT (KS qua it review -> Agoda khong render widget): grades
            rong va review_count < nguong. Danh dau nhung KHONG nen recrawl.
          - THIEU DO LOI CRAWL: nguon required khong bat duoc. Nen recrawl.
        validate.py se doc _incomplete + reason de quyet dinh co day vao
        recrawl_queue hay khong.
        """
        dc = self.cfg.get("detail_crawl", {})
        threshold = dc.get("min_reviews_threshold", 20)

        incomplete = []
        # 1) Required nguon khong bat duoc -> loi crawl
        for s in self._missing_required(store):
            incomplete.append({"field": s, "reason": "crawl_miss"})

        # 2) reviews ve nhung rong: phan biet it-review-that vs loi
        rv = record.get("reviews_detail") or {}
        review_count = rv.get("review_count") or record.get("review_count") or 0
        grades_empty = not rv.get("grades")
        if "reviews" in store and grades_empty:
            reason = "few_reviews" if review_count < threshold else "crawl_miss"
            incomplete.append({"field": "reviews_detail.grades", "reason": reason})

        if incomplete:
            record["_incomplete"] = incomplete

    # =====================================================================
    # TOOL REVIEW: 1 hotel -> nhieu review chi tiet (phan trang endpoint review)
    # =====================================================================
    def _cap_for(self, hotel_id, review_count) -> tuple:
        """Tra ve (cap, tier) theo config review_crawl + so review that.

        review_count >= flagship_min_reviews -> cap_flagship (tier=flagship);
                                      KS rat nhieu review = trong diem (tu suy)
        khong biet so (None/0)     -> cap_normal (tier=unknown) — KHONG de 0
                                      chan crawl; nhieu KS multi-provider thieu
                                      reviewCommentsCount nhung van co review that
        0 < n <= cap_normal        -> lay het n (tier=small)
        cap_normal < n             -> cap_normal (tier=normal)
        """
        rc = self.cfg["review_crawl"]
        flagship_min = rc.get("flagship_min_reviews") or 0
        if flagship_min and review_count and review_count >= flagship_min:
            return rc["cap_flagship"], "flagship"
        if not review_count:                 # None hoac 0 -> khong tin, lay cap thuong
            return rc["cap_normal"], "unknown"
        if review_count <= rc["cap_normal"]:
            return review_count, "small"
        return rc["cap_normal"], "normal"

    def _capture_review_seed(self, context, url: str) -> dict | None:
        """Mo trang KS, bat response review/HotelReviews dau tien (trang 1).

        Tra ve dict cua response (de lay providerIds, comments_count, comments
        trang 1) + giu page MO de tai dung session cho page.request.post().
        Tra ve None neu khong bat duoc.
        """
        sig = self.cfg["capture_endpoints"]["reviews"]
        rc = self.cfg["review_crawl"]
        dc = self.cfg.get("detail_crawl", {})
        steps = rc.get("seed_scroll_steps", dc.get("scroll_steps", 18))
        pause = dc.get("scroll_pause_ms", 800)
        wait_secs = rc.get("seed_wait_secs", 20)

        store = {"body": None, "req": None}
        page = context.new_page()

        def on_resp(r, st=store):
            if sig not in r.url or st["body"] is not None:
                return
            try:
                st["body"] = json.loads(r.body().decode("utf-8", "replace"))
                st["req"] = r.request.post_data
            except Exception:
                pass

        page.on("response", on_resp)
        try:
            page.goto(url, wait_until="commit", timeout=60000)
            try:
                page.wait_for_selector("h1", timeout=20000, state="visible")
            except Exception:
                pass
            for _ in range(steps):
                if store["body"]:
                    break
                page.mouse.wheel(0, 1500)
                page.wait_for_timeout(pause)
            # 1 so KS tra response review rat muon -> cho lau (config seed_wait_secs)
            deadline = time.time() + wait_secs
            while time.time() < deadline and not store["body"]:
                page.wait_for_timeout(700)
        except Exception:
            page.close()
            return None

        if not store["body"]:
            page.close()
            return None
        store["page"] = page   # giu page mo cho caller post() roi tu dong close
        return store

    def _post_reviews_page(self, page, base_vars: dict, page_no: int,
                           sorting: int) -> list:
        """Goi 1 trang review qua page.request.post() (dung session cua page).

        base_vars: payload mau lay tu request goc cua trang. Ta chi thay
        pageNo + sorting + pageSize. Tra ve list comment tho (co the rong).
        """
        rc = self.cfg["review_crawl"]
        api = self.cfg["base_url"] + rc["api_path"]
        payload = dict(base_vars)
        payload["pageNo"] = page_no
        payload["sorting"] = sorting
        payload["pageSize"] = rc["page_size"]
        try:
            resp = page.request.post(api, data=json.dumps(payload), headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Referer": self.cfg["base_url"] + "/",
            })
            if not resp.ok:
                return []
            body = resp.json()
        except Exception:
            return []
        return (P.safe(body, "commentList", "comments", default=[]) or [])

    def _collect_sort(self, page, base_vars, sorting, cap, seen, out,
                      seed_comments=None):
        """Lap phan trang 1 vong sort: them review (co text, chua trung) vao out
        toi khi du cap / het trang / cham tran max_pages. `seen` = set review_id.

        seed_comments: comment trang 1 da bat san (chi dung cho vong sort dau de
        khoi goi lai trang 1)."""
        rc = self.cfg["review_crawl"]
        require_content = rc.get("require_content", True)
        delay = rc.get("request_delay", [1.0, 2.5])

        for page_no in range(1, rc["max_pages_per_sort"] + 1):
            if len(out) >= cap:
                break
            if page_no == 1 and seed_comments is not None:
                comments = seed_comments
            else:
                comments = self._post_reviews_page(page, base_vars, page_no, sorting)
                time.sleep(random.uniform(*delay))
            if not comments:
                break   # het trang
            added = 0
            for c in comments:
                rid = c.get("hotelReviewId")
                if rid is None or rid in seen:
                    continue
                review = P.parse_review_comment(c)
                has_content = any((review.get(k) or "").strip()
                                  for k in ("text", "positives", "negatives"))
                if require_content and not has_content:
                    seen.add(rid)   # danh dau de khong xet lai, nhung khong luu
                    continue
                seen.add(rid)
                out.append(review)
                added += 1
                if len(out) >= cap:
                    break
            if added == 0 and page_no > 1:
                # trang co data nhung toan trung/khong text -> nhieu kha nang het moi
                continue

    def crawl_reviews(self, context, hotel: dict) -> tuple:
        """1 hotel -> (review_record, error).

        Huong C: mo trang lay seed (providerIds + comments trang 1 + payload
        mau) roi page.request.post() lap phan trang. Chien luoc 2 vong sort:
        vet review diem THAP truoc (sort_low_first), roi lap bang review MOI NHAT
        (sort_recent) toi khi du cap. Dedup theo review_id."""
        rc = self.cfg["review_crawl"]
        url = self._detail_url(hotel) or hotel.get("full_url")
        if not url:
            return None, "no slug/url"

        # Retry mo trang: 1 so KS tra response review rat muon/chap chon ->
        # thu lai toi seed_max_attempts lan (giong crawl_detail).
        attempts = rc.get("seed_max_attempts", 2)
        seed = None
        for _ in range(attempts):
            seed = self._capture_review_seed(context, url)
            if seed:
                break
        if not seed:
            return None, f"khong bat duoc response review (trang 1) sau {attempts} lan"
        page = seed["page"]
        comments_count = review_count = 0
        seed_comments, out = [], []
        hid = hotel.get("hotel_id") or (seed["body"] or {}).get("hotelId")
        hotel_name = hotel.get("name") or ""
        cap, tier = rc["cap_normal"], "unknown"
        try:
            body = seed["body"]
            comments_count = P.safe(body, "combinedReview", "score",
                                    "reviewCommentsCount", default=0) or 0
            review_count = P.safe(body, "combinedReview", "score",
                                  "reviewCount", default=0) or 0
            # bu tu file KS goc khi seed thieu (KS multi-provider hay rong so)
            if not review_count:
                review_count = hotel.get("review_count") or 0
            hid = hotel.get("hotel_id") or body.get("hotelId")
            hotel_name = body.get("hotelName") or hotel.get("name") or ""

            # payload mau tu request goc cua trang (co providerIds + token an)
            base_vars = {}
            if seed.get("req"):
                try:
                    base_vars = json.loads(seed["req"])
                except Exception:
                    base_vars = {}
            # fallback toi thieu neu khong doc duoc request goc
            if "hotelId" not in base_vars:
                base_vars = {
                    "hotelId": hid,
                    "hotelProviderId": P.safe(body, "combinedReview", "providers",
                                              default=[{}])[0].get("providerId", 332),
                    "demographicId": 0, "isReviewPage": False,
                    "isCrawlablePage": True, "paginationSize": 5,
                }

            # Dung review_count (tong) lam co so cap — KHONG dung comments_count
            # (so co text, nho hon) keo cap small chan som. Vong lap van tu dung
            # khi het trang that.
            cap, tier = self._cap_for(hid, review_count or comments_count)
            seen, out = set(), []
            seed_comments = P.safe(body, "commentList", "comments", default=[]) or []

            # vong 1: review diem thap (hiem, quy) — dung seed cho trang 1? KHONG,
            # vi seed la sort mac dinh (7); seed_comments chi tai dung khi sort khop.
            seed_sort = P.safe(body, "commentList", "selectedSortOption", default=None)
            self._collect_sort(page, base_vars, rc["sort_low_first"], cap, seen, out,
                               seed_comments=seed_comments
                               if seed_sort == rc["sort_low_first"] else None)
            # vong 2: lap phan con lai bang review moi nhat
            if len(out) < cap:
                self._collect_sort(page, base_vars, rc["sort_recent"], cap, seen, out,
                                   seed_comments=seed_comments
                                   if seed_sort == rc["sort_recent"] else None)
        finally:
            page.close()

        # 0 review nhung co dau hieu KS THUC SU co review => loi tool (post phan
        # trang lo / trang qua tai), KHONG phai KS rong. Tra error de retry.
        # comments_count cua Agoda thuong = 0 sai (vd 1176921/1179398) -> dung
        # them seed trang 1 + review_count (da bu tu file KS) lam tin hieu.
        if not out and (comments_count or len(seed_comments) or review_count):
            return None, (f"0 review nhung KS co review "
                          f"(comments_count={comments_count}, seed_trang1={len(seed_comments)}, "
                          f"review_count={review_count})")

        record = {
            "hotel_id": hid,
            "hotel_name": hotel_name,
            "source": self.site,
            "crawled_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
            "review_count_total": review_count,
            "comments_count_total": comments_count,
            "crawled_count": len(out),
            "cap_applied": cap,
            "cap_tier": tier,
            "sort_strategy": f"low_first({rc['sort_low_first']})+recent({rc['sort_recent']})",
            "reviews": out,
        }
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

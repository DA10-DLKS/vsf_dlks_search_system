"""base — interface chung cho moi spider site.

Moi site (Agoda, Booking, ...) hien thuc cac buoc:
  crawl_list      : tu khoa  -> danh sach hotel (id, ten, url_path)
  resolve_slugs   : bo sung slug/property_page cho tung hotel (neu can)
  crawl_detail    : 1 hotel  -> 1 record day du
  crawl_from_url  : 1 link   -> 1 record (bo qua list/resolve)

Nho do main.py dieu phoi 2 nhanh (tu khoa / link) ma khong can biet site nao.
"""
from abc import ABC, abstractmethod


class BaseSpider(ABC):
    #: ten site, trung voi ten file config <site>.yaml va key trong SPIDERS
    site = None

    def __init__(self, cfg: dict, headful: bool = False):
        self.cfg = cfg
        self.headful = headful

    # --- Nhanh tu khoa (batch) ---
    @abstractmethod
    def crawl_list(self, keyword: str) -> list:
        """Tu khoa -> list hotel dict (toi thieu co hotel_id, name)."""

    @abstractmethod
    def resolve_slugs(self, hotels: list) -> list:
        """Bo sung field can thiet de mo trang chi tiet (vd property_page)."""

    @abstractmethod
    def crawl_detail(self, context, hotel: dict):
        """1 hotel dict -> (record, error). Dung chung 1 browser context."""

    # --- Nhanh link (single) ---
    @abstractmethod
    def parse_url(self, url: str) -> dict:
        """1 link hotel -> hotel dict (hoac None neu khong parse duoc)."""

    @abstractmethod
    def is_site_url(self, url: str) -> bool:
        """URL co thuoc site nay khong (de main.py chon spider)."""

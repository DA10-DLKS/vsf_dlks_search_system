"""crawler — package crawl du lieu khach san da-site (Agoda, ...).

Cau truc:
  configs/   Layer 1: config crawl theo site (URL goc, endpoint, rate limit, filter)
  spiders/   Logic crawl theo site (BaseSpider -> AgodaSpider, ...)
  parsers/   Boc tach response tho cua tung site -> record sach
  browser.py Setup Playwright dung chung
  pipelines.py Luu/tach record, slugify, checkpoint
  main.py    Entry point: nhan dien link vs tu khoa
"""

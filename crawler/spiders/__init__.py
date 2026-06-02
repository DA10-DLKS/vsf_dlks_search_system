"""spiders — logic crawl theo tung site."""
from .base import BaseSpider
from .agoda import AgodaSpider

# Registry: ten site -> class spider (de main.py chon theo config/link)
SPIDERS = {
    "agoda": AgodaSpider,
}

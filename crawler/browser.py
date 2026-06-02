"""browser — setup Playwright dung chung cho moi spider.

Gom phan launch browser + new_context (lap o moi file cu) vao 1 context
manager, cau hinh tu config cua site (user_agent, locale, viewport).
"""
from contextlib import contextmanager

from playwright.sync_api import sync_playwright

_LAUNCH_ARGS = ["--disable-blink-features=AutomationControlled"]


@contextmanager
def browser_context(cfg: dict, headful: bool = False):
    """Mo browser + context theo config site. Tu dong dong khi thoat `with`.

    Dung:
        with browser_context(cfg, headful=False) as context:
            page = context.new_page()
            ...
    """
    vp = cfg.get("viewport", {}) or {}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not headful, args=_LAUNCH_ARGS)
        try:
            context = browser.new_context(
                user_agent=cfg.get("user_agent"),
                locale=cfg.get("locale", "vi-vn"),
                viewport={"width": vp.get("width", 1366),
                          "height": vp.get("height", 900)},
            )
            yield context
        finally:
            browser.close()

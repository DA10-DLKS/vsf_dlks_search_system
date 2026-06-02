"""configs — loader cho config crawl theo site (Layer 1).

Doc <site>.yaml trong thu muc nay -> tra ve dict. Cache de khong doc lai.
"""
import functools
import os

import yaml

_HERE = os.path.dirname(os.path.abspath(__file__))


@functools.lru_cache(maxsize=None)
def load_config(site: str) -> dict:
    """Doc configs/<site>.yaml -> dict. Loi neu khong ton tai."""
    path = os.path.join(_HERE, f"{site}.yaml")
    if not os.path.exists(path):
        available = [f[:-5] for f in os.listdir(_HERE) if f.endswith(".yaml")]
        raise FileNotFoundError(
            f"Khong co config cho site '{site}'. Co san: {available}")
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def available_sites() -> list:
    """Danh sach site co config (theo file .yaml)."""
    return sorted(f[:-5] for f in os.listdir(_HERE) if f.endswith(".yaml"))

from cachelib import BaseCache
from flask import current_app


def get_cache() -> BaseCache:
    return current_app.cache  # type: ignore

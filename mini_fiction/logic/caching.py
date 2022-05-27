from cachelib import BaseCache
from flask import current_app


def get_cache() -> BaseCache:
    # SAFETY: Proved by manually restricting cache instances
    return current_app.cache  # type: ignore

from cachelib import BaseCache
from flask import current_app  # noqa: I251
from jinja2 import Environment

from mini_fiction.settings import Config


def get_settings() -> Config:
    # SAFETY: Manually assigned during app initialization
    return current_app.settings  # type: ignore


def get_cache() -> BaseCache:
    # SAFETY: Proved by manually restricting cache instances
    return current_app.cache  # type: ignore


def get_jinja() -> Environment:
    # SAFETY: Assigned by Flask itself
    return current_app.jinja_env  # type: ignore

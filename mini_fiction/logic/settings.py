from flask import current_app

from mini_fiction.settings import Config


def get_settings() -> Config:
    # SAFETY: Manually assigned during app initialization
    return current_app.settings  # type: ignore

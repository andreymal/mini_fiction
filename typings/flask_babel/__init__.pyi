from flask_babel.speaklater import LazyString as LazyString  # type: ignore


def lazy_gettext(*args: str, **kwargs: str) -> LazyString: ...

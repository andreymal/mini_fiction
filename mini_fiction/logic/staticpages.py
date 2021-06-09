from flask import current_app, render_template
from flask_babel import lazy_gettext

from mini_fiction.logic.adminlog import log_addition, log_changed_fields, log_deletion
from mini_fiction.models import AnonymousUser, Author, StaticPage
from mini_fiction.validation import RawData, ValidationError, Validator
from mini_fiction.validation.staticpages import STATIC_PAGE

SYSTEM_PAGES = frozenset({"help", "terms", "robots.txt"})


def _is_system_page(static_page: StaticPage) -> bool:
    return static_page.name in SYSTEM_PAGES and static_page.lang == "none"


def create(author: Author, data: RawData) -> StaticPage:
    data = Validator(STATIC_PAGE).validated(data)

    if not author.is_superuser and data.get("is_template"):
        raise ValidationError({"is_template": [lazy_gettext("Access denied")]})

    if data.get("is_template"):
        check_renderability(author, data["name"], data["content"])

    if not data.get("lang"):
        data["lang"] = "none"

    exist_staticpage = StaticPage.get(name=data["name"], lang=data["lang"])
    if exist_staticpage:
        raise ValidationError({"name": [lazy_gettext("Page already exists")]})

    static_page = StaticPage(**data)
    static_page.flush()
    log_addition(by=author, what=static_page)
    return static_page


def update(static_page: StaticPage, author: Author, data: RawData) -> None:
    data = Validator(STATIC_PAGE).validated(data, update=True)

    if not author.is_superuser and (static_page.is_template or data.get("is_template")):
        raise ValidationError({"is_template": [lazy_gettext("Access denied")]})

    if ("name" in data and data["name"] != static_page.name) or (
        "lang" in data and data["lang"] != static_page.lang
    ):
        raise ValidationError(
            {
                "name": [lazy_gettext("Cannot change primary key")],
                "lang": [lazy_gettext("Cannot change primary key")],
            }
        )

    if data.get("is_template", static_page.is_template) and "content" in data:
        check_renderability(author, data.get("name", static_page.name), data["content"])

    changed_fields = set()
    for key, value in data.items():
        if getattr(static_page, key) != value:
            setattr(static_page, key, value)
            changed_fields |= {key}

    if changed_fields:
        log_changed_fields(by=author, what=static_page, fields=sorted(changed_fields))


def delete(static_page: StaticPage, author: Author) -> None:
    if _is_system_page(static_page):
        raise ValidationError(
            {"is_template": [lazy_gettext("This is system page, you cannot delete it")]}
        )
    if static_page.is_template and not author.is_superuser:
        raise ValidationError({"is_template": [lazy_gettext("Access denied")]})

    log_deletion(by=author, what=static_page)
    static_page.delete()


def check_renderability(author: Author, name: str, content: str) -> None:
    try:
        template = current_app.jinja_env.from_string(content)
        template.name = f"db/staticpages/{name}.html"
    except Exception as exc:
        raise ValidationError(
            {
                "content": [
                    lazy_gettext('Cannot parse static_page "{0}": {1}').format(
                        name, str(exc)
                    )
                ]
            }
        ) from exc

    try:
        render_template(template, staticpage_name=name, current_user=AnonymousUser())
    except Exception as exc:
        raise ValidationError(
            {
                "content": [
                    lazy_gettext(
                        'Cannot render static_page "{0}" for anonymous: {1}'
                    ).format(name, str(exc))
                ]
            }
        ) from exc

    try:
        render_template(template, staticpage_name=name, current_user=author)
    except Exception as exc:
        raise ValidationError(
            {
                "content": [
                    lazy_gettext('Cannot render static_page "{0}" for you: {1}').format(
                        name, str(exc)
                    )
                ]
            }
        ) from exc


def get_mimetype(static_page: StaticPage) -> str:
    if static_page.name == "robots.txt":
        return "text/plain"
    return "text/html"

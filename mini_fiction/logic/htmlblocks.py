from dataclasses import dataclass
from typing import Optional, Union

from flask import Markup, current_app, render_template
from flask_babel import lazy_gettext
from typing_extensions import TypedDict

from mini_fiction.logic.adminlog import log_addition, log_changed_fields, log_deletion
from mini_fiction.models import AnonymousUser, Author, HtmlBlock
from mini_fiction.utils.misc import call_after_request as later
from mini_fiction.validation import RawData, ValidationError, Validator
from mini_fiction.validation.htmlblocks import HTML_BLOCK


class HtmlBlockContext(TypedDict):
    htmlblock_name: str
    htmlblock_title: str
    current_user: Optional[Union[AnonymousUser, Author]]


@dataclass
class RenderedHtmlBlock:
    name: str = ""
    lang: str = "none"
    title: str = ""
    content: str = ""

    def __html__(self) -> Markup:
        return Markup(self.content)

    def __str__(self) -> str:
        return self.content


EMPTY_BLOCK = RenderedHtmlBlock()

ERROR_BLOCK = RenderedHtmlBlock(
    content='<span style="color: red; font-size: 1.5em; display: inline-block;">[ERROR]</span>'
)

DEFAULT_CONTEXT: HtmlBlockContext = {
    "htmlblock_name": "",
    "htmlblock_title": "",
    "current_user": None,
}


def create(author: Author, data: RawData) -> HtmlBlock:
    data = Validator(HTML_BLOCK).validated(data)

    if not author.is_superuser and data.get("is_template"):
        raise ValidationError({"is_template": [lazy_gettext("Access denied")]})

    if data.get("is_template"):
        check_renderability(author=author, name=data["name"], content=data["content"])

    if not data.get("lang"):
        data["lang"] = "none"

    exist_htmlblock = HtmlBlock.get(name=data["name"], lang=data["lang"])
    if exist_htmlblock:
        raise ValidationError({"name": [lazy_gettext("Block already exists")]})

    htmlblock = HtmlBlock(**data)
    htmlblock.flush()
    log_addition(by=author, what=htmlblock)
    later(clear_cache, htmlblock.name)
    return htmlblock


def update(htmlblock: HtmlBlock, author: Author, data: RawData) -> None:
    data = Validator(HTML_BLOCK).validated(data, update=True)

    if not author.is_superuser and (htmlblock.is_template or data.get("is_template")):
        raise ValidationError({"is_template": [lazy_gettext("Access denied")]})

    if ("name" in data and data["name"] != htmlblock.name) or (
        "lang" in data and data["lang"] != htmlblock.lang
    ):
        raise ValidationError(
            {
                "name": [lazy_gettext("Cannot change primary key")],
                "lang": [lazy_gettext("Cannot change primary key")],
            }
        )

    if data.get("is_template", htmlblock.is_template) and "content" in data:
        check_renderability(
            author=author,
            name=data.get("name", htmlblock.name),
            content=data["content"],
            htmlblock=htmlblock,
        )

    changed_fields = set()
    old_name = htmlblock.name

    for key, value in data.items():
        if getattr(htmlblock, key) != value:
            setattr(htmlblock, key, value)
            changed_fields |= {key}

    later(clear_cache, old_name)
    if htmlblock.name != old_name:
        later(clear_cache, htmlblock.name)

    if changed_fields:
        log_changed_fields(by=author, what=htmlblock, fields=sorted(changed_fields))


def delete(htmlblock: HtmlBlock, author: Author) -> None:
    if htmlblock.is_template and not author.is_superuser:
        raise ValidationError({"is_template": [lazy_gettext("Access denied")]})
    later(clear_cache, htmlblock.name)
    log_deletion(by=author, what=htmlblock)
    htmlblock.delete()


def clear_cache(name: str) -> None:
    for lang in current_app.config["LOCALES"]:
        cache_key = f"block_{lang}_{name}"
        current_app.cache.set(cache_key, None, 1)


def check_renderability(
    *,
    author: Author,
    name: str,
    content: str,
    htmlblock: Optional[HtmlBlock] = None,
) -> None:
    try:
        template = current_app.jinja_env.from_string(content)
        template.name = f"db/htmlblocks/{name}.html"
    except Exception as exc:
        raise ValidationError(
            {
                "content": [
                    lazy_gettext('Cannot parse htmlblock "{0}": {1}').format(
                        name, str(exc)
                    )
                ]
            }
        ) from exc

    if htmlblock:
        context = _render_context(htmlblock)
    else:
        context = DEFAULT_CONTEXT

    try:
        context["current_user"] = AnonymousUser()
        render_template(template, **context)
    except Exception as exc:
        raise ValidationError(
            {
                "content": [
                    lazy_gettext(
                        'Cannot render htmlblock "{0}" for anonymous: {1}'
                    ).format(name, str(exc))
                ]
            }
        ) from exc

    try:
        context["current_user"] = author
        render_template(template, **context)
    except Exception as exc:
        raise ValidationError(
            {
                "content": [
                    lazy_gettext('Cannot render htmlblock "{0}" for you: {1}').format(
                        name, str(exc)
                    )
                ]
            }
        ) from exc


def render_block(htmlblock: HtmlBlock) -> RenderedHtmlBlock:
    rendered_block = RenderedHtmlBlock(
        name=htmlblock.name,
        lang=htmlblock.lang,
        title=htmlblock.title,
        content=htmlblock.content,
    )
    if not htmlblock.is_template:
        return rendered_block

    template = current_app.jinja_env.from_string(htmlblock.content)
    template.name = f"db/htmlblocks/{htmlblock.name}.html"
    rendered_block.content = render_template(template, **_render_context(htmlblock))

    return rendered_block


def _render_context(htmlblock: HtmlBlock) -> HtmlBlockContext:
    return {
        "htmlblock_name": htmlblock.name,
        "htmlblock_title": htmlblock.title,
        "current_user": None,
    }

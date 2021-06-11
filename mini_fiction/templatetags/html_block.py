import traceback

from flask import current_app, g

from mini_fiction.logic import htmlblocks
from mini_fiction.logic.htmlblocks import RenderedHtmlBlock
from mini_fiction.models import HtmlBlock
from mini_fiction.templatetags import registry


@registry.simple_tag()
def html_block(name, ignore_missing=True):
    lang = g.locale.language

    cache_key = f'block_{lang}_{name}'
    rendered_block = current_app.cache.get(cache_key)

    if rendered_block is None or not isinstance(rendered_block, RenderedHtmlBlock):
        block = HtmlBlock.get(name=name, lang=g.locale.language)
        if not block:
            block = HtmlBlock.get(name=name, lang='none')

        try:
            if block:
                rendered_block = htmlblocks.render_block(block)
            else:
                rendered_block = None

        except Exception:
            current_app.logger.error('Cannot render htmlblock "{}"\n\n{}'.format(name, traceback.format_exc()))
            rendered_block = htmlblocks.ERROR_BLOCK

        else:
            if block and block.cache_time > 0:
                current_app.cache.set(cache_key, rendered_block, block.cache_time)

    if not rendered_block:
        if not ignore_missing:
            raise KeyError(name)  # TODO: refactor exceptions
        return htmlblocks.EMPTY_BLOCK

    return rendered_block

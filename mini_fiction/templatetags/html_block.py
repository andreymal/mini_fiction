#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import Markup, current_app, render_template, g

from mini_fiction.models import HtmlBlock
from mini_fiction.templatetags import registry


@registry.simple_tag()
def html_block(name, ignore_missing=True):
    cache_key = 'block_{}_{}'.format(g.locale.language, name)
    block_data = current_app.cache.get(cache_key)
    if block_data is None:
        block_data = {}
        block = HtmlBlock.get(name=name, lang=g.locale.language)
        if not block:
            block = HtmlBlock.get(name=name, lang='none')
        if block:
            block_data['lang'] = block.lang
            block_data['content'] = block.content
            block_data['is_template'] = block.is_template
        current_app.cache.set(cache_key, block_data, 7200)

    if not block_data:
        if not ignore_missing:
            raise KeyError(name)  # TODO: refactor exceptions
        return ''

    if block_data['is_template']:
        try:
            template = current_app.jinja_env.from_string(block_data['content'])
            template.name = 'db/htmlblocks/{}.html'.format(name)
            return Markup(render_template(template, htmlblock_name=name))
        except Exception:
            import traceback
            current_app.logger.error('Cannot render htmlblock "{}"\n\n{}'.format(name, traceback.format_exc()))
            return Markup('<span style="color: red; font-size: 2em">ERROR</span>')
    else:
        return Markup(block_data['content'])

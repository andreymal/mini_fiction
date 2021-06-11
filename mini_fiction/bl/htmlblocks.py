#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# pylint: disable=unexpected-keyword-arg,no-value-for-parameter

from flask import Markup, current_app, render_template
from flask_babel import lazy_gettext

from mini_fiction.bl.utils import BaseBL
from mini_fiction.logic.adminlog import log_addition, log_changed_fields, log_deletion
from mini_fiction.utils.misc import call_after_request as later
from mini_fiction.validation import Validator, ValidationError
from mini_fiction.validation.htmlblocks import HTML_BLOCK


class HtmlBlockBL(BaseBL):
    def create(self, author, data):
        data = Validator(HTML_BLOCK).validated(data)

        if not author.is_superuser and data.get('is_template'):
            raise ValidationError({'is_template': [lazy_gettext('Access denied')]})

        if data.get('is_template'):
            self.check_renderability(author, data['name'], data['content'])

        if not data.get('lang'):
            data['lang'] = 'none'

        exist_htmlblock = self.model.get(name=data['name'], lang=data['lang'])
        if exist_htmlblock:
            raise ValidationError({'name': [lazy_gettext('Block already exists')]})

        htmlblock = self.model(**data)
        htmlblock.flush()
        log_addition(by=author, what=htmlblock)
        later(self.clear_cache, htmlblock.name)  # avoid race condition by `later` (runs after commit)
        return htmlblock

    def update(self, author, data):
        data = Validator(HTML_BLOCK).validated(data, update=True)
        htmlblock = self.model

        if not author.is_superuser and (htmlblock.is_template or data.get('is_template')):
            raise ValidationError({'is_template': [lazy_gettext('Access denied')]})

        if ('name' in data and data['name'] != htmlblock.name) or ('lang' in data and data['lang'] != htmlblock.lang):
            raise ValidationError({
                'name': [lazy_gettext('Cannot change primary key')],
                'lang': [lazy_gettext('Cannot change primary key')],
            })

        if data.get('is_template', htmlblock.is_template) and 'content' in data:
            self.check_renderability(author, data.get('name', htmlblock.name), data['content'])

        changed_fields = set()
        old_name = htmlblock.name

        for key, value in data.items():
            if getattr(htmlblock, key) != value:
                setattr(htmlblock, key, value)
                changed_fields |= {key,}

        later(self.clear_cache, old_name)
        if htmlblock.name != old_name:
            later(self.clear_cache, htmlblock.name)

        if changed_fields:
            log_changed_fields(by=author, what=htmlblock, fields=sorted(changed_fields))

        return htmlblock

    def delete(self, author):
        htmlblock = self.model
        if htmlblock.is_template and not author.is_superuser:
            raise ValidationError({'is_template': [lazy_gettext('Access denied')]})
        later(self.clear_cache, htmlblock.name)
        log_deletion(by=author, what=htmlblock)
        htmlblock.delete()

    def clear_cache(self, name):
        for lang in current_app.config['LOCALES']:
            cache_key = 'block_{}_{}'.format(lang, name)
            current_app.cache.set(cache_key, None, 1)

    def check_renderability(self, author, name, content):
        try:
            template = current_app.jinja_env.from_string(content)
            template.name = 'db/htmlblocks/{}.html'.format(name)
        except Exception as exc:
            raise ValidationError({'content': [
                lazy_gettext('Cannot parse htmlblock "{0}": {1}').format(name, str(exc))
            ]})

        from mini_fiction.models import AnonymousUser

        context = self._render_context()

        try:
            context['current_user'] = AnonymousUser()
            render_template(template, **context)
        except Exception as exc:
            raise ValidationError({'content': [
                lazy_gettext('Cannot render htmlblock "{0}" for anonymous: {1}').format(name, str(exc))
            ]})

        try:
            context['current_user'] = author
            render_template(template, **context)
        except Exception as exc:
            raise ValidationError({'content': [
                lazy_gettext('Cannot render htmlblock "{0}" for you: {1}').format(name, str(exc))
            ]})

    def render(self) -> 'RenderedHtmlBlock':
        htmlblock = self.model

        rendered_block = RenderedHtmlBlock(
            name=htmlblock.name,
            lang=htmlblock.lang,
            title=htmlblock.title,
            content=htmlblock.content,
        )
        if not htmlblock.is_template:
            return rendered_block

        template = current_app.jinja_env.from_string(htmlblock.content)
        template.name = 'db/htmlblocks/{}.html'.format(htmlblock.name)
        rendered_block.content = render_template(template, **self._render_context())

        return rendered_block

    def _render_context(self):
        htmlblock = self.model
        return {
            'htmlblock_name': htmlblock.name,
            'htmlblock_title': htmlblock.title,
        }


class RenderedHtmlBlock:
    def __init__(self, name: str, lang: str, title: str, content: str):
        self.name = name
        self.lang = lang
        self.title = title
        self.content = content

    @staticmethod
    def empty() -> 'RenderedHtmlBlock':
        return RenderedHtmlBlock(
            name='',
            lang='none',
            title='',
            content='',
        )

    @staticmethod
    def error() -> 'RenderedHtmlBlock':
        return RenderedHtmlBlock(
            name='',
            lang='none',
            title='',
            content='<span style="color: red; font-size: 1.5em; display: inline-block;">[ERROR]</span>',
        )

    def __repr__(self):
        return f"<RenderedHtmlBlock name={self.name!r} lang={self.lang!r}>"

    def __str__(self):
        return self.content

    def __html__(self):
        return Markup(self.content)

#!/usr/bin/env python
# -*- coding: utf-8 -*-

# pylint: disable=unexpected-keyword-arg,no-value-for-parameter

from flask import current_app, render_template
from flask_babel import lazy_gettext

from mini_fiction.bl.utils import BaseBL
from mini_fiction.utils.misc import call_after_request as later
from mini_fiction.validation import Validator, ValidationError
from mini_fiction.validation.htmlblocks import HTML_BLOCK


class HtmlBlockBL(BaseBL):
    def create(self, author, data):
        from mini_fiction.models import AdminLog

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
        AdminLog.bl.create(user=author, obj=htmlblock, action=AdminLog.ADDITION)
        later(self.clear_cache, htmlblock.name)  # avoid race condition by `later` (runs after commit)
        return htmlblock

    def update(self, author, data):
        from mini_fiction.models import AdminLog

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
            AdminLog.bl.create(
                user=author,
                obj=htmlblock,
                action=AdminLog.CHANGE,
                fields=sorted(changed_fields),
            )

        return htmlblock

    def delete(self, author):
        from mini_fiction.models import AdminLog

        htmlblock = self.model
        if htmlblock.is_template and not author.is_superuser:
            raise ValidationError({'is_template': [lazy_gettext('Access denied')]})
        later(self.clear_cache, htmlblock.name)
        AdminLog.bl.create(user=author, obj=htmlblock, action=AdminLog.DELETION)
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

        try:
            render_template(template, htmlblock_name=name, current_user=AnonymousUser())
        except Exception as exc:
            raise ValidationError({'content': [
                lazy_gettext('Cannot render htmlblock "{0}" for anonymous: {1}').format(name, str(exc))
            ]})

        try:
            render_template(template, htmlblock_name=name, current_user=author)
        except Exception as exc:
            raise ValidationError({'content': [
                lazy_gettext('Cannot render htmlblock "{0}" for you: {1}').format(name, str(exc))
            ]})
